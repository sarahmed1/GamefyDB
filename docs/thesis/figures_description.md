# GamefyDB — Generated Figures: Descriptions

All figures are produced by `gamefydb/figures.py` and saved to `docs/` (or the
configured output directory). Metrics below come from the last pipeline run
(`docs/model_comparison.csv`). Use these descriptions when presenting figures
to your supervisor.

---

## 1. `stationarity_rolling.png`

**What it shows:** A 3×2 grid. Each row is one forecast series — daily revenue
(TND), daily session volume, weekly member activity. **Left column** = raw
series (light blue) with a rolling mean (dark blue). **Right column** = the
same series after log(1+y)+first-difference stabilization (orange), with its
own rolling mean. The right-column plots hover around zero with a flat band,
demonstrating stationarity visually.

**How to describe it:** "This figure is a before/after graphical stationarity
check. The raw series on the left show visible trend and bursts of variance
around Eid weeks — visually non-stationary even though the ADF test technically
passes. After log(1+y)+first-difference stabilization (right column), the
rolling mean hovers around zero with a constant band, which is the visual
hallmark of a stationary series. The stabilization is used as a diagnostic;
Prophet and auto\_arima handle the raw series directly through their built-in
trend and differencing components."

---

## 2. `train_test_split.png`

**What it shows:** A horizontal bar split into a blue training segment (80 %)
and a red test segment (20 %), with date labels at the start, cut-point, and end.

**How to describe it:** "We used a strictly chronological 80/20 split to
evaluate all three models. Training covers [start date] to [cut date]; the
20 % test set covers [cut date] to [end date]. No shuffling was applied — using
future data to train would constitute data leakage."

---

## 3–5. `accuracy_revenue_prophet.png` / `_sarima.png` / `_xgboost.png`

**What each shows:** The last 60 training days (light blue) + the actual test
series (dark) + a naive day-of-week baseline (gray dotted) + one model's
predictions. Prophet adds an 80 % confidence band. A vertical dashed line marks
the train/test boundary. The Ramadan 2026 period is lightly shaded in purple.

**Metrics from last run:**

| Model   | MAPE  | MAE (TND) | RMSE (TND) |
|---------|-------|-----------|------------|
| Prophet | 64.7 % | 172.0    | 231.9      |
| SARIMA  | 60.6 % | 150.0    | 198.2      |
| XGBoost | 82.6 % | 166.3    | 225.8      |

**How to describe them:** "Each figure shows one model predicting the held-out
20 % of daily revenue. SARIMA achieves the lowest MAPE (60.6 %) and MAE (150 TND),
followed by Prophet (64.7 %). XGBoost underperforms on this series despite
its strength on structured tabular data — likely because daily revenue is
highly irregular and the lag features do not capture all seasonality patterns.
The naive day-of-week baseline (gray) provides a lower-bound reference; all
three models outperform it on MAE."

---

## 6–8. `accuracy_session_volume_prophet.png` / `_sarima.png` / `_xgboost.png`

**What each shows:** Same layout as revenue accuracy, but the y-axis is total
daily transaction count (a proxy for session volume).

**Metrics from last run:**

| Model   | MAPE  | MAE (tx/day) | RMSE |
|---------|-------|--------------|------|
| Prophet | 54.7 % | 8.1         | 11.3 |
| SARIMA  | 75.7 % | 8.4         | 10.7 |
| XGBoost | 79.6 % | 9.3         | 12.3 |

**How to describe them:** "Prophet achieves the best MAPE (54.7 %) for session
volume, while SARIMA and XGBoost both exceed 75 %. Prophet's trend/seasonality
decomposition handles the weekly pattern in transaction counts better than the
other two models on this series."

---

## 9–11. `accuracy_members_prophet.png` / `_sarima.png` / `_xgboost.png`

**What each shows:** Same layout, but on weekly-aggregated member transaction
counts (daily member data is too sparse for reliable daily modelling).

**Metrics from last run:**

