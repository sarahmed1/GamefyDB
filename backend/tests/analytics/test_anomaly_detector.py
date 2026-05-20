import pandas as pd
import pytest

from backend.packages.analytics.anomaly_detector import detect_anomalies


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_income_tx(dates, amounts):
    """One Income transaction per date at the given amount."""
    return pd.DataFrame({
        'transaction_datetime': pd.to_datetime(dates),
        'amount_tnd': [float(a) for a in amounts],
        'income_expense': 'Income',
        'transaction_type': 'Cash',
    })


def _mondays(n):
    """Return n consecutive Monday dates starting 2025-01-06."""
    return pd.date_range('2025-01-06', periods=n, freq='7D')


# ── tests ────────────────────────────────────────────────────────────────────

def test_normal_data_returns_empty():
    dates = _mondays(5)
    tx = _make_income_tx(dates, [100] * 5)
    result = detect_anomalies(tx)
    assert result.empty


def test_spike_detected_as_severe():
    dates = _mondays(12)
    amounts = [100] * 11 + [1200]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    assert len(result) == 1
    row = result.iloc[0]
    assert row['series'] == 'revenue'
    assert row['severity'] == 'severe'
    assert row['direction'] == 'high'
    assert row['z_score'] > 3.0


def test_dip_detected_as_mild():
    dates = _mondays(6)
    amounts = [100] * 5 + [10]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    assert len(result) == 1
    row = result.iloc[0]
    assert row['severity'] == 'mild'
    assert row['direction'] == 'low'
    assert -3.0 < row['z_score'] < -2.0


def test_revenue_anomaly_not_in_session_volume():
    dates = _mondays(12)
    amounts = [100] * 11 + [1200]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    assert result[result['series'] == 'session_volume'].empty


def test_small_group_skipped():
    dates = _mondays(3)
    tx = _make_income_tx(dates, [1, 100, 1000])
    result = detect_anomalies(tx)
    assert result.empty


def test_output_columns_present():
    dates = _mondays(12)
    amounts = [100] * 11 + [1200]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    expected_cols = {
        'date', 'series', 'weekday', 'actual',
        'weekday_mean', 'weekday_std', 'z_score',
        'direction', 'severity',
    }
    assert expected_cols.issubset(set(result.columns))


def test_sorted_by_abs_z_score_descending():
    mon_dates = _mondays(12)
    mon_amounts = [100] * 11 + [1200]

    tue_dates = pd.date_range('2025-01-07', periods=6, freq='7D')
    tue_amounts = [100] * 5 + [300]

    tx = pd.concat([
        _make_income_tx(mon_dates, mon_amounts),
        _make_income_tx(tue_dates, tue_amounts),
    ], ignore_index=True)

    result = detect_anomalies(tx)
    assert len(result) >= 2
    abs_z = result['z_score'].abs().tolist()
    assert abs_z == sorted(abs_z, reverse=True)




