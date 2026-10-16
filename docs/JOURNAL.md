# Journal de construction

Ce journal garde la mémoire des choix, des impasses et des corrections. Il sert à comprendre pourquoi
le code est fait ainsi et à ne pas refaire les mêmes erreurs.

## Point de départ

Objectif : une vue d'ensemble de tous les partis, mouvements, scissions et personnes de la Ve République
(plusieurs centaines d'entités au total, une cinquantaine de vivantes à une date donnée), avec une
timeline verticale et un zoom par aile. Contrainte : rester frugal, donc ne pas faire lire des milliers
de pages par un modèle de langage.

## Ce qu'on a mesuré avant de construire

- Wikidata recense 615 partis français mais seulement 21 ont un prédécesseur renseigné : les
  filiations n'y sont pas modélisées. En revanche 13 000 personnes y sont rattachées à des partis.
- Les infobox de Wikipédia contiennent exactement ce qui manque : `scission de`, `scission dans`,
  `fusion de`, `précédent`, `suivant`, avec les années. Les infobox de personnes donnent la suite de
  partis avec dates (`parti = FN (2011-2017), LP (depuis 2017)`) et les fonctions avec dates.
- Conclusion : Wikipédia pour les relations et les parcours, Wikidata pour les identifiants, les dates
  de repli, la notoriété et les fondateurs.

## Impasses et corrections

| Problème | Ce qui s'est passé | Solution |
|---|---|---|
| Limitation de débit (erreur 429) | rafales de requêtes, puis veille de l'ordinateur pendant une collecte | une requête à la fois, cache, reprise automatique, maintien en éveil |
| Catégories très bruitées | l'arbre « Parti politique en France » contient congrès, affaires, journaux, personnes | reconnaissance par infobox, puis par la première phrase de l'introduction (introduction seule, très peu coûteux) |
| Écrasement de pages | un téléchargement d'introduction remplaçait une page complète déjà stockée (via une redirection) | le stockage ne remplace plus jamais une page complète par une introduction |
| Infobox invisibles | la première infobox de nombreuses pages est une enveloppe `{{Infobox/Début}}` | lecture tolérante des enveloppes |
| Personnes prises pour des partis | des pages de personnes contiennent une infobox de parti plus bas | la première infobox de la page doit être celle d'un parti |
| Partis étrangers | partis basques espagnols, mouvements coloniaux, groupes du Parlement européen | indices français forts exigés ; les cas frontaliers sont gardés comme périphériques |
| Fusions partielles | le Parti radical aurait été marqué « terminé » à cause d'une fusion ailleurs | une fusion ne termine un parti que si sa propre page l'affirme ou si Wikipédia le dit disparu |
| Positions historiques | la SFIO apparaissait à l'extrême gauche (période « avant 1914 ») | lecture des périodes : « Actuel » sinon la plus récente, factions ignorées |
| Importance | les petits partis ultramarins passaient devant de grands partis | score intégrant les personnes rattachées et les années sous la Ve République |
| Dates manquantes (92 organisations) | l'infobox ne les donne pas | repli : catégories, premier paragraphe, première année d'appartenance à une coalition (17 restent sans date) |
| Familles absurdes (NPA « extrême droite ») | « Internationalisme » contenait « nationalisme » | chaque libellé testé séparément, en début de mot |
| Anciens groupes parlementaires | des groupes de la IIIe République apparaissaient comme actifs | verbe au passé en première phrase, ou groupe parlementaire sans date : retirés |
| Changements de nom | RPR, UMP, Les Républicains sur des lignes différentes | lignées : les successions qui se suivent partagent une ligne ; noms successifs d'une même page repérés par un trait |

## Choix assumés

- Aucun modèle de langage dans la chaîne. Une extraction ciblée (courants internes) pourra en utiliser
  un plus tard, sur des sections précises et avec validation.
- Les positions gauche-droite ne sont pas un jugement : elles sont celles que déclare Wikipédia, ou une
  estimation clairement signalée.
- Les corrections manuelles sont rares, listées dans `data/overrides.json`, et chacune est justifiée
  dans le commit ou dans ce journal.
- Les pages écartées ne sont jamais perdues : `data/review/excluded.csv` donne la raison, et
  `A_VALIDER.md` regroupe les cas que les règles ne tranchent pas.

## Pistes non traitées

- Changements de nom sans relation de succession dans Wikipédia (le graphe ne les devine pas).
- Courants internes et sensibilités hors catégories dédiées ; dirigeants successifs de chaque parti.
- Résultats électoraux, positionnement variable dans le temps.
- Vue réseau libre (personnes et partis) en plus de la frise.

## Deuxième tour : consolidation et mise à jour

- Mise à jour incrémentale : vérifier 6 890 pages stockées coûte environ 140 requêtes (une par lot de 50
  titres) ; seules les pages dont la révision a changé sont retéléchargées (108 lors du premier essai).
  Aucun jeton n'est consommé : ce sont des requêtes HTTP faites par un script Python.
- Wikidata contient 126 relations de filiation entre partis français (et non 21) : elles confirment 43 relations
  de Wikipédia et en ajoutent 15 ; certaines étaient en réalité des scissions (« suivi par »), d'où le filtre sur le
  chevauchement dans le temps.
- Les courants internes sont rattachés à leur parti par la catégorie, sans modèle de langage (16 courants).
- Les dirigeants successifs viennent des tableaux de Wikipédia (311 mandats ajoutés) ; les mandats multiples
  d'une même personne dans un même parti ne sont plus fusionnés.
- Les fonctions du site (photographie à une date, liens permanents, export CSV, formulaire de correction, accessibilité)
  ont été développées par un agent en parallèle dans une copie de travail séparée, puis fusionnées.
- Non fait faute de source fiable et légère : résultats électoraux, nombre d'élus (les champs de l'infobox sont
  alimentés par Wikidata et vides) et position dans le temps issue de CHES ou des votes. Ils demandent des jeux de
  données externes à télécharger et à rapprocher des noms de partis ; à décider ensemble.

## Troisième tour : résultats électoraux et positions d'experts

- Sources retenues parce qu'elles se téléchargent sans compte et en quelques fichiers : ParlGov et CHES
  (le Manifesto Project demande une clé d'accès, non utilisé). L'INSEE ne publie pas de résultats électoraux.
- ParlGov donne 392 lignes de résultats pour la France (législatives et européennes, depuis 1902) et 80 partis ;
  59 sont rapprochés de nos organisations (45 par Wikidata, 7 par sigle, 7 à la main), pour 224 résultats depuis
  1958. CHES apporte 66 mesures pour 1999-2024. Les présidentielles ne sont pas dans ParlGov.
- ParlGov traite UMP et Les Républicains comme un seul parti, FN et RN aussi : les résultats sont répartis entre
  les membres d'une lignée d'après la date de l'élection.
- Les appels `wbgetentities` par titre anglais sont lents (plus d'une minute pour deux titres lors d'un essai) :
  limitation de débit côté Wikidata, sans conséquence car mis en cache.
