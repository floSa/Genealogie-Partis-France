"""Etape 4d - Dirigeants successifs depuis les tableaux et listes des pages de partis.

Les pages de partis contiennent des sections « Dirigeants », « Présidents », « Premiers secrétaires »,
« Secrétaires généraux »... sous forme de tableaux (`{| class="wikitable"`) ou de listes, souvent
avec les dates de mandat. Quand la section renvoie vers une page dédiee ({{Article détaillé|...}}),
cette page est lue aussi (ex. « Premier secrétaire du Parti socialiste »).

Pour chaque ligne : premiere personne citee (lien) + dates de mandat. Les personnes sont ensuite
confirmees par leur propre page (infobox de personnalité ou date de naissance) : seules les
personnes reelles sont retenues.

Sortie : data/graph/leaders_raw.json  [{party, person, role, start, end, source}]
"""
from __future__ import annotations

import json
import re

from client_shortcuts import store
from wikiclient import ROOT, Client
from wikiparse import find_dates, norm_title, parse_template, plain, strip_noise, wikilinks

OUT = ROOT / "data" / "graph" / "leaders_raw.json"
HEAD = re.compile(r"^(={2,5})\s*([^=\n]+?)\s*\1\s*$", re.M)
SECTION_OK = re.compile(
    r"^(historique des )?(dirigeants?|pr[ée]sidents?|premiers? secr[ée]taires?|secr[ée]taires? (g[ée]n[ée]raux?|nationaux?)|"
    r"porte-paroles?|chefs?|leaders?|liste des (dirigeants|pr[ée]sidents|secr[ée]taires[^=]*))( du parti| du mouvement)?$", re.I)
SECTION_NO = re.compile(r"vice|adjoint|d[ée]l[ée]gu|fédéra|honneur|fondateur", re.I)
ROLE = [
    (re.compile(r"premiers? secr", re.I), "Premier secrétaire"),
    (re.compile(r"secr[ée]taires? g[ée]n", re.I), "Secrétaire général"),
    (re.compile(r"secr[ée]taires? nat", re.I), "Secrétaire national"),
    (re.compile(r"porte-parole", re.I), "Porte-parole"),
    (re.compile(r"pr[ée]sident", re.I), "Président"),
    (re.compile(r"chef|leader", re.I), "Chef"),
]
DETAIL = re.compile(r"\{\{\s*(?:Article d[ée]taill[ée]|Article principal|Voir aussi|Article connexe)\s*\|([^{}]+)\}\}", re.I)
NOT_PERSON_TITLE = re.compile(
    r"^(Congr[èe]s|Pr[ée]sident |Premier |Secr[ée]taire |[ÉE]lection|Liste |Parti |Union |Front |Mouvement |Gouvernement|"
    r"Conseil |Assembl[ée]e|S[ée]nat|Cinqui[èe]me|Quatri[èe]me|Troisi[èe]me|Histoire |Fichier|Image|Cat[ée]gorie)", re.I)


def role_of(heading: str) -> str:
    for rx, label in ROLE:
        if rx.search(heading):
            return label
    return "Dirigeant"


def clean_row(txt: str) -> str:
    txt = strip_noise(txt)
    txt = re.sub(r"\{\{\s*(?:dur[ée]e|unit[ée]|formatnum|nobr|nb|nombre)[^{}]*\}\}", " ", txt, flags=re.I)
    txt = re.sub(r"\[\[(?:Fichier|File|Image):[^\]]*\]\]", " ", txt, flags=re.I)
    return txt


def dates_of(txt: str):
    ds = find_dates(clean_row(txt))
    if not ds:
        return None, None
    if len(ds) == 1:
        return ds[0], None
    return ds[0], ds[1]


def first_person(txt: str):
    for tgt, lab in wikilinks(clean_row(txt)):
        if NOT_PERSON_TITLE.match(tgt) or re.fullmatch(r"\d{1,4}", tgt) or re.search(r"congr[èe]s|[ée]lection", tgt, re.I):
            continue
        return tgt
    return None


