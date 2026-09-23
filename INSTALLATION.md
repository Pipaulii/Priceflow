# Installation du correctif PriceFlow

1. Remplacer `app.py` dans le projet par le fichier fourni.
2. Ajouter le contenu de `requirements-ocr.txt` au fichier `requirements.txt` existant du projet. Conserver les autres dépendances.
3. Redémarrer/redéployer l'application pour installer les dépendances et charger le nouveau code.

En local, les dépendances OCR peuvent également être installées avec :

```sh
python -m pip install -r requirements-ocr.txt
```

L'OCR est exécuté localement par RapidOCR. Il n'envoie pas les documents à un service externe et ne nécessite pas Tesseract. Il intervient sur les scans, les couches texte incomplètes et lors d'un nouvel essai si le contrôle financier échoue. Les résultats de lecture sont conservés temporairement en mémoire pour éviter de refaire l'OCR à chaque interaction.

Dans Achats / Fournisseurs, un scan Anconetti regroupant plusieurs bons permet de choisir le bon à importer. Les pages de suite sont réunies. Le PDF conservé dans l'historique correspond au bon sélectionné. Le comparatif refuse un fichier regroupant plusieurs bons et indique de passer par Achats / Fournisseurs.

Les contributions déjà comprises dans les lignes ne sont pas ajoutées deux fois. La REP FIRST facturée après le Total HT est exportée séparément et incluse dans la cible de contrôle. Les REP détaillées de même montant sont additionnées.

Les calculs sont arrondis au centime par ligne. Pour LORFLEX, si le prix affiché à deux décimales ne reproduit pas le montant de ligne imprimé, le prix exporté est calculé à partir de ce montant divisé par la quantité ; l'interface affiche les deux prix.

Le format d'export conserve ses quatre colonnes. Le PDF original reste la référence pour contrôler les libellés et les références OCR. Un total concordant ne garantit pas l'orthographe de chaque désignation. Un écart non résolu reste signalé.

Validation : compilation du fichier complet, exécution des fonctions réelles d'extraction sur les documents fournis, et tests du bloc de calcul/export utilisé par l'interface. L'application déployée et la connexion Supabase n'ont pas été exécutées pendant ces tests. Les tests portent sur les achats et devis fournis ; les locations n'ont pas été modifiées.