| Model   | MAPE   | MAE (tx/week) | RMSE |
|---------|--------|---------------|------|
| Prophet | 62.6 % | 14.4          | 14.4 |
| SARIMA  | 52.4 % | 5.6           | 6.7  |
| XGBoost | 138.1 %| 10.9          | 12.6 |

**How to describe them:** "SARIMA clearly dominates this series (MAPE 52.4 %,
MAE 5.6 transactions/week), benefiting from the regular weekly pattern in member
activity. XGBoost produces the worst MAPE (138.1 %) — the weekly aggregate has
too few data points for the lag-feature approach to generalise well."

---

## 12. `sarima_comparison.png`

**What it shows:** Two side-by-side grouped bar charts — MAPE (left) and MAE
(right) — with three bars per series (Revenue, Session Vol., Member Act.) for
Prophet, SARIMA, and XGBoost. Bar values are annotated on top.

**How to describe it:** "This figure gives a consolidated view of all nine
evaluation results. SARIMA wins on Revenue and Member Activity; Prophet wins on
Session Volume. No single model dominates all three series, which motivates
keeping all three in the pipeline and selecting per-series."

---

## 13. `prophet_revenue_forecast.png`

**What it shows:** Historical daily revenue (light blue line) up to the last
known date, then a Prophet 3-month extrapolation (green dashed line) with an
80 % confidence band, separated by a vertical dashed boundary.

**How to describe it:** "This is the operational output of the forecasting
module: the next 90 days of predicted revenue. The confidence band widens
over time, reflecting growing uncertainty. The forecast serves as input for
budget planning and shift-staffing decisions in the dashboard."

---

## 14. `peak_hours_bar.png`

**What it shows:** A bar chart with hours 0–23 on the x-axis and average
transaction count per day on the y-axis. Bars are gradient-coloured from light
to dark blue by intensity.

**How to describe it:** "This chart identifies the busiest hours of the day
by averaging transaction counts across all recorded dates. The peaks indicate
when the gaming center is most active — useful for scheduling cashiers and
managing terminal availability."

---

## 15. `peak_days_bar.png`

**What it shows:** Same layout as peak hours but with days of the week
(Monday–Sunday) on the x-axis.

**How to describe it:** "Weekday-level activity analysis. The tallest bar
indicates the highest-traffic day of the week on average. This information is
used by the dashboard's shift-planning view."

---

## 16. `kmeans_elbow.png`

**What it shows:** A line plot of K-Means within-cluster inertia (y-axis)
versus the number of clusters k = 1…10 (x-axis), with a dashed red vertical
line at k = 4 (the chosen value).

**How to describe it:** "The elbow method helps choose the optimal number of
member segments. Inertia drops steeply up to k = 4 then flattens, indicating
that adding more clusters yields diminishing returns. We selected k = 4 as the
best trade-off between model complexity and cluster separation."

---

## 17. `kmeans_scatter.png`

**What it shows:** A scatter plot of members in the (Total Spend TND,
Total Duration min) space, colour-coded by their assigned K-Means segment
(k = 4). Each point is one member.

**How to describe it:** "This figure visualises the four member segments in
two-dimensional feature space. Clusters that are spatially separated confirm
that the segments are meaningful — members in the top-right corner are
high-spend, long-session customers; those in the bottom-left are infrequent
visitors."

---

## 18. `segment_distribution.png`

**What it shows:** A bar chart showing how many members fall into each of the
four segments, with counts annotated on top of each bar.

**How to describe it:** "The distribution shows whether segments are balanced
or skewed. A highly imbalanced distribution (one very large segment) may
indicate that k = 4 is too fine-grained or that one cluster is splitting a
natural group."

---

## 19. `anomaly_timeline.png`

**What it shows:** Daily revenue plotted as a light blue line. Mild anomalies
(days more than 2 standard deviations from the rolling mean) are marked with
amber circles; severe anomalies (> 3 SD) with red stars.

**How to describe it:** "This timeline highlights unusual revenue days
automatically detected by the anomaly module. These may correspond to public
holidays, system outages, or promotional events. Flagging them helps
management investigate root causes and avoid penalising forecasting models for
unavoidable outliers."
