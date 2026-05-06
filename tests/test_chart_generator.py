import pandas as pd
import pytest
from chatbot.chart_generator import make_chart


def _tables():
    return {
        "fact_transaction": pd.DataFrame({
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "amount": [100.0, 150.0, 200.0],
            "type": ["Income", "Income", "Income"],
            "category": ["Computer Incomes", "Order Incomes", "Computer Incomes"],
        })
    }


def test_bar_chart_returns_figure():
    spec = {"type": "bar", "x": "date", "y": "amount", "source": "fact_transaction", "filter": "", "title": "Revenue"}
    fig = make_chart(spec, _tables())
    assert fig is not None


def test_line_chart_returns_figure():
    spec = {"type": "line", "x": "date", "y": "amount", "source": "fact_transaction", "filter": "", "title": "Revenue"}
    fig = make_chart(spec, _tables())
    assert fig is not None


def test_filter_is_applied():
    spec = {"type": "bar", "x": "date", "y": "amount", "source": "fact_transaction",
            "filter": "category == 'Computer Incomes'", "title": "Filtered"}
    fig = make_chart(spec, _tables())
    assert fig is not None


def test_missing_source_returns_none():
    spec = {"type": "bar", "x": "date", "y": "amount", "source": "nonexistent", "filter": "", "title": "X"}
    fig = make_chart(spec, _tables())
    assert fig is None


def test_bad_column_returns_none():
    spec = {"type": "bar", "x": "bad_col", "y": "amount", "source": "fact_transaction", "filter": "", "title": "X"}
    fig = make_chart(spec, _tables())
    assert fig is None


def test_malformed_spec_returns_none():
    fig = make_chart({}, _tables())
    assert fig is None
