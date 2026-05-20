# Synthetic Data — Deeper History + Ramadan/Eid Signal Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend synthetic training data from 30 → 44 months and fix the Ramadan/Eid signal so Prophet's 2026-03 forecasts (Ramadan + Eid al-Fitr) match real test-set peaks.

**Architecture:** All changes are confined to `gamefydb/data_generator.py`. We add a year-keyed holiday boost dict, a Ramadan daily-shape multiplier, and an Eid-week cluster pattern; we extend `generate_augment` from 12 → 24 months and route it through the same bootstrap pool as `extended_*.xlsx`. Real `.xls` files in `excel/` are never touched.

**Tech Stack:** Python 3.x, pandas, numpy, openpyxl, pytest, Prophet/SARIMA/XGBoost (already installed).

**Reference spec:** `docs/superpowers/specs/2026-05-12-synthetic-data-ramadan-fix-design.md`

**Python command:** `C:/Users/sarah/AppData/Local/Python/bin/python` (Python is not on PATH — always use the full path).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `gamefydb/data_generator.py` | Modify | All logic changes (constants, helpers, generators) |
| `tests/test_data_generator.py` | Create | Unit tests for new helper functions |
| `excel/augment/augment_cash.xlsx` | Regenerate | Sep 2022 → Aug 2024 cash |
| `excel/augment/augment_session.xlsx` | Regenerate | Sep 2022 → Aug 2024 sessions |
| `excel/augment/augment_stock.xlsx` | Regenerate | Sep 2022 → Aug 2024 stock |
| `excel/extended_*.xlsx` | Regenerate | Sep 2024 → Apr 2026 with new multipliers |

**Never touched:** `excel/Cash DATA 01-09-2025.xls`, `excel/DATA session reports 01-09-2025.xls`, `excel/Stock DATA 01-09-2025.xls`, `excel/memeber DATA 01-09-2025.xls`, `excel/14-06-2025 *.xls`.

---

## Task 1: Set up test scaffold for `data_generator`

**Files:**
- Create: `tests/test_data_generator.py`

- [ ] **Step 1: Create the test file with import + smoke test**

```python
# tests/test_data_generator.py
"""Unit tests for synthetic data generator helpers.

We test the pure helper functions (Ramadan/Eid shapes, holiday boost lookup)
because they drive every transaction's revenue target. The Excel writers and
generate_all() are integration tested manually via re-running the pipeline.
"""
import pandas as pd
import pytest

from gamefydb import data_generator as dg


def test_module_imports():
    """Smoke test: module loads and constants exist."""
    assert dg.MONTHLY_MUL[7] == 1.50
    assert dg.MONTHLY_MUL[8] == 1.35
    assert len(dg._RAMADAN_PERIODS) >= 4
```

- [ ] **Step 2: Run the test to verify it passes against current code**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: PASS (1 test).

- [ ] **Step 3: Commit**

```bash
git add tests/test_data_generator.py
git commit -m "test: add data_generator test scaffold"
```

---

## Task 2: Extend `_RAMADAN_PERIODS` (add 2022/2023, fix 2026 end date)

**Files:**
- Modify: `gamefydb/data_generator.py` (the `_RAMADAN_PERIODS` constant block, lines ~72–77)
- Modify: `tests/test_data_generator.py` (add test)

- [ ] **Step 1: Add the failing test**

Append to `tests/test_data_generator.py`:

```python
def test_ramadan_periods_cover_2022_through_2026():
    """Five Ramadan windows: 2022, 2023, 2024, 2025, 2026."""
    years = sorted({s.year for s, _ in dg._RAMADAN_PERIODS})
    assert years == [2022, 2023, 2024, 2025, 2026]

def test_ramadan_2026_meets_eid_al_fitr():
    """Ramadan 2026 must end no earlier than Mar 19 so it covers the
    pre-Eid prep days (Eid al-Fitr 2026 is Mar 21)."""
    rng_2026 = next((s, e) for s, e in dg._RAMADAN_PERIODS if s.year == 2026)
    assert rng_2026[1] >= pd.Timestamp('2026-03-19')
```

- [ ] **Step 2: Run tests, verify the two new ones fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: 1 PASS, 2 FAIL. Failures should mention `2022` missing and Ramadan 2026 ending too early.

- [ ] **Step 3: Update `_RAMADAN_PERIODS` in `gamefydb/data_generator.py`**

Replace the existing block:

```python
_RAMADAN_PERIODS = [
    (pd.Timestamp('2023-03-22'), pd.Timestamp('2023-04-20')),
    (pd.Timestamp('2024-03-11'), pd.Timestamp('2024-04-09')),
    (pd.Timestamp('2025-03-01'), pd.Timestamp('2025-03-29')),
    (pd.Timestamp('2026-02-17'), pd.Timestamp('2026-03-17')),
]
```

