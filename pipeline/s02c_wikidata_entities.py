"""Etape 2c - Enrichissement Wikidata de toutes les entites retenues (partis + personnes).

Pour chaque identifiant Wikidata connu (via les pages stockees) : nombre de liens
interlangues (notoriete), pays (P17), dates de creation / dissolution (P571 / P576),
natures (P31), date de naissance / deces pour les personnes (P569 / P570).
Sortie : data/raw/wd_entities.json   {qid: {...}}
"""
from __future__ import annotations

import json
import os

from client_shortcuts import store
from wikiclient import RAW, ROOT, WD_API, Client, chunks


def claim_values(ent, pid):
    out = []
    for st in ent.get("claims", {}).get(pid, []):
        dv = st.get("mainsnak", {}).get("datavalue")
        if not dv:
            continue
        v = dv["value"]
        if isinstance(v, dict) and "id" in v:
            out.append(v["id"])
        elif isinstance(v, dict) and "time" in v:
            prec = v.get("precision", 9)
            t = v["time"]
            if t.startswith("-"):
                continue  # avant J.-C. : sans objet ici
            ymd = t.lstrip("+").split("T")[0]
            bits = ymd.split("-")
            if len(bits) != 3:
                continue
            y, m, d = bits
            out.append(y if prec <= 9 else f"{y}-{m}" if prec == 10 else f"{y}-{m}-{d}")
        else:
            out.append(str(v))
    return out


def main():
    c = Client()
    ps = store(c)
    people_path = ROOT / "data" / "graph" / "people_raw.json"
    ptitles = {p["title"] for p in json.loads(people_path.read_text(encoding="utf-8"))} if people_path.exists() else set()
    qids = set()
    for scope, title, qid in ps.db.execute("SELECT scope, title, qid FROM pages WHERE qid IS NOT NULL"):
        if scope == "full" or title in ptitles:
            qids.add(qid)
    qids = sorted(qids)
    out_path = RAW / "wd_entities.json"
    fresh = os.environ.get("PARTIS_FRESH") == "1"
    out = {} if fresh or not out_path.exists() else json.loads(out_path.read_text(encoding="utf-8"))
    todo = [q for q in qids if q not in out]
    print("entites Wikidata a enrichir:", len(todo), "sur", len(qids), flush=True)
    for b in chunks(todo, 50):
        o = c.mw(
            {"action": "wbgetentities", "ids": "|".join(b), "props": "sitelinks|claims|labels",
             "languages": "fr|en"},
            api=WD_API,
        )
        for qid, ent in o.get("entities", {}).items():
            if "missing" in ent:
                continue
            out[qid] = {
                "sl": len(ent.get("sitelinks", {})),
                "p17": claim_values(ent, "P17"),
                "p31": claim_values(ent, "P31"),
                "inc": claim_values(ent, "P571"),
                "dis": claim_values(ent, "P576"),
                "born": claim_values(ent, "P569"),
                "died": claim_values(ent, "P570"),
                "label_fr": ent.get("labels", {}).get("fr", {}).get("value"),
            }
        out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("total:", len(out), "reseau", c.net_calls, flush=True)


if __name__ == "__main__":
    main()
