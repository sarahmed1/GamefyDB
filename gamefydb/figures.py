import logging
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from pmdarima import auto_arima
from prophet import Prophet
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import adfuller
from xgboost import XGBRegressor

logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)

# ── palette & style ───────────────────────────────────────────────────────────
C_TRAIN  = '#3A7ABF'   # steel blue  — historical / training data
C_TEST   = '#E05A2B'   # terracotta  — test / highlight
C_PRED   = '#2E8B57'   # sea green   — Prophet
C_SARIMA = '#E8A838'   # amber       — SARIMA
C_XGB    = '#7B52AB'   # violet      — XGBoost
C_NAIVE  = '#9E9E9E'   # medium gray — naive baseline
C_GRID   = '#E8E8E8'   # light gray  — grid lines
C_BG     = '#FAFAFA'   # off-white   — axes background

FIG_W    = 10
TITLE_FS = 13

plt.rcParams.update({
    'font.family':         'DejaVu Sans',
    'font.size':           11,
    'axes.titlesize':      TITLE_FS,
    'axes.titleweight':    'bold',
    'axes.titlepad':       10,
    'axes.labelsize':      10,
    'axes.labelcolor':     '#333333',
    'axes.edgecolor':      '#CCCCCC',
    'axes.linewidth':      0.8,
    'axes.facecolor':      C_BG,
    'axes.grid':           True,
    'grid.color':          C_GRID,
    'grid.linewidth':      0.7,
    'grid.linestyle':      '--',
    'axes.spines.top':     False,
    'axes.spines.right':   False,
    'xtick.color':         '#555555',
    'ytick.color':         '#555555',
    'xtick.labelsize':     9,
    'ytick.labelsize':     9,
    'legend.fontsize':     9,
    'legend.framealpha':   0.85,
    'legend.edgecolor':    '#CCCCCC',
    'figure.facecolor':    'white',
    'figure.dpi':          100,
    'savefig.dpi':         150,
    'savefig.bbox':        'tight',
})


def _save(fig, path):
    fig.savefig(path)
    plt.close(fig)
    print(f'    Saved: {os.path.basename(path)}')


def _to_daily(df, date_col, value_col):
    daily = df.copy()
    daily['ds'] = pd.to_datetime(daily[date_col]).dt.normalize()
    return daily.groupby('ds')[value_col].sum().reset_index().rename(
        columns={value_col: 'y'})


# ── 1. Rolling mean (stationarity graphical check) ────────────────────────────

def plot_stationarity_rolling(transactions_df: pd.DataFrame, out_dir: str) -> None:
    """3-panel figure: raw series + rolling mean for each forecast series."""
    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    rev = _to_daily(income, 'transaction_datetime', '_v')

    vol = transactions_df.copy()
    vol['_v'] = 1
    vol_daily = _to_daily(vol, 'transaction_datetime', '_v')

    mem = transactions_df[transactions_df['transaction_type'] == 'Member Transactions'].copy()
    mem['_v'] = 1
    mem_d = _to_daily(mem, 'transaction_datetime', '_v')
    mem_d['_w'] = mem_d['ds'].dt.to_period('W').apply(lambda p: p.start_time)
    mem_w = mem_d.groupby('_w')['y'].sum().reset_index().rename(columns={'_w': 'ds'})
    mem_w['ds'] = pd.to_datetime(mem_w['ds'])

    series_list = [
        (rev,       7, 'Daily Revenue (TND)',   'Revenue (TND)'),
        (vol_daily, 7, 'Daily Session Volume',  'Number of transactions'),
        (mem_w,     4, 'Weekly Member Activity','Number of members'),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(FIG_W, 9), sharex=False)

    for ax, (df, win, title, ylabel) in zip(axes, series_list):
        ax.plot(df['ds'], df['y'],
                color='#AACFE4', linewidth=1.2, label='Observed')
        ax.plot(df['ds'], df['y'].rolling(win, center=True).mean(),
                color=C_TRAIN, linewidth=2.2, label=f'Rolling mean (window={win})')
        ax.set_title(title, fontsize=12, pad=6)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis='x', rotation=25)
        ax.legend(loc='upper right', framealpha=0.85)

    plt.tight_layout(pad=2.0)
    _save(fig, os.path.join(out_dir, 'stationarity_rolling.png'))


