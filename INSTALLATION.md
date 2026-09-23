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
