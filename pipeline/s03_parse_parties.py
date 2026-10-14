"""Etape 3 - Analyse des pages de partis : fiches + relations datees (sans decision).

Lit la copie locale (pages.sqlite) et extrait de {{Infobox Parti politique}} :
  - identite : nom, sigle, fondation / disparition, noms successifs ;
  - relations vers d'autres entites, avec annee ou intervalle quand indique :
      split_from / split_into      (scission de / scission dans)
      merged_from / merged_into    (fusion de / fusionne dans)
      predecessor / successor      (precedent / suivant)
      affiliated_to / coalition_of (coalition, affi nationale / francaise, coalition de)
  - fondateurs (lignes 'Fondateur(s)' des paires option-N / valeur-N), dirigeants
    cites (champ 'chef'), positionnement, ideologies, effectifs, elus ;
Sortie : data/graph/parties_raw.json
"""
from __future__ import annotations

import json
import re

from client_shortcuts import store
from wikiclient import ROOT
from wikiparse import (
    find_dates, find_span, norm_title, parse_template, plain, position_code,
    split_br, strip_noise, wikilinks,
)

OUT = ROOT / "data" / "graph" / "parties_raw.json"

REL_FIELDS = [
    (r"^scission de$", "split_from"),
    (r"^scission dans$", "split_into"),
    (r"^fusion de$", "merged_from"),
    (r"^fusionn[ée]e? dans$|^fusion dans$|^absorb[ée]e? par$", "merged_into"),
    (r"^pr[ée]c[ée]dents?$|^pr[ée]d[ée]cesseurs?$|^issu(e)? de$", "predecessor"),
    (r"^suivants?$|^successeurs?$|^devenu(e)?$", "successor"),
    (r"^coalition$|^coalition dans$|^affi nationale$|^affi fran[cç]aise$|^affi r[ée]gionale$", "affiliated_to"),
    (r"^coalition de$", "coalition_of"),
]

FOUNDER_LABEL = re.compile(r"fondat|cr[ée]at|fond[ée] par|initiat", re.I)
RENAME_LABEL = re.compile(r"changement de nom|ancien nom|anciens? noms|renomm", re.I)


def get(fields, *names):
    for n in names:
        if n in fields and fields[n].strip():
            return fields[n]
    return ""


def parse_links_with_span(v: str):
    out = []
    for seg in split_br(strip_noise(v)):
        links = wikilinks(seg)
        if not links:
            continue
        start, end = find_span(seg)
        for tgt, lab in links:
            out.append({"target": tgt, "label": lab, "start": start, "end": end, "raw": plain(seg)[:160]})
    return out


def extract_abbreviations(wikitext: str, title: str) -> list[str]:
    """Sigles entre parentheses dans la premiere phrase : '''Parti socialiste''' (PS)."""
    # saute l'infobox
    r = re.search(r"\{\{\s*Infobox Parti politique", wikitext, re.I)
    body = wikitext
    if r:
        depth, j = 0, r.start()
        while j < len(wikitext) - 1:
            two = wikitext[j : j + 2]
            if two == "{{":
                depth += 1; j += 2
            elif two == "}}":
                depth -= 1; j += 2
                if depth == 0:
                    break
            else:
                j += 1
        body = wikitext[j:]
    m = re.search(r"'''[^\n]{3,200}", body)
    if not m:
        return []
    chunk = plain(m.group(0))[:300]
    out = []
    for g in re.findall(r"\(([^()]{2,40})\)", chunk):
        for part in re.split(r"[,;/]| ou ", g):
            part = part.strip(" .")
            if re.fullmatch(r"[A-ZÉÈÀ0-9][A-Za-zÉÈÀéèà0-9.\-&']{1,14}", part) and part.upper() == part.upper():
                if re.search(r"[A-ZÉÈÀ]{2,}|^[A-Z][a-z]{0,3}\.?[A-Z]", part):
                    out.append(part)
    return list(dict.fromkeys(out))[:4]


def first_infobox_is_party(wikitext: str) -> bool:
    """Vrai si la premiere infobox de la page est une infobox de parti (et non celle d'une
    personne ou d'une institution qui en citerait une plus bas)."""
    for m in re.finditer(r"\{\{\s*(Infobox [^|\n}]+)", wikitext, re.I):
        name = m.group(1).strip().lower()
        if "modulaire" in name or "/d" in name or "/f" in name or "/" in name:
            continue  # enveloppes {{Infobox/Début}}, {{Infobox modulaire/Début}}, sections {{Infobox/Ligne ...}}
        return "parti politique" in name
    return False


