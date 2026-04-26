import pandas as pd
import pytest

from gamefydb.forecaster import _evaluate_prophet, _evaluate_sarima, _print_comparison


def make_daily_series(n=100):
    dates = pd.date_range('2024-01-01', periods=n, freq='D')
    values = [20 + i * 0.2 + [0, 1, 2, 3, 2, 5, 4][i % 7] for i in range(n)]
    return pd.DataFrame({'ds': dates, 'y': values})


def make_weekly_series(n=40):
    dates = pd.date_range('2024-01-01', periods=n, freq='W')
    values = [50 + i * 0.5 + [0, 2, 4, 1][i % 4] for i in range(n)]
    return pd.DataFrame({'ds': dates, 'y': values})


# ── _evaluate_prophet ─────────────────────────────────────────────────────────

def test_evaluate_prophet_returns_dict():
    result = _evaluate_prophet(make_daily_series(), split=0.8)
    assert isinstance(result, dict)


def test_evaluate_prophet_has_required_keys():
    result = _evaluate_prophet(make_daily_series(), split=0.8)
    assert 'mae' in result
    assert 'mape' in result
    assert 'rmse' in result


def test_evaluate_prophet_metrics_are_positive():
    result = _evaluate_prophet(make_daily_series(), split=0.8)
    assert result['mae'] >= 0
    assert result['mape'] >= 0
    assert result['rmse'] >= 0


def test_evaluate_prophet_returns_empty_on_too_short():
    tiny = make_daily_series(n=4)
    result = _evaluate_prophet(tiny, split=0.8)
    assert result == {}


def test_evaluate_prophet_weekly_freq():
    result = _evaluate_prophet(make_weekly_series(), split=0.8, freq='W')
    assert isinstance(result, dict)
    assert 'mape' in result


# ── _evaluate_sarima ──────────────────────────────────────────────────────────

def test_evaluate_sarima_returns_dict():
    result = _evaluate_sarima(make_daily_series(), split=0.8, m=7)
    assert isinstance(result, dict)


def test_evaluate_sarima_has_required_keys():
    result = _evaluate_sarima(make_daily_series(), split=0.8, m=7)
    assert 'mae' in result
    assert 'mape' in result
    assert 'rmse' in result


def test_evaluate_sarima_metrics_are_positive():
    result = _evaluate_sarima(make_daily_series(), split=0.8, m=7)
    assert result['mae'] >= 0
    assert result['mape'] >= 0
    assert result['rmse'] >= 0


def test_evaluate_sarima_returns_none_on_too_short():
    tiny = make_daily_series(n=4)
    result = _evaluate_sarima(tiny, split=0.8, m=7)
    assert result is None


# ── _print_comparison ─────────────────────────────────────────────────────────

def test_print_comparison_runs_without_error(capsys):
    p = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    s = {'mae': 15.0, 'mape': 14.0, 'rmse': 18.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=s)
    out = capsys.readouterr().out
    assert 'Prophet' in out
    assert 'SARIMA' in out
    assert 'Winner' in out


def test_print_comparison_prophet_wins(capsys):
    p = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    s = {'mae': 20.0, 'mape': 16.0, 'rmse': 24.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=s)
    out = capsys.readouterr().out
    assert 'Winner: Prophet' in out


def test_print_comparison_sarima_wins(capsys):
    p = {'mae': 20.0, 'mape': 16.0, 'rmse': 24.0}
    s = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=s)
    out = capsys.readouterr().out
    assert 'Winner: SARIMA' in out


def test_print_comparison_handles_none_sarima(capsys):
    p = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=None)
    out = capsys.readouterr().out
    assert 'Prophet' in out
    assert 'skipped' in out
