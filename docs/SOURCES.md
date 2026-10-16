# Sources et requêtes

Ce document dit exactement d'où vient chaque donnée, avec quelles requêtes, et comment vérifier un
chiffre ou une relation du graphe. Rien n'est obtenu ailleurs que sur Wikipédia en français et
Wikidata ; aucune donnée n'est saisie à la main, hormis `data/overrides.json` (lisible et versionné).

## Les deux sources

| Source | Adresse | Ce qu'on en tire | Licence |
|---|---|---|---|
| Wikipédia en français | `https://fr.wikipedia.org/w/api.php` (API MediaWiki) | wikitexte des pages (infobox, introduction), catégories, redirections, liens | texte CC BY-SA 4.0 |
| Wikidata | `https://query.wikidata.org/sparql` et `https://www.wikidata.org/w/api.php` | liste des partis français, adhésions et fonctions avec dates, nombre de versions linguistiques, pays, naissance et décès | CC0 |

Ni dump téléchargé, ni scraping de pages HTML : uniquement les API officielles, qui renvoient du
JSON. Chaque appel est mis en cache dans `data/raw/cache.sqlite` (clé : empreinte de l'URL et des
paramètres), ce qui rend toute la chaîne rejouable hors ligne.

## Politesse envers les serveurs

- une seule requête à la fois, au moins 1,1 seconde entre deux requêtes (`MIN_DELAY` dans
  `pipeline/wikiclient.py`) ;
- en-tête `User-Agent` descriptif (projet personnel non commercial) ;
- paramètre `maxlag=5` sur l'API MediaWiki : le serveur peut demander d'attendre ;
- erreurs 429 et 5xx : nouvelle tentative avec attente croissante, en respectant `Retry-After` ;
- pages demandées par lots de 20 (limite de l'API pour les résumés), jamais une par une.

## Requêtes Wikidata (SPARQL)

Un parti français est un élément dont la nature (P31) est « parti politique » (Q7278) ou l'une de
ses sous-classes, et dont le pays (P17) est la France (Q142).

1. Découverte (`s01_discover.py`) : tous les partis français, avec titre de la page Wikipédia
   française, dates de création (P571) et de dissolution (P576) et nombre de versions
   linguistiques.

```sparql
SELECT ?item ?frTitle ?label ?inc ?dis ?sl WHERE {
  ?item wdt:P31/wdt:P279* wd:Q7278; wdt:P17 wd:Q142.
  ?item wikibase:sitelinks ?sl.
  OPTIONAL { ?item wdt:P571 ?inc }  OPTIONAL { ?item wdt:P576 ?dis }
  OPTIONAL { ?art schema:about ?item; schema:isPartOf <https://fr.wikipedia.org/>; schema:name ?frTitle }
  OPTIONAL { ?item rdfs:label ?label. FILTER(LANG(?label)='fr') }
}
```

2. Adhésions (`s04a_wikidata_people.py`) : les humains rattachés (P102) à l'un de ces partis, avec
   les dates de début (P580) et de fin (P582) de l'adhésion. Même clause de parti, puis
   `?person p:P102 ?st. ?st ps:P102 ?party.` et les qualificateurs de dates.
3. Fondateurs et dirigeants (deux requêtes séparées pour éviter le dépassement de délai du service) :
   `?party p:P112 ?st. ?st ps:P112 ?person.` (fondateur) et `?party p:P488 ?st. ?st ps:P488 ?person.`
   (président ou dirigeant).

4. Relations de filiation (`s04c_wikidata_relations.py`) : pour les mêmes partis, les propriétés P155 et
   P1365 (suit, remplace), P156 et P1366 (suivi par, remplacé par) et P807 (séparé de), filtrées par
   `FILTER(?p IN (wdt:P155, wdt:P156, wdt:P1365, wdt:P1366, wdt:P807))`.

Le nombre de versions linguistiques (`wikibase:sitelinks`) sert d'indice de notoriété.

## Appels à l'API de Wikipédia

| Besoin | Appel | Étape |
|---|---|---|
| Pages utilisant l'infobox de parti | `list=embeddedin`, titre `Modèle:Infobox Parti politique`, `eilimit=500` | s01 |
| Catégories d'une page | `prop=categories`, `cllimit=max`, `clshow=!hidden` | s01, s02b |
| Arbre de catégories | `list=categorymembers`, `cmtype=page|subcat` à partir des racines « Parti politique en France », « Ancien parti politique en France », coalitions, micro-partis, jeunesses, listes (3 niveaux) | s01 |
| Liens des pages de listes | `prop=links`, `pllimit=max`, espace principal | s01 |
| Wikitexte, résumé, identifiant Wikidata | `prop=revisions|extracts|pageprops`, `rvprop=content|ids|timestamp`, `rvslots=main`, `exintro`, `explaintext`, `ppprop=wikibase_item`, `redirects=1` | s02, s02b |
| Introduction seule (économie de requêtes) | même appel avec `rvsection=0` | s02, s04b |
| Redirections | `titles=...&redirects=1` sans contenu | s04b, s02b |
| Enrichissement Wikidata | `action=wbgetentities`, `props=sitelinks|claims|labels` | s02c |

Les racines de catégories explorées figurent dans `ROOT_CATS` (`s01_discover.py`) ; les branches
écartées (personnalités, financement, catégories techniques) dans `SKIP_CAT_RE`.

## Ce qu'on lit dans les pages

**Infobox de parti** (`{{Infobox Parti politique}}`, lue en tolérant les enveloppes
`{{Infobox/Début}}` et `{{Infobox modulaire/Début}}`) :

| Champ | Utilisation |
|---|---|
| `fondation`, `disparition` | dates de naissance et de fin, avec les noms successifs (« 1972 (FN), 2018 (RN) ») |
| `scission de`, `scission dans` | arête `split` (parent vers enfant), avec l'année entre parenthèses |
| `fusion de`, `fusionné dans` | arête `merge` |
| `précédent`, `suivant` | arête `succession` |
| `coalition`, `coalition de`, `coalition dans`, `affi nationale`, `affi française` | arête `affiliation` avec années de début et de fin |
| `positionnement` | position gauche-droite, par période (« Actuel », « Avant 1914 »...) |
| `idéologie` | idéologies, qui servent aux familles politiques |
| `chef`, `dénomination chef` | dirigeant actuel cité |
| `option-N` / `valeur-N` | paires libres : « Fondateurs », « Changement de nom », effectifs... |
| `adherents`, `affi européenne`, `affi internationale` | informations affichées dans la fiche |

**Infobox de personne** (`Infobox Personnalité politique` et voisines) : le champ `parti` (liste de
partis avec années) et les champs `fonctionN` avec `depuis le fonctionN`, `à partir du fonctionN`,
`jusqu'au fonctionN`, ainsi que la naissance et le décès. Seules l'introduction et l'infobox
sont téléchargées (section 0).

**Sections de dirigeants** (`s04d_leaders.py`) : titres de section « Dirigeants », « Présidents », « Premiers
secrétaires », « Secrétaires généraux », « Porte-parole », « Chefs » et les pages citées par
`{{Article détaillé|...}}` ; lignes de tableau (`{|` ... `|-`) et éléments de liste, première personne liée et dates.

**Première phrase de l'introduction** : sert à reconnaître une organisation sans infobox (« est un
parti... »), à repérer un verbe au passé (organisation disparue), à tirer des dates de dernier
recours et des familles en dernier recours.

