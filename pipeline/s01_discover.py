"""Etape 1 - Decouverte des partis et mouvements francais.

Sources croisees (aucune n'est complete seule) :
  A. Wikidata : partis (Q7278 et sous-classes) dont le pays est la France.
  B. Wikipedia FR : toutes les pages utilisant {{Infobox Parti politique}}, filtrees
     sur la France d'apres leurs categories.
  C. Wikipedia FR : pages membres de l'arbre de categories 'Parti politique en France'
     (hors branches de personnes / financement) et pages des listes de partis.

Sortie : data/raw/discovery.json  (candidats + provenance, sans decision finale).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

from wikiclient import RAW, Client, chunks

FR_CAT_RE = re.compile(
    r"en France|de France|\(France\)|fran[cç]ais|Nouvelle-Cal[eé]donie|Polyn[eé]sie|"
    r"Guadeloupe|Martinique|Guyane|La R[eé]union|Mayotte|Saint-Pierre-et-Miquelon|"
    r"Wallis-et-Futuna|Saint-Martin|Saint-Barth[eé]lemy|Corse|Alsace|Bretagne|"
    r"Pays basque|outre-mer|Troisi[eè]me R[eé]publique|Quatri[eè]me R[eé]publique|"
    r"Cinqui[eè]me R[eé]publique|Seconde Guerre mondiale en France|R[eé]gime de Vichy",
    re.I,
)

ROOT_CATS = [
    "Catégorie:Parti politique en France",
    "Catégorie:Ancien parti politique en France",
    "Catégorie:Coalition de partis en France",
    "Catégorie:Ancienne coalition de partis en France",
    "Catégorie:Micro-parti politique en France",
    "Catégorie:Mouvement de jeunesse de parti politique en France",
    "Catégorie:Liste de partis politiques en France",
]
# branches a ne pas parcourir (personnes, financement, categories techniques)
SKIP_CAT_RE = re.compile(
    r"Personnalit|Dirigeant|Financement|Wikip[eé]dia|Cat[eé]gorie d'un parti|"
    r"Groupe politique de la R[eé]volution|Deuxi[eè]me R[eé]publique|Ancien R[eé]gime|"
    r"[ÉE]lu |Candidat|Militant|Membre|Syndicat",
    re.I,
)


def wikidata_parties(c: Client):
    q = """