# ── 2. Train / test split diagram ─────────────────────────────────────────────

def plot_train_test_split(transactions_df: pd.DataFrame, out_dir: str,
                          split: float = 0.8) -> None:
    vol = transactions_df.copy()
    vol['ds'] = pd.to_datetime(vol['transaction_datetime']).dt.normalize()
    dates = vol.groupby('ds').size().reset_index()[['ds']].sort_values('ds')
    n = len(dates)
    cut = int(n * split)
    d_start = dates['ds'].iloc[0].strftime('%d %b %Y')
    d_cut   = dates['ds'].iloc[cut - 1].strftime('%d %b %Y')
    d_end   = dates['ds'].iloc[-1].strftime('%d %b %Y')

    fig, ax = plt.subplots(figsize=(FIG_W, 2.2))
    ax.set_facecolor('white')
    ax.grid(False)

    ax.barh(0, split,     left=0,     height=0.55, color=C_TRAIN,
            label=f'Training set  ({int(split*100)} %)',  zorder=3)
    ax.barh(0, 1 - split, left=split, height=0.55, color=C_TEST,
            label=f'Test set  ({int((1-split)*100)} %)',  zorder=3)

    ax.text(split / 2,           0, f'Training\n{d_start} → {d_cut}',
            ha='center', va='center', color='white', fontweight='bold', fontsize=10)
    ax.text(split + (1-split)/2, 0, f'Test\n{d_cut} → {d_end}',
            ha='center', va='center', color='white', fontweight='bold', fontsize=10)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.55, 0.55)
    ax.set_yticks([])
    ax.set_xticks([0, split, 1])
    ax.set_xticklabels(['0 %', f'{int(split*100)} %', '100 %'])
    ax.set_xlabel('Time progression')
    ax.set_title('80 / 20 Chronological Train–Test Split')
    ax.legend(loc='upper right', bbox_to_anchor=(1.01, 1.45), ncol=2)

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'train_test_split.png'))


# ── 3. Actual vs predicted helpers ────────────────────────────────────────────

