# Vérification PriceFlow - 23 PDF, 24 documents

Les 20 fichiers du dossier, les deux PDF supplémentaires et le BL FIRST initial ont été exécutés avec le nouveau code. Le scan contient deux bons distincts. Les 24 contrôles financiers concordent après traitement des frais, de la REP séparée et des arrondis.

| Fournisseur | N° document | Lignes avant ajout de frais | Total exporté | Écart |
|---|---|---:|---:|---:|
| ANCONETTI | 74.77279 | 1 | 33,09 € | 0,00 € |
| CLIM+ | 889C4004897043 | 1 | 91,60 € | 0,00 € |
| OUEST ISOL | 6000270583 | 1 | 13,71 € | 0,00 € |
| REXEL | 960142395 | 1 | 50,76 € | 0,00 € |
| ALDES | 20369487 | 3 | 29,45 € | 0,00 € |
| FIRST ROBINETTERIE | 292128 | 5 | 242,16 € | 0,00 € |
| AREDIS | M/BL2615213 | 20 | 343,24 € | 0,00 € |
| RODACLIM | AR2615345 | 5 | 385,45 € | 0,00 € |
| FRITEC | 35234233 | 6 | 252,26 € | 0,00 € |
| PACK SERVICE | 295473 | 9 | 4 094,20 € | 0,00 € |
| L'OUTILLAGE MERIDIONAL | 146283 | 1 | 30,00 € | 0,00 € |
| H-TUBE / POINT PLASTIQUE | 16113639-1 | 23 | 1 348,14 € | 0,00 € |
| LORFLEX | 10500718 | 14 | 2 744,02 € | 0,00 € |
| FRANS BONHOMME | 2760869 | 24 | 1 095,01 € | 0,00 € |
| CLIM+ | 9235257960 | 2 | 136,11 € | 0,00 € |
| CEDEO | 9237623240 | 12 | 54,99 € | 0,00 € |
| VIM | RI/26042971 | 7 | 1 538,01 € | 0,00 € |
| PUM | 10478431 | 20 | 974,73 € | 0,00 € |
| PROLIANS | 1315115 | 1 | 81,44 € | 0,00 € |
| MPS | 0098651 | 1 | 28,42 € | 0,00 € |
| ANCONETTI | 4121520 | 6 | 36,87 € | 0,00 € |
| ANCONETTI | 4122188 | 22 | 428,30 € | 0,00 € |
| YACK | SCH261434 | 9 | 7 282,93 € | 0,00 € |
| FIRST ROBINETTERIE | 291466 | 16 | 516,12 € | 0,00 € |

Les lignes comptées peuvent inclure du transport ou des contributions déjà présentes dans le tableau source. Une contribution ajoutée séparément crée une ligne supplémentaire dans l’export.

## Résultats importants

- Scan Anconetti : BL 4121520, 6 articles + 0,03 € de REP = 36,87 € ; BL 4122188, 22 articles + 1,75 € de REP = 428,30 €. Le sous-total intermédiaire de 295,57 € n’est pas additionné au total final.
- Frans Bonhomme : 24 lignes, transport et carburant compris, 1 095,01 €. Les 0,24 € d’écoparticipation sont déjà inclus. Un second passage OCR récupère une référence mal reconnue au premier passage.
- YACK : 9 lignes, 7 269,00 € + 13,93 € = 7 282,93 €.
- VIM : 7 articles, 1 533,10 € + 4,91 € = 1 538,01 €.
- FIRST 291466 : 16 articles, 516,10 € + 0,02 € de REP facturée séparément = 516,12 € hors TVA.
- PACK SERVICE : arrondi par ligne, total 4 094,20 €.
- LORFLEX : le montant imprimé 76,12 € pour 5 unités donne un PU exporté de 15,224 € ; l’interface signale la différence avec le PU imprimé de 15,22 €.

## Contrôles exécutés

Compilation Python complète ; comparaison des nombres de lignes et des totaux attendus ; exécution du bloc de calcul/export réel de l’interface pour chaque résultat ; cas de régression sur les REP répétées, les contributions déjà incluses, les arrondis par ligne, les lignes physiques identiques, les sous-totaux et les titres des articles YACK.

Les PDF ont été rendus pour inspection visuelle. Les références et désignations issues de scans peuvent encore contenir des erreurs de lecture ou des espaces manquants : la concordance financière ne valide pas chaque caractère. Les tests n’ont pas lancé l’application déployée, son authentification ni les écritures Supabase. Aucun correctif Locations n’est inclus.


## Mise à jour du 23 septembre — blanc et bleu et erreur cv2

- Régression sur le fichier 7477279.PDF fourni : une ligne article, total exporté 33,09 €, écart nul, sans OCR (appel OCR volontairement interdit durant le test).
- Navigation Achats / Locations / Comparatif testée sans exception avec Streamlit 1.64.0.
- Contrôle visuel navigateur du menu, des cartes Locations et du comparatif réel PUM/H-TUBE/Frans Bonhomme, puis du comparatif à une largeur mobile de 390 pixels.
- Moteur d’extraction identique à la version corrigée précédente, hormis le traitement des annexes Anconetti et le message de dépendances OCR.
- Connexion et historique cloud conservés dans le fichier livré ; aucune connexion au service distant ni déploiement effectués durant ces tests.
- Nouveau contrôle du scan Anconetti contenant deux BL : 4121520 à 36,87 € et 4122188 à 428,30 €, tous deux avec écart nul.

## Progression uniforme

Compilation et navigation des trois pages validées. Barre Locations vérifiée à 100 % avec un exemple de location dans AppTest. Boucle de progression du comparatif vérifiée avec deux succès puis deux échecs simulés : progression complète, erreurs correctement comptabilisées.

## Locations — 24 septembre

- Accès Industrie DEV-COM-AIX1260077 : trois lignes de base = 550 € ; cinq suppléments estimés (31,20 + 14 + 5,59 + 12 + 23,20) = 85,99 € ; total estimé 635,99 € ; total imprimé laissé vide.
- Actis 35574 : cinq lignes = 3270,52 €, écart nul.
- Loxam 905410040433 : huit lignes = 662,35 €, écart nul.
- Exécution du bloc réel d’export et relecture des trois classeurs en mémoire : totaux et distinction base/estimation validés.
- Page Locations contrôlée avec AppTest sur les données Accès Industrie extraites : 635,99 € affichés, aucune exception.

## Connexion harmonisée

Affichage des cinq champs connexion/inscription et validation de connexion vide contrôlés avec AppTest. Rendu vérifié dans le navigateur local. Aucun appel au service de connexion externe pendant ces contrôles.

## Brand France — 1692-1977 V.1

Extraction vérifiée : trois lignes [420, 272, 272], dates 28/08/2026–08/09/2026 prévisionnelles, supplément 24,83 € par facture, aucun faux total imprimé. Bloc réel d’export exécuté et classeur relu : base 964 €, estimation 988,83 €, réserves présentes. AppTest Locations : total estimé affiché, aucune exception. Lecture des trois exemples Accès Industrie, Actis et Loxam conservée.

## Logos et exports

Catalogue de 24 logos extrait des documents fournis et contrôlé visuellement. AppTest : Achats (Anconetti), Locations (exemple) et Comparatif (données du corpus) affichent les trois téléchargements sans exception. Comparatif PDF : 47 lignes, 3 pages, tous les fournisseurs et totaux présents ; les trois pages ont été rendues et inspectées. PDF Location Brand : conditions et estimation conservées. Interface Comparatif : logos, rangée de synthèse/actions et menu de partage vérifiés dans le navigateur local. Aucun message envoyé ni déploiement réalisé.