def parse_party(page: dict):
    r = parse_template(page["wikitext"], r"Infobox Parti politique")
    if r and not first_infobox_is_party(page["wikitext"]):
        r = None
    rec = {
        "title": page["title"],
        "qid": page.get("qid"),
        "revid": page.get("revid"),
        "scope": page.get("scope"),
        "intro": page.get("intro", ""),
        "has_infobox": bool(r),
        "abbreviations": extract_abbreviations(page["wikitext"], page["title"]),
        "relations": [],
        "name_field": "",
        "founded_raw": "", "dissolved_raw": "", "founded_dates": [], "dissolved_dates": [],
        "position_raw": "", "positions": [], "ideologies": [],
        "leaders_listed": [], "leader_plain": "", "options": [], "founders_listed": [],
        "former_names": [], "members_raw": "", "eu_affiliation": [], "intl_affiliation": [],
        "infobox_keys": [],
    }
    if not r:
        return rec
    _, f = r
    rec["name_field"] = plain(get(f, "nom", "nom_complet"))
    for rx, typ in REL_FIELDS:
        pat = re.compile(rx, re.I)
        for key, val in f.items():
            if pat.search(key) and val.strip():
                for rel in parse_links_with_span(val):
                    rec["relations"].append({"type": typ, "field": key, **rel})

    rec["founded_raw"] = strip_noise(get(f, "fondation", "création"))[:400]
    rec["dissolved_raw"] = strip_noise(get(f, "disparition", "dissolution"))[:400]
    rec["founded_dates"] = find_dates(rec["founded_raw"])
    rec["dissolved_dates"] = find_dates(rec["dissolved_raw"])

    pos_raw = strip_noise(get(f, "positionnement", "position politique"))
    rec["position_raw"] = plain(pos_raw)[:300]
    pos = []
    header = ""  # intitule de periode precedent ('Actuel :', 'Avant 1914 :', 'Factions :'...)
    for seg in split_br(pos_raw):
        txt = plain(seg)
        found = False
        for tgt, lab in wikilinks(seg) or [(None, txt)]:
            code = position_code((tgt or "") + " " + lab)
            if code:
                found = True
                s, e = find_span(seg)
                pos.append({"code": code, "label": lab, "context": txt[:80], "header": header[:60],
                            "start": s, "end": e})
        if not found and txt and len(txt) < 80:
            header = txt
    rec["positions"] = pos

    ideo_raw = strip_noise(get(f, "idéologie", "ideologie"))
    rec["ideologies"] = list(dict.fromkeys(t for t, _ in wikilinks(ideo_raw)))[:20]

    rec["leaders_listed"] = [
        {"target": t, "label": l, "title_label": plain(get(f, "dénomination chef"))[:60]}
        for t, l in wikilinks(strip_noise(get(f, "chef", "président", "direction", "dirigeants")))
    ]
    rec["leader_plain"] = plain(get(f, "chef", "président", "direction"))[:200]

    # paires option-N / valeur-N : fondateurs, anciens noms, secretaires, etc.
    options = []
    for i in range(1, 12):
        lab = get(f, f"option-{i}")
        val = get(f, f"valeur-{i}")
        if not lab and not val:
            continue
        options.append(
            {
                "label": plain(lab)[:80],
                "value": plain(val)[:300],
                "links": [t for t, _ in wikilinks(strip_noise(val))],
                "span": find_span(val),
            }
        )
    rec["options"] = options
    rec["founders_listed"] = list(
        dict.fromkeys(t for o in options if FOUNDER_LABEL.search(o["label"]) for t in o["links"])
    )
    rec["former_names"] = [o["value"] for o in options if RENAME_LABEL.search(o["label"])]
    f_ = get(f, "fondateur", "fondateurs")
    if f_:
        rec["founders_listed"] = list(dict.fromkeys(rec["founders_listed"] + [t for t, _ in wikilinks(strip_noise(f_))]))

    rec["members_raw"] = plain(get(f, "adherents", "adhérents", "membres"))[:200]
    rec["eu_affiliation"] = list(dict.fromkeys(t for t, _ in wikilinks(get(f, "affi européenne", "groupe européen"))))
    rec["intl_affiliation"] = list(dict.fromkeys(t for t, _ in wikilinks(get(f, "affi internationale"))))
    rec["infobox_keys"] = sorted(f)
    return rec


def main():
    ps = store()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    recs = [parse_party(ps.get(t)) for t in sorted(ps.all_titles("full"))]
    OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    n_ib = sum(r["has_infobox"] for r in recs)
    from collections import Counter

    c = Counter(rel["type"] for r in recs for rel in r["relations"])
    print(f"{len(recs)} pages, {n_ib} avec infobox; relations brutes: {dict(c)}")


if __name__ == "__main__":
    main()
