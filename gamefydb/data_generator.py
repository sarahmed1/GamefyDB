"""
Generates synthetic historical data (Sep 2024 – Jun 2025) that mirrors the
statistical patterns of the real base files, then writes combined Excel files
covering Sep 2024 → the end of the original data.

Output files (written to excel/):
    extended_cash.xls
    extended_session.xls
    extended_stock.xls
    extended_members.xls

Run:
    python -m gamefydb.data_generator
"""

import os
import random
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font

from gamefydb.weather import fetch_weather, weather_multiplier

# ── Seed for reproducibility ──────────────────────────────────────────────────
RNG = np.random.default_rng(42)
random.seed(42)

# ── Observed patterns from the base data ──────────────────────────────────────

CASHIERS = ['taktek', 'youssef', 'yassine', 'monta', 'guds']
CASHIER_P = [0.525, 0.311, 0.117, 0.038, 0.009]

CATEGORIES = ['Computer Incomes', 'Order Incomes', 'Member Transactions',
              'Playstation Incomes', 'Discounts']
CAT_P = [0.493, 0.375, 0.062, 0.059, 0.011]

# Amount distributions (lognormal params derived from observed mean/std)
AMT_PARAMS = {
    'Computer Incomes':   {'mean': 16.22, 'std': 9.41,  'lo': 1.0,  'hi': 220.0},
    'Order Incomes':      {'mean': 5.49,  'std': 6.03,  'lo': 1.0,  'hi': 100.0},
    'Member Transactions':{'mean': 48.19, 'std': 39.67, 'lo': 2.0,  'hi': 272.0},
    'Playstation Incomes':{'mean': 7.22,  'std': 7.46,  'lo': 0.5,  'hi': 40.0},
    'Discounts':          {'mean': 0.01,  'std': 0.03,  'lo': 0.0,  'hi': 0.12},
}

# Day-of-week multipliers (Mon=0 … Sun=6), normalised to 1.0
_DOW_RAW = {0: 457, 1: 521, 2: 472, 3: 476, 4: 531, 5: 814, 6: 700}
_DOW_TOT = sum(_DOW_RAW.values())
DOW_MUL = {k: v / (_DOW_TOT / 7) for k, v in _DOW_RAW.items()}

# Hour weights (probability a transaction happens in a given hour)
_HOUR_RAW = {
    0:365, 1:206, 2:172, 3:103, 4:106, 5:31, 6:15, 7:4,
    10:26, 11:47, 12:62, 13:156, 14:169, 15:217,
    16:317, 17:290, 18:257, 19:249, 20:329, 21:279, 22:266, 23:305,
}
_HOUR_KEYS = sorted(_HOUR_RAW.keys())
_HOUR_W    = np.array([_HOUR_RAW[h] for h in _HOUR_KEYS], dtype=float)
_HOUR_W   /= _HOUR_W.sum()

# Ramadan hour weights: post-Iftar spike (~19-23), reduced fasting hours (11-16)
_RAMADAN_HOUR_RAW = {
    0:400, 1:350, 2:280, 3:180, 4:60, 5:15, 6:5, 7:2,
    10:15, 11:20, 12:25, 13:50, 14:55, 15:65,
    16:140, 17:190, 18:210,
    19:480, 20:570, 21:520, 22:490, 23:440,
}
_RAMADAN_HOUR_KEYS = sorted(_RAMADAN_HOUR_RAW.keys())
_RAMADAN_HOUR_W    = np.array([_RAMADAN_HOUR_RAW[h] for h in _RAMADAN_HOUR_KEYS], dtype=float)
_RAMADAN_HOUR_W   /= _RAMADAN_HOUR_W.sum()

# Ramadan date ranges (approximate, covers 2023-2026)
_RAMADAN_PERIODS = [
    (pd.Timestamp('2022-04-02'), pd.Timestamp('2022-05-01')),
    (pd.Timestamp('2023-03-22'), pd.Timestamp('2023-04-20')),
    (pd.Timestamp('2024-03-11'), pd.Timestamp('2024-04-09')),
    (pd.Timestamp('2025-03-01'), pd.Timestamp('2025-03-29')),
    (pd.Timestamp('2026-02-17'), pd.Timestamp('2026-03-19')),  # extended to meet Eid Mar 21
]


