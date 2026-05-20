import os
import numpy as np
import pandas as pd


FILES = {
    'cash':     'extended_cash.xlsx',
    'sessions': 'extended_session.xlsx',
    'stock':    'extended_stock.xlsx',
    'members':  'extended_members.xlsx',
}

AUGMENT_FILES = {
    'cash':     'augment/augment_cash.xlsx',
    'sessions': 'augment/augment_session.xlsx',
    'stock':    'augment/augment_stock.xlsx',
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_amount(val):
    if pd.isna(val) or str(val).strip() == '':
        return np.nan
    v = str(val).replace(' ', '').replace('\xa0', '')
    v = v.replace(' TND', '').replace('TND', '').strip()
    v = v.replace(' ', '').replace(',', '.')
    try:
        return float(v)
    except ValueError:
        return np.nan


def _parse_duration(val):
    if pd.isna(val) or str(val).strip() == '':
        return np.nan
    v = str(val).strip()
    total = 0.0
    if 'h' in v:
        parts = v.split('h')
        total += float(parts[0].strip()) * 60
        rest = parts[1].replace('min', '').strip()
        total += float(rest) if rest else 0
    elif 'min' in v:
        total = float(v.replace('min', '').strip())
    else:
        try:
            total = float(v)
        except ValueError:
            return np.nan
    return total


def _is_header_row(val):
    if pd.isna(val):
        return True
    v = str(val).strip()
    return v in ('Cashier', '') or (len(v) >= 8 and '/' in v and v[:2].isdigit())


_SESSION_NOISE = {
    'Computer', 'Playstation', 'Table', 'Total', 'Orders Amount',
    'Usage Amount', 'USB Data Amount', 'Discount Amount',
    'Collected (Cash)', 'Collected (Credit Card)',
    'Terminal Type', 'Terminal', 'Tariff Type', 'Payment Method',
    'Session Type', 'Date Range', 'Report Result :', 'Filter Status :',
}

_REAL_CASHIERS = ['taktek', 'youssef', 'yassine', 'monta', 'guds']

_TYPE_FROM_CATEGORY = {
    'Computer Incomes': 'Income', 'Order Incomes': 'Income',
    'Playstation Incomes': 'Income', 'Member Transactions': 'Income',
    'Discounts': 'Expense',
}


def _fill_cashier(df):
    generic = ~df['cashier'].isin(_REAL_CASHIERS)
    if generic.any():
        clean = df['cashier'].where(df['cashier'].isin(_REAL_CASHIERS))
        df['cashier'] = clean.ffill().bfill()
    return df


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_and_clean_cash(path):
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(axis=1, how='all')
    COLS = {0: 'cashier', 4: 'date', 9: 'type', 11: 'payment',
            21: 'category', 40: 'amount', 50: 'comment'}
    df = raw.iloc[4:][list(COLS)].rename(columns=COLS).copy()

    df = df[~df['cashier'].apply(_is_header_row)].reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    df['amount'] = df['amount'].apply(_parse_amount)
    df['cashier'] = df['cashier'].str.strip().str.lower()
    df['type'] = df['type'].str.strip()
    df['payment'] = df['payment'].str.strip()
    df['category'] = df['category'].str.strip()

    df = _fill_cashier(df)

    df['payment'] = df['payment'].fillna('Cash')

    missing_type = df['type'].isna()
    if missing_type.any():
        df.loc[missing_type, 'type'] = df.loc[missing_type, 'category'].map(_TYPE_FROM_CATEGORY)

    missing_amt = df['amount'].isna()
    if missing_amt.any():
        medians = df.groupby('category')['amount'].median()
        df.loc[missing_amt, 'amount'] = df.loc[missing_amt, 'category'].map(medians)

    if df['date'].isna().any():
        df['date'] = df['date'].ffill()

    return df.drop(columns=['comment'])


def load_and_clean_sessions(path):
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(axis=1, how='all')
    COLS = {0: 'cashier', 4: 'terminal', 9: 'session_type',
            11: 'free_time', 20: 'duration',
            22: 'order_transfer', 27: 'usb_data',
            28: 'usage', 30: 'discount', 32: 'total'}
    df = raw.iloc[4:][list(COLS)].rename(columns=COLS).copy()

    df = df[~df['cashier'].apply(_is_header_row)]
    df = df[~df['terminal'].isin(_SESSION_NOISE)]
    df = df[~df['free_time'].isin(_SESSION_NOISE)].reset_index(drop=True)

    for col in ['order_transfer', 'usb_data', 'usage', 'discount', 'total']:
        df[col] = df[col].apply(_parse_amount)
    df['duration_min'] = df['duration'].apply(_parse_duration)
    df['cashier'] = df['cashier'].str.strip().str.lower()
    df['terminal'] = df['terminal'].astype(str).str.strip()
    df['session_type'] = df['session_type'].astype(str).str.strip()

    df = _fill_cashier(df)

    for col in ['order_transfer', 'usb_data', 'usage', 'discount', 'total']:
        df[col] = df[col].fillna(0)

    computed = df['usage'] + df['order_transfer'] + df['usb_data'] - df['discount']
    mismatch = (df['total'] - computed).abs() > 0.01
    df.loc[mismatch, 'total'] = computed[mismatch]

    df['terminal_type'] = df['terminal'].apply(
        lambda t: 'PlayStation' if 'PS5' in t else ('VIP PC' if 'VIP' in t else 'Standard PC')
    )

    return df.drop(columns=['duration', 'free_time'])


def load_and_clean_stock(path):
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(axis=1, how='all')
    COLS = {0: 'cashier', 4: 'date', 8: 'item', 13: 'category',
            20: 'direction', 25: 'quantity', 28: 'unit_price',
            29: 'total', 32: 'comment'}
    df = raw.iloc[4:][list(COLS)].rename(columns=COLS).copy()

    df = df[~df['cashier'].apply(_is_header_row)].reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    df['unit_price'] = df['unit_price'].apply(_parse_amount)
    df['total'] = df['total'].apply(_parse_amount)
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    df['cashier'] = df['cashier'].astype(str).str.strip().str.lower()
    df['item'] = df['item'].astype(str).str.strip()
    df['category'] = df['category'].astype(str).str.strip()

    df = _fill_cashier(df)

    missing_qty = df['quantity'].isna() & df['unit_price'].notna() & df['total'].notna()
    if missing_qty.any():
        df.loc[missing_qty, 'quantity'] = (df.loc[missing_qty, 'total'] / df.loc[missing_qty, 'unit_price']).round()

    missing_total = df['total'].isna() & df['quantity'].notna() & df['unit_price'].notna()
    if missing_total.any():
        df.loc[missing_total, 'total'] = df.loc[missing_total, 'quantity'] * df.loc[missing_total, 'unit_price']

    missing_price = df['unit_price'].isna() & df['quantity'].notna() & df['total'].notna()
    if missing_price.any():
        df.loc[missing_price, 'unit_price'] = df.loc[missing_price, 'total'] / df.loc[missing_price, 'quantity']

    computed = df['quantity'] * df['unit_price']
    mismatch = ((df['total'] - computed).abs() > 0.01) & computed.notna()
    df.loc[mismatch, 'total'] = computed[mismatch]

    df['quantity'] = df['quantity'].astype('Int64')

    return df.drop(columns=['comment'])


def load_and_clean_members(path):
    raw = pd.read_excel(path, header=None)
    raw = raw.dropna(axis=1, how='all')
    COLS = {2: 'member_id', 6: 'username', 8: 'firstname', 13: 'lastname',
            14: 'duration', 22: 'usage_tnd', 27: 'orders_tnd',
            28: 'usb_tnd', 30: 'total_tnd'}
    valid_cols = {k: v for k, v in COLS.items() if k in raw.columns}
    df = raw.iloc[4:][list(valid_cols)].rename(columns=valid_cols).copy()

    df = df[pd.to_numeric(df['member_id'], errors='coerce').notna()].reset_index(drop=True)
    df['member_id'] = pd.to_numeric(df['member_id'], errors='coerce').astype('Int64')

    for col in ['usage_tnd', 'orders_tnd', 'usb_tnd', 'total_tnd']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_amount)
    df['duration_min'] = df['duration'].apply(_parse_duration)
    df['username'] = df['username'].astype(str).str.strip()
    df['firstname'] = df['firstname'].astype(str).str.strip()
    df['lastname'] = df['lastname'].astype(str).str.strip()

    missing_fn = df['firstname'].isin(['', 'nan']) | df['firstname'].isna()
    if missing_fn.any():
        df.loc[missing_fn, 'firstname'] = df.loc[missing_fn, 'username']

    missing_ln = df['lastname'].isin(['', 'nan']) | df['lastname'].isna()
    if missing_ln.any():
        df.loc[missing_ln, 'lastname'] = ''

    usb = df['usb_tnd'].fillna(0) if 'usb_tnd' in df.columns else 0
    computed = df['usage_tnd'].fillna(0) + df['orders_tnd'].fillna(0) + usb
    mismatch = (df['total_tnd'] - computed).abs() > 0.01
    df.loc[mismatch, 'total_tnd'] = computed[mismatch]

    return df.drop(columns=['duration'])


