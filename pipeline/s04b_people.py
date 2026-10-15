"""Etape 4b - Personnes : telechargement leger (introduction + infobox) et analyse.

Candidats (aucune lecture integrale de page) :
  A. personnes citees dans les infobox de partis : fondateurs, dirigeants ;
  B. Wikidata : fondateurs / dirigeants de partis (tous) et membres de partis avec
     au moins MIN_SL liens interlangues (indicateur de notoriete).
Pour chaque personne on telecharge seulement la section 0 (introduction + infobox)
et on lit :
  - 'parti'  : suite de partis avec dates ;
  - 'fonctionN' : fonctions (president de X...) avec dates ;
  - naissance, deces.
Sortie : data/graph/people_raw.json
"""
from __future__ import annotations

import json
import re
import sys

from client_shortcuts import store
from wikiclient import RAW, ROOT, Client
from wikiparse import (
    find_dates, find_span, norm_title, parse_template, plain, split_br, strip_noise, wikilinks,
)

MIN_SL = int(sys.argv[1]) if len(sys.argv) > 1 else 6
OUT = ROOT / "data" / "graph" / "people_raw.json"

LEADER_ROLE = re.compile(
    r"pr[ée]sident|secr[ée]taire|porte-parole|co-?pr[ée]sident|coordinat|d[ée]l[ée]gu[ée] g[ée]n[ée]ral|"
    r"chef|dirigeant|animateur|tr[ée]sorier|fondateur|leader|directeur|"
    r"commissaire|haut-commissaire|guide|rapporteur|responsable national",
    re.I,
)
# fonctions d'Etat ou d'assemblee : a ne pas confondre avec une direction de parti
NOT_PARTY_ROLE = re.compile(
    r"r[ée]publique|conseil (r[ée]gional|g[ée]n[ée]ral|d[ée]partemental|municipal|de paris|m[ée]tropolitain)|"
    r"assembl[ée]e|s[ée]nat|commission|groupe|mairie|maire|communaut[ée]|syndicat|minist|gouvernement|"
    r"cour |tribunal|banque|fondation|chambre|d[ée]put[ée]|s[ée]nateur|parlement",
    re.I,
)


def candidates(ps):
    cands = {}

    def add(title, why, **kw):
        d = cands.setdefault(title, {"title": title, "why": [], "qid": None, "sl": None})
        if why not in d["why"]:
            d["why"].append(why)
        for k, v in kw.items():
            if v is not None:
                d[k] = v

    parties = json.loads((ROOT / "data" / "graph" / "parties_raw.json").read_text(encoding="utf-8"))
    for p in parties:
        if not p["has_infobox"]:
            continue
        for t in p["founders_listed"]:
            add(t, "founder_infobox")
        for l in p["leaders_listed"]:
            add(l["target"], "leader_infobox")
    lp = ROOT / "data" / "graph" / "leaders_raw.json"  # dirigeants lus dans les tableaux (s04d)
    if lp.exists():
        for x in json.loads(lp.read_text(encoding="utf-8")):
            add(x["person"], "leader_table")
    wd = json.loads((RAW / "wd_people.json").read_text(encoding="utf-8"))
    for r in wd["roles"]:
        if r.get("frTitle"):
            add(r["frTitle"], "wd_" + r["prop"], qid=r["person"], sl=r["sl"])
    for r in wd["members"]:
        if r.get("frTitle") and r["sl"] >= MIN_SL:
            add(r["frTitle"], "wd_member", qid=r["person"], sl=r["sl"])
    return cands


def keyed(fields, rx):
    pat = re.compile(rx, re.I)
    return {k: v for k, v in fields.items() if pat.search(k) and v.strip()}


def parse_person(page):
    r = parse_template(page["wikitext"], r"Infobox Personnalit[ée] politique|Infobox Personnalit[ée]|Infobox Biographie")
    rec = {
        "title": page["title"],
        "qid": page.get("qid"),
        "intro": (page.get("intro") or "").split("\n")[0][:600],
        "has_infobox": bool(r),
        "infobox_name": r[0] if r else None,
        "party_spans": [],
        "functions": [],
    }
    if not r:
        return rec
    f = r[1]
    births = find_dates(strip_noise(f.get("naissance", "") or f.get("date de naissance", "")))
    deaths = find_dates(strip_noise(f.get("décès", "") or f.get("deces", "") or f.get("date de décès", "")))
    rec["born"] = births[0] if births else None
    rec["died"] = deaths[0] if deaths else None

    for key, val in f.items():
        if re.fullmatch(r"parti(s)?( politique)?", key.strip()):
            for seg in split_br(strip_noise(val)):
                links = wikilinks(seg)
                if not links:
                    continue
                s, e = find_span(seg)
                for tgt, lab in links:
                    rec["party_spans"].append({"target": tgt, "label": lab, "start": s, "end": e, "raw": plain(seg)[:120]})

    # fonctions
    nums = sorted({int(m.group(1)) for k in f for m in [re.search(r"fonction ?(\d+)\s*$", k)] if m})
    for n in nums:
        label_raw = ""
        for k in (f"fonction{n}", f"fonction {n}"):
            if k in f:
                label_raw = f[k]
                break
        if not label_raw.strip():
            continue
        start = end = None
        for k, v in f.items():
            m = re.search(r"^(.*?)fonction ?(\d+)\s*$", k)
            if not m or int(m.group(2)) != n or not v.strip():
                continue
            pre = m.group(1)
            ds = find_dates(strip_noise(v))
            if not ds:
                continue
            if re.search(r"jusqu", pre):
                end = ds[0]
            elif re.search(r"depuis|partir|d[ée]but", pre):
                start = start or ds[0]
        rec["functions"].append(
            {
                "n": n,
                "label": plain(label_raw)[:160],
                "links": [t for t, _ in wikilinks(strip_noise(label_raw))],
                "start": start,
                "end": end,
            }
        )
    return rec


def main():
    c = Client()
    ps = store(c)
    cands = candidates(ps)
    print("Candidats personnes:", len(cands), flush=True)
    ps.resolve_redirects(list(cands))
    # fusion apres redirection
    merged = {}
    for t, d in cands.items():
        ct = ps.resolve(t)
        m = merged.setdefault(ct, {**d, "title": ct, "why": []})
        m["why"] = list(dict.fromkeys(m["why"] + d["why"]))
        m["qid"] = m.get("qid") or d.get("qid")
        m["sl"] = max(filter(None, [m.get("sl"), d.get("sl")]), default=None)
    print("Apres redirections:", len(merged), flush=True)
    ps.fetch(list(merged), scope="lead", batch=20)

    out = []
    for t, d in merged.items():
        p = ps.get(t)
        if not p:
            continue
        rec = parse_person(p)
        rec["why"] = d["why"]
        rec["sl"] = d.get("sl")
        rec["qid"] = rec["qid"] or d.get("qid")
        out.append(rec)
    # resolution des cibles de liens (partis) apres redirection
    targets = set()
    for r in out:
        targets |= {s["target"] for s in r["party_spans"]}
        for fn in r["functions"]:
            targets |= set(fn["links"])
    ps.resolve_redirects(list(targets))
    for r in out:
        for s in r["party_spans"]:
            s["target"] = ps.resolve(s["target"])
        for fn in r["functions"]:
            fn["links"] = [ps.resolve(x) for x in fn["links"]]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_p = sum(1 for r in out if r["has_infobox"])
    print(f"{len(out)} personnes stockees, {n_p} avec infobox; reseau={c.net_calls} cache={c.cache_hits}")


if __name__ == "__main__":
    main()
