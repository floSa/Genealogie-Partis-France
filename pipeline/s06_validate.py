"""Etape 6 - Controle qualite : anomalies, couverture, statistiques.

Produit dans data/review/ :
  anomalies.csv        incoherences detectees (dates, cycles, orphelins...)
  excluded.csv         pages ecartees et raison
  unresolved_edges.csv relations dont la cible n'est pas dans le graphe
  coverage_check.csv   entites attendues (exemples de l'utilisateur, serie YouTube...) trouvees ou non
  RAPPORT.md           statistiques de synthese
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict

from wikiclient import ROOT

G = ROOT / "data" / "graph"
REVIEW = ROOT / "data" / "review"

# (libelle, alias normalises possibles)
EXPECTED = [
    # serie #EspritDeParti et exemples cites par l'utilisateur
    ("Parti communiste francais", ["pcf", "parti communiste francais"]),
    ("Parti communiste des ouvriers de France", ["pcof", "parti communiste des ouvriers de france"]),
    ("Pole de renaissance communiste en France", ["prcf", "pole de renaissance communiste en france"]),
    ("Lutte ouvriere", ["lo", "lutte ouvriere"]),
    ("Nouveau Parti anticapitaliste", ["npa", "nouveau parti anticapitaliste"]),
    ("Parti ouvrier independant", ["poi", "parti ouvrier independant"]),
    ("Parti ouvrier independant democratique", ["poid", "parti ouvrier independant democratique"]),
    ("Revolution permanente", ["revolution permanente"]),
    ("Ligue communiste revolutionnaire", ["lcr", "ligue communiste revolutionnaire"]),
    ("Parti socialiste", ["ps", "parti socialiste"]),
    ("Section francaise de l'Internationale ouvriere", ["sfio", "section francaise de l internationale ouvriere"]),
    ("Generation.s", ["generation s", "generations"]),
    ("Place publique", ["place publique"]),
    ("Les Ecologistes / EELV", ["eelv", "europe ecologie les verts", "les ecologistes"]),
    ("Les Verts", ["les verts"]),
    ("Generation ecologie", ["generation ecologie"]),
    ("Mouvement ecologiste independant", ["mei", "mouvement ecologiste independant", "mouvement des ecologistes independants"]),
    ("Union pour la democratie francaise", ["udf", "union pour la democratie francaise"]),
    ("Mouvement democrate", ["modem", "mouvement democrate"]),
    ("Union des democrates et independants", ["udi", "union des democrates et independants"]),
    ("Rassemblement pour la Republique", ["rpr", "rassemblement pour la republique"]),
    ("Union pour un mouvement populaire", ["ump", "union pour un mouvement populaire"]),
    ("Les Republicains", ["lr", "les republicains"]),
    ("Renaissance", ["renaissance", "larem", "la republique en marche", "lrem"]),
    ("Rassemblement national / Front national", ["rn", "fn", "rassemblement national", "front national"]),
    ("Les Patriotes", ["les patriotes", "lp"]),
    ("Debout la France", ["dlf", "debout la france"]),
    ("Union des droites pour la Republique", ["udr", "union des droites pour la republique"]),
    ("Reconquete", ["reconquete"]),
    ("La France insoumise", ["lfi", "la france insoumise"]),
    ("Parti de gauche", ["pg", "parti de gauche"]),
    ("Parti radical de gauche", ["prg", "parti radical de gauche"]),
    ("Parti radical", ["parti radical"]),
    ("Mouvement republicain et citoyen", ["mrc", "mouvement republicain et citoyen"]),
    ("Mouvement des citoyens", ["mdc", "mouvement des citoyens"]),
    ("Nouvelle Union populaire ecologique et sociale", ["nupes", "nouvelle union populaire ecologique et sociale"]),
    ("Nouveau Front populaire", ["nfp", "nouveau front populaire"]),
    ("Union de la gauche", ["union de la gauche"]),
    ("Front de gauche", ["front de gauche"]),
    ("Horizons", ["horizons"]),
    ("Agir", ["agir"]),
    ("Mouvement pour la France", ["mpf", "mouvement pour la france"]),
    ("Centre des democrates sociaux", ["cds", "centre des democrates sociaux"]),
    ("Parti republicain", ["pr", "parti republicain"]),
    ("Mouvement republicain populaire", ["mrp", "mouvement republicain populaire"]),
    ("Rassemblement du peuple francais", ["rpf", "rassemblement du peuple francais"]),
    ("Union pour la nouvelle Republique", ["unr", "union pour la nouvelle republique"]),
    ("Union des democrates pour la Republique", ["udr 1968", "union des democrates pour la republique"]),
    ("Centre national des independants et paysans", ["cnip", "centre national des independants et paysans"]),
    ("Parti socialiste unifie", ["psu", "parti socialiste unifie"]),
    ("Chasse, peche, nature et traditions", ["cpnt", "chasse peche nature et traditions"]),
    ("Union populaire republicaine", ["upr", "union populaire republicaine"]),
    ("Les Centristes", ["les centristes", "nouveau centre"]),
    ("Alliance centriste", ["alliance centriste"]),
    ("Parti de la France", ["parti de la france"]),
    ("Mouvement national republicain", ["mnr", "mouvement national republicain"]),
    ("Ordre nouveau", ["ordre nouveau"]),
    ("Parti des forces nouvelles", ["pfn", "parti des forces nouvelles"]),
    ("Nouvelle Donne", ["nouvelle donne"]),
    ("Parti animaliste", ["parti animaliste"]),
    ("Ensemble !", ["ensemble"]),
    ("Alternative libertaire", ["alternative libertaire"]),
    ("Solidarite et progres", ["solidarite et progres"]),
    ("Parti ecologiste", ["parti ecologiste"]),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def ymd(d):
    return d or ""


def year(d):
    return int(d[:4]) if d and d[:4].isdigit() else None


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in rows:
            w.writerow(r)


def find_cycles(adj):
    """Cycles dans un graphe dirige {u: [v]} (iteratif)."""
    state, cycles = {}, []
    for root in list(adj):
        if state.get(root):
            continue
        stack = [(root, iter(adj.get(root, [])))]
        path = [root]
        state[root] = 1
        while stack:
            u, it = stack[-1]
            for v in it:
                if state.get(v) == 1:
                    i = path.index(v)
                    cycles.append(path[i:] + [v])
                elif not state.get(v):
                    state[v] = 1
                    path.append(v)
                    stack.append((v, iter(adj.get(v, []))))
                    break
            else:
                state[u] = 2
                stack.pop()
                path.pop()
    return cycles


def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    nodes = json.loads((G / "nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((G / "edges.json").read_text(encoding="utf-8"))
    side = json.loads((REVIEW / "_build_side.json").read_text(encoding="utf-8"))
    orgs = {n["id"]: n for n in nodes if n["type"] == "org"}
    people = {n["id"]: n for n in nodes if n["type"] == "person"}
    oe = [e for e in edges if e["layer"] == "org_org"]
    pe = [e for e in edges if e["layer"] == "person_org"]

    an = []  # (gravite, type, objet, detail)

    # ---- organisations
    for n in orgs.values():
        t = n["title"]
        if not n["start"]:
            an.append(("moyenne" if n["tier"] <= 2 else "faible", "sans_date_de_fondation", t, ""))
        if n["start"] and n["end"] and n["end"][:4] < n["start"][:4]:
            an.append(("haute", "fin_avant_debut", t, f"{n['start']} -> {n['end']}"))
        if n["position_value"] is None and n["tier"] <= 2 and n["kind"] in ("party", "coalition", "movement"):
            an.append(("moyenne", "sans_positionnement", t, ""))
        if not n["summary"]:
            an.append(("faible", "sans_resume", t, ""))
        if n["degree"] == 0 and n["tier"] <= 2:
            an.append(("moyenne", "organisation_isolee_importante", t, "aucune relation org-org"))
        if "dates_contradictoires" in n.get("flags", []):
            an.append(("moyenne", "dates_contradictoires", t, ""))

    # ---- aretes org-org
    adj_split, adj_succ = defaultdict(list), defaultdict(list)
    for e in oe:
        a, b = orgs[e["source"]], orgs[e["target"]]
        d = e.get("date") or e.get("start")
        if e["type"] == "split":
            adj_split[e["source"]].append(e["target"])
            if d and a["start"] and year(d) and year(a["start"]) and year(d) < year(a["start"]):
                an.append(("haute", "scission_avant_la_naissance_du_parent", b["title"], f"scission {d} < fondation de {a['title']} {a['start']}"))
            elif not d and a["start"] and b["start"] and year(b["start"]) < year(a["start"]):
                an.append(("moyenne", "enfant_ne_avant_son_parent", b["title"], f"enfant {b['start']} < parent {a['title']} {a['start']}"))
            if d and b["start"] and year(d) and year(b["start"]) and abs(year(d) - year(b["start"])) > 3:
                an.append(("faible", "date_scission_differente_de_la_fondation_de_l_enfant", b["title"], f"scission {d} / fondation {b['start']}"))
        if e["type"] == "succession":
            adj_succ[e["source"]].append(e["target"])
            if a["start"] and b["start"] and year(b["start"]) < year(a["start"]) - 1:
                an.append(("moyenne", "successeur_ne_avant_son_predecesseur", a["title"] + " -> " + b["title"], f"{a['start']} / {b['start']}"))
        if e["type"] == "merge" and a["end"] and d and year(d) and year(a["end"]) and year(a["end"]) < year(d) - 1:
            an.append(("faible", "fusion_apres_la_disparition_de_la_source", a["title"] + " -> " + b["title"], f"fin {a['end']} / fusion {d}"))
        if "dates_contradictoires" in e.get("flags", []):
            an.append(("moyenne", "relation_dates_contradictoires", a["title"] + " -> " + b["title"], e["type"]))
    # un cycle n'a de sens que parmi un meme type de relation : scission seule ou succession seule
    # (une scission suivie d'une fusion de retour est une histoire normale, pas une erreur)
    for label, graph in (("scission", adj_split), ("succession", adj_succ)):
        for cyc in find_cycles(graph):
            an.append(("haute", f"cycle_de_{label}", " -> ".join(orgs[c]["title"] for c in cyc), ""))

    pairs = defaultdict(set)
    for e in oe:
        pairs[(e["source"], e["target"])].add(e["type"])
        pairs[(e["target"], e["source"])].add("inverse_" + e["type"])
    for (a, b), ts in pairs.items():
        real = {t for t in ts if not t.startswith("inverse_")}
        if "split" in real and real & {"merge", "succession"}:
            an.append(("faible", "relations_multiples_entre_deux_organisations", orgs[a]["title"] + " / " + orgs[b]["title"], ",".join(sorted(real))))

    # ---- personnes
    for pid, p in people.items():
        if p["born"] and p["died"] and p["died"][:4] < p["born"][:4]:
            an.append(("haute", "deces_avant_naissance", p["title"], f"{p['born']} / {p['died']}"))
    for e in pe:
        o, p = orgs[e["target"]], people[e["source"]]
        if e["start"] and e["end"] and e["end"][:4] < e["start"][:4]:
            an.append(("haute", "intervalle_inverse", p["title"] + " @ " + o["title"], f"{e['start']} -> {e['end']}"))
        if e["start"] and p["born"] and year(e["start"]) < year(p["born"]) + 12:
            an.append(("moyenne", "adhesion_avant_12_ans", p["title"] + " @ " + o["title"], f"ne {p['born']} / debut {e['start']}"))
        if e["start"] and o["end"] and year(e["start"]) > year(o["end"]) + 1:
            an.append(("moyenne", "adhesion_apres_dissolution", p["title"] + " @ " + o["title"], f"debut {e['start']} / fin du parti {o['end']}"))
        if e["start"] and o["start"] and year(e["start"]) < year(o["start"]) - 1 and e["type"] != "founder":
            an.append(("faible", "adhesion_avant_fondation", p["title"] + " @ " + o["title"], f"debut {e['start']} / parti {o['start']}"))

    sev = {"haute": 0, "moyenne": 1, "faible": 2}
    an.sort(key=lambda r: (sev[r[0]], r[1], r[2]))
    write_csv(REVIEW / "anomalies.csv", an, ["gravite", "type", "objet", "detail"])
    write_csv(REVIEW / "excluded.csv", sorted(side["excluded"]), ["titre", "raison"])
    write_csv(REVIEW / "unresolved_edges.csv", sorted(side["unresolved_edges"]), ["page", "type_relation", "cible", "texte"])
    write_csv(REVIEW / "dropped_scope.csv", sorted(side["dropped_scope"]), ["titre", "fin"])

    # ---- couverture
    # 'trouve' : un alias correspond exactement au titre ou au nom d'une organisation ;
    # 'trouve_par_sigle' : seulement par un sigle (a verifier a la main, risque de faux positif).
    exact, abbr = defaultdict(list), defaultdict(list)
    for n in orgs.values():
        for k in {norm(n["title"]), norm(n["name"])}:
            if k:
                exact[k].append(n["title"])
        for a in n["abbreviations"]:
            if norm(a):
                abbr[norm(a)].append(n["title"])
    cov = []
    for label, aliases in EXPECTED:
        hit_e, hit_a = [], []
        for a in aliases:
            hit_e += exact.get(norm(a), [])
            hit_a += abbr.get(norm(a), [])
        hit_e = list(dict.fromkeys(hit_e))
        hit_a = [h for h in dict.fromkeys(hit_a) if h not in hit_e]
        if hit_e:
            cov.append((label, "trouve", " | ".join(hit_e)))
        elif hit_a:
            cov.append((label, "trouve_par_sigle", " | ".join(hit_a)))
        else:
            cov.append((label, "ABSENT", ""))
    write_csv(REVIEW / "coverage_check.csv", cov, ["attendu", "statut", "correspondance"])
    missing = [c for c in cov if c[1] == "ABSENT"]
    by_sigle = [c for c in cov if c[1] == "trouve_par_sigle"]

    # ---- statistiques
    kinds = Counter(n["kind"] for n in orgs.values())
    status = Counter(n["status"] for n in orgs.values())
    scope = Counter(n["scope"] for n in orgs.values())
    tier = Counter(n["tier"] for n in orgs.values())
    etype = Counter(e["type"] for e in oe)
    conf = Counter(e["confidence"] for e in oe)
    ptype = Counter(e["type"] for e in pe)
    has_pos = sum(1 for n in orgs.values() if n["position_value"] is not None)
    has_start = sum(1 for n in orgs.values() if n["start"])
    has_fam = sum(1 for n in orgs.values() if n["families"])
    decades = Counter((year(n["start"]) // 10 * 10) for n in orgs.values() if n["start"] and n["scope"] == "coeur")
    alive_by_year = {y: sum(1 for n in orgs.values() if n["start"] and year(n["start"]) <= y and (not n["end"] or year(n["end"]) >= y))
                     for y in (1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025)}
    sev_c = Counter((a[0]) for a in an)
    lines = [
        "# Rapport de qualite des donnees",
        "",
        f"Organisations : {len(orgs)} (coeur 1958+ : {scope.get('coeur',0)}, ancetres anterieurs : {scope.get('ancetre',0)})",
        f"Personnes : {len(people)} ; aretes personne-organisation : {len(pe)} ({dict(ptype)})",
        f"Aretes organisation-organisation : {len(oe)} ({dict(etype)})",
        f"  dont confirmees par les deux pages : {conf.get('confirmee_2_pages',0)} ; par une seule page : {conf.get('une_page',0)}",
        "",
        "## Completude des champs (organisations)",
        f"- date de fondation : {has_start}/{len(orgs)} ({100*has_start//max(1,len(orgs))} %)",
        f"- positionnement (valeur -3..+3) : {has_pos}/{len(orgs)} ({100*has_pos//max(1,len(orgs))} %)",
        f"- au moins une famille politique : {has_fam}/{len(orgs)} ({100*has_fam//max(1,len(orgs))} %)",
        "",
        "## Repartition",
        f"- natures : {dict(kinds)}",
        f"- statuts : {dict(status)}",
        f"- niveaux de zoom (1 = macro, 3 = detail) : {dict(sorted(tier.items()))}",
        f"- fondations par decennie : {dict(sorted(decades.items()))}",
        f"- organisations existantes a une date donnee : {alive_by_year}",
        "",
        "## Controles",
        f"- anomalies : {dict(sev_c)} (voir anomalies.csv)",
        f"- couverture des entites attendues : {len(cov)-len(missing)-len(by_sigle)}/{len(cov)} trouvees par leur nom, "
        f"{len(by_sigle)} seulement par un sigle ({[m[0] for m in by_sigle]}), absentes : {[m[0] for m in missing]}",
        f"- pages ecartees : {len(side['excluded'])} (excluded.csv) ; relations non resolues : {len(side['unresolved_edges'])} (unresolved_edges.csv)",
        "",
    ]
    (REVIEW / "RAPPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
