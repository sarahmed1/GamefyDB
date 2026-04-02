import os
import pandas as pd
import pytest
from gamefydb.writer import write_all


@pytest.fixture
def schema():
    return {
        'dim_cashier':  pd.DataFrame({'cashier_id': [1, 2], 'cashier_name': ['taktek', 'youssef']}),
        'dim_terminal': pd.DataFrame({'terminal_id': [1], 'terminal_name': ['GAMEFY01'], 'terminal_type': ['Computer']}),
        'dim_item':     pd.DataFrame({'item_id': [1], 'item_name': ['Soda'], 'category': ['Drinks']}),
        'dim_member':   pd.DataFrame({'member_id': [35], 'username': ['mhmd'], 'firstname': ['MOHAMED'], 'lastname': ['LOUATI']}),
        'fact_cash_transactions': pd.DataFrame({'cashier_id': [1], 'transaction_datetime': [pd.Timestamp('2026-03-23')], 'amount_tnd': [27.50]}),
        'fact_sessions':          pd.DataFrame({'cashier_id': [1], 'terminal_id': [1], 'duration_minutes': [89]}),
        'fact_stock_movements':   pd.DataFrame({'cashier_id': [1], 'item_id': [1], 'quantity': [4]}),
        'fact_member_stats':      pd.DataFrame({'member_id': [35], 'total_amount_tnd': [1745.44]}),
    }


@pytest.fixture
def output_dir(tmp_path):
    return str(tmp_path / 'output')


def test_write_csv_creates_dims_directory(schema, output_dir):
    write_all(schema, output_dir)
    assert os.path.isdir(os.path.join(output_dir, 'dims'))


def test_write_csv_creates_facts_directory(schema, output_dir):
    write_all(schema, output_dir)
    assert os.path.isdir(os.path.join(output_dir, 'facts'))


def test_write_csv_all_files_exist(schema, output_dir):
    write_all(schema, output_dir)
    for name in ['dim_cashier', 'dim_terminal', 'dim_item', 'dim_member']:
        assert os.path.isfile(os.path.join(output_dir, 'dims', f'{name}.csv')), f"Missing {name}.csv"
    for name in ['fact_cash_transactions', 'fact_sessions', 'fact_stock_movements', 'fact_member_stats']:
        assert os.path.isfile(os.path.join(output_dir, 'facts', f'{name}.csv')), f"Missing {name}.csv"


def test_write_csv_content(schema, output_dir):
    write_all(schema, output_dir)
    df = pd.read_csv(os.path.join(output_dir, 'dims', 'dim_cashier.csv'))
    assert list(df.columns) == ['cashier_id', 'cashier_name']
    assert df['cashier_name'].tolist() == ['taktek', 'youssef']


def test_write_excel_creates_single_file(schema, output_dir):
    write_all(schema, output_dir, fmt='excel')
    assert os.path.isfile(os.path.join(output_dir, 'gamefydb.xlsx'))


def test_write_excel_has_all_sheets(schema, output_dir):
    write_all(schema, output_dir, fmt='excel')
    xl = pd.ExcelFile(os.path.join(output_dir, 'gamefydb.xlsx'))
    assert set(xl.sheet_names) == set(schema.keys())


def test_write_excel_sheet_content(schema, output_dir):
    write_all(schema, output_dir, fmt='excel')
    df = pd.read_excel(os.path.join(output_dir, 'gamefydb.xlsx'), sheet_name='dim_cashier')
    assert df['cashier_name'].tolist() == ['taktek', 'youssef']
