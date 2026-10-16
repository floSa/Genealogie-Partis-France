# Méthode

## Principe

Aucun modèle de langage ne lit les pages : tout est extrait par des règles explicites, ce qui
rend l'opération gratuite, reproductible et vérifiable ligne par ligne. Chaque relation du graphe
garde la page, le champ d'infobox et le texte d'origine qui l'ont produite (`evidence`), et chaque
donnée dérivée porte un indicateur (`flags`, `position_source`, `confidence`).

La collecte est polie envers Wikimédia : une requête à la fois, une seconde d'écart au moins,
réponses mises en cache sur disque, respect des délais d'attente demandés par le serveur.

## Reproduire pas à pas

Prérequis : Python 3.10 ou plus, aucune bibliothèque à installer. Depuis la racine du projet :

```bash
python pipeline/run_all.py 1 2 3     # découverte, copie locale des pages de partis, analyse des infobox
python pipeline/run_all.py 4         # personnes : requêtes Wikidata, puis pages des personnes
python pipeline/run_all.py 5 6       # élargissement de proche en proche, enrichissement Wikidata
python pipeline/run_all.py 7 8 9 10  # construction du graphe, contrôle, site, liste à valider
```

Les étapes 1 à 6 interrogent Wikipédia et Wikidata (une à deux heures au total, une requête par
seconde) ; les étapes 7 à 10 travaillent sur la copie locale et prennent quelques secondes. Les
requêtes exactes sont décrites dans `SOURCES.md`, le schéma de la chaîne dans `ARCHITECTURE.md`, les
choix et impasses dans `JOURNAL.md`. Les fichiers `data/raw/*.sqlite` ne sont pas versionnés : sans
eux, les étapes 1 à 6 les reconstruisent ; avec eux, tout se rejoue sans réseau.

## Les étapes

1. `s01_discover.py` : découverte des candidats par trois sources croisées.
   Wikidata (partis dont le pays est la France), toutes les pages utilisant l'infobox de parti
   de Wikipédia (filtrées sur la France d'après leurs catégories), et l'arbre de catégories
   « Parti politique en France » avec les pages de listes de partis.
2. `s02_fetch_parties.py` : copie locale. Wikitexte complet pour les candidats solides ;
   introduction seule pour les incertains, ce qui permet de reconnaître les mouvements sans infobox
   à leur première phrase avant de les télécharger en entier (stratégie économe en requêtes).
3. `s03_parse_parties.py` : lecture des infobox. Relations (scission de / dans, fusion de /
   dans, précédent, suivant, coalition, affiliation) avec leurs dates, dates de fondation et de
   disparition, positionnement, idéologies, fondateurs, dirigeants cités, sigles.
4. `s04a_wikidata_people.py`, `s04b_people.py` : les personnes. Candidats : fondateurs et
   dirigeants cités dans les infobox de partis, fondateurs et présidents de partis dans Wikidata, et
   membres de partis ayant au moins 6 versions linguistiques sur Wikidata (indice de notoriété).
   Seules l'introduction et l'infobox de chaque personne sont lues : champ « parti » (suite de partis
   avec dates) et champs « fonction » (président de..., avec dates).
5. `s02b_snowball.py` : élargissement de proche en proche. Tout parti cité par une relation ou
   par une personne et absent de la base est téléchargé, reconnu ou non comme organisation, et suivi à
   son tour s'il est français ; la boucle s'arrête quand plus rien de nouveau n'apparaît.
6. `s02c_wikidata_entities.py` : nombre de langues, pays, dates, naissance et décès via Wikidata.
7. `s05_build_graph.py` : construction du graphe (voir ci-dessous).
8. `s06_validate.py` : contrôle qualité (voir `data/review/`).
9. `s07_export_site.py` : export vers `site/data.js`.

## Règles de construction (étape 7)

**Qui est une organisation.** Page dont la première infobox est celle d'un parti, ou, sans
infobox, page dont une catégorie ou la première phrase la désigne comme parti, mouvement, coalition,
courant, organisation politique, etc. Les personnes, congrès, affaires, journaux, syndicats, concepts
(« Socialisme ») et listes sont écartés ; la liste figure dans `data/review/excluded.csv`.

**Qui est français.** Il faut au moins un indice fort : Wikidata donne la France comme pays, ou une
catégorie du type « parti politique en France », ou une région française (Corse, outre-mer...).
Un indice étranger sans indice français fort exclut la page. Les organisations reliées à la France
mais d'abord étrangères (partis basques espagnols, mouvements d'Afrique coloniale) sont conservées avec
`peripheral = true` : masquées par défaut sur le site, jamais au niveau de zoom macro.

