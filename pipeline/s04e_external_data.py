"""Etape 4e - Donnees externes : resultats electoraux, sieges et positions d'experts.

Sources (telechargement libre, sans compte) :
  ParlGov   https://www.parlgov.org/data/parlgov-development_csv-utf-8/   (legislatives et europeennes :
            voix, sieges ; position gauche-droite composite, echelle 0-10)
  CHES      Chapel Hill Expert Survey, fichier de tendance 1999-2024 (position gauche-droite 'lrgen',
            economique 'lrecon', societale 'galtan', echelle 0-10, par annee d'enquete)

Rapprochement avec nos organisations : page Wikipedia anglaise de ParlGov -> identifiant Wikidata
(un appel par lot de 50) -> notre organisation ; repli par sigle. CHES est relie a ParlGov par l'identifiant
Manifesto (cmp), repli par sigle. Les fichiers sont gardes dans data/external/ (versionnes avec les donnees).

Sorties : data/graph/external_raw.json, data/review/externes_non_rapproches.csv
"""
from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict

from wikiclient import ROOT, USER_AGENT, WD_API, Client, chunks

EXT = ROOT / "data" / "external"
OUT = ROOT / "data" / "graph" / "external_raw.json"
PG = "https://www.parlgov.org/data/parlgov-development_csv-utf-8/"
CHES_TREND = "https://github.com/chesdata/chesdata.github.io/releases/download/ches-trend/1999-2024_CHES_dataset_meansV2.csv"
FILES = {
    "view_party.csv": PG + "view_party.csv",
    "party.csv": PG + "party.csv",
    "view_election.csv": PG + "view_election.csv",
    "ches_trend_1999_2024.csv": CHES_TREND,
}


def download():
    EXT.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        path = EXT / name
        if path.exists() and os.environ.get("PARTIS_FRESH") != "1":
            continue
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
        print("telecharge", name, path.stat().st_size, "octets", flush=True)


