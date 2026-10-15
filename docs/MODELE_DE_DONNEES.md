# Modèle de données

Le graphe de connaissances est stocké dans `data/graph/`. Il se compose de deux types de
noeuds (organisations, personnes) et de deux couches d'arêtes. Le fichier de référence est
`graph.json` (`{"nodes": [...], "edges": [...]}`), prêt à être chargé par une page web ;
`nodes.json` et `edges.json` contiennent les mêmes données séparées, et les fichiers CSV sont
des exports à plat pour un tableur ou un notebook.

## Noeud organisation (`type = "org"`)

Un parti, un mouvement, une coalition, un courant, un mouvement de jeunesse, etc.

| Champ | Contenu |
|---|---|
| `id` | identifiant stable, `org:<titre-de-la-page-en-minuscules-sans-accents>` |
| `kind` | `party`, `movement`, `coalition`, `current`, `youth`, `micro_party`, `parliamentary_group` |
| `title`, `name` | titre de la page Wikipédia ; nom d'usage (champ « nom » de l'infobox) |
| `abbreviations` | sigles détectés dans la première phrase (PS, RN, LFI...) |
| `qid`, `url` | identifiant Wikidata ; lien vers la page Wikipédia |
| `start`, `end` | dates ISO partielles (`1969`, `1972-10`, `1972-10-05`) ; `end` vide si toujours actif |
| `start_precision`, `end_precision` | `year`, `month` ou `day` |
| `start_alternatives` | autres dates de fondation rencontrées (changements de nom, désaccords entre sources) |
| `status` | `actif`, `dissous`, `fusionne` (a fusionné dans un autre), `transforme` (devenu un autre) |
| `scope` | `coeur` (existe en 1958 ou après) ou `ancetre` (disparu avant 1958 mais relié au coeur) |
| `summary` | premier paragraphe de l'introduction de la page (texte Wikipédia) |
| `position_value` | position gauche-droite de -3 (extrême gauche) à +3 (extrême droite) ; vide si inconnue |
| `position_codes` | `extreme_gauche`, `gauche`, `centre_gauche`, `centre`, `centre_droit`, `droite`, `extreme_droite` |
| `position_source` | `infobox` (déclarée par Wikipédia) ou `categories` (déduite) |
| `position_history` | toutes les positions rencontrées dans l'infobox, avec leur contexte et leurs dates |
| `families` | familles politiques (plusieurs possibles) : communiste, trotskiste, socialiste, écologiste, etc. |
| `ideologies` | liens d'idéologie de l'infobox |
| `eu_affiliation`, `intl_affiliation` | affiliations européenne et internationale |
| `leaders_listed` | dirigeants cités dans l'infobox |
| `sitelinks`, `degree`, `persons_linked`, `importance` | nombre de langues Wikidata, nombre de relations entre organisations, nombre de personnes rattachées, score combiné |
| `peripheral` | vrai pour une organisation d'abord étrangère mais reliée à la France (partis basques espagnols, mouvements coloniaux) ; jamais au niveau de zoom macro |
| `tier` | niveau de zoom : 1 = macro (grands partis), 2 = intermédiaire, 3 = détail |
| `france_evidence` | pourquoi l'entité est considérée comme française |
| `flags` | avertissements sur la qualité de cette fiche |

## Noeud personne (`type = "person"`)

`id` (`per:<titre>`), `title`, `name`, `qid`, `url`, `born`, `died`, `summary` (première phrase
de la page), `sitelinks`, `degree`, `importance`, `tier`.

## Arêtes organisation vers organisation (`layer = "org_org"`)

| `type` | Sens (`source` vers `target`) | Date |
|---|---|---|
| `split` | parti d'origine vers parti issu de la scission | `date` de la scission |
| `merge` | parti qui fusionne vers parti résultant | `date` de la fusion |
| `succession` | ancien parti vers parti qui le remplace (renommage, refondation) | `date` si connue |
| `affiliation` | membre vers coalition ou structure d'appartenance (NUPES, Front populaire...) | `start` / `end` |

Chaque arête porte `confidence` (`confirmee_2_pages` si les deux pages concernées l'affirment,
`une_page` sinon), `evidence` (page, champ d'infobox et texte d'origine), `declared_by_source`
(vrai si la page de l'organisation source l'affirme elle-même, ce qui autorise à en déduire sa fin)
et `flags`.

Le graphe est un multigraphe : deux organisations peuvent être reliées par plusieurs types de
relations (par exemple une scission puis une fusion de retour, comme Parti radical et Mouvement
radical). Des cycles entre types différents sont donc normaux.

## Arêtes personne vers organisation (`layer = "person_org"`)

`type` vaut `member` (adhésion), `leader` (fonction dirigeante : président, secrétaire
général, porte-parole...) ou `founder`. Chaque arête a `start`, `end`, `label` (intitulé de la
fonction ou texte d'origine) et `sources`, qui liste d'où vient l'information
(`wikipedia_infobox_parti`, `wikipedia_infobox_fonction`, `wikipedia_infobox_parti_fondateur`,
`wikipedia_infobox_parti_chef`, `wikidata`).

## Dates

Toutes les dates sont des chaînes ISO partielles : l'année seule est fréquente et c'est
normal, Wikipédia ne donne souvent que l'année. Utiliser `*_precision` pour savoir quoi
afficher. Un champ vide signifie « inconnu » ou, pour `end`, « toujours en cours ».
