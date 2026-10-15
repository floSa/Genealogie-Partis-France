"""Etape 4c - Relations de filiation declarees dans Wikidata entre partis francais.

Une seule requete SPARQL : pour les partis francais, les proprietes
  P155 / P1365  (suit / remplace)            P156 / P1366 (suivi par / remplace par)
  P807          (separe de)
Wikidata en renseigne peu (une vingtaine de successions), mais chacune est une seconde source
independante de Wikipedia : s05 s'en sert pour confirmer des relations (confiance
'confirmee_page_et_wikidata') et pour en ajouter quelques-unes absentes des infobox.

Sortie : data/raw/wd_relations.json
"""
from __future__ import annotations

import json

from wikiclient import RAW, Client

QUERY = """
SELECT ?a ?prop ?b WHERE {
  ?a wdt:P31/wdt:P279* wd:Q7278; wdt:P17 wd:Q142.
  ?a ?p ?b.
  FILTER(?p IN (wdt:P155, wdt:P156, wdt:P1365, wdt:P1366, wdt:P807))
  BIND(REPLACE(STR(?p), '.*/', '') AS ?prop)
}"""


def main():
    c = Client()
    rows = c.sparql(QUERY)["results"]["bindings"]
    rels = []
    for b in rows:
        a = b["a"]["value"].rsplit("/", 1)[1]
        o = b["b"]["value"].rsplit("/", 1)[1]
        rels.append({"a": a, "prop": b["prop"]["value"], "b": o})
    (RAW / "wd_relations.json").write_text(json.dumps({"relations": rels}, ensure_ascii=False), encoding="utf-8")
    from collections import Counter

    print("relations Wikidata:", len(rels), dict(Counter(r["prop"] for r in rels)))


if __name__ == "__main__":
    main()
