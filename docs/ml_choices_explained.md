# ML & Algorithm Choices — Explained

Every technical decision made in the forecasting and segmentation modules, with justification.

---

## 1. Forecasting Algorithm — Prophet

**What it is:**
Prophet is a time series forecasting library developed by Meta (Facebook). It is designed specifically for business data that has daily, weekly, and yearly patterns.

**Why we chose it:**
Our data is a time series — transactions recorded over time at a gaming center. Prophet is built exactly for this: it automatically detects weekly patterns (e.g. weekends are busier), handles missing days, and does not require manual feature engineering.

**Alternatives considered:**
- **ARIMA** — the classical approach. Requires manual selection of parameters (p, d, q) and struggles with multiple seasonality patterns. Harder to use correctly.
- **XGBoost** — a powerful general-purpose algorithm. Can work for time series but requires manually creating lag features (e.g. "revenue 7 days ago", "revenue 14 days ago"). More work for no meaningful gain at this scale.

**Conclusion:** Prophet gives the best results with the least manual work for a single-location business time series.

---

## 2. Comparison Algorithm — SARIMA

**What it is:**
SARIMA stands for Seasonal AutoRegressive Integrated Moving Average. It is the classical standard for time series forecasting, extended with a seasonal component. It has four parts:
- **AR** (AutoRegressive) — uses past values to predict future values
- **I** (Integrated) — removes trend by differencing (subtracts today from yesterday to make the series stationary)
- **MA** (Moving Average) — smooths out random noise using past errors
- **S** (Seasonal) — repeats the same three components at a seasonal frequency (e.g. every 7 days for weekly patterns)

**Why SARIMA and not plain ARIMA:**
A gaming center has clear weekly seasonality — weekends are busier than weekdays. Plain ARIMA does not capture seasonality. SARIMA does, making it a fair comparison against Prophet (which also handles seasonality). Comparing Prophet against a model that ignores seasonality would be unfair and academically weak.

**Why we use it as a comparison and not as the main algorithm:**
SARIMA requires selecting six parameters (p, d, q, P, D, Q) manually or through grid search. Prophet requires none. For a single gaming center with 8 months of data, the added complexity of SARIMA does not justify replacing Prophet. It is used here specifically to validate that Prophet is the better choice — not as the primary model.

**Parameter selection — auto_arima:**
Rather than tuning SARIMA parameters manually (which is error-prone and time-consuming), we use `pmdarima`'s `auto_arima` function. It tests multiple parameter combinations and selects the best one using AIC (Akaike Information Criterion — a standard model quality metric that balances accuracy against complexity). This removes human bias from parameter selection.

**Seasonal period (m):**
- Daily series (revenue, session volume): `m=7` — weekly seasonality (7 days per cycle)
- Weekly series (member activity): `m=4` — monthly seasonality within weekly data (4 weeks per cycle)

**Alternatives considered:**
- **Plain ARIMA** — rejected because it ignores seasonality, making comparison unfair
- **Holt-Winters (Exponential Smoothing)** — another classical seasonal method, but less well-known than SARIMA in academic literature and harder to justify in a thesis
- **XGBoost** — requires manually engineering lag features (revenue 7 days ago, 14 days ago, etc.), adding complexity with no benefit at this scale

**How the comparison works:**
Both Prophet and SARIMA are evaluated on the same 80/20 chronological split. The winner per series is determined by MAPE (lowest percentage error wins). This gives an objective, reproducible basis for recommending Prophet as the primary forecasting algorithm.

---

## 3. Train/Test Split — 80/20 Chronological (Both Algorithms)

**What it is:**
We split the historical data into two parts: the first 80% is used to train the model, and the last 20% is held out as the test set. The model never sees the test set during training.

**Why 80/20:**
Standard split ratio in machine learning. With roughly 8 months of data, this gives ~6.4 months for training and ~1.6 months for testing — enough data in both parts to be meaningful.