def _prophet_test_preds(df, split, freq='D', log_y=False):
    from gamefydb.forecaster import _build_holiday_df
    n = len(df)
    cut = int(n * split)
    train, test = df.iloc[:cut].copy(), df.iloc[cut:].copy()
    fit_train = train.copy()
    if log_y:
        fit_train['y'] = np.log1p(fit_train['y'])
    holiday_df = _build_holiday_df(df['ds'].min(), df['ds'].max())
    m = Prophet(interval_width=0.8,
                holidays=holiday_df if holiday_df is not None else None,
                holidays_prior_scale=20.0)
    m.fit(fit_train)
    future = m.make_future_dataframe(periods=len(test), freq=freq)
    fc = m.predict(future)
    if log_y:
        for col in ('yhat', 'yhat_lower', 'yhat_upper'):
            fc[col] = np.expm1(fc[col])
    merged = test.merge(fc[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds', how='inner')
    return train, test, merged


def _xgboost_test_preds(df, split):
    from gamefydb.forecaster import _evaluate_xgboost
    result = _evaluate_xgboost(df, split)
    if result is None:
        return df.iloc[int(len(df) * split):], None
    n = len(df)
    cut = int(n * split)
    return df.iloc[cut:], result['preds']


def _sarima_test_preds(df, split, m_period):
    n = len(df)
    cut = int(n * split)
    train, test = df.iloc[:cut], df.iloc[cut:]
    try:
        model = auto_arima(train['y'], seasonal=True, m=m_period,
                           stepwise=True, suppress_warnings=True,
                           error_action='ignore', information_criterion='aic')
        preds = model.predict(n_periods=len(test))
        return test, preds
    except Exception:
        return test, None


def _mae(actual, pred): return float(np.abs(actual - pred).mean())
def _rmse(actual, pred): return float(np.sqrt(((actual - pred) ** 2).mean()))
def _mape(actual, pred):
    nz = actual != 0
    if not nz.any():
        return float('nan')
    return float(np.abs((actual[nz] - pred[nz]) / actual[nz]).mean() * 100)


def _naive_baseline(train, test):
    t = train.copy()
    t['dow'] = t['ds'].dt.dayofweek
    # For weekly series all dates share the same weekday — fall back to overall mean
    if t['dow'].nunique() == 1:
        return np.full(len(test), t['y'].mean())
    means = t.groupby('dow')['y'].mean()
    t2 = test.copy()
    t2['dow'] = t2['ds'].dt.dayofweek
    return t2['dow'].map(means).values


# ── 3-shared. Compute all predictions once ────────────────────────────────────

def _compute_all_predictions(tx: pd.DataFrame, split: float = 0.8) -> dict:
    """Fit Prophet, SARIMA, and XGBoost on train and generate test predictions
    for all three forecast series.  Called once by generate_all_figures so that
    the accuracy plots and the comparison chart share the same fitted models."""
    from gamefydb.forecaster import _to_weekly

    income = tx[tx['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    rev_daily  = _to_daily(income, 'transaction_datetime', '_v')
    rev_weekly = _to_weekly(rev_daily)

    vol = tx.copy()
    vol['_v'] = 1
    vol_daily  = _to_daily(vol, 'transaction_datetime', '_v')
    vol_weekly = _to_weekly(vol_daily)

    mem = tx[tx['transaction_type'] == 'Member Transactions'].copy()
    mem['_v'] = 1
    mem_d = _to_daily(mem, 'transaction_datetime', '_v')
    mem_w = _to_weekly(mem_d)

    def _eval(df, freq, m_period, log_y=False):
        train, test, p_merged = _prophet_test_preds(df, split, freq=freq, log_y=log_y)
        s_test, s_preds       = _sarima_test_preds(df, split, m_period)
        x_test, x_preds       = _xgboost_test_preds(df, split)
        return {
            'train': train, 'test': test,
            'prophet': p_merged,
            'sarima':  (s_test, s_preds),
            'xgb':     (x_test, x_preds),
        }

    print('    Revenue series (weekly, log)...')
    rev = _eval(rev_weekly, '7D', 4, log_y=True)
    print('    Session volume series (weekly, log)...')
    ses = _eval(vol_weekly, '7D', 4, log_y=True)
    print('    Member activity series (weekly)...')
    mem_r = _eval(mem_w, '7D', 4)
    return {'revenue': rev, 'sessions': ses, 'members': mem_r}


def _plot_single_model_accuracy(train, test, model_name, color, linestyle,
                                pred_ds, pred_actual, pred_values,
                                yhat_lower=None, yhat_upper=None,
                                title='', ylabel='', out_path='',
                                shade_ramadan=False):
    """One-model accuracy plot: historical + actual + naive baseline + one model."""
    fig, ax = plt.subplots(figsize=(FIG_W, 5))

    show_train = train.iloc[-60:] if len(train) > 60 else train
    ax.plot(show_train['ds'], show_train['y'],
            color='#AACFE4', linewidth=1.2, label='Historical (train)')

    ax.plot(pred_ds, pred_actual,
            color='#333333', linewidth=2, label='Actual (test)')

    naive = _naive_baseline(train, test)
    ax.plot(test['ds'], naive,
            color=C_NAIVE, linewidth=1.2, linestyle=':',
            label=f'Naive baseline  (MAPE {_mape(test["y"].values, naive):.0f} %)')

    if yhat_lower is not None and yhat_upper is not None:
        ax.fill_between(pred_ds, yhat_lower, yhat_upper, alpha=0.15, color=color)

    mae_v  = _mae(pred_actual, pred_values)
    mape_v = _mape(pred_actual, pred_values)
    ax.plot(pred_ds, pred_values, color=color, linewidth=2, linestyle=linestyle,
            label=f'{model_name}  MAPE {mape_v:.0f} %  MAE {mae_v:.1f}')

    # Capture ylim after all series are plotted so annotations are placed correctly
    ylim_top = ax.get_ylim()[1]

    split_date = test['ds'].iloc[0]
    ax.axvline(split_date, color='#AAAAAA', linestyle='--', linewidth=1)
    ax.text(split_date, ylim_top * 0.98, '  train | test',
            fontsize=8.5, color='#888888', va='top')

    if shade_ramadan:
        r_start = pd.Timestamp('2026-02-18')  # Ramadan 2026 (approx., ±1 day moon sighting)
        r_end   = pd.Timestamp('2026-03-19')
        ax.axvspan(r_start, r_end, alpha=0.07, color='#9B59B6', zorder=0)
        ax.text(r_start, ylim_top * 0.90, ' Ramadan\n 2026',
                fontsize=8, color='#9B59B6', va='top')

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8.5, loc='upper left')
    ax.tick_params(axis='x', rotation=25)
    plt.tight_layout()
    _save(fig, out_path)


# ── 3a-c. Accuracy per series ─────────────────────────────────────────────────

def plot_accuracy_revenue(out_dir: str, preds: dict, split: float = 0.8) -> None:
    train, test     = preds['train'], preds['test']
    p_merged        = preds['prophet']
    s_test, s_preds = preds['sarima']
    x_test, x_preds = preds['xgb']

    base = 'Revenue (TND) — Actual vs Predicted (20 % test set)'
    kw   = dict(ylabel='Revenue (TND)', shade_ramadan=True)

    if not p_merged.empty:
        _plot_single_model_accuracy(
            train, test, model_name='Prophet', color=C_PRED, linestyle='-',
            pred_ds=p_merged['ds'].values, pred_actual=p_merged['y'].values,
            pred_values=p_merged['yhat'].values,
            yhat_lower=p_merged['yhat_lower'].values,
            yhat_upper=p_merged['yhat_upper'].values,
            title=f'{base} — Prophet',
            out_path=os.path.join(out_dir, 'accuracy_revenue_prophet.png'), **kw)

    if s_preds is not None:
        _plot_single_model_accuracy(
            train, test, model_name='SARIMA', color=C_SARIMA, linestyle='--',
            pred_ds=s_test['ds'].values, pred_actual=s_test['y'].values,
            pred_values=s_preds,
            title=f'{base} — SARIMA',
            out_path=os.path.join(out_dir, 'accuracy_revenue_sarima.png'), **kw)

    if x_preds is not None:
        _plot_single_model_accuracy(
            train, test, model_name='XGBoost', color=C_XGB, linestyle=(0, (4, 2)),
            pred_ds=x_test['ds'].values, pred_actual=x_test['y'].values,
            pred_values=x_preds,
            title=f'{base} — XGBoost',
            out_path=os.path.join(out_dir, 'accuracy_revenue_xgboost.png'), **kw)


def plot_accuracy_session_volume(out_dir: str, preds: dict, split: float = 0.8) -> None:
    train, test     = preds['train'], preds['test']
    p_merged        = preds['prophet']
    s_test, s_preds = preds['sarima']
    x_test, x_preds = preds['xgb']

    base = 'Session Volume — Actual vs Predicted (20 % test set)'
    kw   = dict(ylabel='Transactions / day')

    if not p_merged.empty:
        _plot_single_model_accuracy(
            train, test, model_name='Prophet', color=C_PRED, linestyle='-',
            pred_ds=p_merged['ds'].values, pred_actual=p_merged['y'].values,
            pred_values=p_merged['yhat'].values,
            yhat_lower=p_merged['yhat_lower'].values,
            yhat_upper=p_merged['yhat_upper'].values,
            title=f'{base} — Prophet',
            out_path=os.path.join(out_dir, 'accuracy_session_volume_prophet.png'), **kw)

    if s_preds is not None:
        _plot_single_model_accuracy(
            train, test, model_name='SARIMA', color=C_SARIMA, linestyle='--',
            pred_ds=s_test['ds'].values, pred_actual=s_test['y'].values,
            pred_values=s_preds,
            title=f'{base} — SARIMA',
            out_path=os.path.join(out_dir, 'accuracy_session_volume_sarima.png'), **kw)

    if x_preds is not None:
        _plot_single_model_accuracy(
            train, test, model_name='XGBoost', color=C_XGB, linestyle=(0, (4, 2)),
            pred_ds=x_test['ds'].values, pred_actual=x_test['y'].values,
            pred_values=x_preds,
            title=f'{base} — XGBoost',
            out_path=os.path.join(out_dir, 'accuracy_session_volume_xgboost.png'), **kw)


def plot_accuracy_members(out_dir: str, preds: dict, split: float = 0.8) -> None:
    train, test     = preds['train'], preds['test']
    p_merged        = preds['prophet']
    s_test, s_preds = preds['sarima']
    x_test, x_preds = preds['xgb']

    base = 'Member Activity (weekly) — Actual vs Predicted (20 % test set)'
    kw   = dict(ylabel='Member transactions / week')

    if not p_merged.empty:
        _plot_single_model_accuracy(
            train, test, model_name='Prophet', color=C_PRED, linestyle='-',
            pred_ds=p_merged['ds'].values, pred_actual=p_merged['y'].values,
            pred_values=p_merged['yhat'].values,
            yhat_lower=p_merged['yhat_lower'].values,
            yhat_upper=p_merged['yhat_upper'].values,
            title=f'{base} — Prophet',
            out_path=os.path.join(out_dir, 'accuracy_members_prophet.png'), **kw)

    if s_preds is not None:
        _plot_single_model_accuracy(
            train, test, model_name='SARIMA', color=C_SARIMA, linestyle='--',
            pred_ds=s_test['ds'].values, pred_actual=s_test['y'].values,
            pred_values=s_preds,
            title=f'{base} — SARIMA',
            out_path=os.path.join(out_dir, 'accuracy_members_sarima.png'), **kw)

    if x_preds is not None:
        _plot_single_model_accuracy(
            train, test, model_name='XGBoost', color=C_XGB, linestyle=(0, (4, 2)),
            pred_ds=x_test['ds'].values, pred_actual=x_test['y'].values,
            pred_values=x_preds,
            title=f'{base} — XGBoost',
            out_path=os.path.join(out_dir, 'accuracy_members_xgboost.png'), **kw)


# ── 4. Model comparison grouped bar ───────────────────────────────────────────

def plot_model_comparison(out_dir: str, all_preds: dict) -> None:
    """Grouped bar chart comparing Prophet / SARIMA / XGBoost across all series.
    Uses pre-computed predictions — no model re-training."""

    def _metrics(p_merged, s_test, s_preds, x_test, x_preds):
        nan3 = (float('nan'),) * 3
        p_vals = ((_mape(p_merged['y'].values, p_merged['yhat'].values),
                   _mae(p_merged['y'].values,  p_merged['yhat'].values),
                   _rmse(p_merged['y'].values, p_merged['yhat'].values))
                  if not p_merged.empty else nan3)
        s_vals = ((_mape(s_test['y'].values, s_preds),
                   _mae(s_test['y'].values,  s_preds),
                   _rmse(s_test['y'].values, s_preds))
                  if s_preds is not None else nan3)
        x_vals = ((_mape(x_test['y'].values, x_preds),
                   _mae(x_test['y'].values,  x_preds),
                   _rmse(x_test['y'].values, x_preds))
                  if x_preds is not None else nan3)
        return p_vals, s_vals, x_vals

    r = all_preds['revenue']
    v = all_preds['sessions']
    m = all_preds['members']

    r_p, r_s, r_x = _metrics(r['prophet'], *r['sarima'], *r['xgb'])
    v_p, v_s, v_x = _metrics(v['prophet'], *v['sarima'], *v['xgb'])
    m_p, m_s, m_x = _metrics(m['prophet'], *m['sarima'], *m['xgb'])

    labels   = ['Revenue', 'Session Vol.', 'Member Act.']
    p_mapes  = [r_p[0], v_p[0], m_p[0]]
    s_mapes  = [r_s[0], v_s[0], m_s[0]]
    x_mapes  = [r_x[0], v_x[0], m_x[0]]
    p_maes   = [r_p[1], v_p[1], m_p[1]]
    s_maes   = [r_s[1], v_s[1], m_s[1]]
    x_maes   = [r_x[1], v_x[1], m_x[1]]

    pos = np.arange(len(labels))
    w   = 0.24

    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, 4.5))
    fig.suptitle('Prophet vs SARIMA vs XGBoost — 80/20 chronological split', y=1.01)

    for ax, p_vals, s_vals, x_vals, metric in [
        (axes[0], p_mapes, s_mapes, x_mapes, 'MAPE (%)'),
        (axes[1], p_maes,  s_maes,  x_maes,  'MAE'),
    ]:
        bp = ax.bar(pos - w, p_vals, w, color=C_PRED,   label='Prophet',  zorder=3)
        bs = ax.bar(pos,     s_vals, w, color=C_SARIMA, label='SARIMA',   zorder=3)
        bx = ax.bar(pos + w, x_vals, w, color=C_XGB,   label='XGBoost',  zorder=3)
        ax.set_xticks(pos)
        ax.set_xticklabels(labels)
        ax.set_ylabel(metric)
        ax.set_title(metric)
        ax.legend(fontsize=9)
        for bars in [bp, bs, bx]:
            for bar in bars:
                h = bar.get_height()
                if not np.isnan(h):
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            h + ax.get_ylim()[1] * 0.01,
                            f'{h:.0f}', ha='center', va='bottom',
                            fontsize=8, color='#333333')

    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'model_comparison_bar.png'))

    rows = []
    for label, pv, sv, xv in zip(labels,
                                  zip(p_mapes, p_maes, [r_p[2], v_p[2], m_p[2]]),
                                  zip(s_mapes, s_maes, [r_s[2], v_s[2], m_s[2]]),
                                  zip(x_mapes, x_maes, [r_x[2], v_x[2], m_x[2]])):
        rows.append({'series': label,
                     'prophet_mape':  round(pv[0], 1), 'prophet_mae':  round(pv[1], 1), 'prophet_rmse':  round(pv[2], 1),
                     'sarima_mape':   round(sv[0], 1), 'sarima_mae':   round(sv[1], 1), 'sarima_rmse':   round(sv[2], 1),
                     'xgboost_mape':  round(xv[0], 1), 'xgboost_mae':  round(xv[1], 1), 'xgboost_rmse':  round(xv[2], 1)})
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, 'model_comparison.csv'), index=False)
    print(f'    Saved: model_comparison.csv')