# ── Star Schema ───────────────────────────────────────────────────────────────

def build_star_schema(cash, sessions, stock, members):
    # dim_cashier
    all_cashiers = sorted(set(
        cash['cashier'].tolist() + sessions['cashier'].tolist() + stock['cashier'].tolist()
    ))
    dim_cashier = pd.DataFrame({
        'cashier_id': range(1, len(all_cashiers) + 1),
        'cashier_name': all_cashiers,
    })
    cashier_map = dict(zip(dim_cashier['cashier_name'], dim_cashier['cashier_id']))

    # dim_member
    dim_member = members.copy()

    # dim_item (stock dissolved — quantity aggregated per item)
    item_agg = stock.groupby('item').agg(
        category=('category', 'first'),
        unit_price=('unit_price', 'median'),
        quantite=('quantity', 'sum'),
        total_revenue=('total', 'sum'),
    ).reset_index()
    item_agg.insert(0, 'item_id', range(1, len(item_agg) + 1))
    dim_item = item_agg
    item_map = dict(zip(dim_item['item'], dim_item['item_id']))

    price_to_item = dict(zip(dim_item['unit_price'], dim_item['item_id']))
    item_prices = np.array(sorted(price_to_item.keys()))

    # dim_terminal
    terminals = (
        sessions[['terminal', 'terminal_type']]
        .drop_duplicates()
        .sort_values('terminal')
        .reset_index(drop=True)
    )
    terminals.insert(0, 'terminal_id', range(1, len(terminals) + 1))
    dim_terminal = terminals
    terminal_map = dict(zip(dim_terminal['terminal'], dim_terminal['terminal_id']))

    pc_ids = dim_terminal[dim_terminal['terminal_type'] == 'Standard PC']['terminal_id'].tolist()
    ps_ids = dim_terminal[dim_terminal['terminal_type'] == 'PlayStation']['terminal_id'].tolist()
    member_ids = dim_member['member_id'].tolist()

    # fact_transaction
    fact_tx = cash.copy()
    fact_tx.insert(0, 'tx_id', range(1, len(fact_tx) + 1))
    fact_tx['cashier_id'] = fact_tx['cashier'].map(cashier_map)
    fact_tx['date'] = fact_tx['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    fact_tx = fact_tx.drop(columns=['cashier'])

    fact_tx['terminal_id'] = np.nan
    pc_mask = fact_tx['category'] == 'Computer Incomes'
    ps_mask = fact_tx['category'] == 'Playstation Incomes'
    if pc_ids:
        fact_tx.loc[pc_mask, 'terminal_id'] = [pc_ids[i % len(pc_ids)] for i in range(pc_mask.sum())]
    if ps_ids:
        fact_tx.loc[ps_mask, 'terminal_id'] = [ps_ids[i % len(ps_ids)] for i in range(ps_mask.sum())]
    fact_tx['terminal_id'] = fact_tx['terminal_id'].astype('Int64')

    fact_tx['item_id'] = np.nan
    order_mask = fact_tx['category'] == 'Order Incomes'
    if len(item_prices) > 0 and order_mask.sum() > 0:
        amounts = fact_tx.loc[order_mask, 'amount'].values
        closest = item_prices[np.abs(item_prices[:, None] - amounts[None, :]).argmin(axis=0)]
        fact_tx.loc[order_mask, 'item_id'] = [price_to_item[p] for p in closest]
    fact_tx['item_id'] = fact_tx['item_id'].astype('Int64')

    fact_tx['member_id'] = np.nan
    member_mask = fact_tx['category'] == 'Member Transactions'
    if member_ids and member_mask.sum() > 0:
        fact_tx.loc[member_mask, 'member_id'] = [member_ids[i % len(member_ids)] for i in range(member_mask.sum())]
    fact_tx['member_id'] = fact_tx['member_id'].astype('Int64')

    # fact_session
    fact_sess = sessions.copy()
    fact_sess.insert(0, 'session_id', range(1, len(fact_sess) + 1))
    fact_sess['cashier_id'] = fact_sess['cashier'].map(cashier_map)
    fact_sess['terminal_id'] = fact_sess['terminal'].map(terminal_map)

    fact_sess['member_id'] = np.nan
    sess_member_mask = fact_sess['session_type'] == 'Member'
    if member_ids and sess_member_mask.sum() > 0:
        fact_sess.loc[sess_member_mask, 'member_id'] = [
            member_ids[i % len(member_ids)] for i in range(sess_member_mask.sum())
        ]
    fact_sess['member_id'] = fact_sess['member_id'].astype('Int64')
    fact_sess = fact_sess.drop(columns=['cashier', 'terminal', 'terminal_type'])

    return {
        'dim_cashier': dim_cashier,
        'dim_member': dim_member,
        'dim_item': dim_item,
        'dim_terminal': dim_terminal,
        'fact_transaction': fact_tx,
        'fact_session': fact_sess,
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def run_pipeline(input_dir: str, use_augment: bool = True) -> tuple:
    """Load, clean, and build star schema from the four source files.

    If use_augment=True (default) and excel/augment/ files exist, they are
    prepended to the training data in memory — the original files are never
    modified.

    Returns:
        (schema, cash, stock) where schema is the star schema dict and
        cash/stock are the cleaned intermediate DataFrames needed for forecasting.
    """
    base = input_dir.rstrip('/').rstrip('\\')
    src = {k: os.path.join(base, v) for k, v in FILES.items()}

    missing = [k for k, p in src.items() if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(f'Missing source files: {missing}')

    cash     = load_and_clean_cash(src['cash'])
    sessions = load_and_clean_sessions(src['sessions'])
    stock    = load_and_clean_stock(src['stock'])
    members  = load_and_clean_members(src['members'])

    if use_augment:
        aug_src = {k: os.path.join(base, v) for k, v in AUGMENT_FILES.items()}
        if all(os.path.exists(p) for p in aug_src.values()):
            aug_cash     = load_and_clean_cash(aug_src['cash'])
            aug_sessions = load_and_clean_sessions(aug_src['sessions'])
            aug_stock    = load_and_clean_stock(aug_src['stock'])
            cash     = pd.concat([aug_cash,     cash],     ignore_index=True)
            sessions = pd.concat([aug_sessions, sessions], ignore_index=True)
            stock    = pd.concat([aug_stock,    stock],    ignore_index=True)
            print(f'  Augment loaded: +{len(aug_cash):,} cash  '
                  f'+{len(aug_sessions):,} sessions  +{len(aug_stock):,} stock rows')

    cutoff = pd.Timestamp('2026-12-31')
    cash  = cash[cash['date'] <= cutoff].reset_index(drop=True)
    stock = stock[stock['date'] <= cutoff].reset_index(drop=True)

    schema = build_star_schema(cash, sessions, stock, members)
    return schema, cash, stock