**Passage souple.** Une page sans infobox dont la première phrase a une forme inhabituelle (« est,
de 1968 à 2024, une organisation étudiante... ») est reprise par une seconde règle plus tolérante,
qui écarte les personnes, journaux, syndicats, institutions, intercommunalités, congrès et groupes
parlementaires. Ces entrées portent le drapeau `inclus_par_regle_souple`. Une organisation dont
aucune catégorie ne la dit française mais dont la première phrase le fait, sans mot étranger, reçoit
l'indice « le résumé mentionne la France ».

**Dates.** Fondation : infobox, sinon Wikidata, sinon catégorie « fondé en XXXX », sinon dates du
premier paragraphe (« de 1997 à 2002 », « fondée en 1996 », signalé `fondation_depuis_resume`), sinon
première année où un parti déclare appartenir à la coalition. Fin : infobox,
sinon Wikidata, sinon catégorie « disparu en XXXX », sinon intervalle du résumé. Un verbe au passé
(« était », « fut ») dans la première phrase marque l'organisation comme disparue même sans date
de fin. Les groupes parlementaires et organisations sans date manifestement antérieurs à 1958 (IIIe
République, Second Empire...) sont retirés. Une fusion ou une succession ne termine un
parti que si sa propre page l'affirme ou si Wikipédia le classe comme disparu (sinon c'est souvent
une fusion partielle, comme celle du Parti radical, toujours actif). Quand la fondation est double
(SFIO 1905 puis PS 1969), la date est alignée sur celle du prédécesseur pour que les deux barres ne se
chevauchent pas. Les dates antérieures à la naissance de la personne, hors de 1800-2027, ou à
l'intervalle inversé sont retirées (4 cas) et signalées.

**Relations.** Une relation écrite sur les deux pages concernées est « confirmée » ; sur une seule,
elle est conservée comme « une page ». Les relations dont la cible n'est pas une organisation
retenue sont écartées et listées dans `unresolved_edges.csv`.

**Position gauche-droite.** Lue dans le champ « positionnement » de l'infobox ; quand plusieurs périodes
sont données (« Avant 1914 », « Après 1914 », « Actuel »), la période actuelle ou la plus récente est
retenue, les factions sont ignorées, et une plage (« centre gauche à gauche ») donne la moyenne.
Échelle : -3 extrême gauche, -2 gauche, -1 centre gauche, 0 centre, +1 centre droit, +2 droite,
+3 extrême droite. À défaut, une position est déduite des catégories (59 cas) ; à défaut encore,
pour les organisations sans famille connue (coalitions, mouvements régionaux...), de la moyenne des
organisations voisines dans le graphe : membres, parents, successeurs (17 cas, `position_source =
relations`, tracé en pointillés). Sinon le site place le parti d'après sa famille politique (contour
en pointillés) ou dans la zone « non positionné ».

**Familles politiques.** Au plus trois par organisation, d'après les idéologies de l'infobox (dans
l'ordre), les catégories de type organisation et le nom. Ce sont des mots-clés : une heuristique
utile pour filtrer, pas un jugement historique.

**Changements de nom.** Un parti qui change de nom sans changer d'identité (Front national puis
Rassemblement national, RPR puis UMP puis Les Républicains) est représenté de deux façons : quand
Wikipédia a une seule page, les noms successifs lus dans le champ « fondation » (« 1972 (FN), 2018
(RN) ») sont repérés par un trait sur la barre ; quand Wikipédia a une page par nom, la relation
`succession` (déclarée par la page elle-même ou confirmée par les deux, sans chevauchement de plus de
deux ans) les place sur une même ligne du site. Les changements de nom que Wikipédia ne relie pas
par une succession ne sont pas devinés.

**Relations de Wikidata.** Une requête (P155, P156, P1365, P1366, P807) apporte une seconde source
indépendante : elle confirme des relations de Wikipédia (niveau de confiance `confirmee_page_et_wikidata`)
et en ajoute quelques-unes (`wikidata_seule`). Wikidata emploie parfois « suivi par » pour une scission : une
succession qui chevauche son prédécesseur de plus de deux ans, ou qui le précède, est écartée.

**Lignées.** Les successions déclarées par la page source, confirmées par deux sources ou par Wikidata, qui
se suivent sans chevaucher de plus de deux ans, forment une lignée (champ `lineage` : tête, rang, taille). Le
site place une lignée sur une même ligne. `data/overrides.json` permet d'imposer une lignée (`lineages`) ou une date.

