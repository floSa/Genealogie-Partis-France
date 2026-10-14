"""Etape 5 - Construction du graphe de connaissances propre.

Entrees : copie locale des pages (pages.sqlite), Wikidata (wd_entities.json,
wd_people.json), decouverte (discovery.json), personnes (people_raw.json) et
corrections manuelles optionnelles (data/overrides.json).

Sorties (data/graph/) :
  nodes.json / edges.json / graph.json   graphe complet
  organisations.csv, people.csv, edges_org.csv, edges_person.csv
Les anomalies et exclusions sont ecrites dans data/review/ par s06_validate.py.

Modele :
  noeud 'org'    : parti, mouvement, coalition, courant... (id 'org:<slug>')
  noeud 'person' : personne (id 'per:<slug>')
  aretes org -> org  : split (parent -> enfant), merge (fusionne -> resultat),
                       succession (ancien -> nouveau), affiliation (membre -> coalition)
  aretes person -> org : member, leader, founder  (dates quand elles existent)
"""
from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict

from client_shortcuts import store
from s02b_snowball import FR_STRICT
from s02_fetch_parties import looks_like_org
from s03_parse_parties import parse_party
from s04b_people import LEADER_ROLE, NOT_PARTY_ROLE
from wikiclient import RAW, ROOT
from wikiparse import SPECTRUM, find_dates, plain, split_br, strip_noise


def name_changes_from(founded_raw: str):
    """Noms successifs d'un meme parti d'apres le champ 'fondation' de l'infobox, ex.
    '5 octobre 1972 (FN)<br>1er juin 2018 (RN)' -> [{'date': '1972-10-05', 'label': 'FN'}, ...]."""
    out = []
    for seg in split_br(strip_noise(founded_raw or "")):
        ds = find_dates(seg)
        if not ds:
            continue
        txt = plain(seg)
        m = re.search(r"\(([^()]{1,60})\)", txt)
        label = m.group(1).strip() if m else ""
        if not label:
            continue
        # on ignore les precisions du type '(association)', '(parti)'
        if re.fullmatch(r"(association|parti|mouvement|premi[èe]re fois|refondation)", label, re.I):
            continue
        if re.search(r"lancement|congr[èe]s|enregistrement|appel|coalition|parti politique|tendance|courant|"
                     r"section|branche|autonome|fondation|association|fusion|scission", label, re.I):
            continue
        out.append({"date": ds[0], "label": label})
    return out if len({o["date"] for o in out}) >= 2 else []

G = ROOT / "data" / "graph"
REVIEW = ROOT / "data" / "review"
FRANCE_QID = "Q142"
PARTY_QS = {"Q7278"}  # parti politique
YEAR_MIN_SCOPE = 1958

# ----------------------------------------------------------------- utilitaires


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:80] or "x"


def year_of(iso):
    return int(iso[:4]) if iso else None


def precision(iso):
    return None if not iso else ("year" if len(iso) == 4 else "month" if len(iso) == 7 else "day")


def wd_date(v):
    """Date SPARQL Wikidata -> ISO partiel fiable, sinon None (valeur inconnue = noeud anonyme)."""
    if not v:
        return None
    m = re.match(r"^\+?(\d{4})-(\d\d)-(\d\d)", v)
    if not m:
        return None
    y, mo, d = m.groups()
    if mo == "01" and d == "01":
        return y  # 1er janvier : precision annuelle probable
    return f"{y}-{mo}-{d}"


def wp_url(title):
    return "https://fr.wikipedia.org/wiki/" + title.replace(" ", "_")


def first_para(intro: str, n=900) -> str:
    for line in intro.split("\n"):
        line = line.strip()
        if len(line) > 60:
            return line[:n]
    return intro.strip()[:n]


# --------------------------------------------------------------- familles
FAMILY_RULES = [
    ("communiste", r"communis|marxisme-l[ée]ninisme|stalin|l[ée]nin"),
    ("trotskiste", r"trotsk"),
    ("maoiste", r"ma[oö]ï?s"),
    ("anarchiste_libertaire", r"anarch|libertaire|syndicalisme r[ée]volutionnaire"),
    ("extreme_gauche_autre", r"alter ?mondialis|anticapitalis|gauchisme|r[ée]volutionnaire"),
    ("socialiste", r"socialis(?!te unifi)|social-d[ée]mocra|travailli"),
    ("ecologiste", r"[ée]colog|\bverts?\b|d[ée]croissance"),
    ("radical", r"radical|radicalisme"),
    ("centriste_democrate_chretien", r"d[ée]mocratie chr[ée]tienne|centr(e|iste)|d[ée]mocrate|MRP|d[ée]mocrates?-chr"),
    ("liberal", r"lib[ée]ral|lib[ée]ralisme|lib[ée]taria"),
    ("gaulliste", r"gaull|r[ée]publicain social|rpf|union pour la nouvelle r[ée]publique"),
    ("conservateur_droite", r"conservat|droite"),
    ("souverainiste", r"souverain"),
    ("extreme_droite_nationaliste", r"extr[êe]me droite|nationalis|fascis|n[ée]o-?nazi|identitair|poujad|royalis|monarchis|p[ée]tain|vichy|n[ée]ofascis"),
    ("regionaliste_autonomiste", r"autonomis|r[ée]gionalis|ind[ée]pendantis|nationalisme (basque|breton|corse|kanak|alsacien)|abertzale|kanak|tahiti|polyn[ée]sien|mahorais"),
    ("agrarien_rural", r"agrari|rural|paysan|chasse"),
    ("populiste", r"populis"),
    ("republicain_laique", r"r[ée]publicanisme|la[iï]cit[ée]"),
]
_WORD_START = r"(?<![a-zàâçéèêëîïôûùüÿœ])(?:"
FAMILY_RX = [(n, re.compile(_WORD_START + rx + ")", re.I)) for n, rx in FAMILY_RULES]


def families_of(rec, cats, max_families=3):
    """Familles politiques (au plus 3), dans l'ordre d'importance des idéologies de l'infobox,
    puis des categories d'organisation et du nom. Chaque libelle est teste separement, en debut
    de mot (ainsi 'internationalisme' ne compte pas comme 'nationalisme')."""
    out = []

    def add(label):
        for fam, rx in FAMILY_RX:
            if fam not in out and rx.search(label):
                out.append(fam)

    for ideo in rec.get("ideologies", [])[:8]:
        add(ideo)
    for c in cats:
        c = c.replace("Catégorie:", "")
        if ORG_CAT.search(c) or re.search(r"^(Ancien(ne)? )?parti", c, re.I):
            add(c)
    add(rec.get("name_field", "") or "")
    add(re.sub(r"\s*\([^)]*\)", "", rec["title"]))
    if len(out) < max_families:
        # en dernier recours, la premiere phrase du resume ('... parti d'extreme gauche trotskiste')
        add(first_para(rec.get("intro", ""), 200))
    return out[:max_families]


