import pandas as pd


def _classify_terminal(name: str) -> str:
    # name is always a clean non-empty string from terminal_names
    n = name.upper()
    if 'VIP' in n:
        return 'VIP'
    if n.startswith('PS'):
        return 'PlayStation'
    if n.startswith('GAMEFY'):
        return 'Computer'
    return 'Other'


def build_dims(cleaned: dict) -> dict:
    """Build all four dimension tables from cleaned DataFrames.

    Returns:
        {'dim_cashier': df, 'dim_terminal': df, 'dim_item': df, 'dim_member': df}
    """
    cash = cleaned['cash']
    sessions = cleaned['sessions']
    stock = cleaned['stock']
    members = cleaned['members']

    # dim_cashier — union of cashier names across all transactional files
    all_cashiers = pd.concat([cash['cashier'], sessions['cashier'], stock['cashier']])
    cashier_names = sorted(set(
        str(n).strip() for n in all_cashiers.dropna() if str(n).strip()
    ))
    dim_cashier = pd.DataFrame({
        'cashier_id': range(1, len(cashier_names) + 1),
        'cashier_name': cashier_names,
    })

    # dim_terminal — union from sessions + cash.terminal + stock.terminal (nullable)
    # sessions always has a terminal column (core schema); cash/stock terminal is derived and may be absent
    terminal_sources = [sessions['terminal']]
    if 'terminal' in cash.columns:
        terminal_sources.append(cash['terminal'].dropna())
    if 'terminal' in stock.columns:
        terminal_sources.append(stock['terminal'].dropna())
    terminal_names = sorted(set(
        str(n).strip() for n in pd.concat(terminal_sources).dropna() if str(n).strip()
    ))
    dim_terminal = pd.DataFrame({
        'terminal_id': range(1, len(terminal_names) + 1),
        'terminal_name': terminal_names,
        'terminal_type': [_classify_terminal(n) for n in terminal_names],
    })

    # dim_item — unique (item_name, category) pairs from stock
    items = (
        stock[['item_name', 'category']]
        .drop_duplicates()
        .sort_values(['category', 'item_name'])
        .reset_index(drop=True)
    )
    dim_item = pd.DataFrame({
        'item_id': range(1, len(items) + 1),
        'item_name': items['item_name'].values,
        'category': items['category'].values,
    })

    # dim_member — descriptive columns only (member_id is the source PK)
    dim_member = (
        members[['member_id', 'username', 'firstname', 'lastname']]
        .copy()
        .reset_index(drop=True)
    )

    return {
        'dim_cashier': dim_cashier,
        'dim_terminal': dim_terminal,
        'dim_item': dim_item,
        'dim_member': dim_member,
    }


def _resolve_fk(df: pd.DataFrame, src_col: str,
                dim: pd.DataFrame, dim_name_col: str, dim_id_col: str) -> pd.Series:
    """Map natural key column → surrogate FK using the dimension table.

    Unresolved values (e.g. None terminals) become NaN (nullable float).
    """
    mapping = dict(zip(dim[dim_name_col], dim[dim_id_col]))
    return df[src_col].map(mapping)


def build_facts(cleaned: dict, dims: dict) -> dict:
    """Build all four fact tables, resolving FK columns via dimension tables.

    Args:
        cleaned: Output of clean_all.
        dims: Output of build_dims.

    Returns:
        {'fact_cash_transactions': df, 'fact_sessions': df,
         'fact_stock_movements': df, 'fact_member_stats': df}
    """
    cash = cleaned['cash']
    sessions = cleaned['sessions']
    stock = cleaned['stock']
    members = cleaned['members']
    dim_cashier = dims['dim_cashier']
    dim_terminal = dims['dim_terminal']
    dim_item = dims['dim_item']

    fact_cash = pd.DataFrame({
        'cashier_id':           _resolve_fk(cash, 'cashier', dim_cashier, 'cashier_name', 'cashier_id'),
        'transaction_datetime': cash['date'],
        'income_expense':       cash['income_expense'],
        'payment_method':       cash['payment_method'],
        'transaction_type':     cash['transaction_type'],
        'amount_tnd':           cash['amount_tnd'],
        'terminal_id':          _resolve_fk(cash, 'terminal', dim_terminal, 'terminal_name', 'terminal_id'),
    }).reset_index(drop=True)

    fact_sessions = pd.DataFrame({
        'cashier_id':             _resolve_fk(sessions, 'cashier', dim_cashier, 'cashier_name', 'cashier_id'),
        'terminal_id':            _resolve_fk(sessions, 'terminal', dim_terminal, 'terminal_name', 'terminal_id'),
        'session_type':           sessions['session_type'],
        'is_free_time':           sessions['is_free_time'],
        'paused_duration_minutes': sessions['paused_duration_minutes'],
        'duration_minutes':       sessions['duration_minutes'],
        'order_transfer_tnd':     sessions['order_transfer_tnd'],
        'usage_tnd':              sessions['usage_tnd'],
        'discount_tnd':           sessions['discount_tnd'],
        'total_amount_tnd':       sessions['total_amount_tnd'],
    }).reset_index(drop=True)

    fact_stock = pd.DataFrame({
        'cashier_id':        _resolve_fk(stock, 'cashier', dim_cashier, 'cashier_name', 'cashier_id'),
        'movement_datetime': stock['date'],
        'item_id':           _resolve_fk(stock, 'item_name', dim_item, 'item_name', 'item_id'),
        'in_out':            stock['in_out'],
        'quantity':          stock['quantity'],
        'unit_price_tnd':    stock['unit_price_tnd'],
        'total_amount_tnd':  stock['total_amount_tnd'],
        'terminal_id':       _resolve_fk(stock, 'terminal', dim_terminal, 'terminal_name', 'terminal_id'),
    }).reset_index(drop=True)

    fact_members = members[[
        'member_id', 'duration_minutes', 'usage_tnd',
        'orders_transfer_tnd', 'total_amount_tnd',
    ]].copy().reset_index(drop=True)

    return {
        'fact_cash_transactions': fact_cash,
        'fact_sessions':          fact_sessions,
        'fact_stock_movements':   fact_stock,
        'fact_member_stats':      fact_members,
    }


def transform(cleaned: dict) -> dict:
    """Build the full star schema from cleaned DataFrames.

    Returns:
        Dict of all 8 tables: 4 dims + 4 facts.
    """
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    return {**dims, **facts}
