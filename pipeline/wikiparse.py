"""Outils d'analyse du wikitexte francais (infobox, liens, dates).

Bibliotheque standard uniquement. Les fonctions sont tolerantes : une donnee mal
formee donne un resultat vide, jamais une exception, afin de ne pas bloquer le
traitement de milliers de pages heterogenes.
"""
from __future__ import annotations

import re

MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10,
    "novembre": 11, "décembre": 12, "decembre": 12,
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))

# ---------------------------------------------------------------- nettoyage
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_REF_BLOCK = re.compile(r"<ref\b[^>/]*>.*?</ref\s*>", re.S | re.I)
_REF_SELF = re.compile(r"<ref\b[^>]*/\s*>", re.I)
_BR = re.compile(r"<br\s*/?>", re.I)


def strip_noise(s: str) -> str:
    s = _COMMENT.sub("", s)
    s = _REF_BLOCK.sub("", s)
    s = _REF_SELF.sub("", s)
    return s


def split_br(s: str) -> list[str]:
    """Decoupe sur <br> et sur les puces de liste, en conservant les segments non vides."""
    s = _BR.sub("\n", s)
    s = re.sub(r"\n\s*[*#]+\s*", "\n", s)
    return [x.strip() for x in s.split("\n") if x.strip()]


# -------------------------------------------------------------- modeles {{ }}
def _find_template_span(wt: str, start_re: re.Pattern, pos: int = 0):
    m = start_re.search(wt, pos)
    if not m:
        return None
    i = m.start()
    depth, j, n = 0, i, len(wt)
    while j < n - 1:
        two = wt[j : j + 2]
        if two == "{{":
            depth += 1
            j += 2
        elif two == "}}":
            depth -= 1
            j += 2
            if depth == 0:
                return i, j
        else:
            j += 1
    return None


def _split_top_level(body: str) -> list[str]:
    parts, buf = [], []
    depth_t = depth_l = 0
    i, n = 0, len(body)
    while i < n:
        two = body[i : i + 2]
        if two == "{{":
            depth_t += 1
            buf.append(two)
            i += 2
        elif two == "}}":
            depth_t -= 1
            buf.append(two)
            i += 2
        elif two == "[[":
            depth_l += 1
            buf.append(two)
            i += 2
        elif two == "]]":
            depth_l -= 1
            buf.append(two)
            i += 2
        elif body[i] == "|" and depth_t == 0 and depth_l == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(body[i])
            i += 1
    parts.append("".join(buf))
    return parts


def parse_template(wt: str, name_re: str):
    """Premier modele dont le nom correspond a name_re -> (nom, {champ: valeur brute})."""
    start = re.compile(r"\{\{\s*(" + name_re + r")\b", re.I)
    span = _find_template_span(wt, start)
    if not span:
        return None
    block = wt[span[0] + 2 : span[1] - 2]
    parts = _split_top_level(block)
    name = parts[0].strip()
    fields = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            k = re.sub(r"\s+", " ", k.strip().lower())
            fields[k] = v.strip()
    return name, fields


# ----------------------------------------------------------------- liens
_LINK = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\[\]|]*)?(?:\|([^\[\]]*))?\]\]")


def norm_title(t: str) -> str:
    t = t.replace("_", " ").strip().lstrip(":").strip()
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:] if t else t


def wikilinks(s: str) -> list[tuple[str, str]]:
    """[(cible normalisee, libelle)] hors fichiers, categories et interwikis."""
    out = []
    for m in _LINK.finditer(s):
        tgt = m.group(1)
        if re.match(r"\s*(Fichier|File|Image|Catégorie|Category|[a-z]{2,3}):", tgt, re.I):
            # interwiki 'en:' etc. ou fichier
            if not re.match(r"\s*(Wikipédia|Projet|Portail):", tgt, re.I):
                continue
        out.append((norm_title(tgt), (m.group(2) or tgt).strip()))
    return out


def plain(s: str) -> str:
    """Texte brut approximatif d'une valeur de champ."""
    s = strip_noise(s)
    s = _LINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), s)
    s = re.sub(r"\{\{\s*(?:abr[ée]viation discr[èe]te|abbr)\s*\|([^|}]*)(?:\|[^}]*)?\}\}", r"\1", s, flags=re.I)
    s = re.sub(r"\{\{\s*(?:petit|small)\s*\|([^}]*)\}\}", r"\1", s, flags=re.I)
    s = re.sub(r"\{\{\s*date\s*\|([^}]*)\}\}", lambda m: " ".join(m.group(1).split("|")), s, flags=re.I)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"</?[a-zA-Z][^>]*>", "", s)
    s = s.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------- dates
