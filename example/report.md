# Support Volume Forecast

> Démonstration synthétique. Aucune performance de production ni garantie de couverture.

Modèle retenu sur validation : **weekday_mean4**.

| Période | Début | Fin | Jours |
|---|---|---|---:|
| initial_history | 2025-10-01 | 2026-02-17 | 140 |
| validation | 2026-02-18 | 2026-05-12 | 84 |
| calibration | 2026-05-13 | 2026-08-04 | 84 |
| test | 2026-08-05 | 2026-09-29 | 56 |

## Comparaison sur le test

| Modèle | MAE | RMSE | Biais prévision − réel | WAPE |
|---|---:|---:|---:|---:|
| seasonal_naive | 13.02 | 17.11 | -5.41 | 5.7% |
| weekday_mean4 | 16.22 | 19.66 | -12.40 | 7.2% |
| weekday_trend8 | 14.88 | 18.08 | 0.73 | 6.6% |

Bande indicative : prévision ± 21.00 tickets, plancher zéro.
Couverture observée sur les 56 jours de test : **67.9%**.

Le rayon est le quantile empirique 90 % des erreurs absolues de calibration, mutualisées entre horizons. La dépendance temporelle et les changements de régime empêchent de garantir une couverture future de 90 %.

## Sept jours suivants — scénario synthétique

| Date | Prévision | Borne basse | Borne haute |
|---|---:|---:|---:|
| 2026-09-30 | 251.8 | 230.8 | 272.8 |
| 2026-10-01 | 243.5 | 222.5 | 264.5 |
| 2026-10-02 | 235.0 | 214.0 | 256.0 |
| 2026-10-03 | 178.8 | 157.8 | 199.8 |
| 2026-10-04 | 170.2 | 149.2 | 191.2 |
| 2026-10-05 | 275.8 | 254.8 | 296.8 |
| 2026-10-06 | 255.8 | 234.8 | 276.8 |
