import os
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from api.services.data_cache import DataCache, EMPTY_COLUMNS


def test_empty_schema_has_all_tables():
    cache = DataCache()
    assert set(cache.schema.keys()) == {
        "dim_cashier", "dim_terminal", "dim_item", "dim_member",
        "fact_transaction", "fact_session",
    }


def test_empty_schema_columns_match_contract():
    cache = DataCache()
    for table, columns in EMPTY_COLUMNS.items():
        assert list(cache.schema[table].columns) == columns
        assert len(cache.schema[table]) == 0


def test_loaded_flag_starts_false():
    cache = DataCache()
    assert cache.loaded is False


def test_build_with_missing_dir_keeps_empty_schema(tmp_path):
    cache = DataCache()
    cache.build(tmp_path / "does-not-exist")  # must NOT raise

    assert cache.loaded is False
    assert len(cache.schema["fact_transaction"]) == 0
    assert list(cache.schema["fact_transaction"].columns) == EMPTY_COLUMNS["fact_transaction"]


def test_build_with_real_excel_dir_loads_schema():
    repo_root = Path(__file__).resolve().parents[2]
    excel_dir = repo_root / "excel"
    if not excel_dir.exists() or not (excel_dir / "extended_cash.xlsx").exists():
        pytest.skip("extended_*.xlsx not present in excel/")

    cache = DataCache()
    cache.build(excel_dir)

    assert cache.loaded is True
    assert len(cache.schema["fact_transaction"]) > 0
    assert pd.api.types.is_datetime64_any_dtype(cache.schema["fact_transaction"]["date"])


def test_build_pipeline_exception_logged_and_swallowed(caplog):
    cache = DataCache()
    with patch("gamefydb.pipeline.run_pipeline", side_effect=RuntimeError("boom")):
        with caplog.at_level("WARNING"):
            cache.build("/tmp/whatever")

    assert cache.loaded is False
    assert "DataCache build failed" in caplog.text


def test_app_startup_builds_cache(monkeypatch):
    from api.services.data_cache import cache as singleton

    called = {}

    def fake_build(input_dir):
        called["dir"] = str(input_dir)
        singleton.loaded = True

    monkeypatch.setattr(singleton, "build", fake_build)

    from api.main import app
    from fastapi.testclient import TestClient
    with TestClient(app):
        pass

    assert "dir" in called
    assert called["dir"].endswith("excel")