KIND_RULES = [
    ("coalition", r"coalition|alliance|front populaire|union de la gauche|union des gauches|cartel"),
    ("youth", r"jeunesse|jeunes|[ée]tudiant"),
    ("current", r"courant|tendance|motion|club"),
    ("micro_party", r"micro-parti"),
    ("parliamentary_group", r"groupe politique|groupe parlementaire|intergroupe"),
]


def kind_of(rec, cats):
    cat_text = " ".join(cats)
    if re.search(r"Coalition de partis|Ancienne coalition", cat_text):
        return "coalition"
    if re.search(r"Mouvement de jeunesse", cat_text):
        return "youth"
    if re.search(r"Micro-parti", cat_text):
        return "micro_party"
    first = first_para(rec.get("intro", ""), 300).lower()
    if not rec["has_infobox"] and (rec["title"].startswith("Groupe ") or re.search(r"groupe parlementaire", first[:200])):
        return "parliamentary_group"
    if re.match(r".{0,120}\b(est|était|fut)\b[^.]{0,30}\b(think tank|laboratoire d'idées|cercle de réflexion|fondation)\b", first):
        return "think_tank"
    if not rec["has_infobox"] and re.match(r".{0,120}\b(est|était|fut)\b\s+(une|l')\s*(ancienne\s+)?association\b", first):
        return "association"
    if re.match(r".{0,80}\b(est|était|fut)\b[^.]{0,40}\b(coalition|alliance électorale|cartel)", first):
        return "coalition"
    if re.match(r".{0,100}\b(est|était|fut)\b[^.]{0,40}\bcourant\b", first):
        return "current"
    if re.match(r".{0,100}\b(est|était|fut)\b[^.]{0,40}\b(mouvement de jeunesse|organisation de jeunesse)\b", first):
        return "youth"
    if not rec["has_infobox"]:
        return "movement"
    return "party"


# ------------------------------------------------------------- positionnement


def position_from(rec, cats):
    """-> (valeur numerique -3..3 ou None, codes principaux, source, historique)."""
    cands = rec.get("positions", [])
    hist = [
        {"code": p["code"], "start": p["start"], "end": p["end"], "context": p["context"], "header": p.get("header", "")}
        for p in cands
    ]
    if not cands:
        return None, [], None, hist
    # Segments (un par ligne d'infobox, avec l'intitule de periode qui les precede). Ordre de
    # preference : 'Actuel' ; sinon la derniere periode connue ; les factions et courants internes
    # ne definissent pas la position du parti.
    def tag(p):
        return (p.get("header", "") + " " + p["context"]).strip()

    faction = re.compile(r"faction|courant|tendance|aile |sous-?courant", re.I)
    base = [p for p in cands if not faction.search(p.get("header", ""))] or cands
    cur = [p for p in base if re.search(r"actuel|aujourd|depuis|désormais", p.get("header", "") + " " + p["context"], re.I)]
    if cur:
        pool = cur
    else:
        headers = list(dict.fromkeys(p.get("header", "") for p in base))
        if len(headers) > 1:
            pool = [p for p in base if p.get("header", "") == headers[-1]]  # periode la plus recente
        else:
            pool = base
    # les codes d'un meme segment (ex. 'centre gauche a gauche') forment une plage
    first_ctx = pool[0]["context"]
    group = [p for p in pool if p["context"] == first_ctx] or [pool[0]]
    codes = list(dict.fromkeys(p["code"] for p in group))
    vals = [SPECTRUM[c] for c in codes]
    return round(sum(vals) / len(vals), 2), codes, "infobox", hist


def position_fallback(cats, rec):
    from wikiparse import position_code

    best = []
    for c in cats:
        cc = c.replace("Catégorie:", "")
        if re.search(r"\bde (gauche|droite|centre)|extr[êe]me (gauche|droite)|centre", cc, re.I):
            code = position_code(cc)
            if code:
                best.append(code)
    if best:
        v = [SPECTRUM[c] for c in best]
        return round(sum(v) / len(v), 2), list(dict.fromkeys(best)), "categories"
    return None, [], None


# ------------------------------------------- reconnaissance des organisations
ORG_NOUN = (r"parti|mouvement|courant|coalition|alliance|organisation|groupuscule|f[ée]d[ée]ration|ligue|"
            r"rassemblement|cartel|association|collectif|think tank|cercle|club|front|union|formation|"
            r"tendance|plate-?forme|regroupement|r[ée]seau|bloc|comit[ée]|groupe politique|groupe arm[ée]|"
            r"groupe terroriste|groupe clandestin|structure|ccartel")
ORG_FIRST = re.compile(
    r"^[^.]{0,140}?\b(est|était|fut|sont|étaient|a été)\b[^.]{0,45}?\b(?:un|une|le|la|l'|les|des|d'un|d'une)\s*"
    r"(?:ancien(?:ne)?\s+|petit(?:e)?\s+|ex-)?(?:nouveau\s+|nouvelle\s+)?(?:" + ORG_NOUN + r")s?\b", re.I)
PERSON_TEXT = re.compile(
    r"\b(né|née) le\b|\b(est|était|fut)\s+(un|une)\s+(ancien\s+|ancienne\s+)?(homme|femme|personnalité|"
    r"député|députée|sénateur|sénatrice|maire|avocat|avocate|journaliste|écrivain|écrivaine|historien|"
    r"historienne|syndicaliste|poète|philosophe|général|militant|militante|résistant|résistante|ministre|"
    r"haut fonctionnaire|universitaire|professeur|économiste|éditeur|dirigeant|théoricien)\b", re.I)
POL_WORDS = re.compile(r"politi|[ée]lector|[ée]lectoral|trotsk|commun|socialis|lib[ée]ral|[ée]colog|nationalis|souverain|"
                       r"r[ée]gional|autonom|ind[ée]pendanti|gaull|centr|droite|gauche|anarch|royalis|fascis|ma[oö]ï|marxis|"
                       r"radical|d[ée]mocrat|r[ée]publicain|identitaire|syndicalis|alter ?mondial|anticapital", re.I)