**Catégories** : « Parti politique fondé en 1971 », « Parti politique disparu en 1981 », « Ancien
parti politique en France », « Courant du Parti socialiste », « Coalition de partis en France »...
servent aux dates de repli, au statut, à la nationalité et à la nature (coalition, jeunesse, courant).

## Vérifier une donnée

Chaque arête du graphe garde ses preuves (exemple simplifié, les champs réels sont dans
`data/graph/edges.json`) :

```json
{ "type": "split", "source": "org:union-pour-un-mouvement-populaire", "target": "org:debout-la-france",
  "date": "2008", "confidence": "confirmee_2_pages",
  "evidence": [ { "page": "Debout la France", "champ": "scission de", "texte": "Union pour un mouvement populaire" },
                { "page": "Union pour un mouvement populaire", "champ": "scission dans", "texte": "Debout la France (2008)" } ] }
```

Pour retrouver la source d'une donnée : ouvrir la page Wikipédia indiquée (`page`), chercher le champ
d'infobox (`champ`). Pour une organisation, `flags` dit comment ses dates ou sa position ont été
obtenues (`fondation_depuis_wikidata`, `fondation_depuis_resume`, `position_deduite_des_relations`,
`inclus_par_regle_souple`...), et `france_evidence` pourquoi elle est jugée française. La copie
locale du wikitexte de chaque page est dans `data/raw/pages.sqlite` (table `pages`).

## Données externes (résultats électoraux, positions d'experts)

| Source | Fichiers | Usage | Citation |
|---|---|---|---|
| ParlGov (parlgov.org) | `view_party.csv`, `party.csv`, `view_election.csv` (dossier `parlgov-development_csv-utf-8`) | partis français, voix et sièges aux législatives et européennes depuis 1958, position gauche-droite composite | Döring, Holger et Philip Manow, *Parliaments and governments database (ParlGov)*, parlgov.org (version de développement) ; conditions d'utilisation à confirmer sur le site avant toute diffusion |
| Chapel Hill Expert Survey (chesdata.eu) | `1999-2024_CHES_dataset_meansV2.csv` | position gauche-droite (`lrgen`), économique (`lrecon`) et société (`galtan`) par année d'enquête | Rovny, Polk, Bakker, Hooghe, Jolly, Marks, Steenbergen et Vachudova, 2025, « The 2024 Chapel Hill Expert Survey on political party positioning in Europe : Twenty-five years of party positional data », *Electoral Studies* 97, doi:10.1016/j.electstud.2025.102981 |

Les fichiers sont dans `data/external/`. Rapprochement (`s04e_external_data.py`) : page Wikipédia anglaise
du parti dans ParlGov, convertie en identifiant Wikidata (`wbgetentities` avec `sites=enwiki`), puis notre
organisation ; repli par sigle ; correspondances manuelles dans `data/overrides.json` (`external_matches`).
CHES est relié à ParlGov par l'identifiant Manifesto (`cmp`). Échelle 0-10 convertie en -3 à +3
(`(x - 5) x 0,6`). Les partis non rapprochés sont listés dans `data/review/externes_non_rapproches.csv`
(surtout des regroupements : « autres de gauche », « sans étiquette »). ParlGov regroupe UMP et Les
Républicains en un seul parti : les résultats sont répartis entre les membres de la lignée selon la date.

## Ce qui n'est pas utilisé

Ni dump complet de Wikipédia, ni moteur de recherche, ni modèle de langage, ni résultats de présidentielles
(absents de ParlGov pour la France), ni résultats détaillés par commune. Le texte des résumés est repris tel quel de Wikipédia (première phrase ou premier
paragraphe), avec renvoi vers la page d'origine.
