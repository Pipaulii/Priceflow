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
