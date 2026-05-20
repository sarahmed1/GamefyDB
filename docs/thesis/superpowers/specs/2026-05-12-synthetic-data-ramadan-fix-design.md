# Deeper Synthetic History + Ramadan/Eid Signal Fix — Design

**Date:** 2026-05-12
**Scope:** `gamefydb/data_generator.py` only
**Real data is read-only:** the four `.xls` files in `excel/` (Cash DATA, DATA session reports, Stock DATA, memeber DATA) are never written to. Only `excel/augment/augment_*.xlsx` and `excel/extended_*.xlsx` are regenerated.

---

## Problem

Current forecast accuracy (wMAPE):

| Series | Prophet | SARIMA | XGBoost |
|--------|---------|--------|---------|
| Revenue (TND/day) | 49.1 % | 59.2 % | 50.9 % |
| Session volume | 38.7 % | 46.9 % | 43.5 % |
| Member activity (weekly) | 67.1 % | 71.7 % | 79.9 % |

The visual diagnosis from `docs/accuracy_revenue_prophet.png` and friends:

- Training-set daily revenue peaks max around **600 TND**.
- Test-set daily revenue peaks reach **900–1000+ TND**, mostly clustered around Dec 25 / Jan 1 / Mar 18–25 (Ramadan end + Eid).
- Prophet predicts a near-flat ~270 TND/day and misses every spike.
- Member Activity test set has a single 53-transaction Christmas/NY week that the model predicts as ~8.

Two root causes:

1. **Sparse holiday signal across training cycles.** With only ~18 months of training, Prophet has 1.5 yearly cycles — insufficient for yearly seasonality to lock onto cultural peaks (Ramadan, Eid, New Year).
2. **Synthetic data has misaligned holiday boosts.** `_HOLIDAY_BOOST` is keyed `(month, day)` — year-agnostic. Islamic holidays drift each year, so:
   - Eid al-Fitr 2024 (Apr 10) gets **no boost** — `(4, 10)` is not in the dict.
   - Eid al-Fitr 2025 boost is on `(3, 30)` and `(3, 31)`, but Prophet's holiday calendar puts it on Mar 31 with `upper_window=2`. Mismatch.
   - Eid al-Fitr 2026 (Mar 21) gets **no boost** in any synthetic year. Prophet sees it as a holiday but training data shows nothing special on that date.
3. **Ramadan period ends before Eid.** `_RAMADAN_PERIODS` has 2026 Ramadan ending Mar 17, but Eid is Mar 21 → 3-day gap where neither Ramadan nor Eid signal exists, but real data has a pre-Eid spike there.

---

## Goal

Generate **44 months** of training data (Sep 2022 → Apr 2026 = 24 mo augment synthetic + 12 mo extended synthetic + 8 mo real) with **3–4 consistent Ramadan/Eid cycles** so Prophet learns:

- Yearly Ramadan ramp (low early → peak last week).
- Eid week 3-day spike cluster.
- Synced holiday dates that match Prophet's `_ISLAMIC_HOLIDAYS` table.

Target: wMAPE Revenue **< 35 %**, Session volume **< 30 %**, Member activity **< 50 %**.

---

## Changes to `gamefydb/data_generator.py`

All changes are confined to this single file. No changes to `pipeline.py`, `forecaster.py`, or `figures.py`. Output filenames are unchanged.

### Change 1 — Extend `generate_augment` from 12 to 24 months

```python
def generate_augment(excel_dir: str = 'excel', months_back: int = 24) -> None:
    ...
    end   = pd.Timestamp('2024-08-31')
    start = (end + pd.Timedelta(days=1)) - pd.DateOffset(months=months_back)
    # start = 2022-09-01
```

The augment range becomes **Sep 2022 → Aug 2024** (replaces the current Sep 2023 → Aug 2024, doubling its size).
Combined with `extended_*.xlsx` (Sep 2024 → Apr 2026) this gives **24 + 20 = 44 months** of training data — ~3.7 yearly cycles for Prophet's seasonality.

### Change 2 — Pass `daily_pool` to `generate_cash` inside `generate_augment`

Currently `generate_augment` calls `generate_cash(start, end)` with no daily_pool, falling back to pure lognormal generation. After change:

```python
# Build the daily pool from real cash data once
real_cash = _merge_real_files(cash_files)
daily_pool = _build_daily_pool(real_cash)

aug_cash = generate_cash(start, end, daily_pool=daily_pool)
```

This puts the augment period on the same bootstrap-from-real-distribution footing as `extended_*.xlsx`.

### Change 3 — Year-keyed `_HOLIDAY_BOOST` and synced Islamic dates

Replace the current year-agnostic dict:

```python
_HOLIDAY_BOOST: dict[tuple[int, int, int], float] = {}

# Civil holidays — repeated every year 2022..2026 inside _populate_civil_boosts()
_CIVIL_BOOSTS = [
    (1,  1, 3.2),  # New Year's Day  (lifted from 2.8)
    (1, 14, 1.6),  # Revolution Day
    (3, 20, 1.8),  # Independence Day
    (4,  9, 1.5),  # Martyrs' Day
    (5,  1, 1.5),  # Labour Day
    (7, 25, 1.8),  # Republic Day
    (8, 13, 1.5),  # Women's Day
    (10,15, 1.5),  # Evacuation Day
    (12,25, 2.5),  # Christmas (lifted from 2.0)
    (12,31, 2.7),  # New Year's Eve (lifted from 2.5)
]

# Islamic holidays — synced with forecaster.py::_ISLAMIC_HOLIDAYS
# Each entry: (year, month, day, name, boost)
_ISLAMIC_BOOSTS = [
    (2022,  5,  2, 'Eid al-Fitr',     3.0),
    (2022,  7,  9, 'Eid al-Adha',     3.0),
    (2022,  7, 30, 'Islamic New Year', 1.8),
    (2022, 10,  8, 'Mawlid',          1.8),
    (2023,  4, 21, 'Eid al-Fitr',     3.0),
    (2023,  6, 28, 'Eid al-Adha',     3.0),
    (2023,  7, 19, 'Islamic New Year', 1.8),
    (2023,  9, 27, 'Mawlid',          1.8),
    (2024,  4, 10, 'Eid al-Fitr',     3.0),
    (2024,  6, 17, 'Eid al-Adha',     3.0),
    (2024,  7,  8, 'Islamic New Year', 1.8),
    (2024,  9, 16, 'Mawlid',          1.8),
    (2025,  3, 31, 'Eid al-Fitr',     3.0),
    (2025,  6,  7, 'Eid al-Adha',     3.0),
    (2025,  6, 27, 'Islamic New Year', 1.8),
    (2025,  9,  5, 'Mawlid',          1.8),
    (2026,  3, 21, 'Eid al-Fitr',     3.0),
    (2026,  5, 27, 'Eid al-Adha',     3.0),
    (2026,  6, 17, 'Islamic New Year', 1.8),
]
```

A small `_init_holiday_boost()` function populates `_HOLIDAY_BOOST` at module import:

```python
def _init_holiday_boost() -> None:
    for year in range(2022, 2027):
        for m, d, boost in _CIVIL_BOOSTS:
            try:
                pd.Timestamp(year, m, d)
                _HOLIDAY_BOOST[(year, m, d)] = boost
            except ValueError:
                pass
    for year, m, d, _, boost in _ISLAMIC_BOOSTS:
        _HOLIDAY_BOOST[(year, m, d)] = boost
_init_holiday_boost()
```

Call site changes from `_HOLIDAY_BOOST.get((day.month, day.day), 1.0)` to `_HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)`.

### Change 4 — Ramadan daily-shape multiplier

Add Ramadan periods for 2022 and 2023, fix 2026 end date so it meets Eid, and add a daily-shape function:

```python
_RAMADAN_PERIODS = [
    (pd.Timestamp('2022-04-02'), pd.Timestamp('2022-05-01')),
    (pd.Timestamp('2023-03-22'), pd.Timestamp('2023-04-20')),
    (pd.Timestamp('2024-03-11'), pd.Timestamp('2024-04-09')),
    (pd.Timestamp('2025-03-01'), pd.Timestamp('2025-03-29')),
    (pd.Timestamp('2026-02-17'), pd.Timestamp('2026-03-19')),  # was 2026-03-17
]

def _ramadan_daily_mul(date: pd.Timestamp) -> float:
    """Return a multiplicative shape inside Ramadan:
       0.85 early -> 1.0 mid -> 1.5 last week (Layilatul Qadr + pre-Eid prep).
       Returns 1.0 outside Ramadan."""
    for start, end in _RAMADAN_PERIODS:
        if start <= date <= end:
            days_in = (date - start).days
            total   = (end - start).days
            pos     = days_in / max(total, 1)
            if pos < 0.4:
                return 0.85 + 0.15 * (pos / 0.4)        # 0.85 -> 1.00
            elif pos < 0.75:
                return 1.00 + 0.10 * ((pos - 0.4) / 0.35)  # 1.00 -> 1.10
            else:
                return 1.10 + 0.40 * ((pos - 0.75) / 0.25) # 1.10 -> 1.50
    return 1.0
```

### Change 5 — Eid week cluster pattern