def parse_rows(text: str):
    """Lignes de tableau (separees par '|-') ou elements de liste -> [(personne, debut, fin)]."""
    out = []
    chunks = []
    if "{|" in text:
        for tbl in re.findall(r"\{\|.*?\n\|\}", text, flags=re.S):
            chunks += re.split(r"\n\|-+", tbl)[1:]
    for line in text.split("\n"):
        if re.match(r"^\s*[*#]", line):
            chunks.append(line)
    for ch in chunks:
        p = first_person(ch)
        if not p:
            continue
        a, b = dates_of(ch)
        if a:
            out.append((p, a, b))
    return out


def sections(wt: str):
    hs = [(m.start(), m.end(), m.group(2).strip()) for m in HEAD.finditer(wt)]
    for i, (s, e, name) in enumerate(hs):
        if SECTION_NO.search(name) or not SECTION_OK.match(name):
            continue
        end = hs[i + 1][0] if i + 1 < len(hs) else len(wt)
        # un titre de niveau inferieur (sous-section) fait partie de la section
        yield name, wt[e:end]


def main():
    c = Client()
    ps = store(c)
    parties = json.loads((ROOT / "data" / "graph" / "parties_raw.json").read_text(encoding="utf-8"))
    party_titles = [p["title"] for p in parties if p["has_infobox"]]
    rows = []  # (party, person, role, start, end, source)
    detail_targets = {}
    for t in party_titles:
        pg = ps.get(t)
        if not pg or pg["scope"] != "full":
            continue
        for name, body in sections(pg["wikitext"]):
            role = role_of(name)
            for person, a, b in parse_rows(body):
                rows.append((t, person, role, a, b, f"{t}#{name}"))
            for m in DETAIL.finditer(body):
                for tgt in m.group(1).split("|"):
                    tgt = norm_title(tgt.split("{{!}}")[0])
                    if tgt and not re.search(r"\b(congr[èe]s|[ée]lection)\b", tgt, re.I):
                        detail_targets.setdefault(tgt, set()).add((t, role))
    # pages dediees (« Premier secretaire du Parti socialiste ») : lues en entier
    ps.resolve_redirects(sorted(detail_targets))
    todo = [ps.resolve(x) for x in detail_targets]
    ps.fetch([x for x in todo if x], scope="full", batch=20, progress=False)
    for tgt, owners in detail_targets.items():
        pg = ps.get(tgt)
        if not pg or pg["scope"] != "full":
            continue
        for party, role in owners:
            r = role_of(pg["title"]) if role_of(pg["title"]) != "Dirigeant" else role
            for person, a, b in parse_rows(pg["wikitext"]):
                rows.append((party, person, r, a, b, pg["title"]))
    print("lignes candidates:", len(rows), "dans", len({r[0] for r in rows}), "partis", flush=True)

    # confirmation des personnes par leur propre page
    persons = sorted({ps.resolve(r[1]) for r in rows} | {r[1] for r in rows})
    ps.resolve_redirects(persons)
    persons = sorted({ps.resolve(p) for p in persons})
    ps.fetch(persons, scope="lead", batch=20, progress=False)
    real = {}
    for p in persons:
        pg = ps.get(p)
        if not pg:
            continue
        ib = parse_template(pg["wikitext"], r"Infobox Personnalit[ée]|Infobox Biographie")
        intro = (pg["intro"] or "").split("\n")[0][:240]
        if ib or re.search(r"\bné(e)? (le|en|à)\b", intro):
            real[p] = pg["title"]
    out, seen = [], set()
    for party, person, role, a, b, src in rows:
        p = real.get(ps.resolve(person))
        if not p:
            continue
        if b and a and b < a:
            continue
        key = (party, p, a, role)
        if key in seen:
            continue
        seen.add(key)
        out.append({"party": party, "person": p, "role": role, "start": a, "end": b, "source": src})
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} mandats de dirigeants retenus ({len({o['person'] for o in out})} personnes, {len({o['party'] for o in out})} partis)")


if __name__ == "__main__":
    main()
