# Rapport de qualite des donnees

Organisations : 646 (coeur 1958+ : 603, ancetres anterieurs : 43)
Personnes : 2364 ; aretes personne-organisation : 5568 ({'member': 4741, 'founder': 197, 'leader': 630})
Aretes organisation-organisation : 590 ({'split': 168, 'merge': 137, 'affiliation': 224, 'succession': 45, 'current_of': 16})
  confiance : deux pages 180 ; une page et Wikidata 3 ; une seule page 378 ; Wikidata seul 13

## Completude des champs (organisations)
- date de fondation : 629/646 (97 %)
- positionnement (valeur -3..+3) : 406/646 (62 %)
- au moins une famille politique : 589/646 (91 %)

## Repartition
- natures : {'party': 372, 'movement': 147, 'parliamentary_group': 23, 'current': 14, 'youth': 18, 'coalition': 44, 'association': 19, 'micro_party': 5, 'think_tank': 4}
- statuts : {'fusionne': 116, 'actif': 318, 'dissous': 196, 'transforme': 16}
- niveaux de zoom (1 = macro, 3 = detail) : {1: 39, 2: 160, 3: 447}
- fondations par decennie : {1880: 3, 1890: 5, 1900: 6, 1910: 4, 1920: 5, 1930: 10, 1940: 17, 1950: 42, 1960: 61, 1970: 77, 1980: 54, 1990: 71, 2000: 102, 2010: 102, 2020: 27}
- organisations existantes a une date donnee : {1960: 86, 1970: 119, 1980: 151, 1990: 177, 2000: 229, 2010: 298, 2020: 343, 2025: 344}

## Controles
- anomalies : {'moyenne': 137, 'faible': 88} (voir anomalies.csv)
- couverture des entites attendues : 62/64 trouvees par leur nom, 2 seulement par un sigle (['Parti ouvrier independant democratique', 'Chasse, peche, nature et traditions']), absentes : []
- pages ecartees : 899 (excluded.csv) ; relations non resolues : 92 (unresolved_edges.csv)
