import numpy as np
import pandas as pd
from gamefydb.ingestor import _strip_artifacts

CASH_COL_MAP = {
    0: 'cashier', 4: 'date', 9: 'income_expense', 11: 'payment_method',
    21: 'transaction_type', 40: 'amount', 51: 'comment',
}


def make_cash_raw():
    """Minimal raw Cash DataFrame replicating real artifact structure."""
    n = 60
    nan = np.nan

    def row(vals):
        r = [nan] * n
        for k, v in vals.items():
            r[k] = v
        return r

    return pd.DataFrame([
        row({0: 'Cash Reports'}),                           # 0: title
        row({55: '23/03/2026'}),                            # 1: report date
        row({}),                                            # 2: blank
        row({}),                                            # 3: blank
        row({0: 'Cashier', 4: 'Date', 9: 'Income/Expense', # 4: headers
             11: 'Payment Method', 21: 'Transaction Type',
             40: 'Amount', 50: 'Comment'}),
        row({0: 'taktek', 4: '23.03.2026 03:23:54',         # 5: data row 1
             9: 'Income', 11: 'Cash',
             21: 'Order Incomes', 40: '27,50 TND',
             51: '(PS5 (1))'}),
        row({0: 'youssef', 4: '22.03.2026 17:41:47',        # 6: data row 2
             9: 'Income', 11: 'Cash',
             21: 'Member Transactions', 40: '30,00 TND',
             51: 'Money deposited to member'}),
        row({}),                                            # 7: blank (page break)
        row({}),                                            # 8: blank
        row({54: 'Page 1/3'}),                              # 9: page marker
        row({}),                                            # 10: blank after marker
        row({0: 'Cashier', 4: 'Date'}),                    # 11: repeated header
        row({0: 'taktek', 4: '21.03.2026 03:38:54',         # 12: data row 3
             9: 'Income', 11: 'Cash',
             21: 'Computer Incomes', 40: '24,50 TND',
             51: '(GAMEFY09)'}),
        row({}),                                            # 13: blank (footer)
        row({8: 'Computer Incomes'}),                       # 14: footer row
        row({8: '76245,51 TND'}),                           # 15: footer row
        row({}),                                            # 16: blank
        row({54: 'Page 3/3'}),                              # 17: final page marker
    ])


def test_strip_artifacts_row_count():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    assert len(result) == 3


def test_strip_artifacts_columns():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    assert list(result.columns) == [
        'cashier', 'date', 'income_expense',
        'payment_method', 'transaction_type', 'amount', 'comment',
    ]


def test_strip_artifacts_data_preserved():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    assert result.iloc[0]['cashier'] == 'taktek'
    assert result.iloc[0]['amount'] == '27,50 TND'
    assert result.iloc[1]['cashier'] == 'youssef'
    assert result.iloc[2]['cashier'] == 'taktek'
    assert result.iloc[2]['date'] == '21.03.2026 03:38:54'


def test_strip_artifacts_no_page_markers():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    for col in result.columns:
        assert not result[col].astype(str).str.contains(r'Page \d+/\d+').any()


import os
from gamefydb.ingestor import ingest_all

EXCEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'excel')


def test_ingest_all_returns_four_keys():
    result = ingest_all(EXCEL_DIR)
    assert set(result.keys()) == {'cash', 'sessions', 'stock', 'members'}


def test_ingest_cash_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['cash'].columns) == [
        'cashier', 'date', 'income_expense', 'payment_method',
        'transaction_type', 'amount', 'comment',
    ]


def test_ingest_sessions_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['sessions'].columns) == [
        'cashier', 'terminal', 'session_type', 'free_time', 'paused',
        'duration', 'order_transfer', 'usage', 'discount', 'total_amount',
    ]


def test_ingest_stock_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['stock'].columns) == [
        'cashier', 'date', 'item_name', 'category', 'in_out',
        'quantity', 'unit_price', 'total_amount', 'comment',
    ]


def test_ingest_members_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['members'].columns) == [
        'member_id', 'username', 'firstname', 'lastname',
        'duration', 'usage', 'orders_transfer', 'total_amount',
    ]


def test_ingest_cash_has_data():
    result = ingest_all(EXCEL_DIR)
    assert len(result['cash']) > 100


def test_ingest_no_page_marker_rows():
    result = ingest_all(EXCEL_DIR)
    for name, df in result.items():
        for col in df.columns:
            has_page = df[col].astype(str).str.contains(r'Page \d+/\d+', regex=True)
            assert not has_page.any(), f"{name}.{col} still contains page markers"


def test_ingest_members_has_data():
    result = ingest_all(EXCEL_DIR)
    assert len(result['members']) > 10
