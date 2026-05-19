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
