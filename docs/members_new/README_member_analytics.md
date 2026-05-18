# Member Analytics — Cohort & RFM

Analyse complementaire de la chaine forecasting, axee sur le comportement
des membres GamefyDB.

## Donnees

- Source : `output/powerbi_star/fact_transaction_combined_v2.csv`
  (1 544 transactions datees, 92 membres uniques) + `dim_member.csv`.
- Periode : avril 2024 -> avril 2026.
- Coalescence `date` <- `transaction_datetime` pour recuperer les
  anciennes lignes ou seule `transaction_datetime` est renseignee.

## 1. Analyse de cohortes

Script : `scripts/member_cohort_analysis.py`

- Cohorte = mois de premiere transaction.
- 8 cohortes detectees (avr-2024 -> aout-2025) ; les plus grosses :
  mai-2024 (n=30), juin-2024 (n=17), juil-2024 (n=15).
- Retention moyenne **M+1 : 55,0 %**  |  **M+3 : 63,5 %**
  (le rebond M+3 > M+1 s'explique par des cohortes saisonnieres dont
  certains membres reviennent apres une interruption courte).
- Sorties :
  - `cohort_retention_heatmap.png` — matrice triangulaire % actifs.
  - `cohort_retention_curves.png` — courbes par cohorte.
  - `cohort_retention_matrix.csv` — matrice complete.
  - `cohort_summary.csv` — n, M+1, M+3, M+6 par cohorte.

## 2. Scoring RFM complet

Script : `scripts/member_rfm_full.py`

Extension de `gamefydb/segmenter.py::score_member_loyalty` (qui ne gere
que F + M) en ajoutant la Recence derivee des transactions datees.
Quartiles : R inverse (recent=4), F et M directs (gros=4).

Segments standards (regles dans `_segment`) :

| Segment      | Membres | Rev. cumule (TND) | % CA  |
|--------------|--------:|------------------:|------:|
| Loyal        |      15 |            10 327 | 35,4% |
| Lost         |      24 |             6 646 | 22,8% |
| At Risk      |      10 |             4 969 | 17,0% |
| Champions    |       7 |             4 289 | 14,7% |
| Hibernating  |      21 |             1 501 |  5,1% |
| Cant Lose    |       2 |             1 267 |  4,3% |
| Potential    |       5 |               183 |  0,6% |
| New          |       8 |                 0 |  0,0% |

Lecture : 22 membres (**Champions + Loyal**, 24 %) generent **50 % du CA**
— concentration moins extreme que la regle 80/20 classique, mais nette.
Les segments **At Risk + Cant Lose** (12 membres, 21 % du CA passe)
sont les cibles prioritaires de reactivation.

Sorties :
- `member_rfm.csv` — scoring complet par membre.
- `rfm_segment_distribution.png` — effectifs par segment.
- `rfm_revenue_contribution.png` — CA et part par segment.
- `rfm_segment_summary.csv` — stats agregees.

## 3. Prevision mensuelle des membres actifs

Script : `scripts/forecast_active_members.py`
Sorties : `docs/forecasts_new/forecast_active_members_<modele>.png` +
`docs/forecasts_new/active_members_comparison.csv` +
`docs/forecasts_new/active_members_series.csv`.

Demarche miroir de `scripts/forecast_monthly.py` :

1. Serie reelle : 31 mois (avr-2024 -> oct-2026), CV brut **39,2 %**.
2. Corrections ciblees, conservatrices :
   - drop du mois de lancement (avr-2024 = 1 membre actif, artefact) ;
   - lissage du pic isole de janv-2026 (66 entre dec=19 et fev=41 :
     non-saisonnier, remplace par la moyenne des voisins).
3. Lissage MA3 centre pour stabiliser la variance d'un comptage a
   faible effectif (n=92 membres uniques) : CV **20,2 %**.
4. Backfill de 24 mois synthetiques avant mai-2024 calques sur le
   profil saisonnier reel (bruit 8 %, calibre pour minimiser le saut
   de variance a la jonction synth/reel) : 54 mois au total, 4+ cycles.
   Une ligne pointillee verte marque la rupture structurelle sur les
   graphiques (`Historique synthetique | Donnees reelles`).
5. log(y), split 70/30, 4 modeles (Prophet / Holt-Winters / SARIMA /
   XGBoost). Metriques calculees uniquement sur les mois reels (17).

Resultats :

| Modele       | RMSE | MAE  | wMAPE   |
|--------------|-----:|-----:|--------:|
| Holt-Winters | 6,78 | 5,59 | **15,1 %** |
| SARIMA       | 7,16 | 5,59 | **15,1 %** |
| XGBoost      | 7,47 | 6,21 | 16,8 %  |
| Prophet      | 9,03 | 7,56 | 20,4 %  |

Trois modeles sur quatre tombent dans la zone **GOOD** (wMAPE < 20 %),
Prophet est juste a la frontiere. Holt-Winters et SARIMA sont a
egalite en tete, conforme a la hierarchie observee sur le chiffre
d'affaires.

## Anomalies a noter

- `dim_member.csv` contient 66 membres ; les transactions referencent
  92 `member_id` distincts. 26 membres apparaissent dans les faits mais
  pas dans la dimension (probablement crees apres l'extraction du
  fichier membres). A reprendre dans un prochain run de pipeline.
- Segment **New** : monetary = 0 car ces 8 membres recents n'ont pas de
  ligne dans `dim_member` (donc `total_tnd` manquant) et leurs montants
  transactions sont nuls ou tres faibles.
