# Rapport de qualite des donnees

Organisations : 645 (coeur 1958+ : 603, ancetres anterieurs : 42)
Personnes : 2212 ; aretes personne-organisation : 5161 ({'member': 4464, 'leader': 500, 'founder': 197})
Aretes organisation-organisation : 561 ({'split': 167, 'merge': 137, 'affiliation': 224, 'succession': 33})
  dont confirmees par les deux pages : 180 ; par une seule page : 381

## Completude des champs (organisations)
- date de fondation : 628/645 (97 %)
- positionnement (valeur -3..+3) : 404/645 (62 %)
- au moins une famille politique : 589/645 (91 %)

## Repartition
- natures : {'party': 372, 'movement': 146, 'parliamentary_group': 23, 'current': 14, 'youth': 18, 'coalition': 44, 'association': 19, 'micro_party': 5, 'think_tank': 4}
- statuts : {'fusionne': 116, 'actif': 318, 'dissous': 198, 'transforme': 13}
- niveaux de zoom (1 = macro, 3 = detail) : {1: 39, 2: 160, 3: 446}
- fondations par decennie : {1880: 3, 1890: 5, 1900: 6, 1910: 4, 1920: 5, 1930: 10, 1940: 17, 1950: 42, 1960: 61, 1970: 77, 1980: 55, 1990: 71, 2000: 102, 2010: 101, 2020: 27}
- organisations existantes a une date donnee : {1960: 86, 1970: 119, 1980: 151, 1990: 178, 2000: 230, 2010: 298, 2020: 343, 2025: 344}

## Controles
- anomalies : {'moyenne': 128, 'faible': 74} (voir anomalies.csv)
- couverture des entites attendues : 62/64 trouvees par leur nom, 2 seulement par un sigle (['Parti ouvrier independant democratique', 'Chasse, peche, nature et traditions']), absentes : []
- pages ecartees : 895 (excluded.csv) ; relations non resolues : 92 (unresolved_edges.csv)