**Courants internes.** Une organisation dont une catégorie est « Courant du Parti socialiste » (ou « de l'... »)
est reliée à ce parti par une relation `current_of`, sans modèle de langage.

**Dirigeants successifs.** `s04d_leaders.py` lit les sections « Présidents », « Premiers secrétaires »,
« Secrétaires généraux », « Dirigeants » des pages de partis, ainsi que les pages dédiées qu'elles citent
(« Premier secrétaire du Parti socialiste »), sous forme de tableaux ou de listes : première personne citée par
ligne et dates du mandat. Une personne n'est retenue que si sa propre page est celle d'une personnalité. Les mandats
successifs d'une même personne dans un même parti restent distincts.

**Mise à jour.** `s00_refresh.py` compare les révisions ; `run_update.py` enchaîne vérification, découverte,
reconstruction et `s09_diff_builds.py`. Le client accepte `PARTIS_FRESH=1` (ignorer le cache en lecture).

**Données externes.** `s04e_external_data.py` apporte, depuis ParlGov et CHES, les résultats aux législatives et
européennes (voix, sièges), la position gauche-droite composite et les positions d'experts par année (voir
`SOURCES.md`). Elles complètent la position quand Wikipédia n'en donne pas (`position_source` = `experts` ou
`parlgov`, avant la déduction par relations), alimentent le score d'importance (part de voix maximale aux
législatives) et servent de contrôle : un écart de plus de 1,3 point entre Wikipédia et les experts est signalé
dans `anomalies.csv` (`position_wikipedia_vs_experts`).

**Niveau de zoom.** Score = nombre de langues Wikidata + 0,5 x nombre de relations + 0,25 x nombre
de personnes rattachées + années d'existence sous la Ve République (plafonnées, divisées par 4).
Les 40 premières organisations du coeur, hors étrangères, associations, think tanks, groupes
parlementaires et micro-partis, sont de niveau 1 ; les 160 suivantes de niveau 2 ; le reste de
niveau 3. Corrigeable organisation par organisation dans `data/overrides.json`.

**Personnes.** Trois types de liens : adhésion (champ « parti »), direction (fonction dont l'intitulé
contient président, secrétaire, porte-parole, coordinateur, délégué général... et qui pointe vers un
parti), fondation. Les liens Wikidata complètent les manques sans écraser les dates de Wikipédia.
Un lien de personne dont la page est en fait une organisation (erreur d'interwiki) est écarté.

## Limites

- Wikipédia ne donne souvent que l'année : 97 % des organisations ont une date de fondation, rarement
  le jour, dont 38 tirées du résumé (moins fiables, signalées). 17 organisations n'ont aucune date
  et ne sont pas dessinées (liste dans le site et dans `A_VALIDER.md`).
- Le positionnement est celui que Wikipédia déclare (328 par l'infobox, 59 par les catégories) ;
  17 sont déduites des relations, 185 estimées d'après la famille, 56 restent non positionnées.
- Les relations ne sont aussi complètes que les infobox : 381 des 561 relations ne reposent que sur
  une page. Un parti sans page Wikipédia est absent, de même que la plupart des listes locales.
- Seules les personnes notables sont retenues (environ 2 200) : plus de 6 versions linguistiques, ou
  citées comme fondateur ou dirigeant. Les dates d'adhésion manquent pour une partie d'entre elles.
- Les résultats électoraux couvrent les législatives et les européennes (ParlGov) ; pas de présidentielles, pas de
  municipales ni de départementales. Les 80 partis français de ParlGov ne sont pas tous rapprochés (59 le sont ;
  le reste est surtout des regroupements).
- Quelques fusions ou scissions de l'infobox sont partielles ou ambiguës ; elles sont conservées
  telles quelles (voir `anomalies.csv`).
- Les courants internes ne sont ceux que Wikipédia range comme tels (14) ; les sections « Histoire »
  des pages ne sont pas exploitées (voir pistes ci-dessous).
- Le rattachement « français » est volontairement large (outre-mer, régionalistes, mouvements
  clandestins) ; quelques organisations frontalières ont pu passer ou être écartées à tort : voir
  `excluded.csv`, colonne raison.

## Contrôle qualité

`data/review/RAPPORT.md` résume la complétude, la répartition et les anomalies ; `anomalies.csv`
liste les incohérences (scission antérieure à la naissance du parent, adhésion après la dissolution,
cycles de filiation, organisations importantes sans relation...) ; `coverage_check.csv` vérifie la
présence de 64 organisations attendues (exemples cités par le commanditaire et série #EspritDeParti)
et distingue les correspondances par nom et par sigle.

## Pistes pour la suite

- Courants internes et sensibilités : extraire les sections « Courants » des pages, avec un modèle
  de langage utilisé seulement sur ces sections (coût limité) puis validation humaine.
- Dirigeants successifs de chaque parti : tableaux « Liste des dirigeants » des pages de partis.
- Résultats électoraux (présidentielles, législatives) pour fonder l'importance sur les voix.
- Positionnement qui évolue dans le temps, en s'appuyant sur CHES ou sur les votes parlementaires.
- Ajouter une vue graphe libre (réseau de personnes et de partis) à côté de la frise.
