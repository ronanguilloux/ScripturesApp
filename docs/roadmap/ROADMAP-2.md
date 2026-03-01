# Relationnalité textuelle Analysée

Pour transformer votre base de données biblique en un véritable analyseur de relations textuelles, vous devez passer d'une simple liste de « renvois » (liens bruts) à une base de données caractérisée et hiérarchisée.

Voici une stratégie pour structurer cet outil en vous appuyant sur la méthodologie de votre document.

## 1. Créer une « Matrice de Caractérisation »
La première étape consiste à automatiser ou à guider la qualification de vos liens existants. Vous pouvez utiliser les 4 modalités de citation pour définir si un lien entre un texte A (source) et un texte B (citant) est de l'ordre de l'intertextualité:

Grille de qualification (Intertextualité)
Critère	Littéral (L)	Non-littéral (NL)
Explicite (E)	

Citation directe indexée (« Comme il est écrit », « Afin que s'accomplisse »).

Référence : Rappel d'un épisode ou d'une figure sans citation mot pour mot.

Non-explicite (NE)	

Implicitation : Citation « cachée » sans guillemets ni introduction.

Allusion : Emprunt subtil d'une image ou d'un mot-clé.

L'outil devrait :

Repérer les formules d'introduction (« Il est écrit ») pour marquer automatiquement le lien comme Explicite (E).

Comparer les chaînes de caractères : si le texte B est identique à la Septante (LXX), marquer comme Littéral (L).

## 2. Détecter l'Hypertextualité (Imitation vs Transformation)
Si votre lien de renvoi relie deux récits complets (ex: la résurrection d'un fils chez Élie et chez Jésus), l'outil doit basculer en mode Hypertextualité.

L'Hypotexte (A) : Le texte source (ex: 1 Rois 17).

L'Hypertexte (B) : Le texte qui imite (ex: Luc 7).

Fonctionnalité de l'outil :

Repérage des « Septantismes » : Chercher des marqueurs stylistiques comme kai egeneto (« et il arriva que ») ou kai idou (« et voici ») qui signalent une volonté d'imiter le style biblique ancien.

Analyse de la Transformation : L'outil doit permettre de noter la transposition (le changement d'espace-temps).

## 3. Classifier par Architextualité (Scènes types)
Pour les liens qui ne sont ni des citations ni des imitations directes, votre outil peut identifier des Scènes types (Type-Scenes).

L'outil pourrait proposer des « Tags » de genre :

La rencontre au puits : (Gn 24, Gn 29, Ex 2, Jn 4) .

Le récit de miracle : Structure codifiée (détresse → geste → constatation → réaction).

## 4. Protocole d'Analyseur (Algorithme suggéré)
Pour chaque lien de votre Bible numérique, vous pouvez implémenter ce parcours méthodologique en 4 étapes  :

Isolation (Lecture autonome) : Afficher le texte B seul pour en saisir le sens premier.

Qualification : L'utilisateur (ou l'IA) choisit : est-ce une Inter, Hyper ou Architextualité ?.

Contextualisation (Étude de la source) : Ouvrir automatiquement le texte A dans son contexte d'origine pour voir ce qui a été conservé ou modifié.

Synthèse Herméneutique : Un champ de note final pour rédiger le « sens nouveau » produit par la transformation ou la subversion du modèle.

## 5. Usage:

### 5.1 Septantismes
- rédiger un nouveau service 'biblecli find septantism -i (--in) [livre par son abbréviation française]' qui pour un livre est capable de scanner vos notes de renvoi pour y détecter automatiquement les "Septantismes" c'est à dire que la note qui renvoie vers un autre livre de l'Ancien Testament  doit être analysée dans sa version grecque (LXX) pour y déceler des "Septantismes" 

 créer un nouveau service 'biblecli find septantism -i (--in) [livre par son abbréviation française]' qui pour un livre est capable de scanner vos notes de renvoi pour y détecter automatiquement les "Septantismes" c'est à dire que la note qui renvoie vers un autre livre de l'Ancien Testament  doit être analysée dans sa version grecque (LXX) pour y déceler des "Septantismes" 

Pour trouver les référérences on utilise le fichier JSON des notes du livre correspondant ("Mc" = @MRK_notes.min.json in data/cross_refs_by_book/tob/

Pour les filtres morphologiques (les hébraïsmes) ou l'analyse des vecteurs sémantiques (Similarity Word Embeddings), ce sera une excellente piste de développement futur pour un niveau de détail et d'érudition encore supérieur.

### Autres:

- idem, pour les citations explicites
- idem, pour les allusions
- idem, pour les architextualités
- idem, pour les transpositions
- idem, pour les subversions
- idem, pour les réécritures
- idem, pour les réinterprétations
- idem, pour les réécritures
- idem, pour les réécritures