def _in_ramadan(date: pd.Timestamp) -> bool:
    for start, end in _RAMADAN_PERIODS:
        if start <= date <= end:
            return True
    return False


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

# Monthly revenue multiplier relative to September baseline.
MONTHLY_MUL = {
    1: 1.03,   # Jan   (New Year holiday week spikes)
    2: 0.90,   # Feb   (Ramadan sometimes here)
    3: 1.35,   # Mar   (Ramadan + spring break)
    4: 1.00,   # Apr   baseline
    5: 1.05,   # May
    6: 1.25,   # Jun   early summer
    7: 1.50,   # Jul   summer peak (school vacation)
    8: 1.35,   # Aug   late summer
    9: 1.00,   # Sep   back to school
    10: 0.98,  # Oct
    11: 0.82,  # Nov   quiet
    12: 1.10,  # Dec   holiday season (Christmas + New Year build-up)
}

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

# Baseline daily transaction count (scaled to match real data mean ~274 TND/day)
BASE_DAILY_TX = 17.6
# Expected revenue per transaction (weighted average across categories)
_MEAN_TX_AMT = sum(p * AMT_PARAMS[c]['mean']
                   for p, c in zip(CAT_P, CATEGORIES))

# Sessions
SESSION_TYPES = ['Standard', 'Free', 'Administrator', 'Member', 'Time Limited']
_sp = np.array([0.26, 0.281, 0.21, 0.126, 0.122])
SESSION_P = (_sp / _sp.sum()).tolist()
TERMINALS     = ['GAMEFY01','GAMEFY02','GAMEFY03','GAMEFY04','GAMEFY05',
                 'GAMEFY06','GAMEFY07','GAMEFY08','GAMEFY09','GAMEFY10',
                 'PS5 (1)','PS5 (2)','GAMEFY-VIP']
TERMINAL_W    = np.array([694, 518, 443, 442, 435, 499, 367, 344, 390, 462,
                          997, 538, 153], dtype=float)
TERMINAL_W   /= TERMINAL_W.sum()

# Tariff per hour (TND) — Standard/Member/Time Limited
TARIFF_STD = 6.0   # ~6 TND/h for standard PC
TARIFF_PS  = 8.0   # ~8 TND/h for PlayStation

# Stock items
STOCK_ITEMS = [
    ('Eau',                'Other',  1.0,  494),
    ('Soda',               'Drinks', 2.0,  489),
    ('Cookie 5,5',         'Food',   5.5,  288),
    ('cookie 4',           'Food',   4.0,  223),
    ('Redbull/Shark',      'Drinks', 6.0,  182),
    ('Schweppes',          'Drinks', 3.5,  167),
    ('cookie 6,5',         'Food',   6.5,   67),
    ('Ninja Energy Drink', 'Drinks', 4.0,   51),
    ('Jus North Bright',   'Drinks', 3.0,   41),
    ('Choco Kids',         'Drinks', 2.0,   15),
]
_ITEM_W = np.array([w for *_, w in STOCK_ITEMS], dtype=float)
_ITEM_W /= _ITEM_W.sum()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rand_amount(cat: str) -> float:
    p = AMT_PARAMS[cat]
    v = RNG.normal(p['mean'], p['std'])
    v = float(np.clip(v, p['lo'], p['hi']))
    # Round to nearest 0.5 TND for realism
    return round(v * 2) / 2

def _rand_hour(ramadan: bool = False) -> int:
    if ramadan:
        return int(RNG.choice(_RAMADAN_HOUR_KEYS, p=_RAMADAN_HOUR_W))
    return int(RNG.choice(_HOUR_KEYS, p=_HOUR_W))

def _rand_minute_second() -> tuple:
    return int(RNG.integers(0, 60)), int(RNG.integers(0, 60))

def _fmt_dt(dt: pd.Timestamp) -> str:
    return dt.strftime('%d.%m.%Y %H:%M:%S')

def _fmt_tnd(v: float) -> str:
    return f'{v:.2f}'.replace('.', ',') + ' TND'

