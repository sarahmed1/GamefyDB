import logging
from pathlib import Path
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_INPUT_PATTERNS = ("*.xlsx", "*.xls", "*.html")

_REPORT_DEFINITIONS: dict[str, tuple[str, list[str]]] = {
    "SESSION DATA": ("session", ["Cashier", "Terminal", "Session Type"]),
    "CASH DATA": ("cash", ["Cashier", "Date", "Income/Expense"]),
    "STOCK DATA": ("stock", ["Cashier", "Date", "Item Name"]),
    "MEMBER DATA": ("member", ["ID", "Username", "Firstname"]),
}


def collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge duplicate column labels by taking the first non-null value per row.
    FastReport HTML often creates repeated headers because of colspans.
    """
    if df.columns.is_unique:
        return df

    collapsed = pd.DataFrame(index=df.index)
    for col in pd.unique(df.columns):
        same_named_cols = df.loc[:, df.columns == col]
        if same_named_cols.shape[1] == 1:
            collapsed[col] = same_named_cols.iloc[:, 0]
        else:
            collapsed[col] = same_named_cols.bfill(axis=1).iloc[:, 0]
    return collapsed


def _detect_report_type(filename: str) -> tuple[str, list[str]] | None:
    upper_name = filename.upper()
    for marker, (record_type, headers_to_find) in _REPORT_DEFINITIONS.items():
        if marker in upper_name:
            return record_type, headers_to_find

    return None


def _clean_col_name(col_name: object) -> str:
    return str(col_name).replace("\xa0", " ").strip()


def _extract_valid_tables(
    dataframes: list[pd.DataFrame],
    headers_to_find: list[str],
) -> list[pd.DataFrame]:
    valid_dfs: list[pd.DataFrame] = []
    for df in dataframes:
        if df.empty:
            continue

        df = df.dropna(axis=1, how="all")
        if df.empty:
            continue

        header_row_idx = None
        for idx, row in df.iterrows():
            row_str = " ".join(str(x) for x in row.values)
            if all(header in row_str for header in headers_to_find):
                header_row_idx = idx
                break

        if header_row_idx is None:
            continue

        df.columns = df.iloc[header_row_idx].astype(str).str.strip()
        df = df.iloc[header_row_idx + 1 :].copy()

        if df.empty:
            continue

        df = collapse_duplicate_columns(df)
        df = df.dropna(axis=0, how="all")

        if "Cashier" in df.columns:
            df = df[~df["Cashier"].astype(str).str.contains("Total|nan", case=False, na=False)]
        if "ID" in df.columns:
            df = df[~df["ID"].astype(str).str.contains("Total|nan", case=False, na=False)]

        valid_dfs.append(df)

    return valid_dfs


def _extract_from_html(filepath: str, headers_to_find: list[str]) -> list[pd.DataFrame]:
    try:
        dataframes = pd.read_html(filepath, flavor="lxml", encoding="utf-8")
    except ValueError as exc:
        logger.warning(f"No tables found or failed to parse HTML in {filepath}: {exc}")
        return []

    return _extract_valid_tables(dataframes, headers_to_find)


def _extract_from_excel(filepath: str, headers_to_find: list[str]) -> list[pd.DataFrame]:
    try:
        sheets = pd.read_excel(filepath, sheet_name=None, header=None)
    except ImportError as exc:
        logger.error(
            f"Excel dependency is missing while parsing {filepath}: {exc}. "
            "Install openpyxl for .xlsx and xlrd for .xls support."
        )
        return []
    except ValueError as exc:
        logger.warning(f"Failed to parse Excel file in {filepath}: {exc}")
        return []

    if not sheets:
        logger.warning(f"No worksheets found in {filepath}")
        return []

    dataframes = [df for df in sheets.values() if isinstance(df, pd.DataFrame)]
    return _extract_valid_tables(dataframes, headers_to_find)

def extract_file(filepath: str) -> tuple[str, list[dict]] | None:
    try:
        path = Path(filepath)
        report_type = _detect_report_type(path.name)
        if report_type is None:
            logger.warning(f"Unknown report type for file: {filepath}")
            return None
        record_type, headers_to_find = report_type

        suffix = path.suffix.lower()
        if suffix == ".html":
            valid_dfs = _extract_from_html(filepath, headers_to_find)
        elif suffix in {".xlsx", ".xls"}:
            valid_dfs = _extract_from_excel(filepath, headers_to_find)
        else:
            logger.warning(f"Unsupported file extension for file: {filepath}")
            return None

        if not valid_dfs:
            logger.warning(f"Could not find valid data table in {filepath}")
            return None

        target_df = pd.concat(valid_dfs, ignore_index=True)

        target_df.columns = [_clean_col_name(c) for c in target_df.columns]
        target_df = target_df.replace({np.nan: None})

        records = target_df.to_dict("records")

        # Add source_file to each record
        for r in records:
            r["source_file"] = filepath

        return record_type, records

    except Exception as exc:
        logger.error(f"Error extracting {filepath}: {exc}", exc_info=True)
        return None


def extract_html_file(filepath: str) -> tuple[str, list[dict]] | None:
    """Backward-compatible alias for legacy callers."""
    return extract_file(filepath)
