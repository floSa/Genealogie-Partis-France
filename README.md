# Partis et mouvements politiques français depuis 1958

Graphe de connaissances des partis, mouvements, coalitions et courants de la Ve République, de
leurs scissions, fusions et filiations, et des personnes qui les ont fondés, dirigés ou rejoints,
avec un site pour l'explorer.

Tout est construit à partir de Wikipédia en français et de Wikidata, sans aucune API payante et
sans lire les pages avec un modèle de langage : l'extraction est entièrement déterministe, donc
gratuite, rejouable et vérifiable.

## Ouvrir le site

Double-cliquer sur `site/index.html` (aucun serveur ni connexion nécessaires). Si votre
navigateur le bloque, lancer dans un terminal :

```bash
python -m http.server 8765 --directory site
```

puis ouvrir http://localhost:8765. Le site propose :

- une frise verticale du temps (1958 en haut) sur un axe horizontal gauche-droite ;
- un zoom par zone du spectre (extrême gauche, gauche, centre, droite, extrême droite) qui
  agrandit la zone et fait apparaître les petits mouvements, et un curseur de niveau de détail
  (grands partis, principaux, tous) ;
- les scissions, fusions et successions tracées entre les barres, les coalitions en option ;
- un clic sur un parti : résumé, origine, scissions, fondateurs, dirigeants, personnes rattachées ;
- un clic sur une personne (ou la recherche) : son parcours tracé à travers les partis ;
- une photographie à une date donnée, des liens permanents, un export CSV et un formulaire
  « Corriger cette fiche » qui produit l'entrée à coller dans `data/overrides.json` ;
- résultats aux législatives et européennes (ParlGov) et positions d'experts par année (CHES) dans chaque fiche ;
- des filtres par famille politique (communiste, trotskiste, socialiste, écologiste, centriste,
  libéral, gaulliste, droite, souverainiste, extrême droite, régionaliste...) et par nature.

## Contenu du dossier

| Dossier | Contenu |
|---|---|
| `site/` | le site (HTML, CSS, JavaScript sans dépendance) et ses données `data.js` |
| `data/graph/` | le graphe : `graph.json` (référence), `nodes.json`, `edges.json` et exports CSV |
| `data/review/` | contrôle qualité : `RAPPORT.md`, anomalies, pages écartées, couverture |
| `data/overrides.json`, `data/definitions.json` | corrections manuelles ; seuils et décisions sur les positions politiques |
| `data/raw/` | copie locale de Wikipédia et Wikidata (bases SQLite) : tout est rejouable hors ligne |
| `pipeline/` | les scripts Python (bibliothèque standard uniquement) |
| `docs/` | `DEFINITIONS.md` (ce qui est de gauche, de droite, d'extrême...), `METHODE.md` (règles de construction), `SOURCES.md` (requêtes exactes et vérification), `ARCHITECTURE.md` (chaîne et schéma), `MODELE_DE_DONNEES.md` (champs), `JOURNAL.md` (choix et impasses) |

## Chiffres (collecte du 16 octobre 2026)

- 646 organisations (603 depuis 1958, 43 ancêtres antérieurs reliés) : 372 partis, 146 mouvements
  et organisations, 44 coalitions, 14 courants internes, 18 mouvements de jeunesse, 19 associations,
  4 think tanks, 5 micro-partis et 23 groupes parlementaires (masqués par défaut sur le site).
- 590 relations entre organisations : 168 scissions, 137 fusions, 45 successions, 224 affiliations et
  16 rattachements de courants internes à leur parti. 180 sont confirmées par les deux pages concernées,
  3 par une page et Wikidata, 13 ne reposent que sur Wikidata.
- 2 364 personnes et 5 568 liens (4 741 adhésions, 630 mandats de dirigeants, 197 fondations).
- 97 % des organisations ont une date de fondation (17 n'en ont aucune et ne sont pas dessinées).
- 62 % ont une position gauche-droite lue sur Wikipédia (infobox ou catégories) ou déduite de leurs
  relations ; 185 autres sont placées d'après leur famille politique (contour en pointillés sur le
  site), et 56 dans la zone « non positionné ».
- 91 % ont au moins une famille politique.
- 22 organisations « périphériques » (basques espagnols, mouvements d'Afrique coloniale...) sont
  conservées mais masquées par défaut.

## Mettre à jour les données

```bash
python pipeline/run_update.py            # vérifie les pages, découvre les nouveaux partis, reconstruit
python pipeline/run_update.py --offline  # reconstruction et rapport seulement (sans réseau)
python -m unittest discover -s tests     # tests de non-régression du graphe
```

La mise à jour compare la révision de chaque page stockée avec celle de Wikipédia (une requête par
lot de 50 pages) et ne retélécharge que les pages modifiées, puis écrit `data/review/CHANGEMENTS.md` :
organisations nouvelles ou disparues, dates et relations modifiées, nouveaux candidats, pages Wikipédia
changées. Compter 15 à 30 minutes, sans aucun coût en jetons (le réseau seul est sollicité).

## Rejouer

```bash
python pipeline/run_all.py          # toute la chaîne (reprend là où elle s'est arrêtée)
python pipeline/run_all.py 7 8 9    # reconstruire le graphe, le contrôle et le site sans télécharger
```

Les téléchargements sont mis en cache dans `data/raw/` : relancer ne retélécharge rien. Pour
rafraîchir les données depuis Wikipédia, supprimer `data/raw/cache.sqlite` et `data/raw/pages.sqlite`
puis relancer (une à deux heures : une requête par seconde pour respecter les règles de Wikimédia).

## Corriger ou compléter à la main

Ne jamais modifier `data/graph/` ou `data/raw/` à la main : ils sont régénérés. Les corrections
vont dans `data/overrides.json` (forcer l'inclusion ou l'exclusion d'une page, changer le niveau
de zoom ou la position d'une organisation), puis `python pipeline/run_all.py 7 8 9`.
La liste des pages écartées (`data/review/excluded.csv`) et des relations non résolues
(`data/review/unresolved_edges.csv`) indique où chercher ce qui manque. `data/review/A_VALIDER.md`
regroupe en un seul document les cas que les règles automatiques ne tranchent pas (organisations
sans date, sans position, périphériques, pages écartées qui ressemblent à des organisations) : c'est
le fichier à relire pour valider ou corriger.

## Licences et sources

Le texte des résumés vient de Wikipédia et reste sous licence CC BY-SA 4.0 (attribution et partage
à l'identique) ; les données structurées viennent de Wikidata (CC0). Les résultats électoraux viennent de
ParlGov (publication sous licence CC0) et les positions d'experts de la Chapel Hill Expert Survey (citation
demandée) : références complètes dans `docs/SOURCES.md`. Le code est sous licence MIT (`LICENSE`), les données
sous les licences de leurs sources (`data/LICENCE.md`). Le site rappelle la source de
chaque fiche et renvoie vers la page Wikipédia.

## Limites connues

Voir `docs/METHODE.md`, section « Limites ». À retenir : Wikipédia ne donne souvent que l'année,
les positions gauche-droite sont celles de ses infobox ou des estimations signalées, les très petits
partis sans page Wikipédia n'existent pas ici, et les courants internes ne sont que ceux que
Wikipédia classe comme tels.