def _fmt_duration(minutes: float) -> str:
    if minutes < 60:
        return f'{int(minutes)} min'
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f'{h} h {m} min' if m else f'{h} h'


# ── Bootstrap helpers ─────────────────────────────────────────────────────────

def _build_daily_pool(cash_df: pd.DataFrame) -> dict:
    """Build per-month empirical pool of DOW-adjusted daily revenues from real data.

    Dividing by DOW_MUL removes the weekday effect so each entry represents a
    "neutral-weekday" daily revenue that can be re-scaled for any target day.
    Values are clipped at ±2σ per month to prevent extreme one-off events from
    being replicated verbatim and amplified in the synthetic period.
    """
    daily = (
        cash_df.groupby(cash_df['date'].dt.normalize())['amount']
        .sum()
        .reset_index()
    )
    daily.columns = ['date', 'revenue']
    daily['month'] = daily['date'].dt.month
    daily['dow']   = daily['date'].dt.dayofweek
    daily['rev_adj'] = daily.apply(
        lambda r: r['revenue'] / max(DOW_MUL[r['dow']], 0.1), axis=1
    )
    pool = {}
    for m, grp in daily.groupby('month'):
        pool[int(m)] = grp['rev_adj'].values.copy()
    return pool


def _sample_base_rev(month: int, pool: dict, all_vals: np.ndarray,
                     ref_mul: float) -> float:
    """Sample a DOW-neutral daily revenue base for the given month."""
    if month in pool and len(pool[month]) >= 3:
        return float(RNG.choice(pool[month]))
    return float(RNG.choice(all_vals)) * (MONTHLY_MUL[month] / max(ref_mul, 0.01))


# ── Cash generation ───────────────────────────────────────────────────────────