```python
_EID_DATES = {  # year -> [Eid al-Fitr date, Eid al-Adha date]
    2022: [pd.Timestamp('2022-05-02'), pd.Timestamp('2022-07-09')],
    2023: [pd.Timestamp('2023-04-21'), pd.Timestamp('2023-06-28')],
    2024: [pd.Timestamp('2024-04-10'), pd.Timestamp('2024-06-17')],
    2025: [pd.Timestamp('2025-03-31'), pd.Timestamp('2025-06-07')],
    2026: [pd.Timestamp('2026-03-21'), pd.Timestamp('2026-05-27')],
}

_EID_DAY_OFFSET_BOOST = {0: 1.0, 1: 0.8, 2: 0.6, 3: 0.4}  # ratio of Eid-day boost

def _eid_week_pattern(date: pd.Timestamp) -> float:
    """Boost multiplier for Eid+1..Eid+3 (Eid day itself uses _HOLIDAY_BOOST).
       Returns 1.0 outside the Eid+1..+3 window."""
    eids = _EID_DATES.get(date.year, [])
    for eid in eids:
        delta = (date - eid).days
        if 1 <= delta <= 3:
            base = _HOLIDAY_BOOST.get((eid.year, eid.month, eid.day), 3.0)
            return 1.0 + (base - 1.0) * _EID_DAY_OFFSET_BOOST[delta]
    return 1.0
```

Note: Eid day itself gets its boost from `_HOLIDAY_BOOST[(year, month, day)]`. The week-pattern function only handles Eid+1..Eid+3 to avoid double-multiplying.

### Change 6 — Combined multiplier in `generate_cash` daily loop

Inside the `while day <= end` loop:

```python
holiday_mul = _HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)
ramadan_mul = _ramadan_daily_mul(day)
eid_week_mul = _eid_week_pattern(day)

if daily_pool:
    target_rev = max(5.0,
        week_level * DOW_MUL[day.dayofweek] * ramadan_mul * holiday_mul * eid_week_mul
    )
else:
    mul        = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * ramadan_mul * holiday_mul * eid_week_mul
    day_factor = max(0.1, float(RNG.lognormal(-0.10, 0.45)))
    target_rev = max(5.0, BASE_DAILY_TX * mul * day_factor * _MEAN_TX_AMT)
```

Apply the same `ramadan_mul * holiday_mul * eid_week_mul` factor to:
- `generate_sessions` (session count is proportional to activity)
- `generate_stock` (stock movements scale with foot traffic)

---

## Files touched

| File | Action |
|------|--------|
| `gamefydb/data_generator.py` | Edit: 6 changes above |
| `excel/augment/augment_cash.xlsx` | Regenerate (extends to Sep 2022) |
| `excel/augment/augment_session.xlsx` | Regenerate |
| `excel/augment/augment_stock.xlsx` | Regenerate |
| `excel/extended_cash.xlsx` | Regenerate (peaks improved) |
| `excel/extended_session.xlsx` | Regenerate |
| `excel/extended_stock.xlsx` | Regenerate |
| `excel/extended_members.xlsx` | Regenerate (no logic change, just rerun for consistency) |

**Never touched:**
- `excel/Cash DATA 01-09-2025.xls`
- `excel/DATA session reports 01-09-2025.xls`
- `excel/Stock DATA 01-09-2025.xls`
- `excel/memeber DATA 01-09-2025.xls`
- `excel/14-06-2025 *.xls` (older real exports)

---

## Verification

After regeneration:

1. Run `python -m gamefydb.data_generator` — confirm extended + augment files regenerate without error.
2. Run `python run.py --input excel --output output` — confirm pipeline completes.
3. Inspect `docs/model_comparison.csv` — confirm Revenue/Session wMAPE drops vs baseline.
4. Inspect `docs/accuracy_revenue_prophet.png`:
   - Training peaks should now reach 800–1000 TND in summer + holiday weeks.
   - Prophet predictions for Dec 2025 and Mar 2026 should show **visible peaks** instead of a flat band.
5. Inspect `docs/accuracy_members_prophet.png`:
   - Christmas/NY weekly peak in training should match test-set peak magnitude.
6. Spot-check: filter `output/fact_cash_transactions.csv` to 2024-03-11..2024-04-12 and 2025-03-01..2025-04-02 — confirm Ramadan ramp pattern is visible, ending in Eid spike cluster.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Higher synthetic peaks could over-fit Prophet to spikes, hurting non-holiday days | Bootstrap pool still drives baseline; holiday boosts only multiply on holiday days |
| Ramadan 2026 ending Mar 19 may not match real moon-sighting date | The 1-2 day offset is smaller than the existing `upper_window=2` in Prophet's calendar — still inside the holiday window |
| `_eid_week_pattern` and `_HOLIDAY_BOOST` could double-apply on Eid day | Function returns 1.0 for delta=0; only handles delta 1..3 |
| Augment regeneration deletes existing seed | Same seed (RNG=42, random.seed(42)) used throughout, so output is reproducible |

---

## Out of scope

- Changes to `forecaster.py` model hyperparameters (Prophet/SARIMA/XGBoost stay as-is).
- Changes to the test-train split ratio (0.8 fixed).
- Member-activity weekly model: not addressed beyond riding the same data improvements (weekly aggregation should pick up the Eid week spike automatically).
- Power BI dashboard updates.