# ── 5. Prophet revenue forecast ───────────────────────────────────────────────

def plot_prophet_revenue_forecast(transactions_df: pd.DataFrame, out_dir: str) -> None:
    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    daily = _to_daily(income, 'transaction_datetime', '_v')

    m = Prophet(interval_width=0.8)
    m.fit(daily)
    future = m.make_future_dataframe(periods=90)
    fc = m.predict(future)

    hist_end  = daily['ds'].max()
    fc_future = fc[fc['ds'] > hist_end]

    fig, ax = plt.subplots(figsize=(FIG_W, 4.5))
    ax.plot(daily['ds'], daily['y'],
            color='#AACFE4', linewidth=1.2, label='Historical revenue')
    ax.plot(fc_future['ds'], fc_future['yhat'],
            color=C_PRED, linewidth=2.2, linestyle='--', label='Forecast (3 months)')
    ax.fill_between(fc_future['ds'], fc_future['yhat_lower'], fc_future['yhat_upper'],
                    alpha=0.18, color=C_PRED, label='80 % confidence band')
    ax.axvline(hist_end, color='#AAAAAA', linestyle='--', linewidth=1)
    ax.text(hist_end, ax.get_ylim()[1] * 0.97, '  forecast →',
            fontsize=9, color='#888888', va='top')
    ax.set_title('Revenue Forecast — Prophet (next 3 months)')
    ax.set_ylabel('Revenue (TND)')
    ax.legend()
    ax.tick_params(axis='x', rotation=25)
    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'prophet_revenue_forecast.png'))


