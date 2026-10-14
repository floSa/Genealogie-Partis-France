"""Etape 2 - Copie locale des pages de partis.

Strategie frugale en deux temps :
  1. Pages COMPLETES (wikitexte entier + resume) pour les candidats solides :
     pages utilisant l'infobox de parti, et pages Wikidata de partis francais.
  2. Pages INTRODUCTION seule (section 0, tres leger) pour les candidats incertains
     (arbre de categories, listes) : sert a reconnaitre, par la premiere phrase,
     les mouvements / coalitions / courants sans infobox. Seules celles reconnues
     sont ensuite telechargees en entier.
Tout est stocke dans data/raw/pages.sqlite : un second lancement ne retelecharge rien.
"""
from __future__ import annotations

import json
import re

from pagestore import PageStore
from wikiclient import RAW, Client

# premiere phrase d'une page decrivant une organisation politique
ORG_RE = re.compile(
    r"\b(est|était|sont|étaient|fut|a été)\b[^.]{0,160}?\b("
    r"parti|partis|mouvement|coalition|alliance|rassemblement|courant|formation|"
    r"organisation|groupuscule|fédération|ligue|cartel|confédération|club|"
    r"association|front|union|collectif|groupe politique|groupe arm[ée]|groupe terroriste|groupe clandestin|"
    r"structure|think tank|cercle|"
    r"tendance|plateforme|liste|candidat)\b",
    re.I,
)
POLITICAL_RE = re.compile(
    r"politi|élector|électoral|trotsk|commun|socialis|libér|écolog|nationalis|"
    r"souverain|régional|autonom|indépendant|gaull|centr|droite|gauche|syndical|"
    r"anarch|royalis|fascis|maoïst|marxis|radical|démocrat|républic|identitair",
    re.I,
)
NOT_ORG_RE = re.compile(
    r"^(\S+\s){0,6}?(congrès|affaire|attentat|loi |élection|primaire|manifeste|"
    r"hebdomadaire|quotidien|revue|journal|magazine|film|livre|essai|émission|"
    r"bataille|guerre|traité|manifestation|grève|référendum|scrutin)",
    re.I,
)


def strong_titles(disc) -> list[str]:
    out = []
    for t, d in disc["candidates"].items():
        if d["has_party_infobox"] or ("wikidata" in d["sources"]):
            out.append(t)
    return sorted(out)


def uncertain_titles(disc, strong: set[str]) -> list[str]:
    return sorted(t for t, d in disc["candidates"].items() if t not in strong)


def looks_like_org(title: str, intro: str) -> bool:
    first = intro.strip().split("\n")[0][:400]
    if not first:
        return False
    if NOT_ORG_RE.search(title) and not re.search(r"(parti|mouvement|coalition)", first, re.I):
        return False
    return bool(ORG_RE.search(first)) and bool(POLITICAL_RE.search(first))


def main():
    disc = json.loads((RAW / "discovery.json").read_text(encoding="utf-8"))
    strong = strong_titles(disc)
    unc = uncertain_titles(disc, set(strong))
    print("Candidats solides:", len(strong), "| incertains:", len(unc), flush=True)
    c = Client()
    ps = PageStore(c)

    print("1) pages completes (solides) ...", flush=True)
    ps.fetch(strong, scope="full", batch=20)

    print("2) introductions (incertains) ...", flush=True)
    ps.fetch(unc, scope="lead", batch=20)

    promoted = []
    for t in unc:
        p = ps.get(t)
        if p and p["scope"] == "lead" and looks_like_org(p["title"], p["intro"]):
            promoted.append(p["title"])
    print(f"3) reconnus comme organisations politiques: {len(promoted)} -> pages completes", flush=True)
    ps.fetch(promoted, scope="full", batch=20)
    # 'promues' = pages completes hors candidats solides (union avec les tours precedents)
    strong_set = set(strong)
    all_promoted = sorted({ps.resolve(t) for t in ps.all_titles("full")} - {ps.resolve(t) for t in strong_set})
    (RAW / "promoted.json").write_text(json.dumps(all_promoted, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Termine. reseau={c.net_calls} cache={c.cache_hits}; pages stockees: {len(ps.all_titles())}", flush=True)


if __name__ == "__main__":
    main()
