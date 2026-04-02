import re
import pandas as pd
import xlrd

PAGE_PATTERN = re.compile(r'Page \d+/\d+')


def _strip_artifacts(df: pd.DataFrame, col_map: dict, key_col: str) -> pd.DataFrame:
    """Strip all non-data rows from a raw Excel DataFrame.

    Removes: title row, report date row, blank rows, page markers,
    repeated header rows, and footer rows below the last data row.

    Args:
        df: Raw DataFrame read with header=None (all rows, all cols).
        col_map: {raw_col_index: output_col_name} for the columns to keep.
        key_col: Name (from col_map) of the column that is non-empty only on
                 real data rows (e.g. 'date' for Cash/Stock, 'terminal' for
                 Sessions, 'member_id' for Members).

    Returns:
        DataFrame with only the mapped columns and only data rows.
    """
    # Drop title, report-date, blank, blank, header rows (rows 0–4)
    df = df.iloc[5:].reset_index(drop=True)

    # Drop page marker rows — any cell matching "Page X/Y"
    has_page = df.apply(
        lambda row: any(PAGE_PATTERN.search(str(v)) for v in row),
        axis=1,
    )
    df = df[~has_page].reset_index(drop=True)

    # Drop repeated header rows ("Cashier" text in the first mapped column)
    first_idx = min(col_map.keys())
    df = df[
        df.iloc[:, first_idx].astype(str).str.strip() != 'Cashier'
    ].reset_index(drop=True)

    # Extract and rename the mapped columns
    df = df[list(col_map.keys())].rename(columns=col_map)

    # Drop rows where the key column is empty or NaN (footer / blank rows)
    key = df[key_col]
    # Check for non-NaN and non-empty values
    mask = key.notna() & (key.astype(str).str.strip() != '')
    df = df[mask].reset_index(drop=True)

    return df


# Column positions are the DATA positions (0-indexed) verified directly from
# ws.row_values() output — NOT the visual header positions. Some positions
# differ from their header due to Excel merged cells (e.g., cash 'comment'
# header is at col 50 but data is at col 51; members 'member_id' header is
# at col 0 but data is at col 2). Do not adjust these without re-verifying
# against the raw file with xlrd.
COLUMN_MAPS = {
    'cash': {
        0: 'cashier', 4: 'date', 9: 'income_expense', 11: 'payment_method',
        21: 'transaction_type', 40: 'amount', 51: 'comment',
    },
    'sessions': {
        0: 'cashier', 4: 'terminal', 9: 'session_type', 12: 'free_time',
        14: 'paused', 20: 'duration', 22: 'order_transfer',
        28: 'usage', 30: 'discount', 32: 'total_amount',
    },
    'stock': {
        0: 'cashier', 4: 'date', 8: 'item_name', 13: 'category',
        20: 'in_out', 25: 'quantity', 28: 'unit_price', 29: 'total_amount',
        32: 'comment',
    },
    'members': {
        2: 'member_id', 6: 'username', 8: 'firstname', 13: 'lastname',
        14: 'duration', 22: 'usage', 27: 'orders_transfer',
        30: 'total_amount',
    },
}

FILE_MAP = {
    'cash':     'Cash DATA 01-09-2025.xls',
    'sessions': 'DATA session reports 01-09-2025.xls',
    'stock':    'Stock DATA 01-09-2025.xls',
    'members':  'memeber DATA 01-09-2025.xls',
}

KEY_COLS = {
    'cash':     'date',
    'sessions': 'terminal',
    'stock':    'date',
    'members':  'member_id',
}


def _read_raw(path: str) -> pd.DataFrame:
    """Read .xls via xlrd into a DataFrame with no header parsing."""
    wb = xlrd.open_workbook(path)
    ws = wb.sheet_by_index(0)
    data = [ws.row_values(i) for i in range(ws.nrows)]
    wb.release_resources()
    return pd.DataFrame(data)


def ingest_all(input_dir: str) -> dict:
    """Read all four source files and return stripped DataFrames.

    Returns:
        {'cash': df, 'sessions': df, 'stock': df, 'members': df}
    """
    base = input_dir.rstrip('/').rstrip('\\')
    result = {}
    for name, filename in FILE_MAP.items():
        path = f"{base}/{filename}"
        df_raw = _read_raw(path)
        result[name] = _strip_artifacts(df_raw, COLUMN_MAPS[name], KEY_COLS[name])
    return result
