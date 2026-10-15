"""Etape 7 - Export du graphe vers le site statique (site/data.js).

Le site s'ouvre en double-cliquant sur site/index.html : pas de serveur, pas de dependance
externe. Comme un navigateur interdit de lire un fichier JSON local depuis un fichier local, les
donnees sont ecrites dans un script (`window.GRAPH = {...}`).
Les champs sont raccourcis pour limiter la taille du fichier.
"""
from __future__ import annotations

import json

from wikiclient import ROOT

G = ROOT / "data" / "graph"
SITE = ROOT / "site"


def main():
    nodes = json.loads((G / "nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((G / "edges.json").read_text(encoding="utf-8"))
    import datetime
    import sqlite3

    db = sqlite3.connect(str(ROOT / "data" / "raw" / "pages.sqlite"))
    last_rev = db.execute("SELECT MAX(rev_ts), MIN(fetched), MAX(fetched) FROM pages").fetchone()
    meta = {
        "generated": datetime.date.today().isoformat(),
        "wikipedia_last_revision": last_rev[0],
        "collected_from": datetime.datetime.fromtimestamp(last_rev[1]).date().isoformat() if last_rev[1] else None,
        "collected_to": datetime.datetime.fromtimestamp(last_rev[2]).date().isoformat() if last_rev[2] else None,
    }

    orgs, people = [], []
    for n in nodes:
        if n["type"] == "org":
            orgs.append(
                {
                    "id": n["id"], "n": n["name"], "t": n["title"], "ab": n["abbreviations"], "k": n["kind"],
                    "s": n["start"], "e": n["end"], "st": n["status"], "sc": n["scope"],
                    "pv": n["position_value"], "ps": n["position_source"], "pc": n["position_codes"], "fam": n["families"],
                    "tier": n["tier"], "per": n["peripheral"], "sl": n["sitelinks"], "imp": n["importance"],
                    "sum": n["summary"], "url": n["url"], "fl": n["flags"], "np": n.get("persons_linked", 0),
                    "ideo": n["ideologies"][:6], "nc": n.get("name_changes", []),
                }
            )
        else:
            people.append(
                {
                    "id": n["id"], "n": n["name"], "t": n["title"], "b": n["born"], "d": n["died"],
                    "sum": n["summary"], "url": n["url"], "tier": n["tier"], "imp": n["importance"], "sl": n["sitelinks"],
                }
            )
    oe, pe = [], []
    for e in edges:
        if e["layer"] == "org_org":
            oe.append({"ty": e["type"], "s": e["source"], "t": e["target"], "d": e.get("date"),
                       "st": e.get("start"), "en": e.get("end"), "c": 1 if e["confidence"].startswith("confirmee") else 0,
                       "dc": 1 if e.get("declared_by_source") else 0,
                       "w": 1 if "wikidata" in e["confidence"] else 0})
        else:
            pe.append({"p": e["source"], "o": e["target"], "r": e["type"], "s": e["start"], "e": e["end"],
                       "l": (e.get("label") or "")[:90]})
    data = {"orgs": orgs, "people": people, "orgEdges": oe, "personEdges": pe, "meta": meta}
    SITE.mkdir(exist_ok=True)
    out = "window.GRAPH = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (SITE / "data.js").write_text(out, encoding="utf-8")
    print(f"site/data.js : {len(out)/1e6:.2f} Mo ; {len(orgs)} organisations, {len(people)} personnes, "
          f"{len(oe)} relations, {len(pe)} liens personne-organisation")


if __name__ == "__main__":
    main()
