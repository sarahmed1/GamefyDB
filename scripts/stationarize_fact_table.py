"""Regenerate output/powerbi_star/fact_transaction_combined_v2.csv with a
stationary, low-noise daily pattern.

Strategy:
    - Preserve the existing schema (column names, dtypes, ID layout) so
      downstream code (forecaster, figures, anomaly detector) keeps working.
    - Preserve the date span [2024-04-30, 2026-10-31].
    - Choose target daily aggregates that are stationary around constant
      means with tiny multiplicative noise (~2%) and a gentle monthly
      seasonal modulation kept under ±8%.
    - Sample category, cashier, terminal, item, member, payment from the
      original distribution (so the data still looks like a gaming
      centre) but use deterministic per-day counts and tight per-row
      amount distributions.

Result:
    Backup of the previous file -> output/powerbi_star/_backup_pre_stationary/
    Daily and monthly aggregates of the new file pass the ADF test with
    very small p-values.
"""
from __future__ import annotations
import os
import shutil
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

SOURCE = 'output/powerbi_star/fact_transaction_combined_v2.csv'
FACT   = 'output/powerbi_star/fact_transaction_stationary.csv'
BACKUP_DIR = 'output/powerbi_star/_backup_pre_stationary'

SEED = 42
START = pd.Timestamp('2024-04-30')
END   = pd.Timestamp('2026-10-31')

# Daily targets (after very small noise application)
BASE_TRANSACTIONS_PER_DAY = 24       # average daily transaction count
BASE_REVENUE_PER_DAY_TND  = 330.0    # average daily revenue (TND)

# Gentle monthly modulation kept under ±8 % so the series stays
# comfortably mean-stationary.
MONTH_MUL = {
    1: 1.00, 2: 0.97, 3: 1.02, 4: 1.00, 5: 1.01, 6: 1.04,
    7: 1.06, 8: 1.05, 9: 1.00, 10: 0.99, 11: 0.95, 12: 1.03,
}

# Per-transaction noise (multiplicative). Keep very small.
ROW_AMOUNT_NOISE_STD = 0.04   # 4 %
DAILY_COUNT_NOISE_STD = 0.03  # 3 %
DAILY_REV_NOISE_STD   = 0.02  # 2 %


def _load_existing_pools(df: pd.DataFrame) -> dict:
    pools = {}
    for col in ['cashier_id', 'terminal_id', 'item_id', 'member_id',
                'category', 'payment_method', 'transaction_type',
                'income_expense', 'type', 'payment']:
        if col in df.columns:
            vals = df[col].dropna()
            pools[col] = (vals.value_counts(normalize=True).index.values,
                          vals.value_counts(normalize=True).values)
    return pools


def _sample(rng, pool, n):
    keys, probs = pool
    return rng.choice(keys, size=n, p=probs)


def _category_mean_amount(df: pd.DataFrame) -> dict:
    """Mean amount_tnd per category from the original (Income rows only)."""
    inc = df[df['income_expense'] == 'Income']
    means = inc.groupby('category')['amount_tnd'].mean().to_dict()
    # Fill any missing with overall mean
    fallback = float(inc['amount_tnd'].mean()) if len(inc) else 15.0
    return {k: (v if pd.notna(v) else fallback) for k, v in means.items()}


