"""Client MediaWiki / Wikidata poli, avec cache SQLite et limitation de debit.

Principes :
- une requete a la fois, avec une pause entre deux appels ;
- reponses mises en cache sur disque (data/raw/cache.sqlite) : relancer un script
  ne retelecharge jamais ce qui a deja ete obtenu ;
- respect de maxlag, de Retry-After et des erreurs 429/5xx (reessais espaces).
Aucune dependance externe (bibliotheque standard uniquement).
"""
from __future__ import annotations

import hashlib
import os
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "PartisFrGraph/0.1 (projet personnel non commercial, graphe de l'histoire des "
    "partis francais; requetes sequentielles, mises en cache)"
)
FR_API = "https://fr.wikipedia.org/w/api.php"
WD_SPARQL = "https://query.wikidata.org/sparql"
WD_API = "https://www.wikidata.org/w/api.php"

MIN_DELAY = 1.1  # secondes entre deux requetes reseau


class Client:
    def __init__(self, cache_path: Path | None = None):
        self.db = sqlite3.connect(str(cache_path or RAW / "cache.sqlite"))
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v BLOB, ts REAL)"
        )
        self._last = 0.0
        self.net_calls = 0
        self.cache_hits = 0
        # PARTIS_FRESH=1 : ignorer le cache en lecture (les reponses neuves le remplacent).
        # Sert aux mises a jour (run_update.py) ; la copie locale reste utilisable hors ligne.
        self.fresh = os.environ.get("PARTIS_FRESH") == "1"

    # -- cache ---------------------------------------------------------
    @staticmethod
    def _key(url: str, params: dict) -> str:
        blob = url + "?" + urllib.parse.urlencode(sorted(params.items()), doseq=True)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()

    def _get_cached(self, k: str):
        row = self.db.execute("SELECT v FROM cache WHERE k=?", (k,)).fetchone()
        if row:
            self.cache_hits += 1
            return json.loads(zlib.decompress(row[0]).decode("utf-8"))
        return None

    def _put(self, k: str, obj) -> None:
        raw = zlib.compress(json.dumps(obj, ensure_ascii=False).encode("utf-8"), 6)
        self.db.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?,?)", (k, raw, time.time())
        )
        self.db.commit()

    # -- reseau --------------------------------------------------------
    def _throttle(self):
        wait = MIN_DELAY - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)

    def _fetch(self, req: urllib.request.Request, timeout: int = 90):
        delay = 5.0
        for attempt in range(9):
            self._throttle()
            try:
                self._last = time.time()
                self.net_calls += 1
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504):
                    ra = e.headers.get("Retry-After")
                    pause = float(ra) if ra and ra.isdigit() else delay
                    time.sleep(min(pause, 120))
                    delay = min(delay * 2, 120)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(delay)
                delay = min(delay * 2, 120)
        raise RuntimeError("echec persistant : " + req.full_url[:200])

    # -- API MediaWiki ---------------------------------------------------
    def mw(self, params: dict, api: str = FR_API, use_cache: bool = True):
        p = dict(params)
        p.setdefault("format", "json")
        p.setdefault("formatversion", "2")
        p.setdefault("maxlag", "5")
        k = self._key(api, p)
        if use_cache and not self.fresh:
            hit = self._get_cached(k)
            if hit is not None:
                return hit
        body = urllib.parse.urlencode(p, doseq=True).encode("utf-8")
        req = urllib.request.Request(
            api, data=body, headers={"User-Agent": USER_AGENT}
        )
        obj = self._fetch(req)
        if isinstance(obj, dict) and obj.get("error", {}).get("code") == "maxlag":
            time.sleep(10)
            return self.mw(params, api, use_cache)
        self._put(k, obj)
        return obj

    def mw_continue(self, params: dict, api: str = FR_API):
        """Parcourt toutes les pages de resultats d'une requete 'continue'."""
        p = dict(params)
        while True:
            obj = self.mw(p, api)
            yield obj
            cont = obj.get("continue")
            if not cont:
                return
            p = {**params, **cont}

    # -- SPARQL ----------------------------------------------------------
    def sparql(self, query: str):
        params = {"query": query, "format": "json"}
        k = self._key(WD_SPARQL, params)
        hit = None if self.fresh else self._get_cached(k)
        if hit is not None:
            return hit
        url = WD_SPARQL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
        )
        obj = self._fetch(req, timeout=180)
        self._put(k, obj)
        return obj


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]
