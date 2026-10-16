# Licences des données

Le code du dépôt (dossiers `pipeline/`, `site/`, `tests/`) est sous licence MIT (fichier `LICENSE` à la racine).
Les données du dossier `data/` et les textes de `docs/` viennent de sources aux licences différentes ; chaque
fichier garde les conditions de sa source.

| Contenu | Source | Licence | Obligation |
|---|---|---|---|
| Résumés, dates, relations et noms extraits des pages de partis et de personnes (`data/graph/`, `site/data.js`) | Wikipédia en français | CC BY-SA 4.0 | citer Wikipédia et partager à l'identique : les données dérivées de ce dossier sont donc à reprendre sous CC BY-SA 4.0 |
| Identifiants, dates, liens entre partis, notoriété | Wikidata | CC0 1.0 | aucune |
| Résultats électoraux et positions composites (`data/external/view_*.csv`, `party.csv`) | ParlGov (Döring et Manow), publication 2024 sur Harvard Dataverse, doi:10.7910/DVN/2VZ5ZC | CC0 1.0 | aucune ; citation par courtoisie |
| Positions d'experts (`data/external/ches_trend_1999_2024.csv`) | Chapel Hill Expert Survey | citation demandée par les auteurs | Rovny, Polk, Bakker, Hooghe, Jolly, Marks, Steenbergen et Vachudova, 2025, *Electoral Studies* 97, doi:10.1016/j.electstud.2025.102981 |
| Seuils, décisions et rapprochements manuels (`data/definitions.json`, `data/overrides.json`) | l'auteur du projet | CC BY-SA 4.0 | citer ce dépôt |

Références complètes : `docs/SOURCES.md`.
