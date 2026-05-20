import pandas as pd

from backend.apps.api.services.kpis import overview, heatmap, by_terminal, by_cashier
from backend.tests.api._fixtures.synthetic_schema import build_synthetic_schema


def test_overview_totals_match_synthetic_schema():
    schema = build_synthetic_schema()
    result = overview(schema, date_from=None, date_to=None)

    assert result["total_revenue"] == 91.0  # sum of synthetic amounts
    assert result["transaction_count"] == 6
    assert result["unique_cashiers"] == 2
    assert result["unique_terminals"] == 2
    assert result["top_categories"][0]["category"] in {
        "Computer Incomes", "Playstation Incomes", "Member Transactions"
    }


def test_overview_date_filter_narrows_results():
    schema = build_synthetic_schema()
    result = overview(
        schema,
        date_from=pd.Timestamp("2026-05-12"),
        date_to=pd.Timestamp("2026-05-12T23:59:59"),
    )
    assert result["transaction_count"] == 2
    assert result["total_revenue"] == 43.0  # 25 + 18


def test_overview_empty_schema_returns_zeros():
    from backend.apps.api.services.data_cache import _empty_schema
    result = overview(_empty_schema(), date_from=None, date_to=None)
    assert result["total_revenue"] == 0.0
    assert result["transaction_count"] == 0
    assert result["top_categories"] == []


def test_heatmap_shape_is_24x7():
    schema = build_synthetic_schema()
    result = heatmap(schema, date_from=None, date_to=None)
    assert "matrix" in result
    assert len(result["matrix"]) == 24      # rows = hours
    assert all(len(row) == 7 for row in result["matrix"])
    # Verify at least one populated cell from the synthetic data
    assert any(any(cell > 0 for cell in row) for row in result["matrix"])


def test_by_terminal_returns_named_rows():
    schema = build_synthetic_schema()
    rows = by_terminal(schema, date_from=None, date_to=None)
    by_name = {r["terminal"]: r for r in rows}
    assert "PC-01" in by_name and "PS5-01" in by_name
    # PC-01 transactions: 10 + 15 = 25
    assert by_name["PC-01"]["amount"] == 25.0
    # PS5-01: 20 + 18 = 38
    assert by_name["PS5-01"]["amount"] == 38.0


def test_by_cashier_returns_named_rows():
    schema = build_synthetic_schema()
    rows = by_cashier(schema, date_from=None, date_to=None)
    by_name = {r["cashier"]: r for r in rows}
    assert by_name["taktek"]["amount"] == 38.0    # 10 + 3 + 25
    assert by_name["youssef"]["amount"] == 53.0   # 20 + 15 + 18


def test_kpis_overview_endpoint(cached_app):
    r = cached_app.get("/api/kpis/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_revenue"] == 91.0
    assert body["transaction_count"] == 6


def test_kpis_heatmap_endpoint(cached_app):
    r = cached_app.get("/api/kpis/heatmap")
    assert r.status_code == 200
    body = r.json()
    assert len(body["matrix"]) == 24
    assert len(body["matrix"][0]) == 7


def test_kpis_by_terminal_endpoint(cached_app):
    r = cached_app.get("/api/kpis/by-terminal")
    assert r.status_code == 200
    body = r.json()
    names = {row["terminal"] for row in body["rows"]}
    assert names == {"PC-01", "PS5-01"}


def test_kpis_by_cashier_endpoint(cached_app):
    r = cached_app.get("/api/kpis/by-cashier")
    assert r.status_code == 200
    body = r.json()
    names = {row["cashier"] for row in body["rows"]}
    assert names == {"taktek", "youssef"}


def test_kpis_unauth(client):
    from fastapi.testclient import TestClient
    from backend.apps.api.main import app
    with TestClient(app) as c:
        r = c.get("/api/kpis/overview")
        assert r.status_code == 401