# ── 6 & 7. Peak hours / days ──────────────────────────────────────────────────

def _gradient_colors(values, low='#AACFE4', high=None):
    """Return a list of colors shaded by value magnitude."""
    if high is None:
        high = C_TRAIN
    vmin, vmax = min(values), max(values)
    span = vmax - vmin if vmax != vmin else 1
    from matplotlib.colors import to_rgb
    lo = np.array(to_rgb(low))
    hi = np.array(to_rgb(high))
    return [tuple(lo + (v - vmin) / span * (hi - lo)) for v in values]


def plot_peak_hours(forecasts_dir: str, out_dir: str) -> None:
    path = os.path.join(forecasts_dir, 'peak_hours_by_hour.csv')
    if not os.path.exists(path):
        print('    Skipping peak_hours_bar.png (CSV not found)')
        return
    df = pd.read_csv(path)
    colors = _gradient_colors(df['avg_transactions'].tolist())
    fig, ax = plt.subplots(figsize=(FIG_W, 4))
    bars = ax.bar(df['hour'].astype(str), df['avg_transactions'],
                  color=colors, zorder=3)
    for bar, v in zip(bars, df['avg_transactions']):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ax.get_ylim()[1] * 0.01,
                f'{v:.1f}', ha='center', va='bottom', fontsize=7.5)
    ax.set_xlabel('Hour of day')
    ax.set_ylabel('Avg transactions')
    ax.set_title('Average Transaction Volume by Hour of Day')
    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'peak_hours_bar.png'))