With:

```python
_RAMADAN_PERIODS = [
    (pd.Timestamp('2022-04-02'), pd.Timestamp('2022-05-01')),
    (pd.Timestamp('2023-03-22'), pd.Timestamp('2023-04-20')),
    (pd.Timestamp('2024-03-11'), pd.Timestamp('2024-04-09')),
    (pd.Timestamp('2025-03-01'), pd.Timestamp('2025-03-29')),
    (pd.Timestamp('2026-02-17'), pd.Timestamp('2026-03-19')),  # extended to meet Eid Mar 21
]
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add gamefydb/data_generator.py tests/test_data_generator.py
git commit -m "fix: extend Ramadan periods to 2022 and align 2026 end with Eid"
```

---

## Task 3: Add `_ramadan_daily_mul` helper

**Files:**
- Modify: `gamefydb/data_generator.py` (add function after `_in_ramadan`)
- Modify: `tests/test_data_generator.py` (add tests)

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_data_generator.py`:

```python
class TestRamadanDailyMul:
    def test_outside_ramadan_returns_one(self):
        assert dg._ramadan_daily_mul(pd.Timestamp('2025-07-15')) == 1.0
        assert dg._ramadan_daily_mul(pd.Timestamp('2026-01-01')) == 1.0

    def test_start_of_ramadan_is_near_0_85(self):
        """Ramadan 2025 starts 2025-03-01."""
        val = dg._ramadan_daily_mul(pd.Timestamp('2025-03-01'))
        assert 0.84 <= val <= 0.86

    def test_end_of_ramadan_is_near_1_5(self):
        """Last day of Ramadan should hit the peak ramp value (1.5)."""
        val = dg._ramadan_daily_mul(pd.Timestamp('2025-03-29'))
        assert 1.45 <= val <= 1.5

    def test_mid_ramadan_is_intermediate(self):
        """Around the 50% mark should be between 0.85 and 1.5."""
        val = dg._ramadan_daily_mul(pd.Timestamp('2025-03-15'))
        assert 0.9 < val < 1.3

    def test_ramp_is_monotonic_in_2025(self):
        """Multiplier should be non-decreasing across Ramadan 2025."""
        dates = pd.date_range('2025-03-01', '2025-03-29')
        vals = [dg._ramadan_daily_mul(d) for d in dates]
        assert vals == sorted(vals)
```

- [ ] **Step 2: Run tests, verify the new class fails (function not defined)**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py::TestRamadanDailyMul -v
```

Expected: 5 FAIL with `AttributeError: module 'gamefydb.data_generator' has no attribute '_ramadan_daily_mul'`.

- [ ] **Step 3: Implement `_ramadan_daily_mul` in `gamefydb/data_generator.py`**

Add immediately after the existing `_in_ramadan` function:

```python
def _ramadan_daily_mul(date: pd.Timestamp) -> float:
    """Multiplicative daily shape inside Ramadan.

    Ramps from 0.85 in the first 40 % of the month -> 1.0 -> 1.10 across the
    middle -> 1.50 in the last 25 % (Layilatul Qadr + pre-Eid prep).
    Returns 1.0 outside any Ramadan period.
    """
    for start, end in _RAMADAN_PERIODS:
        if start <= date <= end:
            total = max((end - start).days, 1)
            pos   = (date - start).days / total          # 0.0 -> 1.0
            if pos < 0.40:
                return 0.85 + 0.15 * (pos / 0.40)        # 0.85 -> 1.00
            elif pos < 0.75:
                return 1.00 + 0.10 * ((pos - 0.40) / 0.35)  # 1.00 -> 1.10
            else:
                return 1.10 + 0.40 * ((pos - 0.75) / 0.25)  # 1.10 -> 1.50
    return 1.0
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: 8 PASS total.

- [ ] **Step 5: Commit**

```bash
git add gamefydb/data_generator.py tests/test_data_generator.py
git commit -m "feat: add _ramadan_daily_mul ramp (0.85 -> 1.5 across the month)"
```

---

## Task 4: Convert `_HOLIDAY_BOOST` to year-keyed dict + sync Islamic dates

**Files:**
- Modify: `gamefydb/data_generator.py` (replace the `_HOLIDAY_BOOST` block, lines ~102–126)
- Modify: `tests/test_data_generator.py` (add tests)

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_data_generator.py`:

