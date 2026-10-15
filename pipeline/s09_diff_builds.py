"""Etape 9 - Rapport de changements entre deux constructions du graphe.

Compare data/snapshots/previous_*.json (copie faite par s05 juste avant d'ecrire le nouveau
graphe) au graphe courant et ecrit data/review/CHANGEMENTS.md : organisations nouvelles ou
disparues, champs modifies, relations ajoutees ou retirees, personnes, nouveaux candidats de la
decouverte et pages Wikipedia modifiees depuis la derniere mise a jour.
"""
from __future__ import annotations

import datetime
import json

from wikiclient import RAW, ROOT

G = ROOT / "data" / "graph"
SNAP = ROOT / "data" / "snapshots"
REVIEW = ROOT / "data" / "review"
FIELDS = ["name", "kind", "start", "end", "status", "position_value", "tier", "peripheral", "scope"]
CAP = 60


def load(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def section(title, lines, cap=CAP):
    out = [f"## {title} ({len(lines)})", ""]
    if not lines:
        return out + ["Aucun.", ""]
    out += lines[:cap]
    if len(lines) > cap:
        out.append(f"- ... et {len(lines) - cap} autres")
    return out + [""]


def main():
    prev_nodes, prev_edges = load(SNAP / "previous_nodes.json"), load(SNAP / "previous_edges.json")
    nodes, edges = load(G / "nodes.json"), load(G / "edges.json")
    lines = [f"# Changements depuis la construction precedente", "",
             f"Rapport genere le {datetime.date.today().isoformat()}.", ""]
    if prev_nodes is None:
        lines += ["Pas de construction precedente : rien a comparer (premiere construction).", ""]
        (REVIEW / "CHANGEMENTS.md").write_text("\n".join(lines), encoding="utf-8")
        print("pas de construction precedente")
        return

    po = {n["id"]: n for n in prev_nodes if n["type"] == "org"}
    co = {n["id"]: n for n in nodes if n["type"] == "org"}
    pp = {n["id"] for n in prev_nodes if n["type"] == "person"}
    cp = {n["id"] for n in nodes if n["type"] == "person"}
    added = sorted(set(co) - set(po))
    removed = sorted(set(po) - set(co))
    modified = []
    for i in sorted(set(co) & set(po)):
        diffs = [f"{f}: {po[i].get(f)!r} -> {co[i].get(f)!r}" for f in FIELDS if po[i].get(f) != co[i].get(f)]
        if sorted(po[i].get("families", [])) != sorted(co[i].get("families", [])):
            diffs.append(f"familles: {po[i].get('families')} -> {co[i].get('families')}")
        if diffs:
            modified.append(f"- {co[i]['title']} : " + " ; ".join(diffs))
    lines += [f"Organisations : {len(po)} -> {len(co)} ; personnes : {len(pp)} -> {len(cp)}.", ""]
    lines += section("Organisations nouvelles", [f"- {co[i]['title']} ({co[i]['kind']}, {co[i]['start'] or '?'})" for i in added])
    lines += section("Organisations disparues du graphe", [f"- {po[i]['title']}" for i in removed])
    lines += section("Organisations modifiees", modified)

    def okey(e):
        return (e["type"], e["source"], e["target"])

    pe = {okey(e): e for e in prev_edges if e["layer"] == "org_org"}
    ce = {okey(e): e for e in edges if e["layer"] == "org_org"}
    name = lambda i: (co.get(i) or po.get(i) or {}).get("title", i)
    lines += section("Relations ajoutees", [f"- {k[0]} : {name(k[1])} -> {name(k[2])} ({ce[k].get('date') or ce[k].get('start') or ''})" for k in sorted(set(ce) - set(pe))])
    lines += section("Relations retirees", [f"- {k[0]} : {name(k[1])} -> {name(k[2])}" for k in sorted(set(pe) - set(ce))])
    ch = []
    for k in sorted(set(ce) & set(pe)):
        a, b = pe[k], ce[k]
        if (a.get("date"), a.get("start"), a.get("end"), a.get("confidence")) != (b.get("date"), b.get("start"), b.get("end"), b.get("confidence")):
            ch.append(f"- {k[0]} : {name(k[1])} -> {name(k[2])} : {a.get('date') or a.get('start')} / {a.get('confidence')} -> {b.get('date') or b.get('start')} / {b.get('confidence')}")
    lines += section("Relations modifiees (date ou confiance)", ch)

    ppe = {(e["source"], e["target"], e["type"]) for e in prev_edges if e["layer"] == "person_org"}
    cpe = {(e["source"], e["target"], e["type"]) for e in edges if e["layer"] == "person_org"}
    pname = {n["id"]: n["title"] for n in nodes + prev_nodes if n["type"] == "person"}
    lines += [f"## Personnes et liens personne-organisation", "",
              f"- personnes nouvelles : {len(cp - pp)} ; disparues : {len(pp - cp)}",
              f"- liens ajoutes : {len(cpe - ppe)} ; retires : {len(ppe - cpe)}", ""]
    lines += section("Exemples de liens ajoutes", [f"- {pname.get(a, a)} : {t} {name(b)}" for a, b, t in sorted(cpe - ppe)], cap=30)

    # decouverte : nouveaux candidats
    pd, cd = load(SNAP / "previous_discovery.json"), load(RAW / "discovery.json")
    if pd and cd:
        def strong(d):
            return {t for t, v in d["candidates"].items() if v.get("has_party_infobox") or "wikidata" in v["sources"]}
        new = sorted(strong(cd) - strong(pd))
        lines += section("Nouveaux candidats a la decouverte (infobox de parti ou Wikidata)", [f"- {t}" for t in new])

    rr = load(RAW / "refresh_report.json")
    if rr:
        lines += [f"## Pages Wikipedia modifiees (mise a jour du {rr['date']})", "",
                  f"{len(rr['changed'])} pages modifiees sur {rr['checked']} verifiees ; {len(rr['gone'])} disparues.", ""]
        lines += [f"- {t}" for t in rr["changed"][:40]]
        lines.append("")
    (REVIEW / "CHANGEMENTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"changements : +{len(added)} -{len(removed)} ~{len(modified)} organisations ; relations +{len(set(ce)-set(pe))} -{len(set(pe)-set(ce))}")


if __name__ == "__main__":
    main()