def plot_peak_days(forecasts_dir: str, out_dir: str) -> None:
    path = os.path.join(forecasts_dir, 'peak_hours_by_day.csv')
    if not os.path.exists(path):
        print('    Skipping peak_days_bar.png (CSV not found)')
        return
    df = pd.read_csv(path)
    colors = _gradient_colors(df['avg_transactions'].tolist())
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(df['day_of_week'], df['avg_transactions'],
                  color=colors, zorder=3)
    for bar, v in zip(bars, df['avg_transactions']):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ax.get_ylim()[1] * 0.01,
                f'{v:.1f}', ha='center', va='bottom', fontsize=8)
    ax.set_xlabel('Day of week')
    ax.set_ylabel('Avg transactions')
    ax.set_title('Average Transaction Volume by Day of Week')
    ax.tick_params(axis='x', rotation=20)
    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'peak_days_bar.png'))


# ── 8. K-means elbow ──────────────────────────────────────────────────────────

def plot_kmeans_elbow(dim_member: pd.DataFrame, out_dir: str) -> None:
    feats     = ['total_tnd', 'duration_min', 'orders_tnd']
    available = [c for c in feats if c in dim_member.columns]
    if not available:
        print('    Skipping kmeans_elbow.png (feature columns missing)')
        return
    X        = StandardScaler().fit_transform(dim_member[available].fillna(0))
    ks       = list(range(1, 11))
    inertias = [KMeans(n_clusters=k, random_state=42, n_init=10).fit(X).inertia_
                for k in ks]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(ks, inertias, 'o-', color=C_TRAIN, linewidth=2.2,
            markersize=7, markerfacecolor='white', markeredgewidth=2,
            markeredgecolor=C_TRAIN, zorder=3)
    ax.axvline(4, color=C_TEST, linestyle='--', linewidth=1.8, label='Chosen k = 4')
    ax.set_xlabel('Number of clusters (k)')
    ax.set_ylabel('Inertia')
    ax.set_title('K-Means Elbow — Optimal Number of Clusters')
    ax.legend()
    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'kmeans_elbow.png'))


