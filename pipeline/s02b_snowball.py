"""Etape 2b - Elargissement de proche en proche (boucle de decouverte).

Pour chaque entite francaise connue, on suit les liens de filiation (scission, fusion,
predecesseur, successeur, coalition) et les partis cites par les personnes.
Toute cible absente de la copie locale est telechargee en introduction seule ; si c'est
une organisation politique (infobox de parti ou premiere phrase), la page complete est
telechargee, ses categories lues, et elle est suivie a son tour si elle est francaise.
S'arrete quand plus rien de nouveau n'apparait (point fixe) ou apres MAX_ROUNDS tours.
"""
from __future__ import annotations

import json
import re

from client_shortcuts import store
from s02_fetch_parties import looks_like_org
from s03_parse_parties import parse_party
from wikiclient import RAW, ROOT, Client
from wikiparse import parse_template

MAX_ROUNDS = 4
FR_STRICT = re.compile(
    r"en France|\(France\)|fran[cç]ais|Outre-mer|Nouvelle-Cal[eé]donie|Polyn[eé]sie|Guadeloupe|"
    r"Martinique|Guyane|La R[eé]union|Mayotte|Saint-Pierre-et-Miquelon|Wallis-et-Futuna|"
    r"Saint-Martin|Saint-Barth[eé]lemy|Corse|Alsace|Bretagne|Troisi[eè]me R[eé]publique|"
    r"Quatri[eè]me R[eé]publique|Cinqui[eè]me R[eé]publique|Seconde Guerre mondiale en France|"
    r"R[eé]gime de Vichy|Second Empire|monarchie de Juillet|Restauration|Deuxi[eè]me R[eé]publique",
    re.I,
)
FOLLOW = {"split_from", "split_into", "merged_from", "merged_into", "predecessor", "successor",
          "affiliated_to", "coalition_of"}


def is_french(ps, title, strong_titles: set[str]) -> bool:
    if title in strong_titles:
        return True
    return any(FR_STRICT.search(c) for c in ps.categories(title))


def main():
    c = Client()
    ps = store(c)
    disc = json.loads((RAW / "discovery.json").read_text(encoding="utf-8"))
    strong = {t for t, d in disc["candidates"].items()
              if set(d["sources"]) & {"wikidata", "category_tree"}}
    people_path = ROOT / "data" / "graph" / "people_raw.json"

    # pages deja stockees en introduction seule mais dont l'infobox est une infobox de parti
    lead_ib = []
    for t in ps.all_titles("lead"):
        p = ps.get(t)
        if p and (parse_template(p["wikitext"], r"Infobox Parti politique") or looks_like_org(p["title"], p["intro"])):
            lead_ib.append(t)
    print("introductions (infobox de parti ou organisation reconnue) a completer:", len(lead_ib), flush=True)
    ps.fetch(lead_ib, scope="full", batch=20, progress=False)

    for rnd in range(1, MAX_ROUNDS + 1):
        full = sorted(ps.all_titles("full"))
        ps.fetch_categories(full)
        recs = {}
        for t in full:
            recs[t] = parse_party(ps.get(t))
        parties = {t: r for t, r in recs.items() if r["has_infobox"]}
        french = {t for t in parties if is_french(ps, t, strong)}

        targets = set()
        for t in french:
            for rel in parties[t]["relations"]:
                if rel["type"] in FOLLOW:
                    targets.add(rel["target"])
        if people_path.exists():
            for p in json.loads(people_path.read_text(encoding="utf-8")):
                for s in p["party_spans"]:
                    targets.add(s["target"])
                for fn in p["functions"]:
                    targets.update(fn["links"])
        ps.resolve_redirects(sorted(targets))
        targets = {ps.resolve(x) for x in targets}
        new = sorted(x for x in targets if not ps.has(x) and not ps.is_missing(x))
        print(f"tour {rnd}: {len(french)} entites francaises, {len(new)} cibles nouvelles", flush=True)
        if not new:
            break
        ps.fetch(new, scope="lead", batch=20, progress=False)
        promote = []
        for x in new:
            p = ps.get(x)
            if not p:
                continue
            if parse_template(p["wikitext"], r"Infobox Parti politique") or looks_like_org(p["title"], p["intro"]):
                promote.append(p["title"])
        print(f"   -> {len(promote)} reconnues comme organisations", flush=True)
        ps.fetch(promote, scope="full", batch=20, progress=False)
        if not promote:
            break
    print("fin; pages completes:", len(ps.all_titles("full")), "reseau", c.net_calls, flush=True)


if __name__ == "__main__":
    main()