def _iso(y, m=None, d=None):
    if not y:
        return None
    if m and d:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    if m:
        return f"{int(y):04d}-{int(m):02d}"
    return f"{int(y):04d}"


_FULL = re.compile(rf"\b(\d{{1,2}})(?:er)?\s+({_MONTH_RE})\s+(\d{{4}})", re.I)
_MONTHYEAR = re.compile(rf"\b({_MONTH_RE})\s+(\d{{4}})", re.I)
_YEAR = re.compile(r"(?<!\d)(1[6-9]\d{2}|20\d{2})(?!\d)")


def _normalize_date_templates(s: str) -> str:
    """{{date|5|février|2009}} -> '5 février 2009' ; {{Date|16 mai 2017}} -> '16 mai 2017'."""

    def sub(m):
        parts = [p.strip() for p in m.group(1).split("|") if "=" not in p]
        if len(parts) >= 3 and parts[0].isdigit():
            mo = parts[1]
            if mo.isdigit():
                mo = [k for k, v in MONTHS.items() if v == int(mo)][0]
            return f"{int(parts[0])} {mo} {parts[2]}"
        return " ".join(parts)

    s = re.sub(r"\{\{\s*(?:date|Date|1er)\s*\|([^{}]*)\}\}", sub, s)
    s = re.sub(r"\{\{\s*(?:date|Date)\s*\|([^{}]*)\}\}", sub, s)
    return s


def find_dates(s: str) -> list[str]:
    """Toutes les dates (ISO partiel) d'un fragment, dans l'ordre d'apparition."""
    s = strip_noise(s)
    s = _normalize_date_templates(s)
    s = _LINK.sub(lambda m: (m.group(2) or m.group(1)), s)
    found = []  # (position, iso)
    taken = []
    for m in _FULL.finditer(s):
        found.append((m.start(), _iso(m.group(3), MONTHS[m.group(2).lower()], m.group(1))))
        taken.append((m.start(), m.end()))
    for m in _MONTHYEAR.finditer(s):
        if any(a <= m.start() < b for a, b in taken):
            continue
        found.append((m.start(), _iso(m.group(2), MONTHS[m.group(1).lower()])))
        taken.append((m.start(), m.end()))
    for m in _YEAR.finditer(s):
        if any(a <= m.start() < b for a, b in taken):
            continue
        found.append((m.start(), _iso(m.group(1))))
    found.sort()
    return [d for _, d in found if d]


def find_span(s: str) -> tuple[str | None, str | None]:
    """Intervalle (debut, fin) d'une mention du type '(2011-2017)', 'depuis 2017', 'jusqu'en 2020'."""
    t = plain_for_dates(s)
    ds = find_dates(t)
    low = t.lower()
    if re.search(r"depuis|à partir de|a partir de|« depuis|\(\s*\d{4}\s*[-–—]\s*\)|\d{4}\s*[-–—]\s*\)", low) and ds:
        return ds[0], None
    if re.search(r"jusqu|avant", low) and ds and not re.search(r"depuis", low):
        return None, ds[-1]
    if len(ds) >= 2 and re.search(r"[-–—]|à|puis", low):
        return ds[0], ds[1]
    if len(ds) == 1:
        # '(2017)' seul : date d'evenement (debut = fin = evenement)
        return ds[0], ds[0]
    return None, None


def plain_for_dates(s: str) -> str:
    s = strip_noise(s)
    s = _normalize_date_templates(s)
    s = re.sub(r"\{\{\s*(?:petit|small)\s*\|([^}]*)\}\}", r"\1", s, flags=re.I)
    s = re.sub(r"</?small>", "", s, flags=re.I)
    return s


# ------------------------------------------------------- positionnement
SPECTRUM = {
    "extreme_gauche": -3,
    "gauche": -2,
    "centre_gauche": -1,
    "centre": 0,
    "centre_droit": 1,
    "droite": 2,
    "extreme_droite": 3,
}


def position_code(text: str) -> str | None:
    t = text.lower().replace("-", " ").replace("é", "e").replace("è", "e").replace("ê", "e")
    t = re.sub(r"\s+", " ", t)
    if "extreme gauche" in t or "gauche radicale" in t:
        return "extreme_gauche"
    if "extreme droite" in t:
        return "extreme_droite"
    if "centre gauche" in t:
        return "centre_gauche"
    if "centre droit" in t or "centre droite" in t:
        return "centre_droit"
    if "centrisme" in t or re.search(r"\bcentre\b", t):
        return "centre"
    if "droite" in t:
        return "droite"
    if "gauche" in t:
        return "gauche"
    return None