**Why chronological (not random):**
Time series data cannot be split randomly. If we did, the model would train on future data to predict the past, which is unrealistic. In production, you only know the past — so the test set must always come after the training set in time.

**What we compare:**
The model's predictions for the test period are compared against the real recorded values from the Excel files. This tells us how accurate the model would have been in practice.

---

## 4. Evaluation Metrics — MAE, MAPE, RMSE (Both Algorithms)

Three metrics are printed for each model after evaluation.

### MAE — Mean Absolute Error
Average absolute difference between predicted and actual values. Expressed in the same unit as the data (TND for revenue, count for members).
- Easy to interpret: "on average, the model was off by X TND"
- Treats all errors equally

### MAPE — Mean Absolute Percentage Error
Average percentage error. The most useful metric here because it is scale-independent — you can compare revenue (in TND) and session count (integers) on the same scale.
- **< 10%** → GOOD
- **10–20%** → ACCEPTABLE
- **> 20%** → POOR

These thresholds are standard in business forecasting literature.

### RMSE — Root Mean Squared Error
Like MAE but squares the errors before averaging, which penalizes large individual mistakes more heavily.
- If RMSE is much larger than MAE, it means there are a few predictions that were very far off (outliers)
- If RMSE ≈ MAE, errors are consistent across the test period

**Primary metric for the thesis:** MAPE, because it is the most interpretable and comparable across different series.

---

## 5. Segmentation Algorithm — K-Means Clustering

**What it is:**
K-means is an unsupervised machine learning algorithm that groups data points into k clusters based on similarity. Each point is assigned to the cluster whose center (centroid) it is closest to.

**Why K-means:**
- Well-known, widely used, easy to explain in a thesis
- Works well when clusters are roughly spherical and features are on the same scale (which we handle with normalization)
- Deterministic with a fixed random seed — same input always gives same output
- No labeled training data required (unsupervised)

**Alternatives considered:**
- **DBSCAN** — finds clusters of arbitrary shape, but requires tuning density parameters and can label too many points as "noise". Hard to justify for a thesis.
- **Hierarchical clustering** — produces a dendrogram, good for visualization but computationally heavy and harder to interpret for business segments.
- **RFM scoring** — a rule-based segmentation framework (Recency, Frequency, Monetary). Skipped because our data does not have individual member visit timestamps, making Recency impossible to compute accurately.

**Conclusion:** K-means is the right balance of simplicity, interpretability, and academic credibility.

---

## 6. Number of Clusters — k=4

**Why 4:**
Four clusters map directly to four meaningful business segments:
- Heavy Users
- Casual Spenders
- Regulars
- Light Users

This is a deliberate business decision, not a purely mathematical one. Using k=3 loses the distinction between Casual Spenders and Regulars. Using k=5 or more creates segments that are hard to explain to a non-technical audience.

**Note on the elbow method:**
The standard mathematical approach to choosing k is the "elbow method" — plot inertia vs k and find the bend. We skipped this because our data is small and the business interpretation is clearer with a fixed k=4. This is a valid and common approach in applied ML.

---

## 7. Features Used for Clustering

Three features were selected from the members dataset:

| Feature | What it represents |
|---|---|
| `total_tnd` | Total money spent at the center |
| `duration_min` | Total time spent at the center |
| `orders_tnd` | Money spent on food and drink orders |

**Why these three:**
They capture the two main dimensions of member behavior — time spent and money spent — plus a secondary dimension (orders) that separates members who buy snacks/drinks from those who only pay for computer time.

**What was excluded:**
- `usb_tnd` — always zero in the dataset, no information
- `usage_tnd` — highly correlated with `total_tnd` (usage is the main component of total spend), adding it would give undue weight to the same dimension
- Name/ID fields — non-numeric, not meaningful for distance-based clustering

---

## 8. Feature Normalization — StandardScaler