NOT_ORG_TITLE = re.compile(
    r"^(Liste|Chronologie|Histoire|Élections?|Affaire|Primaire|Loi|Lois|Congr[èe]s|\d+[ee]r?e? congr|"
    r"Conseil (r[ée]gional|d[ée]partemental|g[ée]n[ée]ral|municipal)|Groupe parlementaire|"
    r"(Mouvance|Nationalisme|R[ée]gionalisme|Autonomisme|S[ée]paratisme|Ind[ée]pendantisme|Souverainisme|"
    r"Gauchisme|Courants politiques|Histoire) |"
    r"^(Communaut[ée]|M[ée]tropole|[ÉE]tablissement public|Assembl[ée]e|Moulins|UMPS|[ÉE]l[ée]phant|"
    r"Nous les gar|Gaullisme)\b|"
    r"^(F[êe]te|Soir[ée]es?|Compagnonnage|Crise|Convention du|Micro-parti|Social-[ée]cologie|Arc r[ée]publicain|"
    r"D[ée]centralisation|Coop[ée]rative|B17|Mouvement ondulatoire|Sarreguemines)\b|"
    r"(Droite|Gauche|Centre|Extr[êe]me gauche|Extr[êe]me droite|Divers droite|Divers gauche|Divers centre|Centrisme)"
    r"( en France| politique)?$|"
    r"Manifeste|D[ée]diabolisation|Financement|Alliances? [ée]lectorales)|"
    r"\b(congr[èe]s|affaire|primaire|hebdomadaire|quotidien|magazine|[ée]ditions|film|livre)\b|"
    r"isme( politique)?( en France)?$", re.I)


ORG_WORD = r"(parti|mouvement|organisation|coalition|association|f[ée]d[ée]ration|groupe|courant|ligue|collectif|think tank)"
REGIONAL = (r"corse|breton|bretagne|alsac|savoy|occitan|kanak|cal[ée]donien|polyn[ée]sien|tahitien|mahorais|"
            r"r[ée]unionnais|martiniquais|guadeloup|guyan|antillais|lorrain|normand|fran[cç]ais(e)?\b|"
            r"Nouvelle-Cal[ée]donie|Polyn[ée]sie|La R[ée]union|Mayotte|Saint-Martin|Saint-Pierre|Wallis|Outre-mer|Tahiti")
PERIPHERAL_CAT = re.compile(
    r"\b(en|au|aux|du|de) (Espagne|Alg[ée]rie|Tunisie|Maroc|Italie|Allemagne|Belgique|Suisse|Royaume-Uni|Catalogne|"
    r"Cameroun|S[ée]n[ée]gal|Comores|Madagascar)\b|Pays basque espagnol|Navarre|Euskadi", re.I)
FR_ORG_CAT = re.compile(
    ORG_WORD + r"[^,]{0,60}?(en France|\(France\)|" + REGIONAL + r")|"
    r"^(Catégorie:)?(Ancien |Ancienne )?" + ORG_WORD + r" (corse|breton|alsacien|savoyard|occitan|kanak|calédonien|polynésien|mahorais|réunionnais|martiniquais|guadeloupéen|guyanais)",
    re.I)
FOREIGN_ORG_CAT = re.compile(
    ORG_WORD + r"[^,]{0,60}?\b(en|au|aux|de) (Espagne|Italie|Allemagne|Belgique|Suisse|Alg[ée]rie|Tunisie|Maroc|"
    r"Catalogne|Royaume-Uni|Portugal|Su[èe]de|Pologne|S[ée]n[ée]gal|Cameroun|Madagascar|Comores|Vi[êe]t ?Nam|"
    r"Pays basque espagnol|Navarre|Euskadi|Autriche|Russie|URSS|Union europ[ée]enne|Europe)\b|"
    r"europ[ée]en(ne)?\b", re.I)

PERSON_CAT = re.compile(
    r"^(Catégorie:)?(Naissance en|Décès en|Personnalité|Député|Sénateur|Ministre|Maire |Conseiller|Élu |"
    r"Écrivain|Journaliste|Résistant|Militant|Dirigeant|Candidat|Secrétaire|Président )", re.I)
ORG_CAT = re.compile(
    r"^(Ancien(ne)? )?parti politique|^(Ancien(ne)? )?micro-parti|^(Ancien(ne)? )?coalition de partis|"
    r"^Courant (du|de la|de l'|des|de) |"
    r"^Mouvement de jeunesse|^(Ancien(ne)? )?(organisation|mouvement|association|groupe|groupuscule|"
    r"courant|alliance|organisme)[^()]{0,60}?(politique|trotskiste|communiste|anarchiste|ma[oö]ïste|"
    r"socialiste|libertaire|nationaliste|royaliste|écologiste|régionaliste|autonomiste|indépendantiste|"
    r"d'extrême (droite|gauche)|de gauche|de droite|de jeunesse|souverainiste|identitaire)", re.I)
NOT_ORG_CAT = re.compile(
    r"journal|presse|média|syndic|congrès|affaire|élection|primaire|film|livre|bande dessinée|"
    r"internationale|parlement|gouvernement|assemblée|commission|ministère|histoire de|idéologie|"
    r"théorie|doctrine|concept", re.I)
UNION_ONLY = re.compile(r"syndic|confédération (générale|nationale) du travail|confédération du travail", re.I)


def strict_org(rec) -> bool:
    if rec["has_infobox"]:
        return True
    title = rec["title"]
    if NOT_ORG_TITLE.search(re.sub(r"\s*\([^)]*\)", "", title)):
        return False
    cats = [c.replace("Catégorie:", "") for c in rec.get("cats", [])]
    if any(PERSON_CAT.match(c) for c in cats):
        return False
    if any(re.search(r"Titre de presse|Presse |Maison d'édition|Média|Syndicat|Conseil r[ée]gional", c) for c in cats):
        return False
    first = first_para(rec.get("intro", ""), 500)
    if not first:
        return False
    if UNION_ONLY.search(title) or (UNION_ONLY.search(first[:200]) and not re.search(r"parti", first[:200], re.I)):
        return False
    cat_org = any(ORG_CAT.search(c) and not NOT_ORG_CAT.search(c) for c in cats)
    if PERSON_TEXT.search(first[:220]):
        return False
    if cat_org and POL_WORDS.search(first[:500]):
        return True
    m = ORG_FIRST.search(first)
    if not m:
        return False
    return bool(POL_WORDS.search(first[: m.end() + 160]))


# ------------------------------------------- regles souples (second passage)
SOFT_ORG = re.compile(
    r"\b(est|était|fut|sont|étaient)\b[^.]{0,60}?\b(un|une|le|la|l'|les|d'un|d'une)\s*"
    r"(?:ancien(?:ne)?\s+|petit(?:e)?\s+|nouveau\s+|nouvelle\s+)?"
    r"(parti|mouvement|courant|coalition|alliance|organisation|groupuscule|groupe|collectif|club|cercle|"
    r"rassemblement|tendance|plate-?forme|front|comit[ée]|f[ée]d[ée]ration|ligue|association|formation|"
    r"think tank|laboratoire d'id[ée]es|r[ée]seau)\b", re.I)
