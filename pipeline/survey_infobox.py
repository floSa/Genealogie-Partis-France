"""Outil de diagnostic : frequence des champs de l'infobox de parti dans la copie locale."""
from collections import Counter

from client_shortcuts import store
from wikiparse import parse_template

ps = store()
cnt, n = Counter(), 0
noib = []
for t in ps.all_titles("full"):
    p = ps.get(t)
    r = parse_template(p["wikitext"], r"Infobox Parti politique")
    if not r:
        noib.append(t)
        continue
    n += 1
    for k, v in r[1].items():
        if v.strip():
            cnt[k] += 1
print("pages avec infobox:", n, "| sans infobox:", len(noib))
for k, v in cnt.most_common(70):
    print(f"{v:5d}  {k}")