```python
class TestHolidayBoost:
    def test_keys_are_3_tuples(self):
        """All keys must be (year, month, day)."""
        for k in dg._HOLIDAY_BOOST.keys():
            assert isinstance(k, tuple) and len(k) == 3
            year, month, day = k
            assert 2022 <= year <= 2026
            assert 1 <= month <= 12
            assert 1 <= day <= 31

    def test_eid_al_fitr_2024_present(self):
        """Eid al-Fitr 2024 was Apr 10 — missing in the old dict."""
        assert dg._HOLIDAY_BOOST[(2024, 4, 10)] >= 2.5

    def test_eid_al_fitr_2025_present(self):
        """Eid al-Fitr 2025 is Mar 31 per Prophet's holiday calendar."""
        assert dg._HOLIDAY_BOOST[(2025, 3, 31)] >= 2.5

    def test_eid_al_fitr_2026_present(self):
        """Eid al-Fitr 2026 is Mar 21 — critical for test-set predictions."""
        assert dg._HOLIDAY_BOOST[(2026, 3, 21)] >= 2.5

    def test_eid_al_adha_dates_present(self):
        """Eid al-Adha dates for 2022..2026."""
        expected = [(2022, 7, 9), (2023, 6, 28), (2024, 6, 17),
                    (2025, 6, 7), (2026, 5, 27)]
        for key in expected:
            assert key in dg._HOLIDAY_BOOST, f'Missing Eid al-Adha {key}'

    def test_new_year_lifted(self):
        """New Year's Day was 2.8 in the old dict; spec lifts to 3.2."""
        assert dg._HOLIDAY_BOOST[(2024, 1, 1)] >= 3.0
        assert dg._HOLIDAY_BOOST[(2026, 1, 1)] >= 3.0

    def test_christmas_lifted(self):
        """Christmas was 2.0; spec lifts to 2.5."""
        assert dg._HOLIDAY_BOOST[(2025, 12, 25)] >= 2.4

    def test_civil_holiday_repeats_every_year(self):
        """Republic Day (Jul 25) is fixed-date — present every year."""
        for year in range(2022, 2027):
            assert (year, 7, 25) in dg._HOLIDAY_BOOST
```

- [ ] **Step 2: Run tests, verify the new class fails**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py::TestHolidayBoost -v
```

Expected: 8 FAIL (old dict uses (month, day) 2-tuples).

- [ ] **Step 3: Replace the `_HOLIDAY_BOOST` block in `gamefydb/data_generator.py`**

Delete the existing block:

```python
# Holiday / event boost applied on top of the monthly multiplier.
# Keys are (month, day); values are revenue multipliers.
# Covers both fixed civil holidays and approximate Islamic holidays for 2024-2025.
_HOLIDAY_BOOST = {
    # ... entire current dict ...
}
```

Replace with:

```python
# Holiday / event boost applied on top of the monthly multiplier.
# Keys are (year, month, day); values are revenue multipliers.
# Year-keyed so Islamic holidays (which shift each year) get the correct boost
# on the correct day, and so a calendar mismatch in one year does not leak into
# another (the old (month, day) keys leaked 2025 Eid dates into 2026, etc.).
_HOLIDAY_BOOST: dict = {}

# Civil holidays — repeat every year 2022..2026
_CIVIL_BOOSTS = [
    (1,  1, 3.2),  # New Year's Day  (lifted from 2.8)
    (1, 14, 1.6),  # Revolution Day
    (3, 20, 1.8),  # Independence Day
    (4,  9, 1.5),  # Martyrs' Day
    (5,  1, 1.5),  # Labour Day
    (7, 25, 1.8),  # Republic Day
    (8, 13, 1.5),  # Women's Day
    (10, 15, 1.5), # Evacuation Day
    (12, 25, 2.5), # Christmas (lifted from 2.0)
    (12, 31, 2.7), # New Year's Eve (lifted from 2.5)
]

# Islamic holidays — synced with forecaster.py::_ISLAMIC_HOLIDAYS dates
# Each tuple: (year, month, day, name, boost)
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


def _init_holiday_boost() -> None:
    """Populate _HOLIDAY_BOOST with civil (repeat every year) + Islamic entries."""
    for year in range(2022, 2027):
        for m, d, boost in _CIVIL_BOOSTS:
            try:
                pd.Timestamp(year, m, d)  # validate the date
                _HOLIDAY_BOOST[(year, m, d)] = boost
            except ValueError:
                pass
    for year, m, d, _name, boost in _ISLAMIC_BOOSTS:
        _HOLIDAY_BOOST[(year, m, d)] = boost


_init_holiday_boost()
```

- [ ] **Step 4: Run tests, verify the holiday tests pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py::TestHolidayBoost -v
```

Expected: 8 PASS.

- [ ] **Step 5: Run the full test file to make sure nothing else broke**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: 16 PASS.

- [ ] **Step 6: Commit**

```bash
git add gamefydb/data_generator.py tests/test_data_generator.py
git commit -m "fix: year-keyed _HOLIDAY_BOOST synced with forecaster Islamic dates"
```

---

## Task 5: Add `_eid_week_pattern` helper

