"""Etape 8 - Liste des cas douteux a valider a la main (data/review/A_VALIDER.md).

Rassemble en un seul document ce qu'un humain doit trancher :
  A. organisations dont la date de fondation est inconnue (non dessinees sur la frise)
  B. organisations importantes sans position ni famille
  C. organisations peripheriques etrangeres (gardees mais masquees par defaut)
  D. pages ecartees qui ressemblent pourtant a des organisations politiques francaises
  E. organisations dont la nature est incertaine (sans infobox, nature 'movement')
Pour corriger : ajouter les titres a data/overrides.json ('include' / 'exclude' / 'org').
"""
from __future__ import annotations

import json
import re

from client_shortcuts import store
from s02_fetch_parties import looks_like_org
from s05_build_graph import PERSON_TEXT
from wikiclient import ROOT

G = ROOT / "data" / "graph"
REVIEW = ROOT / "data" / "review"


def short(s, n=120):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    nodes = json.loads((G / "nodes.json").read_text(encoding="utf-8"))
    side = json.loads((REVIEW / "_build_side.json").read_text(encoding="utf-8"))
    orgs = [n for n in nodes if n["type"] == "org"]
    ps = store()
    out = ["# Cas douteux a valider", "",
           "Repondre par listes : inclure ..., exclure ..., corriger ... Les titres sont ceux des pages Wikipedia.", ""]

    # A. sans date
    a = sorted((n for n in orgs if not n["start"]), key=lambda n: -n["importance"])
    out += [f"## A. Organisations sans date de fondation ({len(a)})", "",
            "Non dessinees sur la frise. Une date a ajouter, ou l'organisation a retirer ?", ""]
    for n in a:
        out.append(f"- {n['title']} [{n['kind']}] importance {n['importance']} : {short(n['summary'], 110)}")
    out.append("")

    # B. sans position ni famille, importants
    b = sorted((n for n in orgs if n["position_value"] is None and not n["families"] and n["tier"] <= 2),
               key=lambda n: -n["importance"])
    out += [f"## B. Importantes mais sans position ni famille ({len(b)})", "",
            "Il manque l'information pour les placer sur l'axe. Position souhaitee (-3 extreme gauche ... +3 extreme droite) ?", ""]
    for n in b:
        out.append(f"- {n['title']} [{n['kind']}] {n['start'] or '?'}-{n['end'] or ''} : {short(n['summary'], 100)}")
    out.append("")

    # C. peripheriques
    c = sorted((n for n in orgs if n["peripheral"]), key=lambda n: -n["importance"])
    out += [f"## C. Organisations peripheriques (etrangeres ou frontalieres) ({len(c)})", "",
            "Gardees mais masquees par defaut. A garder comme francaises, a laisser peripheriques, ou a retirer ?", ""]
    for n in c:
        out.append(f"- {n['title']} [{n['kind']}] {n['start'] or '?'} : {short(n['summary'], 100)}")
    out.append("")

    # D. ecartees a tort possibles
    kept_titles = {n["title"] for n in orgs}
    d_org, d_foreign = [], []
    for t, reason in side["excluded"]:
        p = ps.get(t)
        if not p or t in kept_titles:
            continue
        intro = (p["intro"] or "").split("\n")[0]
        if PERSON_TEXT.search(intro[:220]) or re.match(r"^\d", t):
            continue
        if reason == "pas_une_organisation" and looks_like_org(t, p["intro"]):
            d_org.append((t, short(intro, 130)))
        elif reason in ("pays_etranger", "pas_de_preuve_france") and looks_like_org(t, p["intro"]):
            d_foreign.append((t, reason, short(intro, 130)))
    out += [f"## D1. Pages ecartees comme 'pas une organisation' mais qui y ressemblent ({len(d_org)})", ""]
    out += [f"- {t} : {i}" for t, i in sorted(d_org)]
    out += ["", f"## D2. Pages ecartees faute de preuve que l'organisation est francaise ({len(d_foreign)})", ""]
    out += [f"- {t} ({r}) : {i}" for t, r, i in sorted(d_foreign)]
    out.append("")

    # E. nature incertaine
    e = sorted((n for n in orgs if n["kind"] == "movement" and not n["peripheral"] and n["tier"] <= 2),
               key=lambda n: -n["importance"])
    out += [f"## E. Mouvements de niveau 1 ou 2 sans infobox de parti, nature a confirmer ({len(e)})", ""]
    for n in e:
        out.append(f"- {n['title']} {n['start'] or '?'} : {short(n['summary'], 110)}")
    out.append("")

    (REVIEW / "A_VALIDER.md").write_text("\n".join(out), encoding="utf-8")
    print(f"A={len(a)} B={len(b)} C={len(c)} D1={len(d_org)} D2={len(d_foreign)} E={len(e)}")


if __name__ == "__main__":
    main()
