import pandas as pd
import numpy as np
import pytest
from datetime import datetime
from gamefydb.cleaner import parse_amount, parse_datetime, parse_duration, extract_terminal
from gamefydb.cleaner import clean_all


def test_parse_amount_simple():
    assert parse_amount('27,50 TND') == 27.50


def test_parse_amount_thousands_narrow_space():
    # \u202f is the narrow no-break space used as thousands separator
    assert parse_amount('1\u202f745,44 TND') == 1745.44


def test_parse_amount_zero():
    assert parse_amount('0,00 TND') == 0.0


def test_parse_amount_large():
    assert parse_amount('53\u202f366,12 TND') == 53366.12


def test_parse_amount_whole():
    assert parse_amount('8,00 TND') == 8.0


def test_parse_datetime_full():
    assert parse_datetime('23.03.2026 03:23:54') == datetime(2026, 3, 23, 3, 23, 54)


def test_parse_datetime_midnight():
    assert parse_datetime('01.09.2025 08:00:00') == datetime(2025, 9, 1, 8, 0, 0)


def test_parse_duration_hours_and_minutes():
    assert parse_duration('1 h 29 min') == 89


def test_parse_duration_minutes_only():
    assert parse_duration('30 min') == 30


def test_parse_duration_hours_zero_minutes():
    assert parse_duration('2 h 00 min') == 120


def test_parse_duration_large():
    assert parse_duration('223 h 26 min') == 13406


def test_extract_terminal_simple():
    assert extract_terminal('(GAMEFY01)') == 'GAMEFY01'


def test_extract_terminal_with_inner_parens():
    # PS5 (1) has inner parentheses — outer parens only are stripped
    assert extract_terminal('(PS5 (1))') == 'PS5 (1)'


def test_extract_terminal_vip():
    assert extract_terminal('(GAMEFY-VIP)') == 'GAMEFY-VIP'


def test_extract_terminal_no_match():
    assert extract_terminal('Money deposited to member') is None


def test_extract_terminal_none():
    assert extract_terminal(None) is None


def test_extract_terminal_nan():
    assert extract_terminal(float('nan')) is None


def test_parse_duration_invalid():
    with pytest.raises(ValueError):
        parse_duration('45 seconds')


def make_raw_for_clean_all():
    cash = pd.DataFrame([
        {'cashier': 'taktek', 'date': '23.03.2026 03:23:54',
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Order Incomes', 'amount': '27,50 TND',
         'comment': '(PS5 (1))'},
        {'cashier': 'youssef', 'date': '22.03.2026 17:41:47',
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Member Transactions', 'amount': '30,00 TND',
         'comment': 'Money deposited to member'},
    ])
    sessions = pd.DataFrame([
        {'cashier': 'taktek', 'terminal': 'GAMEFY04', 'session_type': 'Member',
         'free_time': np.nan, 'paused': np.nan, 'duration': '1 h 29 min',
         'order_transfer': '0,00 TND',
         'usage': '11,87 TND', 'discount': '0,00 TND', 'total_amount': '11,87 TND'},
        {'cashier': 'taktek', 'terminal': 'PS5 (2)', 'session_type': 'Free',
         'free_time': 'x', 'paused': '30 min', 'duration': '1 h 45 min',
         'order_transfer': '0,00 TND',
         'usage': '0,00 TND', 'discount': '0,00 TND', 'total_amount': '0,00 TND'},
    ])
    stock = pd.DataFrame([
        {'cashier': 'taktek', 'date': '23.03.2026 03:23:54',
         'item_name': 'Soda', 'category': 'Drinks', 'in_out': 'Out',
         'quantity': '4', 'unit_price': '2,00 TND',
         'total_amount': '8,00 TND', 'comment': '(PS5 (1))'},
    ])
    members = pd.DataFrame([
        {'member_id': '35', 'username': 'mhmd', 'firstname': 'MOHAMED',
         'lastname': 'LOUATI', 'duration': '223 h 26 min',
         'usage': '1\u202f745,44 TND', 'orders_transfer': '0,00 TND',
         'total_amount': '1\u202f745,44 TND'},
    ])
    return {'cash': cash, 'sessions': sessions, 'stock': stock, 'members': members}


def test_clean_cash_date_is_datetime():
    result = clean_all(make_raw_for_clean_all())
    assert pd.api.types.is_datetime64_any_dtype(result['cash']['date'])


def test_clean_cash_amount_is_float():
    result = clean_all(make_raw_for_clean_all())
    assert result['cash']['amount_tnd'].iloc[0] == 27.50


def test_clean_cash_terminal_extracted():
    result = clean_all(make_raw_for_clean_all())
    assert result['cash']['terminal'].iloc[0] == 'PS5 (1)'
    assert pd.isna(result['cash']['terminal'].iloc[1])


def test_clean_sessions_duration_minutes():
    result = clean_all(make_raw_for_clean_all())
    assert result['sessions']['duration_minutes'].iloc[0] == 89
    assert result['sessions']['duration_minutes'].iloc[1] == 105


def test_clean_sessions_bool_free_time():
    result = clean_all(make_raw_for_clean_all())
    assert result['sessions']['is_free_time'].iloc[0] == False
    assert result['sessions']['is_free_time'].iloc[1] == True


def test_clean_sessions_paused_duration():
    result = clean_all(make_raw_for_clean_all())
    assert pd.isna(result['sessions']['paused_duration_minutes'].iloc[0])
    assert result['sessions']['paused_duration_minutes'].iloc[1] == 30


def test_clean_sessions_amounts_are_float():
    result = clean_all(make_raw_for_clean_all())
    assert result['sessions']['usage_tnd'].iloc[0] == 11.87


def test_clean_stock_quantity_is_int():
    result = clean_all(make_raw_for_clean_all())
    assert result['stock']['quantity'].iloc[0] == 4
    assert pd.api.types.is_integer_dtype(result['stock']['quantity'])


def test_clean_members_duration_minutes():
    result = clean_all(make_raw_for_clean_all())
    assert result['members']['duration_minutes'].iloc[0] == 13406


def test_clean_members_amount_with_narrow_space():
    result = clean_all(make_raw_for_clean_all())
    assert result['members']['total_amount_tnd'].iloc[0] == 1745.44


def test_clean_members_id_is_int():
    result = clean_all(make_raw_for_clean_all())
    assert result['members']['member_id'].iloc[0] == 35
