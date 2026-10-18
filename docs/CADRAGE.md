# Cadrage — Généalogie des partis de France

Ce document dit **pourquoi** le projet existe et ce qu'il s'interdit. Le **comment** est dans
[ARCHITECTURE.md](ARCHITECTURE.md), les règles de construction dans [METHODE.md](METHODE.md).

## 1. Pitch

Une vue d'ensemble de tous les partis, mouvements et courants politiques français de la Ve République,
avec leurs scissions, fusions et changements de nom, et les personnes qui les ont fondés, dirigés ou rejoints.

1. **Un graphe de connaissances** : 646 organisations, 2 364 personnes, 590 relations entre organisations et
   5 568 liens personne-organisation, avec la preuve (page, champ d'infobox, texte) de chaque relation.
2. **Une frise interactive** : le temps descend de 1958 à aujourd'hui, l'axe horizontal va de l'extrême gauche à
   l'extrême droite, un zoom par zone du spectre fait apparaître les petits mouvements.
3. **Une chaîne rejouable et mettable à jour** : tout se reconstruit par `python pipeline/run_all.py`, et la mise à jour
   (`run_update.py`) ne retélécharge que les pages Wikipédia modifiées.

Cas d'usage de référence : suivre le parcours de Florian Philippot du Front national aux Patriotes ; voir que le
RPR, l'UMP et Les Républicains forment une seule lignée ; voir d'où viennent le NPA et Révolution permanente.

---

## 2. Objectifs & périmètre

**Dans le périmètre (V1)**
- Tous les partis, mouvements, coalitions, courants internes et mouvements de jeunesse qui ont une page Wikipédia
  française décrivant une organisation française active depuis 1958 (et leurs ancêtres reliés).
- Les personnes notables : au moins 6 versions linguistiques sur Wikidata, ou citées comme fondateur ou dirigeant.
- Résultats aux législatives et européennes, positions d'experts, dirigeants successifs, courants rattachés à leur parti.
- Un site statique sans serveur, publié sur GitHub Pages.

**Hors périmètre (V1)**
- Élections présidentielles, municipales, départementales, régionales (ParlGov ne couvre pas les présidentielles françaises).
- Élus locaux et nombre d'élus au-delà des législatives et européennes.
- Programmes et thèmes détaillés des partis (le Manifesto Project demande une clé d'accès).
- Tout usage d'un modèle de langage dans la chaîne de construction.

---

## 3. Contraintes (fermes)

| Contrainte | Détail |
|---|---|
| Coût | **aucun jeton** consommé pour construire ou mettre à jour les données : extraction déterministe |
| Sources | Wikipédia en français, Wikidata, ParlGov, Chapel Hill Expert Survey ; aucune autre |
| Politesse réseau | une requête à la fois, au moins 1,1 s d'écart, cache SQLite, respect de `Retry-After` |
| Dépendances | bibliothèque standard Python uniquement, JavaScript natif sans bibliothèque |
| Diffusion | dépôt public : chaque donnée garde la licence de sa source ([data/LICENCE.md](../data/LICENCE.md)) |

---

## 4. Hypothèses

- **Wikipédia est la source la plus complète pour les filiations.** Wikidata ne renseigne que 126 relations de
  filiation entre partis français (dont 15 absentes de Wikipédia), alors que les infobox donnent scissions, fusions
  et successions avec années. Ce qui la remettrait en cause : un dépôt de données de filiations structuré et à jour.
- **Une page Wikipédia égale une organisation.** Quand Wikipédia a une page par nom (RPR, UMP, LR), le graphe a un
  nœud par page et relie les noms par une relation de succession ; la ligne unique est reconstruite par les lignées.
- **La position gauche-droite se lit sur une règle de -3 à +3** dont les frontières sont fixées dans
  [data/definitions.json](../data/definitions.json), avec le seuil de 2,6 pour les extrêmes retenu par le propriétaire du projet.
- **Les notoriétés se mesurent par le nombre de versions linguistiques** sur Wikidata, faute de meilleure source.

---

## 5. Stack technique

| Brique | Choix | Licence |
|---|---|---|
| Chaîne de collecte et de construction | Python 3.12, bibliothèque standard | PSF-2.0 |
| Copie locale | SQLite 3.49 (module `sqlite3`) | domaine public |
| Interface | HTML, CSS et JavaScript natifs, SVG généré à la main | code MIT |
| Publication | GitHub Pages par GitHub Actions | service GitHub |

---

## 6. Décisions

**Décisions figées**
- **Extraction déterministe plutôt que modèle de langage**, parce que la chaîne doit être gratuite, rejouable et
  vérifiable ligne par ligne ; *limite* : les sections en prose (histoire des partis, courants non catégorisés)
  ne sont pas exploitées.
- **Copie locale SQLite plutôt que requêtes à la demande**, parce que toute analyse se rejoue hors ligne et que
  Wikimédia limite le débit ; *limite* : environ 80 Mo à reconstruire en une à deux heures si on repart de zéro.
- **Site statique sans bibliothèque plutôt que framework**, parce qu'il s'ouvre en double-cliquant et se publie
  tel quel ; *limite* : tout le code d'affichage est écrit à la main dans `site/app.js`.
- **Experts avant Wikipédia pour la position politique**, parce qu'une enquête d'experts applique la même méthode à
  tous les partis avec des mesures datées ; *limite* : seuls 25 partis environ ont des mesures CHES.

**À trancher**
- Faut-il garder les groupes parlementaires dans le graphe (23 aujourd'hui, masqués par défaut) ?
  Recommandation : les garder, ils servent aux relations de filiation avec les partis.
- Critères de chaque famille politique (souverainiste, gaulliste...) : aujourd'hui des mots-clés approximatifs
  ([DEFINITIONS.md](DEFINITIONS.md), section 6).
- Classement du Rassemblement national (+2,57 selon les experts, juste sous le seuil de l'extrême droite) :
  décision du propriétaire attendue.

---

## 7. Roadmap

0. **Socle** : client réseau poli, copie locale SQLite, lecture du wikitexte.
1. **Découverte et analyse** : partis par Wikidata, infobox et catégories ; relations ; personnes.
2. **Graphe et contrôle** : construction, anomalies, couverture des organisations attendues.
3. **Site** : frise, zoom par aile, fiches, parcours de personnes, lignées.
4. **Consolidation** : relations Wikidata, dirigeants successifs, courants, mise à jour incrémentale, tests.
5. **Données externes et définitions** : résultats électoraux, positions d'experts, arbitrage des positions.
6. **Suite possible** : présidentielles lues dans les pages d'élection, courants non catégorisés, position dans le temps.

---

## 8. Stratégie de tests

**16 tests automatiques** (`python -m unittest discover -s tests`), sans réseau, qui lisent le graphe produit :
volumes minimaux, identifiants uniques, arêtes valides, dates bien formées et ordonnées, absence de cycle de scission
ou de succession, couverture des organisations attendues, et cas de référence (Rassemblement national, lignée gaulliste,
Parti socialiste, parcours de Philippot, scission NPA / Révolution permanente, décision sur La France insoumise).
Le site est vérifié à la main dans un navigateur ; il n'a pas de test automatique.

---

## 9. Références

- Sources et requêtes exactes : [SOURCES.md](SOURCES.md).
- Données externes : ParlGov (Döring et Manow, doi:10.7910/DVN/2VZ5ZC) et Chapel Hill Expert Survey (Rovny et al., 2025).
- Choix et impasses rencontrés : [JOURNAL.md](JOURNAL.md).