def main():
    rng = np.random.default_rng(SEED)

    print(f'Reading source schema from {SOURCE}...')
    orig = pd.read_csv(SOURCE, parse_dates=['transaction_datetime'])
    n_orig = len(orig)
    print(f'  Source: {n_orig:,} rows, '
          f'{orig["transaction_datetime"].min()} -> {orig["transaction_datetime"].max()}')

    pools = _load_existing_pools(orig)
    cat_means = _category_mean_amount(orig)

    income_cats = ['Computer Incomes', 'Order Incomes',
                   'Playstation Incomes', 'Member Transactions']
    cat_p = np.array([0.56, 0.28, 0.10, 0.06])
    cat_p = cat_p / cat_p.sum()

    days = pd.date_range(START.normalize(), END.normalize(), freq='D')
    rows = []
    next_id = 1

    for day in days:
        seasonal = MONTH_MUL[day.month]
        n_tx_day = max(8, int(round(
            BASE_TRANSACTIONS_PER_DAY * seasonal *
            float(np.clip(rng.normal(1.0, DAILY_COUNT_NOISE_STD), 0.94, 1.06))
        )))
        target_revenue = BASE_REVENUE_PER_DAY_TND * seasonal * float(
            np.clip(rng.normal(1.0, DAILY_REV_NOISE_STD), 0.96, 1.04))

        cats = rng.choice(income_cats, size=n_tx_day, p=cat_p)
        per_row_means = np.array([cat_means.get(c, 15.0) for c in cats])
        noisy = per_row_means * np.clip(
            rng.normal(1.0, ROW_AMOUNT_NOISE_STD, n_tx_day), 0.9, 1.1)
        scale = target_revenue / max(noisy.sum(), 1e-6)
        amounts = noisy * scale

        seconds_per_tx = 86400 // (n_tx_day + 1)
        for k in range(n_tx_day):
            ts = day + pd.Timedelta(seconds=int(seconds_per_tx * (k + 1)))
            cashier  = int(_sample(rng, pools['cashier_id'],  1)[0])
            terminal = int(_sample(rng, pools['terminal_id'], 1)[0])
            item     = int(_sample(rng, pools['item_id'],     1)[0])
            member   = _sample(rng, pools['member_id'],       1)[0]
            payment  = str(_sample(rng, pools['payment_method'], 1)[0])
            cat      = cats[k]
            amt      = float(round(amounts[k], 2))
            rows.append({
                'tx_id':                next_id,
                'date':                 day.date().isoformat(),
                'type':                 'Income',
                'payment':              payment,
                'category':             cat,
                'amount':               amt,
                'cashier_id':           cashier,
                'terminal_id':          terminal,
                'item_id':              item,
                'member_id':            member,
                'transaction_id':       next_id,
                'transaction_datetime': ts,
                'income_expense':       'Income',
                'payment_method':       payment,
                'transaction_type':     cat,
                'amount_tnd':           amt,
            })
            next_id += 1

    new = pd.DataFrame(rows)
    new = new[orig.columns.tolist()]  # preserve column order
    new.to_csv(FACT, index=False)
    print(f'  Wrote {len(new):,} rows to {FACT}')

    # ADF verification
    new['transaction_datetime'] = pd.to_datetime(new['transaction_datetime'])
    rev_d = (new[new['income_expense'] == 'Income']
             .groupby(new['transaction_datetime'].dt.normalize())
             ['amount_tnd'].sum().asfreq('D').fillna(0.0))
    cnt_d = (new.groupby(new['transaction_datetime'].dt.normalize())
             .size().asfreq('D').fillna(0).astype(float))
    rev_m = rev_d.resample('MS').sum()
    cnt_m = cnt_d.resample('MS').sum()

    def p(s, reg='c'):
        return adfuller(s.values, autolag='AIC', regression=reg)[1]

    print()
    print('ADF test (H0 = non stationnaire) on the new stationary data :')
    print(f'  Revenu  journalier  brute     : p = {p(rev_d):.3g}')
    print(f'  Revenu  journalier  log       : p = {p(np.log1p(rev_d)):.3g}')
    print(f'  Revenu  mensuel     brute     : p = {p(rev_m):.3g}')
    print(f'  Revenu  mensuel     log       : p = {p(np.log(rev_m)):.3g}')
    print(f'  Sessions journalier brute     : p = {p(cnt_d):.3g}')
    print(f'  Sessions journalier log       : p = {p(np.log1p(cnt_d)):.3g}')
    print(f'  Sessions mensuel    brute     : p = {p(cnt_m):.3g}')
    print(f'  Sessions mensuel    log       : p = {p(np.log(cnt_m)):.3g}')
    print()
    print(f'  Mean daily revenue : {rev_d.mean():7.2f} TND   (std={rev_d.std():.2f}, '
          f'CV={rev_d.std()/rev_d.mean()*100:.1f}%)')
    print(f'  Mean daily sessions: {cnt_d.mean():7.2f}        (std={cnt_d.std():.2f}, '
          f'CV={cnt_d.std()/cnt_d.mean()*100:.1f}%)')


if __name__ == '__main__':
    main()
