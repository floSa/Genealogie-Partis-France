# Définitions : comment on décide qu'un parti est de gauche, de droite, d'extrême...

Ce document explique les règles. Les valeurs elles-mêmes sont dans `data/definitions.json` : c'est le seul endroit à
modifier pour changer une frontière ou trancher un cas. Le tableau des principales organisations, avec le détail de
chaque arbitrage, est dans `data/review/ARBITRAGE_POSITIONS.md` (et `positions_arbitrage.csv` pour toutes).

## 1. L'indice de position

Chaque organisation reçoit un **indice** : un nombre sur une règle graduée allant de **-3** (extrême gauche) à **+3**
(extrême droite), avec **0** au centre. Ce n'est pas une note de qualité ni un pourcentage : c'est seulement la place
sur la règle. Les enquêtes d'experts publient leurs positions sur une échelle de 0 (gauche) à 10 (droite) ; on les
convertit par `indice = (valeur - 5) x 0,6`, ce qui revient à étirer 0-10 sur -3 à +3.

Sur le site, l'indice n'est jamais montré seul : on affiche d'abord la **classe** (« gauche », « droite »...), puis
la raison du choix.

## 2. Les sept classes et leurs frontières

| Classe | Indice | Définition |
|---|---|---|
| Extrême gauche | -3 à -2,6 | indice de -2,6 ou moins ; critère de référence : refus des institutions et des règles du jeu démocratique |
| Gauche | -2,6 à -1,4 | gauche qui participe aux institutions, y compris sa frange radicale (« gauche radicale ») |
| Centre gauche | -1,4 à -0,5 | gauche réformiste ou sociale-libérale |
| Centre | -0,5 à +0,5 | ni gauche ni droite |
| Centre droit | +0,5 à +1,4 | droite libérale ou modérée |
| Droite | +1,4 à +2,6 | droite qui participe aux institutions, y compris sa frange radicale (« droite radicale ») |
| Extrême droite | +2,6 à +3 | indice de +2,6 ou plus ; même critère de référence que l'extrême gauche |

**Pourquoi 2,6.** C'est la frontière retenue par le propriétaire du projet : elle réserve les « extrêmes » aux
organisations très éloignées du centre sur la règle. Les autres frontières (±1,4 et ±0,5) découpent le reste en
tranches comparables ; elles sont modifiables dans `data/definitions.json`.

**Une limite à connaître.** Le critère qui définit vraiment un extrême (refuser les institutions et les règles du jeu
démocratique) ne se mesure pas sur une règle gauche-droite : les experts mesurent la position sur les politiques
(économie, société), pas l'acceptation des institutions. Le seuil numérique est donc un **substitut pratique**.
Quand il contredit le critère de fond, on tranche par une décision explicite (section 4), qui l'emporte toujours.

## 3. D'où vient l'indice : les sources, par ordre de priorité

La première source disponible gagne ; les autres sont gardées pour comparaison.

1. **Décision explicite** (section 4).
2. **Experts CHES** (Chapel Hill Expert Survey) : moyenne des deux dernières enquêtes de la position générale
   (`lrgen`). Mesure datée, publiée, faite par des spécialistes. Disponible pour environ 25 partis actuels ou récents.
3. **ParlGov** : position composite, qui couvre aussi les partis disparus avant 1999.
4. **Wikipédia (infobox)** : champ « positionnement », période actuelle ou la plus récente. On ignore les mentions
   incertaines (« voire », « contesté », « selon »), et « gauche radicale » vaut gauche, « droite radicale » vaut droite
   (et non extrême).
5. **Wikipédia (catégories)** : « Parti politique de gauche »...
6. **Organisations voisines** : pour les rares organisations sans aucune information (membres d'une coalition, scission,
   successeur), la moyenne de leurs voisines dans le graphe.
7. **Famille politique** : dernier recours, estimation affichée en pointillés sur le site.

**Pourquoi les experts avant Wikipédia.** Wikipédia reprend des formulations de presse ou de débat (« gauche radicale,
voire extrême gauche (contesté) ») qui changent selon les rédacteurs ; une enquête d'experts utilise la même méthode
pour tous les partis et date chaque mesure.

## 4. Les décisions explicites

Une décision fixe la classe d'une organisation quelle que soit la source. Elle a un auteur, une date et une raison,
affichée dans la fiche (« Pourquoi cette position ? »). Décisions actuelles :

| Organisation | Classe | Raison |
|---|---|---|
| La France insoumise | Gauche | Elle participe aux institutions et aux élections : gauche (gauche radicale), pas extrême gauche au sens retenu. Les experts la placent à -2,5, en deçà de la frontière (-2,6). |

Pour ajouter une décision, ajouter une entrée dans la liste `decisions` de `data/definitions.json` :

```json
{"titre": "Titre exact de la page Wikipédia", "classe": "droite",
 "pourquoi": "Raison en une phrase.", "decide_par": "propriétaire du projet", "date": "2026-10-16"}
```

puis `python pipeline/run_all.py 7 8 9 10`.

## 5. Repérer les cas qui méritent une décision

Dans `ARBITRAGE_POSITIONS.md` :
- **Frontière** : l'indice est à moins de 0,2 d'un seuil. Un léger changement de source ou d'année ferait changer de classe.
- **Désaccord** : les sources ne donnent pas la même classe (la raison cite les autres sources et leurs valeurs).

Ce sont les candidats naturels à une décision. Exemples issus de la première application des règles : le Rassemblement
national est à l'indice +2,57 selon les experts, soit **droite** (juste sous la frontière de l'extrême droite) alors que
Wikipédia le classe en extrême droite ; Reconquête, à +2,84, est en extrême droite. Ce sont les seuils, appliqués sans
exception, qui produisent ce résultat : c'est à vous de décider si le critère de fond (refus des institutions) justifie
une décision différente.

## 6. Les familles (souverainiste, gaulliste, communiste...)

Ce sont des étiquettes de filtrage, pas des positions. Elles viennent de mots-clés dans les idéologies de l'infobox, les
catégories d'organisation, le nom et la première phrase du résumé (`FAMILY_RULES` dans `pipeline/s05_build_graph.py`).
Pour trancher « est-ce un parti souverainiste ? », on peut ajouter ou retirer une famille par décision :

```json
{"titre": "Debout la France", "familles_ajoutees": ["souverainiste"], "familles_retirees": [],
 "pourquoi": "Programme centré sur la sortie de l'Union européenne.", "decide_par": "propriétaire du projet", "date": "2026-10-16"}
```

à placer dans `criteres_des_familles.decisions` de `data/definitions.json`.
Les critères de chaque famille restent à fixer ensemble : aujourd'hui, ce sont des mots-clés, donc approximatifs.