**Files:**
- Modify: `gamefydb/data_generator.py` (add constants + function below `_ramadan_daily_mul`)
- Modify: `tests/test_data_generator.py` (add tests)

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_data_generator.py`:

```python
class TestEidWeekPattern:
    def test_outside_eid_window_returns_one(self):
        assert dg._eid_week_pattern(pd.Timestamp('2025-07-15')) == 1.0
        assert dg._eid_week_pattern(pd.Timestamp('2025-12-31')) == 1.0

    def test_eid_day_itself_returns_one(self):
        """Eid day boost comes from _HOLIDAY_BOOST, not from this function."""
        assert dg._eid_week_pattern(pd.Timestamp('2025-03-31')) == 1.0  # Eid al-Fitr 2025
        assert dg._eid_week_pattern(pd.Timestamp('2026-03-21')) == 1.0  # Eid al-Fitr 2026

    def test_eid_plus_1_is_80_percent_of_eid_boost(self):
        """Day after Eid al-Fitr 2026: 1.0 + (3.0 - 1.0) * 0.8 = 2.6."""
        val = dg._eid_week_pattern(pd.Timestamp('2026-03-22'))
        assert abs(val - 2.6) < 0.01

    def test_eid_plus_2_is_60_percent_of_eid_boost(self):
        val = dg._eid_week_pattern(pd.Timestamp('2026-03-23'))
        assert abs(val - 2.2) < 0.01

    def test_eid_plus_3_is_40_percent_of_eid_boost(self):
        val = dg._eid_week_pattern(pd.Timestamp('2026-03-24'))
        assert abs(val - 1.8) < 0.01

    def test_eid_plus_4_returns_one(self):
        """Window is Eid+1..Eid+3 only."""
        assert dg._eid_week_pattern(pd.Timestamp('2026-03-25')) == 1.0

    def test_eid_al_adha_window_also_works(self):
        """Eid al-Adha 2025 is Jun 7; Jun 8 should be elevated."""
        val = dg._eid_week_pattern(pd.Timestamp('2025-06-08'))
        assert val > 1.0
```

- [ ] **Step 2: Run tests, verify the new class fails**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py::TestEidWeekPattern -v
```

Expected: 7 FAIL (`_eid_week_pattern` not defined).

- [ ] **Step 3: Add the constants + function to `gamefydb/data_generator.py`**

Add immediately after `_ramadan_daily_mul`:

```python
# Eid dates per year — must match the Islamic boost entries above.
_EID_DATES: dict[int, list[pd.Timestamp]] = {
    2022: [pd.Timestamp('2022-05-02'), pd.Timestamp('2022-07-09')],
    2023: [pd.Timestamp('2023-04-21'), pd.Timestamp('2023-06-28')],
    2024: [pd.Timestamp('2024-04-10'), pd.Timestamp('2024-06-17')],
    2025: [pd.Timestamp('2025-03-31'), pd.Timestamp('2025-06-07')],
    2026: [pd.Timestamp('2026-03-21'), pd.Timestamp('2026-05-27')],
}

# Eid+N day boost as a fraction of the Eid day boost: 80 %, 60 %, 40 %.
_EID_DAY_OFFSET_RATIO = {1: 0.8, 2: 0.6, 3: 0.4}


def _eid_week_pattern(date: pd.Timestamp) -> float:
    """Boost multiplier for the 3 days following an Eid (Eid+1..Eid+3).

    The Eid day itself is handled by _HOLIDAY_BOOST. For Eid+N (N=1..3),
    apply a decaying fraction of the same boost so the cluster appears as
    a multi-day spike (matches real behaviour — gaming centres stay full
    for several days post-Eid).

    Returns 1.0 outside the Eid+1..Eid+3 window.
    """
    eids = _EID_DATES.get(date.year, [])
    for eid in eids:
        delta = (date - eid).days
        if delta in _EID_DAY_OFFSET_RATIO:
            eid_boost = _HOLIDAY_BOOST.get((eid.year, eid.month, eid.day), 3.0)
            return 1.0 + (eid_boost - 1.0) * _EID_DAY_OFFSET_RATIO[delta]
    return 1.0
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: 23 PASS.

- [ ] **Step 5: Commit**

```bash
git add gamefydb/data_generator.py tests/test_data_generator.py
git commit -m "feat: add _eid_week_pattern for Eid+1..Eid+3 cluster boost"
```

---

## Task 6: Wire multipliers into `generate_cash`, `generate_sessions`, `generate_stock`

**Files:**
- Modify: `gamefydb/data_generator.py` (`generate_cash` lines ~234–304, `generate_sessions` lines ~309–360, `generate_stock` lines ~365–394)
- Modify: `tests/test_data_generator.py` (add integration tests)

- [ ] **Step 1: Add integration tests that check the multipliers actually take effect**

Append to `tests/test_data_generator.py`:

```python
class TestGeneratorsApplyMultipliers:
    """Generate two short windows and check that synthetic revenue on
    holiday-cluster days is materially higher than on neighbouring days."""

    @pytest.fixture(scope='class')
    def synthetic_cash(self):
        """One year covering Ramadan 2025 + Eid al-Fitr 2025."""
        start = pd.Timestamp('2025-02-01')
        end   = pd.Timestamp('2025-04-15')
        return dg.generate_cash(start, end)  # no daily_pool -> parametric path

    def test_eid_al_fitr_2025_spikes_revenue(self, synthetic_cash):
        """Mar 31 2025 (Eid al-Fitr) should average materially higher than
        a baseline week earlier in March."""
        df = synthetic_cash.copy()
        df['day'] = df['date'].dt.normalize()
        daily = df.groupby('day')['amount'].sum()
        eid_rev = daily.get(pd.Timestamp('2025-03-31'), 0.0)
        baseline = daily.loc['2025-02-15':'2025-02-21'].mean()
        assert eid_rev > 1.5 * baseline, (
            f'Eid al-Fitr revenue ({eid_rev:.0f}) should be >1.5x baseline '
            f'({baseline:.0f})'
        )

    def test_eid_plus_1_still_elevated(self, synthetic_cash):
        """Apr 1 2025 (Eid+1) should be above baseline (decaying spike)."""
        df = synthetic_cash.copy()
        df['day'] = df['date'].dt.normalize()
        daily = df.groupby('day')['amount'].sum()
        eid_p1 = daily.get(pd.Timestamp('2025-04-01'), 0.0)
        baseline = daily.loc['2025-02-15':'2025-02-21'].mean()
        assert eid_p1 > 1.2 * baseline

    def test_last_week_of_ramadan_is_elevated(self, synthetic_cash):
        """Last week of Ramadan 2025 (Mar 23-29) should beat first week
        (Mar 01-07) thanks to the ramp."""
        df = synthetic_cash.copy()
        df['day'] = df['date'].dt.normalize()
        daily = df.groupby('day')['amount'].sum()
        first  = daily.loc['2025-03-01':'2025-03-07'].mean()
        last   = daily.loc['2025-03-23':'2025-03-29'].mean()
        assert last > first
