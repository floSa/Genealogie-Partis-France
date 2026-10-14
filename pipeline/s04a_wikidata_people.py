"""Etape 4a - Personnes liees aux partis francais d'apres Wikidata (sans lire de pages).

Trois requetes SPARQL :
  1. adhesions : personne P102 (parti politique) -> parti francais, avec dates P580/P582
  2. fondateurs / dirigeants cote parti : P112 (fondateur), P488 (president/dirigeant)
     avec dates
  3. fonctions dirigeantes cote personne : P39 (fonction) = President/Chef de parti
     n'est pas fiable -> non utilisee.
Le nombre de liens interlangues (sitelinks) sert d'indicateur de notoriete.

Sortie : data/raw/wd_people.json
"""
from __future__ import annotations

import json

from wikiclient import RAW, Client

PARTY = "?party wdt:P31/wdt:P279* wd:Q7278; wdt:P17 wd:Q142."

Q_MEMBERS = """
SELECT ?person ?party ?start ?end ?sl ?frTitle ?label WHERE {
  %s
  ?person p:P102 ?st. ?st ps:P102 ?party.
  ?person wdt:P31 wd:Q5; wikibase:sitelinks ?sl.
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?art schema:about ?person; schema:isPartOf <https://fr.wikipedia.org/>; schema:name ?frTitle }
  OPTIONAL { ?person rdfs:label ?label. FILTER(LANG(?label)='fr') }
}""" % PARTY

def _roles_query(prop, tag):
    return """
SELECT ?person ?party ?start ?end ?sl ?frTitle ?label WHERE {
  %s
  ?party p:%s ?st. ?st ps:%s ?person.
  ?person wikibase:sitelinks ?sl.
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?art schema:about ?person; schema:isPartOf <https://fr.wikipedia.org/>; schema:name ?frTitle }
  OPTIONAL { ?person rdfs:label ?label. FILTER(LANG(?label)='fr') }
}""" % (PARTY, prop, prop)


Q_FOUNDERS = _roles_query("P112", "founder")
Q_CHAIRS = _roles_query("P488", "chair")


def rows(c, q, keys):
    out = []
    for b in c.sparql(q)["results"]["bindings"]:
        r = {}
        for k in keys:
            if k in b:
                v = b[k]["value"]
                if k in ("person", "party"):
                    v = v.rsplit("/", 1)[1]
                if k == "sl":
                    v = int(v)
                r[k] = v
        out.append(r)
    return out


def main():
    c = Client()
    members = rows(c, Q_MEMBERS, ["person", "party", "start", "end", "sl", "frTitle", "label"])
    roles = []
    for q, tag in ((Q_FOUNDERS, "founder"), (Q_CHAIRS, "chair")):
        try:
            for r in rows(c, q, ["person", "party", "start", "end", "sl", "frTitle", "label"]):
                r["prop"] = tag
                roles.append(r)
        except Exception as e:  # requete trop lourde : on poursuit avec le reste
            print("   requete", tag, "echouee:", str(e)[:80])
    print("adhesions:", len(members), "personnes:", len({r["person"] for r in members}))
    print("roles (fondateur/dirigeant):", len(roles), "personnes:", len({r["person"] for r in roles}))
    (RAW / "wd_people.json").write_text(
        json.dumps({"members": members, "roles": roles}, ensure_ascii=False), encoding="utf-8"
    )
    import collections

    sl = collections.Counter()
    for r in {r["person"]: r for r in members}.values():
        s = r["sl"]
        sl["1-2" if s < 3 else "3-5" if s < 6 else "6-10" if s < 11 else "11-20" if s < 21 else "21+"] += 1
    print("repartition sitelinks (personnes):", dict(sl))


if __name__ == "__main__":
    main()