**What it is:**
StandardScaler transforms each feature so that it has a mean of 0 and a standard deviation of 1. This is called Z-score normalization.

**Why it is required:**
K-means measures distance between points. If `total_tnd` ranges from 0 to 5000 and `duration_min` ranges from 0 to 600, the algorithm will be dominated by `total_tnd` simply because its numbers are larger — not because it is more important. Normalization puts all features on equal footing before clustering.

---

## 9. Cluster Label Assignment Heuristic

After K-means runs, four clusters exist but they have no names — only numeric IDs (0, 1, 2, 3). Labels are assigned automatically using this logic:

1. **Heavy Users** — the cluster with the highest average `total_tnd` (most spending)
2. **Light Users** — the cluster with the lowest average `total_tnd` (least spending)
3. **Casual Spenders** — from the two remaining clusters, the one with the highest ratio of `orders_tnd` to `duration_min` (spends more on food/drinks relative to time)
4. **Regulars** — the remaining cluster

This is a deterministic heuristic applied to the cluster centroids (the average point of each cluster). It ensures labels are consistent and interpretable regardless of which numeric ID K-means assigns internally.

---

## 10. Random Seed — 42

K-means initializes cluster centers randomly before converging. Without a fixed seed, running the same code twice could produce slightly different results. Setting `random_state=42` makes the output fully reproducible — important for a thesis where results must be consistent.