# ── 9. K-means scatter ────────────────────────────────────────────────────────

def plot_kmeans_scatter(forecasts_dir: str, out_dir: str) -> None:
    path = os.path.join(forecasts_dir, 'member_segments.csv')
    if not os.path.exists(path):
        print('    Skipping kmeans_scatter.png (CSV not found)')
        return
    df = pd.read_csv(path, encoding='utf-8-sig')
    if 'total_tnd' not in df.columns or 'duration_min' not in df.columns:
        print('    Skipping kmeans_scatter.png (required columns missing)')
        return

    palette   = [C_TRAIN, C_TEST, C_PRED, C_SARIMA, C_XGB, '#2ECC71']
    labels    = sorted(df['segment_label'].unique())
    color_map = {lbl: palette[i % len(palette)] for i, lbl in enumerate(labels)}

    fig, ax = plt.subplots(figsize=(8, 6))
    for lbl in labels:
        sub = df[df['segment_label'] == lbl]
        ax.scatter(sub['total_tnd'], sub['duration_min'],
                   c=color_map[lbl], label=lbl,
                   alpha=0.75, edgecolors='white', linewidths=0.5, s=55, zorder=3)
    ax.set_xlabel('Total Spend (TND)')
    ax.set_ylabel('Total Duration (min)')
    ax.set_title('Member Segmentation — K-Means (k = 4)')
    ax.legend(title='Segment', fontsize=9, title_fontsize=9)
    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'kmeans_scatter.png'))


# ── 10. Segment distribution ──────────────────────────────────────────────────

