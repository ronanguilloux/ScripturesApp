# Relationnalité Textuelle Analysée : Stratégie de Structure

Pour transformer une base de données biblique en un véritable analyseur de relations textuelles, il est nécessaire de passer d'une simple liste de « renvois » (liens bruts) à une base de données caractérisée (type de lien) et hiérarchisée (importance du lien).

## 1. Matrice de Caractérisation (Intertextualité)
La première étape consiste à automatiser ou guider la qualification des liens entre un Texte A (source) et un Texte B (citant).
Grille de qualification de l'Intertextualité

| Critère | Littéral (L) | Non-littéral (NL) |
|:-|:-|:-|
|Explicite (E)|Citation directe indexée : Présence de formules comme « Comme il est écrit », « Afin que s'accomplisse ». | Référence : Rappel d'un épisode, d'une figure ou d'un nom sans citation mo^ pour mot.|
|Non-explicite (NE)|Implicitation : Citation « cachée » ou écho textuel sans guillemets ni introduction officielle. | Allusion : Emprunt subtil d'une image, d'un motif ou d'un mot-clé thématique.|

Automatisation suggérée :

* Détection E : Repérer les lemmes de citation (, ).
* Détection L : Comparer les chaînes de caractères avec la Septante (LXX). Si le taux de similitude dépasse un seuil (ex: 80%), marquer comme Littéral.

## 2. Détection de l'Hypertextualité (Imitation vs Transformation)
Lorsque le lien relie deux unités narratives complètes, l'outil bascule en mode Hypertextualité (Relation entre un Hypotexte source et un Hypertexte dérivé).

### A. Repérage des Septantismes (Imitation)
L'outil identifie la volonté d'imiter le style biblique ancien via des marqueurs syntaxiques grecs :
Syntagmes pivots :  (kai egeneto - « et il arriva que ») ou  (kai idou - « et voici »).
Parataxe : Structure de phrases calquée sur le waw consécutif hébreu.

### B. Analyse de la Transformation
L'outil permet de documenter la manière dont l'Hypotexte est traité :
Transposition : Changement de cadre spatio-temporel (ex: de la Veuve de Sarepta à la Veuve de Naïn).
Subversion : Reprise d'un modèle pour en inverser la logique théologique ou morale.

## 3. Classification par Architextualité (Scènes-types)
L'architextualité concerne les liens basés sur des structures de genre ou des Scènes-types (Type-Scenes).
Tags de genre et motifs
L'outil propose des catégories pré-remplies :
La rencontre au puits : (Gn 24, Gn 29, Ex 2, Jn 4). Motifs : voyage, puits, femme, puisage, mariage.
Le récit de miracle : Structure codifiée (Détresse -> Geste thaumaturgique -> Constatation  Réaction).
La vocation : Structure (Appel -> Objection -> Signe/Rassurance).

## 4. Protocole de l'Analyseur (Algorithme de travail)
Pour chaque lien, le workflow méthodologique suit 4 étapes :
Isolation (Lecture autonome) : Afficher le texte B seul pour en saisir le sens premier dans son contexte immédiat.
Qualification : L'utilisateur (ou l'IA) définit la nature : Inter, Hyper ou Architextualité.
Contextualisation : Ouverture automatique du texte A (source) dans son contexte d'origine pour analyser les écarts (ajouts, omissions).
Synthèse Herméneutique : Champ de note final pour rédiger la plus-value sémantique produite par la transformation du modèle.

## 5. Usage et Services CLI (biblecli)
Les services sont basés sur les fichiers JSON des notes de renvoi (ex: @MRK_notes.min.json dans data/cross_refs_by_book/tob/).
Commande principale : biblecli find
| Service / Argument      | Description technique |
|:------------------------|:----------------------|
| septantism -i [L]       | Scanne les notes de renvoi vers l'AT et compare le texte grec du NT avec la LXX pour isoler les marqueurs stylistiques ().
| citation -i [L]         | Isole les citations explicites possédant des formules d'introduction.
| allusion -i [L]         | Détecte les liens à faible identité textuelle mais à forte proximité thématique.
| architext -i [L]        | Identifie les structures de scènes-types via des tags sémantiques.
| transposition -i [L]    | Repère les récits qui déplacent un motif ancien dans un nouveau cadre.
| subversion -i [L]       | Marque les réutilisations critiques ou inversées d'un texte source.
| rewriting -i [L]        | Isole les phénomènes de « Bible réécrite » (expansions narratives).
| reinterpretation -i [L] | Identifie les changements de sens théologique d'une même citation.

## Évolutions futures
Filtres morphologiques : Détection automatique des hébraïsmes.
Word Embeddings : Utilisation de vecteurs sémantiques pour trouver des allusions indétectables par simple comparaison de mots.