The value 42 is a conventional default in the machine learning community (a reference to *The Hitchhiker's Guide to the Galaxy*). Any fixed integer works equally well.

---

## 11. Anomaly Detection — Z-Score (Day-of-Week)

**What it is:**
An anomaly is a day where the observed value is statistically far from what is normal for that day of the week. We use Z-score to measure this distance:

    z = (actual − weekday_mean) / weekday_std

Where `weekday_mean` and `weekday_std` are computed from all historical days of the same weekday (e.g. all Mondays, all Tuesdays, etc.).

**Why day-of-week grouping:**
A gaming center has strong weekly seasonality — weekends are busier than weekdays. Comparing a Sunday against the overall daily average would flag almost every Sunday as an anomaly, which is meaningless. By comparing each day only against its own weekday peers, we detect days that are unusual relative to what is expected for that specific day of the week.

**Why all data is used (no train/test split):**
Anomaly detection does not predict the future — it asks which past days were statistically unusual. Using all available data gives the most accurate baseline. Unlike forecasting models, nothing is held back for evaluation.

**Threshold — 2σ:**
A day is flagged if its Z-score exceeds 2.0 in either direction. Roughly 5% of days in a normal distribution fall outside ±2σ. A minimum of 4 data points per weekday group is required to compute a meaningful standard deviation.

**Severity:**
- **Mild (2–3σ):** unusual but plausible — e.g. a slow Monday or a moderately busy Sunday
- **Severe (>3σ):** very unlikely by chance (~0.3% probability) — likely caused by an external event such as a power cut, a gaming tournament, a public holiday, or a cashier error

**Three series monitored independently:**
- Revenue (TND) — daily sum of income transactions
- Session volume — daily count of all transactions
- Member activity — daily count of member transactions

Each series uses its own mean and std. An anomaly in revenue has no effect on the session volume Z-score.

**Alternatives considered:**
- **Rolling Z-score** — uses a sliding window instead of the full historical mean. More adaptive to long-term trends but adds complexity. With 7 months of data, the global weekday mean is stable enough.
- **Isolation Forest** — a machine learning method for anomaly detection. More powerful but harder to explain to a non-technical audience and overkill for three independent univariate series.
- **Prophet residuals** — flag days where actual revenue deviates from Prophet's forecast. Ties anomaly detection to the forecast model; if Prophet overfits, it masks anomalies rather than finding them.

**Conclusion:** Day-of-week Z-score is the right balance of simplicity, statistical rigor, and explainability for a thesis project of this scope.

---

## 12. Member Loyalty Scoring — FM Model

**What it is:**
An FM model is a simplified version of the classic RFM (Recency, Frequency, Monetary) framework used in CRM and customer analytics. Each member receives a score on two dimensions:
- **F (Frequency)** — how often the member visits, approximated by total time spent (`duration_min`)
- **M (Monetary)** — how much the member spends in total (`total_tnd`)

Each dimension is scored 1–4 using quartile ranking. The scores are summed into a composite FM score (range 2–8), which is mapped to four loyalty tiers: Bronze, Silver, Gold, and Platinum.

**Why FM and not full RFM:**
RFM requires a Recency dimension — the date of the member's last visit. Our dataset contains only aggregate member statistics (total spend, total time) with no individual visit timestamps. Recency cannot be computed reliably. Omitting it and using only F and M is a standard and academically accepted adaptation when visit-level data is unavailable.

**Why this complements K-means and does not replace it:**
K-means captures the *shape* of member behavior — it groups members with similar spending and time patterns regardless of their absolute values. A Heavy User cluster might contain both a moderately high spender and a very high spender. FM scoring captures *absolute rank* — it answers "who are our most valuable members?" regardless of what behavioral pattern they follow. The two techniques answer different business questions and are used together.

**Why quartile scoring:**
Quartile ranking (1–4) is the standard approach in RFM models. It avoids the need to set arbitrary monetary thresholds (e.g. "Gold means spending over 500 TND") that would not generalize across different time periods or business scales. Every member is ranked relative to the current member population.

**Why four tiers:**
Four tiers (Bronze/Silver/Gold/Platinum) map naturally to the four quartile combinations at the extremes (score 2 = bottom quartile on both dimensions, score 8 = top quartile on both). The naming convention is widely recognized in loyalty program literature and is immediately interpretable by a non-technical audience.

**Alternatives considered:**
- **Full RFM** — rejected because individual visit timestamps are not available in the dataset
- **Monetary-only tiering** — rejected because it ignores how frequently members use the center, which is an independent dimension of loyalty
- **Extending K-means to 5+ clusters** — rejected because it complicates the segmentation without adding a loyalty ranking lens; K-means answers "what type of member" while FM answers "how loyal"

---

## Summary Table

| Choice | Decision | Main Reason |
|---|---|---|
| Forecasting algorithm | Prophet | Built for business time series, no manual feature engineering |
| Comparison algorithm | SARIMA | Classical benchmark with seasonality, fair comparison against Prophet |
| SARIMA parameter selection | auto_arima (AIC) | Removes manual tuning bias, reproducible |
| Seasonal period m | 7 (daily), 4 (weekly) | Matches the natural seasonality of each series |
| Train/test split ratio | 80/20 | Standard ratio, enough data in both parts |
| Split strategy | Chronological | Time series cannot be split randomly |
| Primary evaluation metric | MAPE | Scale-independent, easy to interpret as % |
| Segmentation algorithm | K-means | Simple, interpretable, well-known |
| Number of clusters | k=4 | Maps to 4 meaningful business segments |
| Features | total_tnd, duration_min, orders_tnd | Capture spend and time dimensions without redundancy |
| Normalization | StandardScaler | Required for distance-based algorithms |
| Label assignment | Heuristic on centroids | Consistent, automatic, business-interpretable |
| Random seed | 42 | Reproducibility |
| Anomaly detection algorithm | Z-score (day-of-week) | Statistical standard, no extra library, easy to explain |
| Anomaly threshold | 2σ (mild) / 3σ (severe) | Flags ~5% of days; severe reserved for true outliers |
| Loyalty scoring model | FM (Frequency + Monetary) | Recency unavailable; FM is a standard accepted adaptation |
| Loyalty scoring method | Quartile ranking 1–4 | Relative ranking, no arbitrary thresholds |
| Loyalty tiers | 4 (Bronze/Silver/Gold/Platinum) | Maps to FM score range 2–8, widely recognized naming |
