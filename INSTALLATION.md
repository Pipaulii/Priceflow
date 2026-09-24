# PriceFlow — version blanc et bleu, PDF et scans

## Mise à jour sur Streamlit Community Cloud

1. Décompressez l'archive.
2. Dans le dépôt de votre application, remplacez `app.py` et `requirements.txt` par ceux fournis. Ajoutez `packages.txt` à la racine du dépôt et `.streamlit/config.toml` dans le dossier `.streamlit`.
3. Conservez vos secrets existants et la configuration de connexion. L'archive ne contient aucun secret et ne modifie pas vos données.
4. Laissez Streamlit reconstruire l'application, puis utilisez « Reboot app » si nécessaire. Si vous recréez l'environnement, choisissez Python 3.12.
5. Importez de nouveau `7477279.PDF` : le résultat attendu est ANCONETTI, document 74.77279, une ligne article à 33,05 € et 0,04 € de REP, soit 33,09 € HT.

Il faut installer les fichiers de dépendances, pas seulement remplacer app.py : le module Python `cv2` est fourni par `opencv-python`. `packages.txt` fournit les bibliothèques Linux utilisées sur Streamlit Cloud. Évitez de conserver en parallèle une autre variante d'OpenCV (headless/contrib) dans vos dépendances.

## Utilisation locale

Dans un environnement Python 3.12 :

```
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

L'OCR principal RapidOCR ne nécessite pas d'installation manuelle de Tesseract. Le moteur Tesseract est un secours facultatif. Les modèles RapidOCR sont inclus dans sa distribution.

## Modifications

- Menu intégré au bandeau blanc, icônes, onglet bleu actif et avatar.
- Pages Achats, Locations et Comparatif harmonisées en blanc et bleu.
- Tableau comparatif avec meilleurs prix en vert et montants au format français.
- Lecture du PDF Anconetti fourni sans OCR inutile des annexes de conditions générales.
- Dépendances OCR explicites et message compréhensible si elles manquent.

La connexion, les droits d'administration et les exports sont conservés. Les données de démonstration et les raccourcis de connexion utilisés pour les contrôles locaux ne sont pas inclus dans l'application livrée.

Les contrôles sont locaux ; cette archive n'a pas été déployée sur votre serveur.

## Mise à jour : progression uniforme

Achats / Fournisseurs, Locations et Comparatif affichent désormais une barre par étapes terminées, le nom du fichier et un indicateur animé avec temps écoulé pendant la lecture. Le comparatif indique le nombre de documents traités et distingue les erreurs. Cette évolution rend le traitement visible ; elle ne réduit pas la durée de l’OCR. Si le paquet blanc et bleu précédent est déjà installé avec ses dépendances, seul app.py doit être remplacé.

## Correction Locations — 24 septembre

Le devis Accès Industrie distingue désormais les lignes de base, les suppléments annoncés dans le devis et le total estimé sous réserve des conditions applicables. L’export Excel comporte une feuille Suppléments estimés avec les calculs et la synthèse rappelle les réserves. Exemple DEV-COM-AIX1260077 : base 550 €, suppléments estimés 85,99 €, estimation 635,99 € HT. Aucun total imprimé n’est inventé. Les totaux Actis et Loxam restent fondés sur les lignes imprimées. Les barres de progression précédentes sont conservées.

Si la version précédente est déjà installée, remplacez uniquement app.py puis redémarrez Streamlit.

## Connexion harmonisée

Bandeau blanc PriceFlow, carte de connexion centrée, onglets et boutons bleus. Création de compte harmonisée également. Remplacer app.py puis redémarrer.

## Location échafaudage Brand France / SGB Hünnebeck

Ajout du format Devis Location Simple testé sur 1692-1977 V.1. Base : location 420 € + transport aller 272 € + retour 272 € = 964 € HT. Contribution environnementale 24,83 € par facture : estimation 988,83 € HT pour une facture. Les sous-totaux 35 €/jour et 544 € de services ne sont pas confondus avec un total général. Les dates prévisionnelles, le transport variable et les frais éventuels exclus sont signalés dans l’interface et l’Excel. Cette validation porte sur le format fourni, pas sur tous les devis d’échafaudage. Remplacer uniquement app.py si les dépendances sont déjà installées.

## Logos, PDF et partage — 24 septembre

Cette version contient toutes les corrections précédentes. Remplacez app.py ET requirements.txt puis redémarrez Streamlit : reportlab 4.4.9 est ajouté pour produire les PDF. Conservez packages.txt et .streamlit/config.toml fournis dans les versions précédentes.

24 logos issus des devis fournis sont intégrés dans app.py. Ils apparaissent pour les fournisseurs reconnus dans Achats, Locations et Comparatif. Un fournisseur absent du catalogue conserve son nom. Les logos ne garantissent pas la reconnaissance de tous les formats de documents.

Les trois rubriques proposent Exporter en Excel, Exporter en PDF et Partager. L’Excel Achats conserve son format d’import. Partager propose de télécharger le PDF et de préparer un e-mail dans votre messagerie habituelle. Il faut joindre le fichier et envoyer vous-même le message ; rien n’est envoyé automatiquement. Aucun lien public n’est créé.