SELECT ?item ?frTitle ?label ?inc ?dis ?sl WHERE {
  ?item wdt:P31/wdt:P279* wd:Q7278; wdt:P17 wd:Q142.
  ?item wikibase:sitelinks ?sl.
  OPTIONAL { ?item wdt:P571 ?inc }
  OPTIONAL { ?item wdt:P576 ?dis }
  OPTIONAL { ?art schema:about ?item; schema:isPartOf <https://fr.wikipedia.org/>; schema:name ?frTitle }
  OPTIONAL { ?item rdfs:label ?label. FILTER(LANG(?label)='fr') }
}"""
    res = c.sparql(q)["results"]["bindings"]
    out = {}
    for b in res:
        qid = b["item"]["value"].rsplit("/", 1)[1]
        d = out.setdefault(qid, {"qid": qid, "inc": set(), "dis": set()})
        if "frTitle" in b:
            d["fr_title"] = b["frTitle"]["value"]
        if "label" in b:
            d["label"] = b["label"]["value"]
        d["sitelinks"] = int(b["sl"]["value"])
        if "inc" in b:
            d["inc"].add(b["inc"]["value"])
        if "dis" in b:
            d["dis"].add(b["dis"]["value"])
    for d in out.values():
        d["inc"] = sorted(d["inc"])
        d["dis"] = sorted(d["dis"])
    return out


def infobox_pages(c: Client):
    titles = []
    for o in c.mw_continue(
        {
            "action": "query",
            "list": "embeddedin",
            "eititle": "Modèle:Infobox Parti politique",
            "eilimit": "500",
            "einamespace": "0",
        }
    ):
        titles += [p["title"] for p in o["query"]["embeddedin"]]
    return titles


def categories_of(c: Client, titles):
    cats = defaultdict(list)
    for batch in chunks(titles, 50):
        for o in c.mw_continue(
            {
                "action": "query",
                "prop": "categories",
                "titles": "|".join(batch),
                "cllimit": "max",
                "clshow": "!hidden",
            }
        ):
            for p in o["query"].get("pages", []):
                for cat in p.get("categories", []):
                    cats[p["title"]].append(cat["title"])
    return cats


def category_tree_pages(c: Client, roots, max_depth=3):
    seen_cats, pages = set(), {}
    frontier = [(r, 0) for r in roots]
    while frontier:
        cat, depth = frontier.pop()
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        for o in c.mw_continue(
            {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat,
                "cmlimit": "500",
                "cmtype": "page|subcat",
                "cmnamespace": "0|14",
            }
        ):
            for m in o["query"]["categorymembers"]:
                if m["ns"] == 0:
                    pages.setdefault(m["title"], []).append(cat)
                elif m["ns"] == 14 and depth < max_depth and not SKIP_CAT_RE.search(m["title"]):
                    frontier.append((m["title"], depth + 1))
    return pages, sorted(seen_cats)


def list_page_links(c: Client, list_titles):
    links = defaultdict(list)
    for t in list_titles:
        for o in c.mw_continue(
            {"action": "query", "prop": "links", "titles": t, "pllimit": "max", "plnamespace": "0"}
        ):
            for p in o["query"].get("pages", []):
                for l in p.get("links", []):
                    links[l["title"]].append(t)
    return links


def main():
    c = Client()
    print("A. Wikidata ...")
    wd = wikidata_parties(c)
    print("   partis Wikidata:", len(wd), "dont page frwiki:", sum(1 for d in wd.values() if d.get("fr_title")))

    print("B. Infobox Parti politique ...")
    ib = infobox_pages(c)
    print("   pages avec infobox (monde):", len(ib))
    cats = categories_of(c, ib)
    wd_titles = {d["fr_title"] for d in wd.values() if d.get("fr_title")}
    ib_fr = {}
    for t in ib:
        fr_cats = [x for x in cats.get(t, []) if FR_CAT_RE.search(x)]
        if fr_cats or t in wd_titles:
            ib_fr[t] = fr_cats
    print("   dont France (categories ou Wikidata):", len(ib_fr))

    print("C. Arbre de categories + listes ...")
    tree_pages, seen_cats = category_tree_pages(c, ROOT_CATS)
    print("   pages de l'arbre:", len(tree_pages), "categories parcourues:", len(seen_cats))
    list_pages = [t for t, cs in tree_pages.items() if cs and any("Liste de partis" in x for x in cs)]
    list_links = list_page_links(c, list_pages)
    print("   pages-listes:", list_pages, "-> liens:", len(list_links))

    cand = {}

    def add(title, src, **extra):
        d = cand.setdefault(title, {"title": title, "sources": [], "fr_cats": []})
        if src not in d["sources"]:
            d["sources"].append(src)
        for k, v in extra.items():
            d[k] = v

    for qid, d in wd.items():
        if d.get("fr_title"):
            add(d["fr_title"], "wikidata", qid=qid)
    for t, fc in ib_fr.items():
        add(t, "infobox_fr", fr_cats=fc[:6])
    for t, cs in tree_pages.items():
        add(t, "category_tree")
    for t in list_links:
        add(t, "list_page")

    ib_all = set(ib)
    for t, d in cand.items():
        d["has_party_infobox"] = t in ib_all

    out = {
        "wikidata": wd,
        "candidates": cand,
        "category_tree": seen_cats,
        "list_pages": list_pages,
        "infobox_world_count": len(ib),
    }
    (RAW / "discovery.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_ib = sum(1 for d in cand.values() if d["has_party_infobox"])
    print(f"Candidats: {len(cand)} (avec infobox parti: {n_ib}); reseau={c.net_calls} cache={c.cache_hits}")


if __name__ == "__main__":
    main()