def plot_segment_distribution(forecasts_dir: str, out_dir: str) -> None:
    path = os.path.join(forecasts_dir, 'member_segments.csv')
    if not os.path.exists(path):
        print('    Skipping segment_distribution.png (CSV not found)')
        return
    df     = pd.read_csv(path, encoding='utf-8-sig')
    counts = df['segment_label'].value_counts().sort_values(ascending=False)

    palette = [C_TRAIN, C_TEST, C_PRED, C_SARIMA, C_XGB, '#2ECC71']
    colors  = [palette[i % len(palette)] for i in range(len(counts))]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(counts.index, counts.values, color=colors, zorder=3)
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + ax.get_ylim()[1] * 0.01,
                str(v), ha='center', va='bottom', fontweight='bold', fontsize=9)
    ax.set_xlabel('Segment')
    ax.set_ylabel('Number of members')
    ax.set_title('Member Segment Distribution')
    ax.tick_params(axis='x', rotation=15)
    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'segment_distribution.png'))


# ── 11. Anomaly timeline ──────────────────────────────────────────────────────

def plot_anomaly_timeline(transactions_df: pd.DataFrame, forecasts_dir: str,
                          out_dir: str) -> None:
    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    daily = _to_daily(income, 'transaction_datetime', '_v')

    anom_path = os.path.join(forecasts_dir, 'anomalies.csv')
    if not os.path.exists(anom_path):
        print('    Skipping anomaly_timeline.png (CSV not found)')
        return
    anomalies = pd.read_csv(anom_path, parse_dates=['date'])
    rev_anom  = anomalies[anomalies['series'] == 'revenue']

    fig, ax = plt.subplots(figsize=(FIG_W, 4))
    ax.plot(daily['ds'], daily['y'],
            color='#AACFE4', linewidth=1.3, label='Daily revenue', zorder=2)

    mild   = rev_anom[rev_anom['severity'] == 'mild']
    severe = rev_anom[rev_anom['severity'] == 'severe']

    if not mild.empty:
        mild_y = daily[daily['ds'].isin(mild['date'])]['y'].values
        ax.scatter(mild['date'], mild_y, color=C_SARIMA, s=75, zorder=5,
                   edgecolors='white', linewidths=0.8, label='Mild anomaly')
    if not severe.empty:
        sev_y = daily[daily['ds'].isin(severe['date'])]['y'].values
        ax.scatter(severe['date'], sev_y, color=C_TEST, s=120, marker='*',
                   zorder=5, edgecolors='white', linewidths=0.5, label='Severe anomaly')

    ax.set_title('Revenue Anomaly Timeline')
    ax.set_ylabel('Revenue (TND)')
    ax.legend()
    ax.tick_params(axis='x', rotation=25)
    plt.tight_layout()
    _save(fig, os.path.join(out_dir, 'anomaly_timeline.png'))


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_all_figures(transactions_df: pd.DataFrame, dim_member: pd.DataFrame,
                         forecasts_dir: str, figures_dir: str) -> None:
    """Generate all thesis figures and save to figures_dir."""
    os.makedirs(figures_dir, exist_ok=True)
    print('  Stationarity chart...')
    plot_stationarity_rolling(transactions_df, figures_dir)

    print('  Train/test split diagram...')
    plot_train_test_split(transactions_df, figures_dir)

    print('  Computing model evaluations (Prophet / SARIMA / XGBoost — runs once)...')
    all_preds = _compute_all_predictions(transactions_df)

    print('  Accuracy — revenue (Prophet / SARIMA / XGBoost, one PNG each)...')
    plot_accuracy_revenue(figures_dir, all_preds['revenue'])

    print('  Accuracy — session volume...')
    plot_accuracy_session_volume(figures_dir, all_preds['sessions'])

    print('  Accuracy — member activity...')
    plot_accuracy_members(figures_dir, all_preds['members'])

    print('  Model comparison chart (Prophet vs SARIMA vs XGBoost)...')
    plot_model_comparison(figures_dir, all_preds)

    print('  Prophet revenue forecast...')
    plot_prophet_revenue_forecast(transactions_df, figures_dir)

    print('  Peak hours / days...')
    plot_peak_hours(forecasts_dir, figures_dir)
    plot_peak_days(forecasts_dir, figures_dir)

    print('  K-means elbow...')
    plot_kmeans_elbow(dim_member, figures_dir)

    print('  K-means scatter + segment distribution...')
    plot_kmeans_scatter(forecasts_dir, figures_dir)
    plot_segment_distribution(forecasts_dir, figures_dir)

    print('  Anomaly timeline...')
    plot_anomaly_timeline(transactions_df, forecasts_dir, figures_dir)
