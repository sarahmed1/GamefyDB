import pandas as pd
import pytest
from gamefydb.transformer import build_dims, build_facts, transform


def make_cleaned():
    cash = pd.DataFrame([
        {'cashier': 'taktek', 'date': pd.Timestamp('2026-03-23 03:23:54'),
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Order Incomes', 'amount_tnd': 27.50,
         'comment': '(PS5 (1))', 'terminal': 'PS5 (1)'},
        {'cashier': 'youssef', 'date': pd.Timestamp('2026-03-22 17:41:47'),
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Member Transactions', 'amount_tnd': 30.00,
         'comment': 'Money deposited', 'terminal': None},
    ])
    sessions = pd.DataFrame([
        {'cashier': 'taktek', 'terminal': 'GAMEFY04', 'session_type': 'Member',
         'is_free_time': False, 'paused_duration_minutes': None, 'duration_minutes': 89,
         'order_transfer_tnd': 0.0, 'usage_tnd': 11.87,
         'discount_tnd': 0.0, 'total_amount_tnd': 11.87},
        {'cashier': 'taktek', 'terminal': 'PS5 (1)', 'session_type': 'Free',
         'is_free_time': True, 'paused_duration_minutes': 30, 'duration_minutes': 105,
         'order_transfer_tnd': 0.0, 'usage_tnd': 0.0,
         'discount_tnd': 0.0, 'total_amount_tnd': 0.0},
    ])
    stock = pd.DataFrame([
        {'cashier': 'taktek', 'date': pd.Timestamp('2026-03-23 03:23:54'),
         'item_name': 'Soda', 'category': 'Drinks', 'in_out': 'Out',
         'quantity': 4, 'unit_price_tnd': 2.0, 'total_amount_tnd': 8.0,
         'comment': '(PS5 (1))', 'terminal': 'PS5 (1)'},
    ])
    members = pd.DataFrame([
        {'member_id': 35, 'username': 'mhmd', 'firstname': 'MOHAMED',
         'lastname': 'LOUATI', 'duration_minutes': 13406, 'usage_tnd': 1745.44,
         'orders_transfer_tnd': 0.0, 'total_amount_tnd': 1745.44},
        {'member_id': 64, 'username': 'zinox', 'firstname': 'Helmi',
         'lastname': 'Chermiti', 'duration_minutes': 7735, 'usage_tnd': 919.72,
         'orders_transfer_tnd': 0.0, 'total_amount_tnd': 919.72},
    ])
    return {'cash': cash, 'sessions': sessions, 'stock': stock, 'members': members}


def test_dim_cashier_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_cashier'].columns) == ['cashier_id', 'cashier_name']


def test_dim_cashier_unique_names():
    dims = build_dims(make_cleaned())
    # taktek + youssef appear across cash/sessions/stock — 2 unique
    assert set(dims['dim_cashier']['cashier_name']) == {'taktek', 'youssef'}


def test_dim_cashier_sequential_ids():
    dims = build_dims(make_cleaned())
    assert sorted(dims['dim_cashier']['cashier_id'].tolist()) == [1, 2]


def test_dim_terminal_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_terminal'].columns) == ['terminal_id', 'terminal_name', 'terminal_type']


def test_dim_terminal_union_across_files():
    dims = build_dims(make_cleaned())
    # GAMEFY04 and PS5 (1) from sessions; PS5 (1) also in cash/stock (deduplicated)
    assert set(dims['dim_terminal']['terminal_name']) == {'GAMEFY04', 'PS5 (1)'}


def test_dim_terminal_type_classification():
    dims = build_dims(make_cleaned())
    types = dict(zip(dims['dim_terminal']['terminal_name'], dims['dim_terminal']['terminal_type']))
    assert types['GAMEFY04'] == 'Computer'
    assert types['PS5 (1)'] == 'PlayStation'


def test_dim_item_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_item'].columns) == ['item_id', 'item_name', 'category']


def test_dim_item_from_stock():
    dims = build_dims(make_cleaned())
    assert dims['dim_item']['item_name'].iloc[0] == 'Soda'
    assert dims['dim_item']['category'].iloc[0] == 'Drinks'


def test_dim_member_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_member'].columns) == ['member_id', 'username', 'firstname', 'lastname']


def test_dim_member_uses_source_ids():
    dims = build_dims(make_cleaned())
    assert set(dims['dim_member']['member_id']) == {35, 64}


def test_fact_cash_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_cash_transactions'].columns) == [
        'cashier_id', 'transaction_datetime', 'income_expense',
        'payment_method', 'transaction_type', 'amount_tnd', 'terminal_id',
    ]


def test_fact_cash_cashier_fk_resolved():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    taktek_id = dims['dim_cashier'].loc[
        dims['dim_cashier']['cashier_name'] == 'taktek', 'cashier_id'
    ].iloc[0]
    assert facts['fact_cash_transactions']['cashier_id'].iloc[0] == taktek_id


def test_fact_cash_terminal_id_nullable():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    # Row 1 has no terminal (comment = 'Money deposited')
    assert pd.isna(facts['fact_cash_transactions']['terminal_id'].iloc[1])


def test_fact_sessions_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_sessions'].columns) == [
        'cashier_id', 'terminal_id', 'session_type', 'is_free_time', 'paused_duration_minutes',
        'duration_minutes', 'order_transfer_tnd', 'usage_tnd',
        'discount_tnd', 'total_amount_tnd',
    ]


def test_fact_sessions_terminal_fk_resolved():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    gamefy04_id = dims['dim_terminal'].loc[
        dims['dim_terminal']['terminal_name'] == 'GAMEFY04', 'terminal_id'
    ].iloc[0]
    assert facts['fact_sessions']['terminal_id'].iloc[0] == gamefy04_id


def test_fact_stock_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_stock_movements'].columns) == [
        'cashier_id', 'movement_datetime', 'item_id', 'in_out', 'quantity',
        'unit_price_tnd', 'total_amount_tnd', 'terminal_id',
    ]


def test_fact_stock_item_fk_resolved():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    soda_id = dims['dim_item'].loc[
        dims['dim_item']['item_name'] == 'Soda', 'item_id'
    ].iloc[0]
    assert facts['fact_stock_movements']['item_id'].iloc[0] == soda_id


def test_fact_member_stats_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_member_stats'].columns) == [
        'member_id', 'duration_minutes', 'usage_tnd',
        'orders_transfer_tnd', 'total_amount_tnd',
    ]


def test_fact_member_stats_ids():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    assert set(facts['fact_member_stats']['member_id']) == {35, 64}


def test_transform_returns_all_eight_tables():
    result = transform(make_cleaned())
    expected = {
        'dim_cashier', 'dim_terminal', 'dim_item', 'dim_member',
        'fact_cash_transactions', 'fact_sessions',
        'fact_stock_movements', 'fact_member_stats',
    }
    assert set(result.keys()) == expected


def test_transform_all_values_are_dataframes():
    for name, val in transform(make_cleaned()).items():
        assert isinstance(val, pd.DataFrame), f"{name} is not a DataFrame"