```

- [ ] **Step 2: Run the tests — they should fail until multipliers are wired**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py::TestGeneratorsApplyMultipliers -v
```

Expected: 3 FAIL (current generator still uses 2-tuple `_HOLIDAY_BOOST.get((day.month, day.day), 1.0)` which now returns 1.0 because keys are 3-tuples).

- [ ] **Step 3: Update `generate_cash` (lines ~258–272) — replace the multiplier block**

Find this block inside the `while day <= end:` loop:

```python
        # Every Monday refresh the weekly "level" via AR(1): α=0.45
        # New sample blended 55% in, previous state 45% out → correlation ≈ 0.45
        if day.dayofweek == 0:
            new_sample = _sample_base_rev(day.month, daily_pool or {}, all_vals, ref_mul)
            week_level = 0.45 * week_level + 0.55 * new_sample

        holiday_mul = _HOLIDAY_BOOST.get((day.month, day.day), 1.0)

        if daily_pool:
            target_rev = max(5.0, week_level * DOW_MUL[day.dayofweek] * holiday_mul)
        else:
            mul        = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * holiday_mul
            day_factor = max(0.1, float(RNG.lognormal(-0.10, 0.45)))
            target_rev = max(5.0, BASE_DAILY_TX * mul * day_factor * _MEAN_TX_AMT)
```

Replace with:

```python
        # Every Monday refresh the weekly "level" via AR(1): α=0.45
        # New sample blended 55% in, previous state 45% out → correlation ≈ 0.45
        if day.dayofweek == 0:
            new_sample = _sample_base_rev(day.month, daily_pool or {}, all_vals, ref_mul)
            week_level = 0.45 * week_level + 0.55 * new_sample

        holiday_mul  = _HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)
        ramadan_mul  = _ramadan_daily_mul(day)
        eid_week_mul = _eid_week_pattern(day)
        event_mul    = holiday_mul * ramadan_mul * eid_week_mul

        if daily_pool:
            target_rev = max(5.0, week_level * DOW_MUL[day.dayofweek] * event_mul)
        else:
            mul        = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * event_mul
            day_factor = max(0.1, float(RNG.lognormal(-0.10, 0.45)))
            target_rev = max(5.0, BASE_DAILY_TX * mul * day_factor * _MEAN_TX_AMT)
```

- [ ] **Step 4: Update `generate_sessions` (lines ~309–360) — same multiplier change**

Find this block inside the `while day <= end:` loop:

```python
        if day.dayofweek == 0:
            week_mul = 0.45 * week_mul + 0.55 * max(0.2, float(RNG.lognormal(0, 0.28)))
        holiday_mul = _HOLIDAY_BOOST.get((day.month, day.day), 1.0)
        mul = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * week_mul * holiday_mul
        n_sess = max(1, int(RNG.poisson(32 * mul)))
```

Replace with:

```python
        if day.dayofweek == 0:
            week_mul = 0.45 * week_mul + 0.55 * max(0.2, float(RNG.lognormal(0, 0.28)))
        holiday_mul  = _HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)
        ramadan_mul  = _ramadan_daily_mul(day)
        eid_week_mul = _eid_week_pattern(day)
        event_mul    = holiday_mul * ramadan_mul * eid_week_mul
        mul = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * week_mul * event_mul
        n_sess = max(1, int(RNG.poisson(32 * mul)))
```

- [ ] **Step 5: Update `generate_stock` (lines ~365–394) — same multiplier change**

Find this block inside the `while day <= end:` loop:

```python
    day = start
    while day <= end:
        mul = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek]
        n_ev = max(0, int(RNG.poisson(10 * mul)))
```

Replace with:

```python
    day = start
    while day <= end:
        holiday_mul  = _HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)
        ramadan_mul  = _ramadan_daily_mul(day)
        eid_week_mul = _eid_week_pattern(day)
        event_mul    = holiday_mul * ramadan_mul * eid_week_mul
        mul = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * event_mul
        n_ev = max(0, int(RNG.poisson(10 * mul)))
```

- [ ] **Step 6: Run all tests, verify everything passes**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: 26 PASS (8 existing + 3 new integration).

Note: the integration tests run `generate_cash` over ~74 days and should complete in <10 s. If they fail with "Eid revenue not high enough", the multipliers aren't being applied — re-check the get key has `day.year`.

- [ ] **Step 7: Commit**

```bash
git add gamefydb/data_generator.py tests/test_data_generator.py
git commit -m "feat: wire ramadan + eid + holiday multipliers into all three generators"
```

---

## Task 7: Extend `generate_augment` to 24 months + use bootstrap pool

**Files:**
- Modify: `gamefydb/data_generator.py` (`generate_augment` function, lines ~526–563)

- [ ] **Step 1: Replace the `generate_augment` function**

Find:

```python
def generate_augment(excel_dir: str = 'excel', months_back: int = 12) -> None:
    """Generate extra synthetic history and write to excel/augment/.
    ...
    """
    augment_dir = os.path.join(excel_dir, 'augment')
    os.makedirs(augment_dir, exist_ok=True)

    end   = pd.Timestamp('2024-08-31')
    start = (end + pd.Timedelta(days=1)) - pd.DateOffset(months=months_back)
    start = start.normalize()

    print(f'Generating augmentation data: {start.date()} -> {end.date()}')

    print('  Cash transactions...')
    aug_cash = generate_cash(start, end)
    print('  Sessions...')
    aug_sess = generate_sessions(start, end)
    print('  Stock movements...')
    aug_stock = generate_stock(start, end)

    write_cash_xls(aug_cash,    os.path.join(augment_dir, 'augment_cash.xlsx'))
    write_session_xls(aug_sess, os.path.join(augment_dir, 'augment_session.xlsx'))
    write_stock_xls(aug_stock,  os.path.join(augment_dir, 'augment_stock.xlsx'))

    print(f'  Augment cash rows:    {len(aug_cash):,}')
    print(f'  Augment session rows: {len(aug_sess):,}')
    print(f'  Augment stock rows:   {len(aug_stock):,}')
    print(f'  Written to {augment_dir}/')
```

Replace with:

```python
def generate_augment(excel_dir: str = 'excel', months_back: int = 24) -> None:
    """Generate extra synthetic history and write to excel/augment/.

    Files are completely separate from extended_*.xlsx — real data is never
    touched. The pipeline loads augment files alongside the main files only
    in memory during training.

    Default months_back is 24, producing Sep 2022 -> Aug 2024, which gives
    Prophet 3 full Ramadan cycles to learn from (2023, 2024 in augment;
    2025, 2026 in extended).

    Args:
        excel_dir:   Root excel directory (must already exist).
        months_back: How many months to generate going backwards from
                     the start of the synthetic window (Sep 2024).
    """
    from gamefydb.pipeline import load_and_clean_cash

    augment_dir = os.path.join(excel_dir, 'augment')
    os.makedirs(augment_dir, exist_ok=True)

    end   = pd.Timestamp('2024-08-31')
    start = (end + pd.Timedelta(days=1)) - pd.DateOffset(months=months_back)
    start = start.normalize()

    # Build the same bootstrap pool used for extended_*.xlsx so the augment
    # period inherits the real revenue distribution (instead of pure parametric).
    cash_files = [os.path.join(excel_dir, f) for f in os.listdir(excel_dir)
                  if f.lower().endswith('.xls') and 'cash' in f.lower()
                  and 'extended' not in f.lower()]
    daily_pool = None
    if cash_files:
        real_cash = _merge_real_files([(load_and_clean_cash, p) for p in cash_files])
        daily_pool = _build_daily_pool(real_cash)
        print(f'  Bootstrap pool built from {len(cash_files)} real cash file(s)')

    print(f'Generating augmentation data: {start.date()} -> {end.date()}')

    print('  Cash transactions...')
    aug_cash = generate_cash(start, end, daily_pool=daily_pool)
    print('  Sessions...')
    aug_sess = generate_sessions(start, end)
    print('  Stock movements...')
    aug_stock = generate_stock(start, end)

    write_cash_xls(aug_cash,    os.path.join(augment_dir, 'augment_cash.xlsx'))
    write_session_xls(aug_sess, os.path.join(augment_dir, 'augment_session.xlsx'))
    write_stock_xls(aug_stock,  os.path.join(augment_dir, 'augment_stock.xlsx'))

    print(f'  Augment cash rows:    {len(aug_cash):,}')
    print(f'  Augment session rows: {len(aug_sess):,}')
    print(f'  Augment stock rows:   {len(aug_stock):,}')
    print(f'  Written to {augment_dir}/')
```