SOFT_REJECT = re.compile(
    r"\b(journal|revue|hebdomadaire|quotidien|mensuel|bimestriel|magazine|chanson|film|librairie|bar|"
    r"maison d'[ée]dition|[ée]ditions|commune|d[ée]partement|assembl[ée]e|commission|gouvernement|[ée]lection|"
    r"primaire|congr[èe]s|affaire|loi|trait[ée]|essai|syndicat|syndicale|confédération|organisation non gouvernementale|"
    r"agence|institution|intercommunal\w*|communauté (d'agglomération|de communes|urbaine)|parlement européen|"
    r"union européenne|internationale|société de communication|établissement|université|radio|chaîne|collectivité|"
    r"groupe parlementaire|groupe politique du Parlement|publication|n[ée]ologisme|expression|surnom|[ée]tiquette|"
    r"m[ée]tropole|conseil|r[ée]sistance|maquis)\b", re.I)
FRANCE_WORDS = re.compile(
    r"\b(fran[cç]ais(e|es)?|France|Nouvelle-Cal[ée]donie|Polyn[ée]sie|Corse|corse|Bretagne|breton(ne)?|Alsace|"
    r"Guadeloupe|Martinique|Guyane|La R[ée]union|Mayotte|Tahiti|Savoie|occitan(e)?|kanak)\b")
FOREIGN_WORDS = re.compile(
    r"\b(espagnol(e)?|italien(ne)?|allemand(e)?|portugais(e)?|belge|britannique|n[ée]erlandais(e)?|catalan(e)?|"
    r"alg[ée]rien(ne)?|tunisien(ne)?|marocain(e)?|camerounais(e)?|comorien(ne)?|s[ée]n[ée]galais(e)?|"
    r"d[ée]ho?m[ée]en(ne)?|b[ée]ninois(e)?|vietnamien(ne)?|africain(e)?|europ[ée]en(ne)?|international(e)?|"
    r"russe|sovi[ée]tique|am[ée]ricain(e)?|suisse|libanais(e)?|guin[ée]en(ne)?|ivoirien(ne)?|malgache)\b", re.I)
PRE58 = re.compile(r"Troisi[èe]me R[ée]publique|Second Empire|monarchie de Juillet|Deuxi[èe]me R[ée]publique|"
                   r"Restauration|R[ée]volution fran[cç]aise|Premier Empire|XIXe si[èe]cle|Ancien R[ée]gime", re.I)


def soft_org(rec) -> bool:
    """Second passage : organisations politiques que la regle stricte a ratees (premiere phrase
    de forme inhabituelle), sans personne, evenement, media, syndicat ni institution."""
    if rec["has_infobox"]:
        return True
    title = rec["title"]
    if NOT_ORG_TITLE.search(re.sub(r"\s*\([^)]*\)", "", title)):
        return False
    cats = [c.replace("Catégorie:", "") for c in rec.get("cats", [])]
    if any(PERSON_CAT.match(c) for c in cats):
        return False
    first = first_para(rec.get("intro", ""), 400)
    if not first or PERSON_TEXT.search(first[:220]) or SOFT_REJECT.search(first[:160]):
        return False
    m = SOFT_ORG.search(first)
    return bool(m) and bool(POL_WORDS.search(first[:300]))


def intro_france(rec) -> bool:
    first = first_para(rec.get("intro", ""), 260)
    return bool(FRANCE_WORDS.search(first)) and not FOREIGN_WORDS.search(first)


def date_from_intro(intro: str):
    """(debut, fin) tires du premier paragraphe quand l'infobox est muette. Prudent : un seul
    motif reconnu, annee entre 1789 et 2026."""
    first = first_para(intro, 700)
    ok = lambda y: 1789 <= int(y) <= 2026
    m = re.search(r"\b(?:de|entre|en|depuis)\s+(\d{4})\s*(?:à|et|-|–|jusqu'en)\s*(\d{4})", first)
    if m and ok(m.group(1)) and ok(m.group(2)) and int(m.group(1)) <= int(m.group(2)):
        return m.group(1), m.group(2)
    m = re.search(r"\b(?:fond[ée]e?|cr[ée]{1,2}e?|constitu[ée]e?|lanc[ée]e?|form[ée]e?|structur[ée]e?|apparue?|"
                  r"organis[ée]e?|issue?|n[ée]e?|ouverte?)\s+(?:officiellement\s+)?(?:en|le|au|à|dès|par|pour)\b[^.\d]{0,45}"
                  r"(?:\d{1,2}(?:er)?\s+)?(?:[a-zéû]+\s+)?(\d{4})", first, re.I)
    if m and ok(m.group(1)):
        return m.group(1), None
    m = re.search(r"[ée]lections?[^.]{0,70}?\b(\d{4})\b", first)
    if m and ok(m.group(1)):
        return m.group(1), None
    m = re.search(r"\bdepuis\s+(?:le\s+)?(?:\d{1,2}(?:er)?\s+)?(?:[a-zéû]+\s+)?(\d{4})", first)
    if m and ok(m.group(1)):
        return m.group(1), None
    return None, None


# --------------------------------------------------------------------- main


