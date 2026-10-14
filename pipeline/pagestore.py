"""Stockage local des pages Wikipedia (wikitexte brut + resume en texte clair).

Une base SQLite (data/raw/pages.sqlite) contient, par page :
  - le titre canonique (apres redirection), l'identifiant Wikidata, la revision ;
  - le wikitexte (page entiere ou section 0 seulement : introduction + infobox) ;
  - le resume en texte clair (introduction).
Sert de copie locale : on ne retelecharge jamais une page deja presente.
"""
from __future__ import annotations

import sqlite3
import time
import zlib

from wikiclient import RAW, Client, chunks

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
  title TEXT PRIMARY KEY,
  pageid INTEGER, revid INTEGER, rev_ts TEXT, qid TEXT,
  scope TEXT,               -- 'full' ou 'lead'
  wikitext BLOB, intro BLOB,
  fetched REAL
);
CREATE TABLE IF NOT EXISTS redirects (src TEXT PRIMARY KEY, dst TEXT);
CREATE TABLE IF NOT EXISTS missing (title TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS cats (title TEXT, cat TEXT);
CREATE TABLE IF NOT EXISTS cats_done (title TEXT PRIMARY KEY);
"""


class PageStore:
    def __init__(self, client: Client, path=None):
        self.c = client
        self.db = sqlite3.connect(str(path or RAW / "pages.sqlite"))
        self.db.executescript(SCHEMA)

    # -- lecture ---------------------------------------------------------
    def resolve(self, title: str) -> str:
        r = self.db.execute("SELECT dst FROM redirects WHERE src=?", (title,)).fetchone()
        return r[0] if r else title

    def has(self, title: str, scope: str | None = None) -> bool:
        t = self.resolve(title)
        r = self.db.execute("SELECT scope FROM pages WHERE title=?", (t,)).fetchone()
        if not r:
            return False
        if scope == "full":
            return r[0] == "full"
        return True

    def is_missing(self, title: str) -> bool:
        return self.db.execute("SELECT 1 FROM missing WHERE title=?", (title,)).fetchone() is not None

    def get(self, title: str):
        t = self.resolve(title)
        r = self.db.execute(
            "SELECT title,pageid,revid,rev_ts,qid,scope,wikitext,intro FROM pages WHERE title=?",
            (t,),
        ).fetchone()
        if not r:
            return None
        return {
            "title": r[0],
            "pageid": r[1],
            "revid": r[2],
            "rev_ts": r[3],
            "qid": r[4],
            "scope": r[5],
            "wikitext": zlib.decompress(r[6]).decode("utf-8") if r[6] else "",
            "intro": zlib.decompress(r[7]).decode("utf-8") if r[7] else "",
        }

    def all_titles(self, scope=None):
        q = "SELECT title FROM pages" + (" WHERE scope=?" if scope else "")
        return [r[0] for r in self.db.execute(q, (scope,) if scope else ())]

    # -- redirections ----------------------------------------------------
    def resolve_redirects(self, titles, batch=50):
        """Resout (sans telecharger le contenu) les redirections d'une liste de titres."""
        todo = [t for t in dict.fromkeys(titles)
                if not self.db.execute("SELECT 1 FROM redirects WHERE src=?", (t,)).fetchone()
                and not self.db.execute("SELECT 1 FROM pages WHERE title=?", (t,)).fetchone()
                and not self.is_missing(t)]
        for b in chunks(todo, batch):
            obj = self.c.mw({"action": "query", "titles": "|".join(b), "redirects": "1"})
            q = obj.get("query", {})
            for r in q.get("normalized", []) + q.get("redirects", []):
                self.db.execute("INSERT OR REPLACE INTO redirects VALUES (?,?)", (r["from"], r["to"]))
            for p in q.get("pages", []):
                if p.get("missing"):
                    self.db.execute("INSERT OR REPLACE INTO missing VALUES (?)", (p["title"],))
            self.db.commit()
        return len(todo)

    # -- categories ------------------------------------------------------
    def fetch_categories(self, titles, batch=50):
        todo = [t for t in dict.fromkeys(self.resolve(x) for x in titles)
                if not self.db.execute("SELECT 1 FROM cats_done WHERE title=?", (t,)).fetchone()]
        for b in chunks(todo, batch):
            seen = set()
            for o in self.c.mw_continue({
                "action": "query", "prop": "categories", "titles": "|".join(b),
                "cllimit": "max", "clshow": "!hidden", "redirects": "1",
            }):
                for p in o["query"].get("pages", []):
                    seen.add(p["title"])
                    for cat in p.get("categories", []):
                        self.db.execute("INSERT INTO cats VALUES (?,?)", (p["title"], cat["title"]))
            for t in b:
                self.db.execute("INSERT OR REPLACE INTO cats_done VALUES (?)", (t,))
            self.db.commit()
        return len(todo)

    def categories(self, title):
        t = self.resolve(title)
        return [r[0] for r in self.db.execute("SELECT cat FROM cats WHERE title=?", (t,))]

    # -- ecriture --------------------------------------------------------
    def fetch(self, titles, scope="full", batch=20, progress=True):
        """Telecharge les pages absentes. scope='lead' : section 0 seulement."""
        todo = []
        for t in titles:
            if self.is_missing(t):
                continue
            if self.has(t, "full" if scope == "full" else None):
                continue
            todo.append(t)
        todo = list(dict.fromkeys(todo))
        done = 0
        t0 = time.time()
        for b in chunks(todo, batch):
            params = {
                "action": "query",
                "titles": "|".join(b),
                "redirects": "1",
                "prop": "revisions|extracts|pageprops",
                "rvprop": "content|ids|timestamp",
                "rvslots": "main",
                "exintro": "1",
                "explaintext": "1",
                "exlimit": str(batch),
                "ppprop": "wikibase_item",
            }
            if scope == "lead":
                params["rvsection"] = "0"
            obj = self.c.mw(params)
            q = obj.get("query", {})
            for r in q.get("redirects", []):
                self.db.execute("INSERT OR REPLACE INTO redirects VALUES (?,?)", (r["from"], r["to"]))
            for n in q.get("normalized", []):
                self.db.execute("INSERT OR REPLACE INTO redirects VALUES (?,?)", (n["from"], n["to"]))
            got = set()
            for p in q.get("pages", []):
                if p.get("missing") or "revisions" not in p:
                    self.db.execute("INSERT OR REPLACE INTO missing VALUES (?)", (p["title"],))
                    continue
                rev = p["revisions"][0]
                wt = rev["slots"]["main"].get("content", "")
                if scope == "lead":
                    cur = self.db.execute("SELECT scope FROM pages WHERE title=?", (p["title"],)).fetchone()
                    if cur and cur[0] == "full":
                        continue  # ne jamais ecraser une page complete par une introduction
                self.db.execute(
                    "INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        p["title"],
                        p.get("pageid"),
                        rev.get("revid"),
                        rev.get("timestamp"),
                        p.get("pageprops", {}).get("wikibase_item"),
                        scope,
                        zlib.compress(wt.encode("utf-8"), 6),
                        zlib.compress((p.get("extract") or "").encode("utf-8"), 6),
                        time.time(),
                    ),
                )
                got.add(p["title"])
            self.db.commit()
            done += len(b)
            if progress and (done // batch) % 10 == 0:
                print(f"   {done}/{len(todo)} pages ({time.time()-t0:.0f}s)", flush=True)
        return len(todo)