- [ ] **Step 2: Run unit tests, confirm still passing (no regression)**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_data_generator.py -v
```

Expected: 26 PASS.

- [ ] **Step 3: Commit**

```bash
git add gamefydb/data_generator.py
git commit -m "feat: generate_augment defaults to 24 months and uses bootstrap pool"
```

---

## Task 8: Regenerate `excel/extended_*.xlsx` and `excel/augment/*.xlsx`

**Files:**
- Regenerate: `excel/extended_cash.xlsx`, `excel/extended_session.xlsx`, `excel/extended_stock.xlsx`, `excel/extended_members.xlsx`
- Regenerate: `excel/augment/augment_cash.xlsx`, `excel/augment/augment_session.xlsx`, `excel/augment/augment_stock.xlsx`

- [ ] **Step 1: Verify the real `.xls` files are present (defensive — they should never be touched, but we need them as the bootstrap source)**

```bash
ls C:/Users/sarah/GamefyDB/excel/*.xls
```

Expected output should include `Cash DATA 01-09-2025.xls`, `DATA session reports 01-09-2025.xls`, `Stock DATA 01-09-2025.xls`, `memeber DATA 01-09-2025.xls`, and any older real files (e.g., `14-06-2025 cash.xls`).

- [ ] **Step 2: Regenerate the extended files**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m gamefydb.data_generator
```

Expected output (truncated):
```
Loading real data files...
  cash:    Cash DATA 01-09-2025.xls
  ...
Generating synthetic data: 2024-09-01 -> 2025-08-31
  Cash transactions...
  ...
Writing extended Excel files...
  Saved excel/extended_cash.xlsx  (N rows)
  ...
```

The script must complete without error. Expect a runtime of ~30–60 s.

- [ ] **Step 3: Regenerate the augment files (24 months back)**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -c "from gamefydb.data_generator import generate_augment; generate_augment()"
```

Expected output:
```
  Bootstrap pool built from N real cash file(s)
Generating augmentation data: 2022-09-01 -> 2024-08-31
  Cash transactions...
  Sessions...
  Stock movements...
  Saved excel/augment/augment_cash.xlsx  (M rows)
  ...
  Written to excel/augment/
```

Runtime: ~45–90 s for 24 months.

- [ ] **Step 4: Sanity-check the file sizes (no zero-byte regressions)**

```bash
ls -la C:/Users/sarah/GamefyDB/excel/extended_*.xlsx C:/Users/sarah/GamefyDB/excel/augment/*.xlsx
```

Each file should be > 100 KB. If any file is <10 KB, the generation failed silently — investigate before proceeding.

- [ ] **Step 5: Confirm real `.xls` files are unchanged (sanity check the "don't touch real data" guarantee)**

```bash
git status excel/
```

Expected: only `excel/extended_*.xlsx` and `excel/augment/augment_*.xlsx` listed as modified/created. NO entries for `Cash DATA 01-09-2025.xls` or the other real files.

If any real `.xls` file appears as modified, STOP and revert immediately:

```bash
git checkout -- "excel/Cash DATA 01-09-2025.xls" "excel/DATA session reports 01-09-2025.xls" "excel/Stock DATA 01-09-2025.xls" "excel/memeber DATA 01-09-2025.xls"
```

- [ ] **Step 6: Commit the regenerated data files**

```bash
git add excel/extended_cash.xlsx excel/extended_session.xlsx excel/extended_stock.xlsx excel/extended_members.xlsx excel/augment/augment_cash.xlsx excel/augment/augment_session.xlsx excel/augment/augment_stock.xlsx
git commit -m "data: regenerate synthetic + augment with ramadan/eid signal fix"
```

---

## Task 9: Verify forecast accuracy improvement

**Files:**
- Run: `run.py` (no code changes)
- Inspect: `docs/model_comparison.csv`, `docs/accuracy_*.png`

- [ ] **Step 1: Run the full pipeline**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python C:/Users/sarah/GamefyDB/run.py --input excel --output output
```

Expected: the pipeline runs end-to-end, prints stationarity tests, prints Prophet/SARIMA/XGBoost wMAPE for each series, writes forecast CSVs to `output/`, and regenerates figures in `docs/`.

- [ ] **Step 2: Compare wMAPE numbers against baseline**

Check the console output for lines like:

```
    [Revenue (TND)] 80/20 split — N_train train / N_test test points
      [Prophet] MAPE  XX.X%  MAE   XXX.XX  RMSE   XXX.XX  -> GOOD/ACCEPTABLE/POOR
      [SARIMA]  MAPE  XX.X%  ...
      [XGBoost] MAPE  XX.X%  ...
```

**Note: the test set will shift.** With 24 more months of augment data, total days grow from ~560 → ~1280, so the 80/20 split now gives ~1024 train / ~256 test instead of 448/112. The test period extends backward from ~Dec 2025 to ~Oct 2025 — it still includes Christmas/NY/Ramadan/Eid (the critical stretch). wMAPE on a longer test set is more statistically reliable but not directly comparable to the old 112-day number.

Baseline (before changes, 112-day test):
- Revenue Prophet: 49.1 %
- Session volume Prophet: 38.7 %
- Member activity Prophet: 67.1 %

Target on the new ~256-day test:
- Revenue Prophet: < 35 %
- Session volume Prophet: < 30 %
- Member activity Prophet: < 50 %

If any series regresses dramatically (wMAPE > 70 %), investigate before claiming success.

- [ ] **Step 3: Visually inspect `docs/accuracy_revenue_prophet.png`**

Open the file. Confirm:
1. Training-data peaks (light-blue line) reach 800–1000 TND in summer months and around Dec/Mar (holidays).
2. Prophet prediction line (green) shows visible peaks around Christmas 2025, New Year 2026, and Mar 21 2026 (Eid al-Fitr) — not a flat band.
3. The Mar 2026 region in the test set is no longer wildly under-predicted.

- [ ] **Step 4: Spot-check synthetic Ramadan 2025 in the regenerated data**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -c "
import pandas as pd
from gamefydb.pipeline import load_and_clean_cash
df = load_and_clean_cash('excel/extended_cash.xlsx')
df = df[(df['date'] >= '2025-03-01') & (df['date'] <= '2025-04-05')]
daily = df.groupby(df['date'].dt.normalize())['amount'].sum()
print(daily.to_string())
"
```

Expected pattern:
- Mar 01-07: lowest revenue (Ramadan start, multiplier 0.85)
- Mar 23-29: revenue ramps up (multiplier toward 1.5)
- Mar 31: huge spike (Eid al-Fitr 3.0× boost)
- Apr 01: still elevated (Eid+1 2.6×)
- Apr 02: 2.2× (Eid+2)
- Apr 03: 1.8× (Eid+3)
- Apr 04+: back to normal

If Mar 31 is not a clear spike, the multipliers are not being applied — investigate.

- [ ] **Step 5: Commit the updated figures + comparison CSV**

```bash
git add docs/accuracy_revenue_prophet.png docs/accuracy_revenue_sarima.png docs/accuracy_revenue_xgboost.png docs/accuracy_revenue.png docs/accuracy_session_volume_prophet.png docs/accuracy_session_volume_sarima.png docs/accuracy_session_volume_xgboost.png docs/accuracy_session_volume.png docs/accuracy_members_prophet.png docs/accuracy_members_sarima.png docs/accuracy_members_xgboost.png docs/accuracy_members.png docs/model_comparison.csv docs/model_comparison_bar.png docs/prophet_revenue_forecast.png
git commit -m "docs: refresh accuracy figures and model comparison after data fix"
```

- [ ] **Step 6: Update memory with new wMAPE numbers**

Open `C:/Users/sarah/.claude/projects/C--Users-sarah-GamefyDB/memory/project_ml_forecasting.md`
and update the evaluation results table with the new wMAPE values.

---

## Done

When all tasks above are complete:
- 44 months of training data (24 months augment + 12 months extended-synthetic + 8 months real)
- Year-keyed holiday boost synced with Prophet's calendar
- Ramadan ramp + Eid week cluster pattern across all 5 synthetic years (2022–2026)
- wMAPE measurably improved
- Real `.xls` files untouched