def rows(name):
    with (EXT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def key(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def to_scale(x):
    """Echelle 0-10 (0 gauche, 10 droite) -> echelle du graphe (-3 extreme gauche ... +3 extreme droite)."""
    return round((float(x) - 5) * 0.6, 2)


def main():
    download()
    c = Client()
    # organisations candidates : toutes les pages de partis analysees (s03) ; s05 ne gardera que les retenues
    orgs = [{"title": r["title"], "qid": r.get("qid"), "abbreviations": r.get("abbreviations", []),
             "infobox": r["has_infobox"]}
            for r in json.loads((ROOT / "data" / "graph" / "parties_raw.json").read_text(encoding="utf-8"))]
    by_qid = {n["qid"]: n for n in orgs if n.get("qid")}
    by_abbr = defaultdict(list)
    for n in orgs:
        if not n["infobox"]:
            continue  # le rapprochement par sigle est reserve aux pages de partis (infobox)
        for a in n["abbreviations"]:
            by_abbr[key(a)].append(n)

    pg_party = {p["party_id"]: p for p in rows("view_party.csv") if p["country_name_short"] == "FRA"}
    wiki = {p["id"]: p["wikipedia"] for p in rows("party.csv") if p["id"] in pg_party}
    # titre Wikipedia anglais -> identifiant Wikidata
    titles = {}
    for pid, url in wiki.items():
        if url:
            titles[pid] = urllib.parse.unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")
    qid_of = {}
    for b in chunks(sorted(set(titles.values())), 50):
        o = c.mw({"action": "wbgetentities", "sites": "enwiki", "titles": "|".join(b), "props": "sitelinks",
                  "sitefilter": "enwiki"}, api=WD_API)
        for q, ent in o.get("entities", {}).items():
            t = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
            if t and q.startswith("Q"):
                qid_of[t] = q

    ov = json.loads((ROOT / "data" / "overrides.json").read_text(encoding="utf-8")).get("external_matches", {})
    by_title = {n["title"]: n for n in orgs}
    match, how, unmatched = {}, {}, []
    for pid, p in pg_party.items():
        n = by_qid.get(qid_of.get(titles.get(pid, "")))
        h = "wikidata"
        if not n:
            cand = by_abbr.get(key(p["party_name_short"]), [])
            n, h = (cand[0], "sigle") if len(cand) == 1 else (None, "")
        if not n and p["party_name_short"] in ov.get("parlgov", {}):
            n, h = by_title.get(ov["parlgov"][p["party_name_short"]]), "manuel"
        if n:
            match[pid], how[pid] = n, h
        else:
            unmatched.append(("ParlGov", p["party_name_short"], p["party_name_english"], p["party_id"]))

    ext = {}

    def slot(n):
        return ext.setdefault(n["title"], {"parlgov_id": None, "parlgov_left_right": None, "elections": [], "ches": [],
                                           "matched_by": None})

    for pid, n in match.items():
        s = slot(n)
        s["parlgov_id"], s["matched_by"] = pid, how[pid]
        lr = pg_party[pid].get("left_right")
        if lr:
            s["parlgov_left_right"] = to_scale(lr)
    for r in rows("view_election.csv"):
        if r["country_name_short"] != "FRA" or r["party_id"] not in match or not r["election_date"] >= "1958":
            continue
        s = slot(match[r["party_id"]])
        s["elections"].append({
            "date": r["election_date"], "type": r["election_type"],
            "vote_share": float(r["vote_share"]) if r["vote_share"] else None,
            "seats": int(float(r["seats"])) if r["seats"] else None,
            "seats_total": int(float(r["seats_total"])) if r["seats_total"] else None,
        })
    # CHES : lien par l'identifiant Manifesto (cmp), repli par sigle
    cmp_to_pg = {p["cmp"]: pid for pid, p in pg_party.items() if p.get("cmp")}
    abbr_to_pg = defaultdict(list)
    for pid, p in pg_party.items():
        abbr_to_pg[key(p["party_name_short"])].append(pid)
    n_ches = 0
    for r in rows("ches_trend_1999_2024.csv"):
        if r.get("country") not in ("fra", "FRA", "6", "France"):
            continue
        pid = cmp_to_pg.get(r.get("cmp_id") or "")
        h = "cmp"
        if not pid:
            cand = abbr_to_pg.get(key(r["party"]), [])
            pid, h = (cand[0], "sigle") if len(cand) == 1 else (None, "")
        target = match.get(pid) if pid else None
        if not target and r["party"] in ov.get("ches", {}):
            target, h = by_title.get(ov["ches"][r["party"]]), "manuel"
        if not target:
            unmatched.append(("CHES", r["party"], r.get("party_name") or "", r.get("cmp_id") or ""))
            continue
        if not r.get("lrgen"):
            continue
        s = slot(target)
        s["ches"].append({
            "year": int(r["year"]), "lrgen": to_scale(r["lrgen"]),
            "lrecon": to_scale(r["lrecon"]) if r.get("lrecon") else None,
            "galtan": to_scale(r["galtan"]) if r.get("galtan") else None,
            "party": r["party"], "link": h,
        })
        n_ches += 1
    for s in ext.values():
        s["elections"].sort(key=lambda e: e["date"])
        s["ches"].sort(key=lambda e: e["year"])
    OUT.write_text(json.dumps(ext, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "data" / "review").mkdir(exist_ok=True)
    with (ROOT / "data" / "review" / "externes_non_rapproches.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["source", "sigle", "nom", "identifiant"])
        w.writerows(sorted(set(unmatched)))
    print(f"ParlGov : {len(pg_party)} partis francais, {len(match)} rapproches ({sum(1 for h in how.values() if h=='wikidata')} par Wikidata, "
          f"{sum(1 for h in how.values() if h=='sigle')} par sigle) ; CHES : {n_ches} mesures ; "
          f"organisations enrichies : {len(ext)} ; non rapproches : {len(set(unmatched))}")


if __name__ == "__main__":
    main()