def main():
    ps = store()
    overrides = {}
    op = ROOT / "data" / "overrides.json"
    if op.exists():
        overrides = json.loads(op.read_text(encoding="utf-8"))
    disc = json.loads((RAW / "discovery.json").read_text(encoding="utf-8"))
    wde = json.loads((RAW / "wd_entities.json").read_text(encoding="utf-8")) if (RAW / "wd_entities.json").exists() else {}
    wdp = json.loads((RAW / "wd_people.json").read_text(encoding="utf-8"))
    strong = {t for t, d in disc["candidates"].items() if set(d["sources"]) & {"wikidata", "category_tree"}}
    promoted = set(json.loads((RAW / "promoted.json").read_text(encoding="utf-8"))) if (RAW / "promoted.json").exists() else set()
    exclude = set(overrides.get("exclude", []))
    include = set(overrides.get("include", []))

    # ---------------------------------------------------------- 1. selection
    recs, excluded = {}, []
    for t in sorted(ps.all_titles("full")):
        page = ps.get(t)
        rec = parse_party(page)
        cats = ps.categories(t)
        rec["cats"] = cats
        strict = strict_org(rec)
        org = strict or soft_org(rec) or t in include
        if not org:
            excluded.append((t, "pas_une_organisation"))
            continue
        rec["soft"] = not strict and t not in include
        if t in exclude:
            excluded.append((t, "exclu_manuellement"))
            continue
        wd = wde.get(rec["qid"] or "", {})
        ev = []
        if FRANCE_QID in wd.get("p17", []):
            ev.append("wikidata_p17")
        if "wikidata" in disc["candidates"].get(t, {}).get("sources", []):
            ev.append("decouverte_wikidata_france")
        if any(FR_ORG_CAT.search(c) for c in cats):
            ev.append("categorie_organisation_francaise")
        if t in include:
            ev.append("inclus_manuellement")
        foreign_wd = bool(wd.get("p17")) and FRANCE_QID not in wd["p17"]
        foreign_cat = any(FOREIGN_ORG_CAT.search(c) for c in cats)
        if ("category_tree" in disc["candidates"].get(t, {}).get("sources", [])
                and any(ORG_CAT.search(c.replace("Catégorie:", "")) for c in cats) and not foreign_cat and not foreign_wd):
            ev.append("arbre_categories_france")
        if not ev and intro_france(rec) and not foreign_cat and not foreign_wd:
            ev.append("resume_mentionne_la_france")
        if not ev:
            excluded.append((t, "pas_de_preuve_france"))
            continue
        strongest ={"wikidata_p17", "inclus_manuellement", "categorie_organisation_francaise"}
        if (foreign_wd or foreign_cat) and not (strongest & set(ev)):
            excluded.append((t, "pays_etranger"))
            continue
        rec["france_evidence"] = ev
        rec["wd"] = wd
        recs[t] = rec

    # ------------------------------------------------------------- 2. dates
    for t, rec in recs.items():
        wd = rec["wd"]
        fd = rec["founded_dates"]
        dd = rec["dissolved_dates"]
        wd_inc = wd.get("inc", [])
        wd_dis = wd.get("dis", [])
        start = fd[0] if fd else (min(wd_inc) if wd_inc else None)
        rec["start_alt"] = sorted(set(fd[1:] + wd_inc) - {start})
        end = dd[-1] if dd else (max(wd_dis) if wd_dis else None)
        rec["flags"] = []
        if not fd and wd_inc:
            rec["flags"].append("fondation_depuis_wikidata")
        # categories Wikipedia : 'Parti politique fondé en 1971', 'Parti politique disparu en 1981'
        cat_names = [c.replace("Catégorie:", "") for c in rec["cats"]]
        press = re.compile(r"presse|titre de|conseil|revue|journal", re.I)
        if not start:
            for c in cat_names:
                m = re.search(r"fond[ée]e? en (\d{4})", c)
                if m and not press.search(c):
                    start = m.group(1)
                    rec["flags"].append("fondation_depuis_categorie")
                    break
        if not end:
            for c in cat_names:
                m = re.search(r"dispar(?:u|ue) en (\d{4})", c)
                if m and not press.search(c):
                    end = m.group(1)
                    rec["flags"].append("fin_depuis_categorie")
                    break
        rec["ended_cat"] = any(
            (re.match(r"(Ancien|Ancienne)\b", c) or re.search(r"dispar", c)) and not press.search(c)
            for c in cat_names
        )
        # dernier recours : dates mentionnees dans le premier paragraphe ('de 1997 a 2002', 'fondee en 1996')
        if not start:
            a, b = date_from_intro(rec.get("intro", ""))
            if a:
                start = a
                rec["flags"].append("fondation_depuis_resume")
                if b and not end:
                    end = b
                    rec["flags"].append("fin_depuis_resume")
        # verbe au passe dans la premiere phrase ('etait un parti...') : organisation disparue
        if re.search(r"\b(était|étaient|fut|furent|a existé|ont existé)\b", first_para(rec.get("intro", ""), 200)):
            rec["ended_cat"] = True
        ovd = overrides.get("org", {}).get(t, {})
        if "start" in ovd:
            start = ovd["start"] or None
            rec["flags"].append("date_de_debut_manuelle")
        if "end" in ovd:
            end = ovd["end"] or None
            rec["flags"].append("date_de_fin_manuelle")
        rec["start"], rec["end"] = start, end
        if rec.get("soft"):
            rec["flags"].append("inclus_par_regle_souple")
        if not start:
            rec["flags"].append("sans_date_de_fondation")
        # division : fondation multiple (ex. SFIO 1905 puis PS 1969) -> voir passe 4

    # ------------------------------------------------------------ 3. aretes
    resolve = ps.resolve
    node_of = {t: "org:" + slug(t) for t in recs}
    # collisions de slug
    seen = Counter(node_of.values())
    for t, nid in list(node_of.items()):
        if seen[nid] > 1:
            node_of[t] = nid + "-" + (recs[t]["qid"] or str(abs(hash(t)) % 10000)).lower()

    raw_edges = defaultdict(lambda: {"evid": [], "sides": set()})
    unresolved = []
    for t, rec in recs.items():
        p = node_of[t]
        for rel in rec["relations"]:
            tgt = resolve(rel["target"])
            if tgt == t:
                continue
            if tgt not in recs:
                unresolved.append((t, rel["type"], rel["target"], rel["raw"]))
                continue
            q = node_of[tgt]
            typ = rel["type"]
            if typ == "split_from":
                key, side = ("split", q, p), "dst"
            elif typ == "split_into":
                key, side = ("split", p, q), "src"
            elif typ == "merged_from":
                key, side = ("merge", q, p), "dst"
            elif typ == "merged_into":
                key, side = ("merge", p, q), "src"
            elif typ == "predecessor":
                key, side = ("succession", q, p), "dst"
            elif typ == "successor":
                key, side = ("succession", p, q), "src"
            elif typ == "affiliated_to":
                key, side = ("affiliation", p, q), "src"
            elif typ == "coalition_of":
                key, side = ("affiliation", q, p), "dst"
            else:
                continue
            e = raw_edges[key]
            e["sides"].add(side)
            e["evid"].append({"page": t, "field": rel["field"], "start": rel["start"], "end": rel["end"], "raw": rel["raw"]})

    edges = []
    for (typ, a, b), e in raw_edges.items():
        starts = [x["start"] for x in e["evid"] if x["start"]]
        ends = [x["end"] for x in e["evid"] if x["end"]]
        flags = []
        if len({s[:4] for s in starts}) > 1:
            flags.append("dates_contradictoires")
        # pour split/merge/succession, start == end == date de l'evenement
        date = min(starts) if starts else None
        edge = {
            "type": typ,
            "source": a,
            "target": b,
            "date": date if typ != "affiliation" else None,
            "start": min(starts) if starts and typ == "affiliation" else None,
            "end": max(ends) if ends and typ == "affiliation" and any(x["end"] != x["start"] for x in e["evid"]) else None,
            "confidence": "confirmee_2_pages" if len(e["sides"]) == 2 else "une_page",
            "evidence": [{"page": x["page"], "champ": x["field"], "texte": x["raw"]} for x in e["evid"]][:4],
            "declared_by_source": "src" in e["sides"],
            "flags": flags,
        }
        if typ == "affiliation":
            edge["end"] = max((x["end"] for x in e["evid"] if x["end"] and x["end"] != x["start"]), default=None)
        edges.append(edge)

    # --------------------------------------------- 4. coherence des dates de noeud
    by_id = {node_of[t]: rec for t, rec in recs.items()}
    # fondation multiple : PS (SFIO 1905, PS 1969) -> garder la date coherente avec le predecesseur
    pred_of = defaultdict(list)
    for e in edges:
        if e["type"] in ("succession", "merge"):
            pred_of[e["target"]].append(e["source"])
    for nid, rec in by_id.items():
        fd = rec["founded_dates"]
        if len(fd) > 1 and rec["start"] == fd[0]:
            for pr in pred_of.get(nid, []):
                ps_start = by_id[pr]["start"]
                if ps_start and year_of(ps_start) == year_of(fd[0]):
                    rec["start_alt"] = sorted(set(rec["start_alt"] + [fd[0]]) - {fd[1]})
                    rec["start"] = fd[1]
                    rec["flags"].append("fondation_alignee_sur_le_predecesseur")
                    break
    # fin deduite des fusions et successions
    out_edges = defaultdict(list)
    for e in edges:
        out_edges[e["source"]].append(e)
    # Une fusion ou une succession ne termine un parti que si sa propre page l'affirme
    # ('fusionne dans', 'suivant') ou si Wikipedia le classe comme disparu : sinon il s'agit
    # souvent d'une fusion partielle (ex. le Parti radical, toujours actif).
    for nid, rec in by_id.items():
        if rec["end"]:
            continue
        outs = [e for e in out_edges.get(nid, []) if e.get("declared_by_source") or rec.get("ended_cat")]
        for e in outs:
            if e["type"] == "merge":
                d = e["date"] or by_id[e["target"]]["start"]
                if d:
                    rec["end"] = d
                    rec["flags"].append("fin_deduite_de_la_fusion")
                    break
        if not rec["end"]:
            for e in outs:
                if e["type"] == "succession":
                    d = e["date"] or by_id[e["target"]]["start"]
                    if d and year_of(d) >= (year_of(rec["start"]) or 0):
                        rec["end"] = d
                        rec["flags"].append("fin_deduite_de_la_succession")
                        break
    for nid, rec in by_id.items():
        outs = out_edges.get(nid, [])
        if rec["end"] is None and rec.get("ended_cat"):
            rec["status"] = "dissous"
            rec["flags"].append("fin_inconnue")
        elif rec["end"] is None:
            rec["status"] = "actif"
        elif any(e["type"] == "merge" and (e.get("declared_by_source") or rec.get("ended_cat")) for e in outs):
            rec["status"] = "fusionne"
        elif any(e["type"] == "succession" and (e.get("declared_by_source") or rec.get("ended_cat")) for e in outs):
            rec["status"] = "transforme"
        else:
            rec["status"] = "dissous"

    # coalition sans date : premiere annee a laquelle un parti declare en faire partie
    for nid, rec in by_id.items():
        if rec["start"] is None:
            cands = [e["start"] for e in edges if e["target"] == nid and e["type"] == "affiliation" and e["start"]]
            if cands:
                rec["start"] = min(cands)
                rec["flags"] = [f for f in rec["flags"] if f != "sans_date_de_fondation"] + ["fondation_depuis_relations"]

    # ------------------------------------------------ 5. perimetre temporel
    connected = defaultdict(set)
    for e in edges:
        connected[e["source"]].add(e["target"])
        connected[e["target"]].add(e["source"])
    keep = {}
    dropped_scope = []
    # sans date et manifestement anterieures a 1958 (groupes parlementaires de la IIIe Republique,
    # courants du Second Empire...) : retirees, jamais dessinables
    for nid, rec in by_id.items():
        if rec["start"] is None:
            first = first_para(rec.get("intro", ""), 400)
            old = PRE58.search(first[:300]) and not re.search(r"\b(19[5-9]\d|20\d\d)\b", first[:300])
            if re.search(r"groupe parlementaire", first[:200]) or old:
                rec["drop"] = True
                dropped_scope.append((rec["title"], "sans_date_ancien_ou_groupe_parlementaire"))
    for nid, rec in by_id.items():
        if rec.get("drop"):
            continue
        ey = year_of(rec["end"])
        sy = year_of(rec["start"])
        ended_long_ago = ey is None and rec.get("ended_cat") and sy is not None and sy < 1950
        if (ey is None and not ended_long_ago) or (ey is not None and ey >= YEAR_MIN_SCOPE):
            rec["scope"] = "coeur"
            keep[nid] = rec
    for nid, rec in by_id.items():
        if nid in keep or rec.get("drop"):
            continue
        # anterieur a 1958 : conserve comme ancetre s'il est relie a un noeud du coeur
        if any(n in keep for n in connected[nid]):
            rec["scope"] = "ancetre"
            keep[nid] = rec
        else:
            dropped_scope.append((rec["title"], rec["end"]))
    edges = [e for e in edges if e["source"] in keep and e["target"] in keep]

    # ---------------------------------------------------- 6. attributs de noeud
    deg = Counter()
    for e in edges:
        deg[e["source"]] += 1
        deg[e["target"]] += 1
    nodes_org = []
    for nid, rec in keep.items():
        cats = rec["cats"]
        pv, pcodes, psrc, phist = position_from(rec, cats)
        if pv is None:
            pv, pcodes, psrc = position_fallback(cats, rec)
        fam = families_of(rec, cats)
        wd = rec["wd"]
        sl = wd.get("sl", 0)
        sy, ey = year_of(rec["start"]), year_of(rec["end"])
        years = (ey or 2026) - sy if sy else None
        # annees d'existence pendant la Ve Republique (1958 -> 2026), plafonnees
        years_ve = max(0, min(ey or 2026, 2026) - max(sy or 1958, 1958)) if (ey or 2026) >= 1958 else 0
        score = sl + 2 * deg[nid] + min(years_ve, 40) / 2
        p17 = set(wd.get("p17") or [])
        first_sentence = first_para(rec.get("intro", ""), 220)
        # peripherique : indice etranger dans les categories, pays Wikidata sans la France, ou
        # plusieurs pays (dont la France) avec un adjectif etranger dans la premiere phrase
        peripheral = (
            any(PERIPHERAL_CAT.search(c) for c in cats)
            or (bool(p17) and FRANCE_QID not in p17)
            or (len(p17) > 1 and bool(FOREIGN_WORDS.search(first_sentence)))
        )
        node = {
            "id": nid,
            "type": "org",
            "kind": kind_of(rec, cats),
            "title": rec["title"],
            "name": rec.get("name_field") or rec["title"],
            "abbreviations": rec["abbreviations"],
            "qid": rec["qid"],
            "url": wp_url(rec["title"]),
            "start": rec["start"],
            "start_precision": precision(rec["start"]),
            "start_alternatives": rec["start_alt"],
            "name_changes": [c for c in name_changes_from(rec.get("founded_raw", ""))
                             if rec["start"] and c["date"][:4] >= rec["start"][:4]],
            "end": rec["end"],
            "end_precision": precision(rec["end"]),
            "status": rec["status"],
            "scope": rec["scope"],
            "summary": first_para(rec["intro"]),
            "position_value": pv,
            "position_codes": pcodes,
            "position_source": psrc,
            "position_history": phist,
            "position_raw": rec.get("position_raw", ""),
            "families": fam,
            "ideologies": rec["ideologies"],
            "eu_affiliation": rec["eu_affiliation"],
            "intl_affiliation": rec["intl_affiliation"],
            "leaders_listed": [x["target"] for x in rec["leaders_listed"]],
            "members_raw": rec["members_raw"],
            "sitelinks": sl,
            "degree": deg[nid],
            "importance": round(score, 1),
            "france_evidence": rec["france_evidence"],
            "peripheral": peripheral,
            "wikipedia_categories": [c.replace("Catégorie:", "") for c in cats][:40],
            "flags": rec["flags"],
        }
        ov = overrides.get("org", {}).get(rec["title"], {})
        node.update(ov)
        nodes_org.append(node)

    # position deduite des organisations voisines (membres d'une coalition, scission, successeur)
    # pour celles qui n'ont ni position, ni famille permettant de l'estimer
    FAM_WITH_POS = {"trotskiste", "communiste", "maoiste", "anarchiste_libertaire", "extreme_gauche_autre",
                    "socialiste", "ecologiste", "republicain_laique", "radical", "centriste_democrate_chretien",
                    "liberal", "agrarien_rural", "gaulliste", "conservateur_droite", "souverainiste",
                    "populiste", "extreme_droite_nationaliste"}
    nb = defaultdict(list)
    for e in edges:
        nb[e["source"]].append(e["target"])
        nb[e["target"]].append(e["source"])
    by_node = {n["id"]: n for n in nodes_org}
    n_inferred = 0
    for n in nodes_org:
        if n["position_value"] is not None or FAM_WITH_POS & set(n["families"]):
            continue
        vals = [by_node[x]["position_value"] for x in nb[n["id"]]
                if x in by_node and by_node[x]["position_value"] is not None
                and by_node[x]["position_source"] != "relations"]
        if vals:
            v = round(sum(vals) / len(vals), 2)
            n["position_value"] = v
            n["position_codes"] = [min(SPECTRUM, key=lambda c: abs(SPECTRUM[c] - v))]
            n["position_source"] = "relations"
            n["flags"].append("position_deduite_des_relations")
            n_inferred += 1
    print("positions deduites des relations:", n_inferred)

    # (le niveau de zoom est calcule plus bas, une fois les personnes rattachees connues)

    # ---------------------------------------------------------------- personnes
    title_to_nid = {n["title"]: n["id"] for n in nodes_org}
    people_raw = json.loads((G / "people_raw.json").read_text(encoding="utf-8")) if (G / "people_raw.json").exists() else []
    person_edges = []
    people_nodes = {}
    wd_by_title = {}
    for r in wdp["members"]:
        if r.get("frTitle"):
            wd_by_title.setdefault(ps.resolve(r["frTitle"]), []).append(("member", r))
    for r in wdp["roles"]:
        if r.get("frTitle"):
            wd_by_title.setdefault(ps.resolve(r["frTitle"]), []).append((r["prop"], r))
    qid_to_org = {n["qid"]: n["id"] for n in nodes_org if n["qid"]}

    def add_pedge(pid, oid, role, start, end, source, label=""):
        person_edges.append({"person": pid, "org": oid, "role": role, "start": start, "end": end,
                             "sources": [source], "label": label})

    for pr in people_raw:
        t = pr["title"]
        if t in title_to_nid:
            continue  # titre deja retenu comme organisation (erreur de lien Wikidata)
        pid = "per:" + slug(t)
        found = False
        # adhesions (infobox)
        wiki_parties = set()
        for s in pr["party_spans"]:
            oid = title_to_nid.get(ps.resolve(s["target"]))
            if not oid:
                continue
            add_pedge(pid, oid, "member", s["start"], s["end"] if s["end"] != s["start"] else (s["end"] if re.search(r"\d{4}\s*[-–]\s*\d{4}", s["raw"]) else None), "wikipedia_infobox_parti", s["raw"])
            wiki_parties.add(oid)
            found = True
        # fonctions de direction
        for fn in pr["functions"]:
            if not LEADER_ROLE.search(fn["label"]):
                continue
            for l in fn["links"]:
                oid = title_to_nid.get(ps.resolve(l))
                if not oid:
                    continue
                label = fn["label"]
                if NOT_PARTY_ROLE.search(label) and not re.search(r"parti|mouvement|union|rassemblement|front|ligue|alliance", label, re.I):
                    continue
                if re.search(r"groupe", label, re.I) and not re.search(r"parti", label, re.I):
                    continue
                add_pedge(pid, oid, "leader", fn["start"], fn["end"], "wikipedia_infobox_fonction", label)
                found = True
        # Wikidata (adhesions / fondateurs / dirigeants) - complete les manques
        for kind, r in wd_by_title.get(t, []):
            oid = qid_to_org.get(r["party"])
            if not oid:
                continue
            role = {"member": "member", "founder": "founder", "chair": "leader"}[kind]
            if role == "member" and oid in wiki_parties:
                continue
            add_pedge(pid, oid, role, wd_date(r.get("start")), wd_date(r.get("end")), "wikidata")
            found = True
        wd = wde.get(pr.get("qid") or "", {})
        looks_person = pr.get("has_infobox") or pr.get("born") or wd.get("born")
        if found and not re.fullmatch(r"[\d\s\-–]+", t) and looks_person:
            people_nodes[pid] = {
                "id": pid, "type": "person", "title": t, "name": t.split(" (")[0],
                "qid": pr.get("qid"), "url": wp_url(t),
                "born": pr.get("born") or (wd.get("born") or [None])[0],
                "died": pr.get("died") or (wd.get("died") or [None])[0],
                "summary": pr.get("intro", ""),
                "sitelinks": wd.get("sl") or pr.get("sl") or 0,
                "flags": [],
            }
    # fondateurs cites dans les infobox de partis
    for n in nodes_org:
        rec = by_id[n["id"]]
        for ft in rec["founders_listed"]:
            ft = ps.resolve(ft)
            pid = "per:" + slug(ft)
            if pid in people_nodes:
                add_pedge(pid, n["id"], "founder", n["start"], None, "wikipedia_infobox_parti_fondateur")
        for l in rec["leaders_listed"]:
            pid = "per:" + slug(ps.resolve(l["target"]))
            if pid in people_nodes:
                add_pedge(pid, n["id"], "leader", None, None, "wikipedia_infobox_parti_chef", l.get("title_label", ""))

    # dedoublonnage des aretes personne-organisation
    merged = {}
    for e in person_edges:
        k = (e["person"], e["org"], e["role"])
        m = merged.setdefault(k, None)
        if m is None:
            merged[k] = {**e, "sources": list(e["sources"]), "spans": [(e["start"], e["end"])]}
            continue
        m["sources"] = list(dict.fromkeys(m["sources"] + e["sources"]))
        m["spans"].append((e["start"], e["end"]))
        # on garde l'intervalle le plus precis (le plus de dates renseignees)
        if sum(1 for x in (e["start"], e["end"]) if x) > sum(1 for x in (m["start"], m["end"]) if x):
            m["start"], m["end"] = e["start"], e["end"]
        elif not m["start"] and e["start"]:
            m["start"] = e["start"]
        if e.get("label") and not m.get("label"):
            m["label"] = e["label"]
    person_edges = []
    for (p, o, r), m in merged.items():
        m.pop("spans", None)
        person_edges.append(m)

    # nettoyage des dates de participation incoherentes (naissance, plage plausible, ordre)
    pborn = {pid: year_of(n["born"]) for pid, n in people_nodes.items()}
    n_cleaned = 0
    for e in person_edges:
        flags = []
        b = pborn.get(e["person"])
        for k in ("start", "end"):
            y = year_of(e[k]) if e[k] else None
            if y is not None and (y < 1800 or y > 2027 or (b and y < b + 10)):
                e[k] = None
                flags.append(k + "_incoherent_supprime")
        if e["start"] and e["end"] and year_of(e["end"]) < year_of(e["start"]):
            e["end"] = None
            flags.append("fin_incoherente_supprimee")
        n_cleaned += bool(flags)
        e["flags"] = flags
    print("aretes personne-organisation dont une date incoherente a ete retiree:", n_cleaned)

    # importance des organisations et niveau de zoom (1 = macro ... 3 = detail)
    org_persons = Counter(e["org"] for e in person_edges)
    for n in nodes_org:
        sy, ey = year_of(n["start"]), year_of(n["end"])
        years_ve = max(0, min(ey or 2026, 2026) - max(sy or 1958, 1958)) if (ey or 2026) >= 1958 else 0
        n["persons_linked"] = org_persons[n["id"]]
        n["importance"] = round(n["sitelinks"] + 0.5 * n["degree"] + 0.25 * n["persons_linked"] + min(years_ve, 40) / 4, 1)
        n["tier"] = 3
    NO_MACRO = {"association", "think_tank", "parliamentary_group", "micro_party"}
    ranked = sorted(
        (n for n in nodes_org if n["scope"] == "coeur" and not n["peripheral"] and n["kind"] not in NO_MACRO),
        key=lambda n: -n["importance"],
    )
    for i, n in enumerate(ranked):
        n["tier"] = 1 if i < 40 else 2 if i < 200 else 3
    for n in nodes_org:
        ov = overrides.get("org", {}).get(n["title"], {})
        if "tier" in ov:
            n["tier"] = ov["tier"]

    # importance des personnes
    person_edges = [e for e in person_edges if e["person"] in people_nodes]
    pdeg = Counter(e["person"] for e in person_edges)
    prole = defaultdict(Counter)
    for e in person_edges:
        prole[e["person"]][e["role"]] += 1
    for pid, pn in people_nodes.items():
        pn["degree"] = pdeg[pid]
        r = prole[pid]
        # poids politique : fonctions de direction et fondations comptent plus que la notoriete generale
        pn["importance"] = round(0.2 * pn["sitelinks"] + 6 * (r["leader"] + r["founder"]) + r["member"], 1)
    prank = sorted(people_nodes.values(), key=lambda n: -n["importance"])
    for i, n in enumerate(prank):
        n["tier"] = 1 if i < 150 else 2 if i < 600 else 3
    people_list = [n for n in people_nodes.values() if pdeg[n["id"]] > 0]

    # ------------------------------------------------------------- ecriture
    G.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    nodes_all = nodes_org + people_list
    (G / "nodes.json").write_text(json.dumps(nodes_all, ensure_ascii=False, indent=1), encoding="utf-8")
    all_edges = [dict(e, id=f"e{i}", layer="org_org") for i, e in enumerate(edges)] + [
        {"id": f"p{i}", "layer": "person_org", "type": e["role"], "source": e["person"], "target": e["org"],
         "start": e["start"], "end": e["end"], "sources": e["sources"], "label": e.get("label", ""),
         "flags": e.get("flags", [])}
        for i, e in enumerate(person_edges)
    ]
    (G / "edges.json").write_text(json.dumps(all_edges, ensure_ascii=False, indent=1), encoding="utf-8")
    (G / "graph.json").write_text(json.dumps({"nodes": nodes_all, "edges": all_edges}, ensure_ascii=False), encoding="utf-8")

    def wcsv(path, rows, fields):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in r.items() if k in fields})

    wcsv(G / "organisations.csv", nodes_org, ["id", "kind", "name", "title", "abbreviations", "qid", "start", "end", "status", "scope",
         "position_value", "position_codes", "families", "tier", "importance", "sitelinks", "degree", "url", "summary", "flags"])
    wcsv(G / "people.csv", people_list, ["id", "name", "title", "qid", "born", "died", "tier", "importance", "sitelinks", "degree", "url", "summary"])
    wcsv(G / "edges_org.csv", edges, ["type", "source", "target", "date", "start", "end", "confidence", "flags", "evidence"])
    wcsv(G / "edges_person.csv", person_edges, ["person", "org", "role", "start", "end", "sources", "label"])

    # elements pour la revue
    (REVIEW / "_build_side.json").write_text(json.dumps({
        "excluded": excluded,
        "unresolved_edges": unresolved,
        "dropped_scope": dropped_scope,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter(e["type"] for e in edges)
    print(f"{len(nodes_org)} organisations (coeur={sum(1 for n in nodes_org if n['scope']=='coeur')}), "
          f"{len(people_list)} personnes; aretes org-org: {dict(c)}; personne-org: {len(person_edges)}")
    print(f"exclues: {len(excluded)}; aretes non resolues: {len(unresolved)}; hors perimetre: {len(dropped_scope)}")


if __name__ == "__main__":
    main()
