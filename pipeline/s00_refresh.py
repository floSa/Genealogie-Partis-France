"""Etape 0 - Mise a jour incrementale de la copie locale.

Compare, par lots de 50 titres, la derniere revision de chaque page stockee sur Wikipedia avec
celle de la copie locale (une seule requete `prop=info` par lot), puis ne retelecharge que les
pages modifiees. Quelques dizaines de requetes suffisent, au lieu de recharger tout le corpus.

Ecrit data/raw/refresh_report.json (pages verifiees, modifiees, disparues) lu par s09_diff_builds.py.
Les categories des pages modifiees sont effacees pour etre relues.
"""
from __future__ import annotations

import datetime
import json

from client_shortcuts import store
from wikiclient import RAW, Client, chunks


def main():
    c = Client()
    ps = store(c)
    revs = ps.stored_revisions()
    print("pages stockees:", len(revs), flush=True)
    changed, gone = [], []
    for b in chunks(sorted(revs), 50):
        o = c.mw({"action": "query", "prop": "info", "titles": "|".join(b)}, use_cache=False)
        for p in o["query"]["pages"]:
            t = p["title"]
            if p.get("missing"):
                gone.append(t)
            elif t in revs and p.get("lastrevid") != revs[t][0]:
                changed.append(t)
    full = [t for t in changed if revs[t][1] == "full"]
    lead = [t for t in changed if revs[t][1] == "lead"]
    print(f"modifiees: {len(changed)} (completes {len(full)}, introductions {len(lead)}); disparues: {len(gone)}", flush=True)
    if full:
        ps.fetch(full, scope="full", batch=20, progress=False, force=True)
    if lead:
        ps.fetch(lead, scope="lead", batch=20, progress=False, force=True)
    ps.forget_categories(changed)
    for t in gone:
        ps.db.execute("INSERT OR REPLACE INTO missing VALUES (?)", (t,))
        ps.db.execute("DELETE FROM pages WHERE title=?", (t,))
    ps.db.commit()
    report = {
        "date": datetime.date.today().isoformat(),
        "checked": len(revs),
        "changed": sorted(changed),
        "gone": sorted(gone),
    }
    (RAW / "refresh_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("rapport: data/raw/refresh_report.json")


if __name__ == "__main__":
    main()
