import pandas as pd
import pytest
from pathlib import Path
from chatbot.data_loader import DataContext, _build_schemas, _build_summary, recent_anomaly_count, load_data, CSV_MAP


def _make_tables():
    tx = pd.DataFrame({
        "tx_id": [1, 2],
        "date": ["2026-01-10", "2026-01-11"],
        "type": ["Income", "Income"],
        "amount": [100.0, 200.0],
        "cashier_id": [1, 1],
        "terminal_id": [1, 2],
    })
    members = pd.DataFrame({
        "member_id": [1, 2],
        "username": ["alice", "bob"],
        "firstname": ["Alice", "Bob"],
        "lastname": ["A", "B"],
    })
    loyalty = pd.DataFrame({
        "member_id": [1, 2],
        "username": ["alice", "bob"],
        "firstname": ["Alice", "Bob"],
        "lastname": ["A", "B"],
        "total_tnd": [500.0, 200.0],
        "duration_min": [1000, 500],
        "m_score": [4, 3],
        "f_score": [4, 3],
        "fm_score": [8, 6],
        "loyalty_tier": ["Platinum", "Gold"],
    })
    anomalies = pd.DataFrame({
        "date": [pd.Timestamp.now().strftime("%Y-%m-%d")],
        "series": ["revenue"],
        "severity": ["severe"],
    })
    return {"fact_transaction": tx, "dim_member": members, "member_loyalty": loyalty, "anomalies": anomalies}


def test_build_schemas_includes_all_keys():
    tables = _make_tables()
    schemas = _build_schemas(tables)
    assert "fact_transaction" in schemas
    assert "dim_member" in schemas


def test_build_summary_includes_revenue():
    tables = _make_tables()
    summary = _build_summary(tables)
    assert "300.00 TND" in summary


def test_build_summary_includes_member_count():
    tables = _make_tables()
    summary = _build_summary(tables)
    assert "Total members: 2" in summary


def test_recent_anomaly_count_today():
    ctx = DataContext(tables=_make_tables())
    assert recent_anomaly_count(ctx) == 1


def test_recent_anomaly_count_no_anomalies_table():
    ctx = DataContext(tables={})
    assert recent_anomaly_count(ctx) == 0


def test_build_summary_includes_forecast_highlights():
    tables = _make_tables()
    tables["forecast_revenue"] = pd.DataFrame({
        "date": ["2026-05-12", "2026-05-19", "2026-06-04"],
        "granularity": ["weekly", "weekly", "monthly"],
        "yhat": [1554.9, 1422.3, 8661.5],
        "yhat_lower": [573.7, 445.6, 4379.7],
        "yhat_upper": [2532.6, 2405.8, 12894.8],
    })
    summary = _build_summary(tables)
    assert "Revenue forecast" in summary
    assert "1555" in summary or "1554" in summary
    assert "8661" in summary or "8662" in summary


def test_build_summary_forecast_handles_missing_granularity():
    tables = {"forecast_revenue": pd.DataFrame({"date": ["2026-05-12"], "yhat": [100.0]})}
    summary = _build_summary(tables)
    assert "Revenue forecast" in summary


def test_load_data_skips_missing_files(tmp_path):
    ctx = load_data(base_dir=str(tmp_path))
    assert isinstance(ctx, DataContext)
    assert len(ctx.tables) == 0
    assert ctx.summary == ""
