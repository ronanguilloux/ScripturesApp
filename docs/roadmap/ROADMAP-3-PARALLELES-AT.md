# Densité des renvois dans l'Ancien Testament : le corpus `ETCBC/parallels`

**Statut : backlog. Reconnaissance faite, décision non prise.**

Ce document consigne l'état d'une piste explorée mais volontairement non implémentée,
pour qu'elle puisse être tranchée plus tard sans refaire l'inspection.

## Le constat de départ

`~/text-fabric-data/github/ETCBC/parallels/tf/2021/` est installé depuis longtemps et
n'a jamais été chargé. Il contient trois jeux d'arêtes — `crossref.tf`, `crossrefLCS.tf`,
`crossrefSET.tf` — produits par le *Parallels notebook* de l'ETCBC (Dirk Roorda,
Martijn Naaijer) : des renvois AT↔AT **déjà scorés** par similarité littérale.

C'est la piste naturelle pour la densité côté Ancien Testament, maintenant que la
marge de type BJ est en place.

## Ce que les données contiennent

Elles chargent proprement : version 2021, alignée sur BHSA 2021 déjà installé. Les
arêtes vont de nœud `verse` à nœud `verse`. `BookNormalizer.code_to_bhsa` fournit une
bijection complète 39/39 pour le retour `'Genesis'` → `'GEN'`. **Aucune dépendance à
ajouter.**

| jeu | arêtes | inter-livres | scores |
|:-|-:|-:|:-|
| `crossref` | 31 742 | 20 814 | 70–100 (toutes ≥ 70) |
| `crossrefLCS` | 31 080 | 20 396 | idem |
| `crossrefSET` | 22 364 | 15 296 | idem |

Sur `crossref` : **3 783 versets sources**, soit ~16 % de l'AT, dont 605 n'ont
aujourd'hui aucune référence openbible. Seules 2 178 arêtes sur 31 742 visent une cible
qu'openbible couvre déjà (exactement ou à l'intérieur d'une plage) : **~93 % de cibles
neuves**.

## Ce que ça donnerait concrètement

Comparaison avec ce qu'openbible fournit aujourd'hui sur les mêmes versets :

| verset | `parallels` | openbible (3 premiers) |
|:-|:-|:-|
| 2 R 18,13 | `ISA.36.1` (96) | HOS.12.1-2, ISA.7.17-25, ISA.36.1-22 |
| Ex 20,13 | `DEU.5.17` (100) | ROM.13.9, 1JN.3.12-15, MAT.19.18 |
| Ne 7,7 | `EZR.2.2` (89) | NEH.12.3, NEH.12.7, EZR.3.8-9 |
| Is 2,2 | `MIC.4.1` (86) | JER.23.20, ACT.2.17, 2PE.3.3 |
| Gn 1,13 | `GEN.1.23` (89), `GEN.1.19` (84) | — |
| Ps 18,3 | — | PSA.91.15, PSA.55.16, LUK.1.71 |

Deux caractères se dégagent, et c'est là que porte la décision.

**Haute précision, rappel irrégulier.** Là où il y a une arête, c'est le parallèle
synoptique exact que la BJ met en marge — et openbible ne le donne qu'en plage
approximative, enterré au rang 3. Mais le doublet Ps 18 / 2 S 22 est *absent* du
corpus : la couverture a des trous.

**Une queue formulaire bruyante.** Les paires de livres dominantes ne sont pas
Rois/Chroniques mais Lv–Nb (2 942 arêtes), Ez–Nb (2 576), Ez–Lv (2 198) : la formule
« et YHWH parla à Moïse en disant ». L'éventail monte à **152 cibles inter-livres pour
un seul verset source**. À l'inverse, 1 584 versets n'ont qu'une seule cible
inter-livres — le cas synoptique propre.

Les livres les plus productifs en versets sources sont bien ceux qu'on attend :
2 Ch (275), 2 R (245), 1 Ch (220), 1 R (217), 2 S (158).

Conséquence : **le filtre naturel n'est pas « inter-livres »** — il garde tout le bruit
Lv/Nb/Ez. C'est un plafond d'éventail, ou un seuil de score, ou les deux.

## Les trois questions ouvertes

### 1. Filtre
Plafond d'éventail par verset source ? Seuil de score ? Les deux ? Un seuil de score
seul ne sert presque à rien puisque toutes les arêtes sont déjà ≥ 70.

### 2. Jeu d'arêtes
`crossref` seul (le jeu principal du notebook, le plus large), ou union avec
`crossrefLCS` ? Les deux variantes se recouvrent fortement ; `crossrefSET` est le plus
conservateur.

### 3. Rang dans la marge — le point dur

`ReferenceDatabase._load_file` concatène les relations de tous les fichiers sources, et
`SearchBibleUseCase` coupe à `crossref_max=3` **positionnellement**, sur l'ordre de
glob :

```
src/references_db.py          _load_file : tgt["relations"].extend(...)
src/application/use_cases/search.py:364   v_relations = [build(r) for r in raw[:crossref_max]]
```

Openbible fournit déjà 3 relations ou plus sur 21 587 versets de l'AT. Un fichier
`data/references_ot_parallels.json` serait donc **invisible par défaut**, accessible
seulement via `--crossref-source parallels`.

Le commentaire `ponytail:` déjà posé en `src/application/use_cases/search.py:359`
anticipe exactement ce cas :

> *« Rank is positional only — if a source ever ships an explicit score, rank on it
> here instead. »*

`parallels` serait la première source à porter un score explicite. Trois options :

- **Classement par score, en concurrence.** Écrire un champ `score` sur les relations
  et trier `raw` par score décroissant avant la coupe. Les parallèles (70–100)
  passeraient devant openbible (sans score) partout où ils existent, soit ~16 % des
  versets de l'AT. Modifie la marge AT par défaut.
- **Source optionnelle seulement.** Livrer le fichier, ne toucher à aucun code de
  classement. Risque nul, gain nul par défaut.
- **Un créneau réservé.** Alterner la sélection entre fichiers sources pour que chaque
  source obtienne un créneau avant qu'une source en obtienne deux. Plus juste, plus de
  code.

## Format cible

Celui que `scripts/tob_fixies/build_tob_references.py` produit déjà, dans
`data/references_ot_parallels.json`, que le glob de `references_db` ramasse sans
modification :

```json
{
  "version": "1.0",
  "description": "ETCBC/parallels crossref edges (OT)",
  "cross_references": [
    {"source": "2KI.18.13", "relations": [{"target": "ISA.36.1", "type": "parallel", "note": ""}]}
  ]
}
```
