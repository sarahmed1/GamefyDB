import pandas as pd

from api.services.kpis import overview
from api.tests._fixtures.synthetic_schema import build_synthetic_schema


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
    from api.services.data_cache import _empty_schema
    result = overview(_empty_schema(), date_from=None, date_to=None)
    assert result["total_revenue"] == 0.0
    assert result["transaction_count"] == 0
    assert result["top_categories"] == []
