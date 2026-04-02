import re
import pandas as pd
from datetime import datetime as _dt


_DURATION_RE = re.compile(r'(?:(\d+)\s*h\s*)?(\d+)\s*min')
_TERMINAL_RE = re.compile(r'^\((.+)\)$')


def parse_amount(value: str) -> float:
    """Parse '1 745,44 TND' → 1745.44.

    Handles narrow no-break space (\\u202f) as thousands separator
    and comma as decimal separator.
    """
    s = str(value).replace('\u202f', '').replace(' TND', '').replace(',', '.')
    return float(s)


def parse_datetime(value: str) -> _dt:
    """Parse '23.03.2026 03:23:54' → datetime(2026, 3, 23, 3, 23, 54)."""
    return _dt.strptime(str(value).strip(), '%d.%m.%Y %H:%M:%S')


def parse_duration(value: str) -> int:
    """Parse '1 h 29 min' → 89, '30 min' → 30 (total minutes)."""
    m = _DURATION_RE.search(str(value))
    if not m:
        raise ValueError(f"Cannot parse duration: {value!r}")
    hours = int(m.group(1)) if m.group(1) else 0
    return hours * 60 + int(m.group(2))


def extract_terminal(value) -> str | None:
    """Extract terminal name from comment like '(GAMEFY01)' → 'GAMEFY01'.

    The regex strips only the outermost parens, so '(PS5 (1))' → 'PS5 (1)'.
    Returns None if the value is null or does not match the pattern.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    m = _TERMINAL_RE.match(str(value).strip())
    return m.group(1) if m else None


def _has_marker(value) -> bool:
    """Return True if value is a non-empty, non-NaN string (i.e. xlrd placed a marker in the cell)."""
    if value is None:
        return False
    if isinstance(value, float) and pd.isna(value):
        return False
    return str(value).strip() != ''


def _clean_cash(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['cashier'] = out['cashier'].str.strip()
    out['date'] = pd.to_datetime(out['date'], format='%d.%m.%Y %H:%M:%S')
    out['amount_tnd'] = out['amount'].apply(parse_amount)
    out['terminal'] = out['comment'].apply(extract_terminal)
    return out.drop(columns=['amount'])


def _clean_sessions(df: pd.DataFrame) -> pd.DataFrame:
    # Sessions has no comment column — terminal names come in directly, not wrapped in parens.
    out = df.copy()
    out['cashier'] = out['cashier'].str.strip()
    out['terminal'] = out['terminal'].str.strip()
    out['duration_minutes'] = out['duration'].apply(parse_duration)
    out['is_free_time'] = out['free_time'].apply(_has_marker)
    out['paused_duration_minutes'] = out['paused'].apply(
        lambda v: parse_duration(v) if _has_marker(v) else None
    )
    for src, dst in [
        ('order_transfer', 'order_transfer_tnd'),
        ('usage',          'usage_tnd'),
        ('discount',       'discount_tnd'),
        ('total_amount',   'total_amount_tnd'),
    ]:
        out[dst] = out[src].apply(parse_amount)
    return out.drop(columns=[
        'duration', 'free_time', 'paused',
        'order_transfer', 'usage', 'discount', 'total_amount',
    ])


def _clean_stock(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['cashier'] = out['cashier'].str.strip()
    out['date'] = pd.to_datetime(out['date'], format='%d.%m.%Y %H:%M:%S')
    out['quantity'] = pd.to_numeric(out['quantity']).astype(int)
    out['unit_price_tnd'] = out['unit_price'].apply(parse_amount)
    out['total_amount_tnd'] = out['total_amount'].apply(parse_amount)
    out['terminal'] = out['comment'].apply(extract_terminal)
    return out.drop(columns=['unit_price', 'total_amount'])


def _clean_members(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['member_id'] = pd.to_numeric(out['member_id'], errors='coerce')
    out = out.dropna(subset=['member_id']).copy()
    out['member_id'] = out['member_id'].astype(int)
    out['duration_minutes'] = out['duration'].apply(parse_duration)
    out['usage_tnd'] = out['usage'].apply(parse_amount)
    out['orders_transfer_tnd'] = out['orders_transfer'].apply(parse_amount)
    out['total_amount_tnd'] = out['total_amount'].apply(parse_amount)
    return out.drop(columns=['duration', 'usage', 'orders_transfer', 'total_amount'])


def clean_all(raw: dict) -> dict:
    """Apply per-file type normalization to all ingested DataFrames.

    Args:
        raw: Output of ingest_all — {'cash': df, 'sessions': df, ...}

    Returns:
        Same keys, with typed and normalized columns.
    """
    return {
        'cash':     _clean_cash(raw['cash']),
        'sessions': _clean_sessions(raw['sessions']),
        'stock':    _clean_stock(raw['stock']),
        'members':  _clean_members(raw['members']),
    }