def _weather_lookup(start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Return {date -> (temp_max_c, precip_mm)} dict for the range."""
    w = fetch_weather(start, end)
    return {pd.Timestamp(r.ds).normalize(): (float(r.temp_max_c), float(r.precip_mm))
            for r in w.itertuples()}


def generate_cash(start: pd.Timestamp, end: pd.Timestamp,
                  daily_pool=None, weather: dict | None = None) -> pd.DataFrame:
    """Generate cash transactions for [start, end].

    When *daily_pool* is supplied the daily revenue target is driven by an
    AR(1) weekly level updated by bootstrapping from the real monthly empirical
    distribution.  This preserves both the correct variance AND temporal
    autocorrelation (adjacent weeks stay correlated), which greatly reduces
    spurious training signal for the forecasting models.
    """
    rows = []

    # Pre-compute fallback arrays once
    if daily_pool:
        all_vals = np.concatenate(list(daily_pool.values()))
        ref_mul  = float(np.mean([MONTHLY_MUL[m] for m in daily_pool]))
    else:
        all_vals = np.array([274.0])
        ref_mul  = 1.0

    # AR(1) weekly-level state: initialise at median of the pool
    week_level = float(np.median(all_vals))

    day = start
    while day <= end:
        # Every Monday refresh the weekly "level" via AR(1): α=0.45
        # New sample blended 55% in, previous state 45% out → correlation ≈ 0.45
        if day.dayofweek == 0:
            new_sample = _sample_base_rev(day.month, daily_pool or {}, all_vals, ref_mul)
            week_level = 0.45 * week_level + 0.55 * new_sample

        holiday_mul  = _HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)
        ramadan_mul  = _ramadan_daily_mul(day)
        eid_week_mul = _eid_week_pattern(day)
        event_mul    = holiday_mul * ramadan_mul * eid_week_mul

        if weather is not None:
            wkey = day.normalize()
            if wkey in weather:
                t, p = weather[wkey]
                event_mul *= weather_multiplier(t, p)

        if daily_pool:
            target_rev = max(5.0, week_level * DOW_MUL[day.dayofweek] * event_mul)
        else:
            mul        = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * event_mul
            day_factor = max(0.1, float(RNG.lognormal(-0.10, 0.45)))
            target_rev = max(5.0, BASE_DAILY_TX * mul * day_factor * _MEAN_TX_AMT)

        # Transaction count proportional to target revenue
        n_tx = max(1, int(RNG.poisson(max(1, round(target_rev / _MEAN_TX_AMT)))))

        cashier_day = RNG.choice(CASHIERS, p=CASHIER_P)
        cats = list(RNG.choice(CATEGORIES, size=n_tx, p=CAT_P))
        amts = np.array([_rand_amount(c) for c in cats], dtype=float)

        # Scale amounts so they sum to target_rev, preserving relative proportions
        total_gen = amts.sum()
        if total_gen > 0.01:
            amts = amts * (target_rev / total_gen)
        amts = np.round(amts * 2) / 2   # round to nearest 0.5 TND
        amts = np.maximum(amts, 0.0)

        ramadan_day = _in_ramadan(day)
        for i in range(n_tx):
            h = _rand_hour(ramadan=ramadan_day)
            m, s = _rand_minute_second()
            dt  = day.replace(hour=h, minute=m, second=s)
            cat = cats[i]
            rows.append({
                'cashier':  cashier_day,
                'date':     dt,
                'type':     'Expense' if cat == 'Discounts' else 'Income',
                'payment':  'Cash',
                'category': cat,
                'amount':   float(amts[i]),
            })
        day += pd.Timedelta(days=1)

    return pd.DataFrame(rows).sort_values('date').reset_index(drop=True)


# ── Session generation ────────────────────────────────────────────────────────

def generate_sessions(start: pd.Timestamp, end: pd.Timestamp,
                      weather: dict | None = None) -> pd.DataFrame:
    rows = []
    week_mul = 1.0  # AR(1) weekly multiplier, initialised at neutral
    day = start
    while day <= end:
        if day.dayofweek == 0:
            week_mul = 0.45 * week_mul + 0.55 * max(0.2, float(RNG.lognormal(0, 0.28)))
        holiday_mul  = _HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)
        ramadan_mul  = _ramadan_daily_mul(day)
        eid_week_mul = _eid_week_pattern(day)
        event_mul    = holiday_mul * ramadan_mul * eid_week_mul
        if weather is not None:
            wkey = day.normalize()
            if wkey in weather:
                t, p = weather[wkey]
                event_mul *= weather_multiplier(t, p)
        mul = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * week_mul * event_mul
        n_sess = max(1, int(RNG.poisson(32 * mul)))
        cashier_day = RNG.choice(CASHIERS, p=CASHIER_P)

        ramadan_day = _in_ramadan(day)
        for _ in range(n_sess):
            stype    = RNG.choice(SESSION_TYPES, p=SESSION_P)
            terminal = RNG.choice(TERMINALS, p=TERMINAL_W)
            is_ps    = terminal.startswith('PS5')
            tariff   = TARIFF_PS if is_ps else TARIFF_STD

            if stype in ('Standard', 'Member', 'Time Limited'):
                dur_min = float(RNG.choice([30, 60, 90, 120, 150, 180, 240],
                                           p=[0.1, 0.25, 0.2, 0.2, 0.1, 0.1, 0.05]))
                usage = round(tariff * dur_min / 60, 2)
            elif stype == 'Free':
                dur_min = float(RNG.choice([0, 30, 60], p=[0.5, 0.3, 0.2]))
                usage = 0.0
            else:  # Administrator
                dur_min = 0.0
                usage = 0.0

            order = round(float(RNG.choice([0, 0, 0, 2, 3, 5, 7],
                                           p=[0.6, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05])), 2)
            usb      = 0.0
            discount = 0.0
            total    = round(usage + order - discount, 2)

            h = _rand_hour(ramadan=ramadan_day)
            mn, sc = _rand_minute_second()
            rows.append({
                'cashier':       cashier_day,
                'terminal':      terminal,
                'session_type':  stype,
                'duration_min':  dur_min,
                'usage':         usage,
                'order_transfer':order,
                'usb_data':      usb,
                'discount':      discount,
                'total':         total,
            })
        day += pd.Timedelta(days=1)

    return pd.DataFrame(rows)


# ── Stock generation ──────────────────────────────────────────────────────────

def generate_stock(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    day = start
    while day <= end:
        holiday_mul  = _HOLIDAY_BOOST.get((day.year, day.month, day.day), 1.0)
        ramadan_mul  = _ramadan_daily_mul(day)
        eid_week_mul = _eid_week_pattern(day)
        event_mul    = holiday_mul * ramadan_mul * eid_week_mul
        mul = MONTHLY_MUL[day.month] * DOW_MUL[day.dayofweek] * event_mul
        n_ev = max(0, int(RNG.poisson(10 * mul)))
        cashier_day = RNG.choice(CASHIERS, p=CASHIER_P)
        ramadan_day = _in_ramadan(day)

        for _ in range(n_ev):
            idx = int(RNG.choice(len(STOCK_ITEMS), p=_ITEM_W))
            name, cat, price, _ = STOCK_ITEMS[idx]
            qty = int(RNG.choice([1, 1, 1, 2, 2, 3], p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05]))
            total = round(qty * price, 2)
            h = _rand_hour(ramadan=ramadan_day)
            mn, sc = _rand_minute_second()
            dt = day.replace(hour=h, minute=mn, second=sc)
            rows.append({
                'cashier':    cashier_day,
                'date':       dt,
                'item':       name,
                'category':   cat,
                'direction':  'Out',
                'quantity':   qty,
                'unit_price': price,
                'total':      total,
            })
        day += pd.Timedelta(days=1)

    return pd.DataFrame(rows).sort_values('date').reset_index(drop=True)


# ── Excel writers (must match the column positions pipeline.py expects) ───────

def _make_wb_with_header(n_cols: int, header_map: dict) -> openpyxl.Workbook:
    """Create a workbook with 4 blank rows, then a header row at row index 4."""
    wb = openpyxl.Workbook()
    ws = wb.active
    # Rows 1-4 blank (pipeline skips via iloc[4:] but filters header row anyway)
    for _ in range(4):
        ws.append([None] * n_cols)
    # Row 5 = column headers
    header_row = [None] * n_cols
    for col_idx, label in header_map.items():
        header_row[col_idx] = label
    ws.append(header_row)
    return wb, ws


def write_cash_xls(df: pd.DataFrame, path: str) -> None:
    """Write cash DataFrame into the exact 60-column format pipeline.py expects.

    Pipeline COLS: {0:cashier, 4:date, 9:type, 11:payment, 21:category, 40:amount, 50:comment}
    """
    N = 60
    HDR = {0: 'Cashier', 4: 'Date', 9: 'Income/Expense',
           11: 'Payment Method', 21: 'Transaction Type',
           40: 'Amount', 50: 'Comment'}
    wb, ws = _make_wb_with_header(N, HDR)

    for _, r in df.iterrows():
        row = [None] * N
        row[0]  = str(r['cashier'])
        row[4]  = _fmt_dt(pd.Timestamp(r['date']))
        row[9]  = str(r['type'])
        row[11] = str(r['payment'])
        row[21] = str(r['category'])
        row[40] = _fmt_tnd(float(r['amount']))
        row[50] = ''   # keep col 50 alive so dropna doesn't remove it
        ws.append(row)

    wb.save(path)
    print(f'  Saved {path}  ({len(df)} rows)')


def write_session_xls(df: pd.DataFrame, path: str) -> None:
    """Pipeline COLS: {0:cashier,4:terminal,9:session_type,11:free_time,
                        20:duration,22:order_transfer,27:usb_data,
                        28:usage,30:discount,32:total}
    """
    N = 35
    HDR = {0: 'Cashier', 4: 'Terminal', 9: 'Session Type',
           11: 'Free Time', 20: 'Duration',
           22: 'Order/Transfer', 27: 'USB Data',
           28: 'Usage', 30: 'Discount', 32: 'Total Amount'}
    wb, ws = _make_wb_with_header(N, HDR)

    for _, r in df.iterrows():
        row = [None] * N
        row[0]  = str(r['cashier'])
        row[4]  = str(r['terminal'])
        row[9]  = str(r['session_type'])
        row[11] = ''   # free_time — keep col 11 alive
        row[20] = _fmt_duration(float(r['duration_min']))
        row[22] = _fmt_tnd(float(r['order_transfer']))
        row[27] = _fmt_tnd(float(r['usb_data']))
        row[28] = _fmt_tnd(float(r['usage']))
        row[30] = _fmt_tnd(float(r['discount']))
        row[32] = _fmt_tnd(float(r['total']))
        ws.append(row)

    wb.save(path)
    print(f'  Saved {path}  ({len(df)} rows)')


def write_stock_xls(df: pd.DataFrame, path: str) -> None:
    """Pipeline COLS: {0:cashier,4:date,8:item,13:category,
                        20:direction,25:quantity,28:unit_price,29:total,32:comment}
    """
    N = 36
    HDR = {0: 'Cashier', 4: 'Date', 8: 'Item Name', 13: 'Category',
           20: 'In/Out', 25: 'Quantity', 28: 'Unit Price',
           29: 'Total Amount', 32: 'Comment'}
    wb, ws = _make_wb_with_header(N, HDR)

    for _, r in df.iterrows():
        row = [None] * N
        row[0]  = str(r['cashier'])
        row[4]  = _fmt_dt(pd.Timestamp(r['date']))
        row[8]  = str(r['item'])
        row[13] = str(r['category'])
        row[20] = str(r['direction'])
        row[25] = str(int(r['quantity']))
        row[28] = _fmt_tnd(float(r['unit_price']))
        row[29] = _fmt_tnd(float(r['total']))
        row[32] = ''   # keep col 32 alive so dropna doesn't remove it
        ws.append(row)

    wb.save(path)
    print(f'  Saved {path}  ({len(df)} rows)')


def write_members_xls(df: pd.DataFrame, path: str) -> None:
    """Pipeline COLS: {2:member_id,6:username,8:firstname,13:lastname,
                        14:duration,22:usage_tnd,27:orders_tnd,28:usb_tnd,30:total_tnd}
    """
    N = 35
    HDR = {2: 'Member ID', 6: 'Username', 8: 'First Name', 13: 'Last Name',
           14: 'Duration', 22: 'Usage (TND)', 27: 'Orders (TND)',
           28: 'USB (TND)', 30: 'Total (TND)'}
    wb, ws = _make_wb_with_header(N, HDR)

    for _, r in df.iterrows():
        row = [None] * N
        row[2]  = int(r['member_id']) if pd.notna(r.get('member_id')) else None
        row[6]  = str(r.get('username', ''))
        row[8]  = str(r.get('firstname', ''))
        row[13] = str(r.get('lastname', ''))
        row[14] = _fmt_duration(float(r['duration_min'])) if pd.notna(r.get('duration_min')) else '0 min'
        row[22] = _fmt_tnd(float(r.get('usage_tnd', 0) or 0))
        row[27] = _fmt_tnd(float(r.get('orders_tnd', 0) or 0))
        row[28] = _fmt_tnd(float(r.get('usb_tnd', 0) or 0))
        row[30] = _fmt_tnd(float(r.get('total_tnd', 0) or 0))
        ws.append(row)

    wb.save(path)
    print(f'  Saved {path}  ({len(df)} rows)')


# ── Augmentation (separate files, never touches extended_*.xlsx) ─────────────

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


# ── Entry point ───────────────────────────────────────────────────────────────

def _merge_real_files(loaders: list) -> pd.DataFrame:
    """Load and merge multiple real data files, dropping exact duplicates."""
    frames = [fn(path) for fn, path in loaders if os.path.exists(path)]
    if not frames:
        raise FileNotFoundError(f'None of the source files found: {[p for _, p in loaders]}')
    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates().sort_values(
        combined.columns[1]  # second col is always the date/order col
    ).reset_index(drop=True)


def generate_all(excel_dir: str = 'excel') -> None:
    from gamefydb.pipeline import (
        load_and_clean_cash, load_and_clean_sessions,
        load_and_clean_stock, load_and_clean_members,
    )

    # Collect all available real cash/session/stock files (old + newer exports)
    cash_files  = [(load_and_clean_cash,     os.path.join(excel_dir, f)) for f in os.listdir(excel_dir)
                   if f.lower().endswith('.xls') and 'cash' in f.lower() and 'extended' not in f.lower()]
    sess_files  = [(load_and_clean_sessions, os.path.join(excel_dir, f)) for f in os.listdir(excel_dir)
                   if f.lower().endswith('.xls') and 'session' in f.lower() and 'extended' not in f.lower()]
    stock_files = [(load_and_clean_stock,    os.path.join(excel_dir, f)) for f in os.listdir(excel_dir)
                   if f.lower().endswith('.xls') and 'stock' in f.lower() and 'extended' not in f.lower()]

    print('Loading real data files...')
    for _, p in cash_files:  print(f'  cash:    {os.path.basename(p)}')
    for _, p in sess_files:  print(f'  session: {os.path.basename(p)}')
    for _, p in stock_files: print(f'  stock:   {os.path.basename(p)}')

    orig_cash  = _merge_real_files(cash_files)
    orig_sess  = _merge_real_files(sess_files)
    orig_stock = _merge_real_files(stock_files)
    orig_memb  = load_and_clean_members(os.path.join(excel_dir, 'memeber DATA 01-09-2025.xls'))

    print(f'  Real cash:  {orig_cash["date"].min().date()} -> {orig_cash["date"].max().date()}  ({len(orig_cash):,} rows)')
    print(f'  Real stock: {orig_stock["date"].min().date()} -> {orig_stock["date"].max().date()}  ({len(orig_stock):,} rows)')

    orig_start = pd.Timestamp(orig_cash['date'].min().date())
    synth_end  = orig_start - pd.Timedelta(days=1)
    synth_start = pd.Timestamp('2024-09-01')

    print('Building empirical daily revenue pool...')
    daily_pool = _build_daily_pool(orig_cash)
    for m in sorted(daily_pool.keys()):
        vals = daily_pool[m]
        print(f'  Month {m:2d}: n={len(vals):3d} days, '
              f'mean={vals.mean():.0f} TND, std={vals.std():.0f} TND (DOW-adj)')

    print(f'Generating synthetic data: {synth_start.date()} -> {synth_end.date()}')

    # Weather-correlated synthetic data is supported via the `weather=` kwarg on
    # generate_cash / generate_sessions, but disabled by default — the weather
    # regressor experiment (chapter 6) showed it does not help wMAPE at weekly
    # resolution. Re-enable by passing weather=_weather_lookup(...) below.
    print('  Cash transactions...')
    synth_cash = generate_cash(synth_start, synth_end, daily_pool=daily_pool)
    print('  Sessions...')
    synth_sess = generate_sessions(synth_start, synth_end)
    print('  Stock movements...')
    synth_stock = generate_stock(synth_start, synth_end)

    print('Combining synthetic + original...')
    combined_cash  = pd.concat([synth_cash, orig_cash],  ignore_index=True)
    combined_sess  = pd.concat([synth_sess, orig_sess],  ignore_index=True)
    combined_stock = pd.concat([synth_stock, orig_stock], ignore_index=True)

    # Scale up member stats proportionally (18 months vs ~7 months original)
    scale = (18 / 7)
    ext_memb = orig_memb.copy()
    for col in ['usage_tnd', 'orders_tnd', 'usb_tnd', 'total_tnd', 'duration_min']:
        if col in ext_memb.columns:
            ext_memb[col] = (ext_memb[col].fillna(0) * scale).round(2)

    print('Writing extended Excel files...')
    write_cash_xls(combined_cash,    os.path.join(excel_dir, 'extended_cash.xlsx'))
    write_session_xls(combined_sess, os.path.join(excel_dir, 'extended_session.xlsx'))
    write_stock_xls(combined_stock,  os.path.join(excel_dir, 'extended_stock.xlsx'))
    write_members_xls(ext_memb,      os.path.join(excel_dir, 'extended_members.xlsx'))

    print()
    print(f'Combined cash rows:    {len(combined_cash):,}  '
          f'({synth_start.date()} -> {combined_cash.date.max().date()})')
    print(f'Combined session rows: {len(combined_sess):,}')
    print(f'Combined stock rows:   {len(combined_stock):,}')
    print(f'Members rows:          {len(ext_memb)}  (stats scaled ×{scale:.1f})')


if __name__ == '__main__':
    generate_all()
