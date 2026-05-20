import os
import re
import calendar
from dataclasses import dataclass
from datetime import datetime

import xlrd
from xlutils.copy import copy
from xlwt.Cell import BlankCell, BooleanCell, ErrorCell, NumberCell, StrCell

MONTHS_TO_ADD = 6
SOURCE_FILES = [
    "Cash DATA 01-09-2025.xls",
    "DATA session reports 01-09-2025.xls",
    "Stock DATA 01-09-2025.xls",
    "memeber DATA 01-09-2025.xls",
]

DATE_FULL_RE = re.compile(r"^(\d{2})([./])(\d{2})\2(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$")
DATE_FIND_RE = re.compile(r"\b\d{2}[./]\d{2}[./]\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?")
PAGE_RE = re.compile(r"^Page\s+\d+/\d+$")

ALLOWED_CASHIERS = ["guds", "monta", "taktek", "yassine", "youssef"]
AMOUNT_HEADERS = {
    "Amount",
    "Total Amount",
    "Unit Price",
    "Order/Transfer",
    "Ord.& Trans.",
    "Orders Amount",
    "Usage",
    "Usage Amount",
    "USB Data",
    "Discount",
}


@dataclass(frozen=True)
class ParsedDate:
    dt: datetime
    sep: str
    has_time: bool
    has_seconds: bool


def add_months(dt: datetime, months: int) -> datetime:
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def parse_date_str(value: str) -> ParsedDate | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    match = DATE_FULL_RE.match(text)
    if not match:
        return None
    day = int(match.group(1))
    sep = match.group(2)
    month = int(match.group(3))
    year = int(match.group(4))
    has_time = match.group(5) is not None
    if has_time:
        hour = int(match.group(5))
        minute = int(match.group(6))
        second = int(match.group(7) or 0)
        dt = datetime(year, month, day, hour, minute, second)
    else:
        dt = datetime(year, month, day)
    return ParsedDate(dt=dt, sep=sep, has_time=has_time, has_seconds=bool(match.group(7)))


def format_date_value(dt: datetime, include_time: bool) -> str:
    date_part = f"{dt.day:02d}.{dt.month:02d}.{dt.year:04d}"
    if not include_time:
        return date_part
    return f"{date_part} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"


def normalize_date_value(value: str, require_time: bool, shift_months: int = 0) -> str:
    parsed = parse_date_str(value)
    if not parsed:
        return value
    dt = add_months(parsed.dt, shift_months) if shift_months else parsed.dt
    include_time = require_time or parsed.has_time
    if require_time and not parsed.has_time:
        dt = dt.replace(hour=0, minute=0, second=0)
    return format_date_value(dt, include_time)


def shift_date_str(value: str, months: int, require_time: bool) -> str:
    return normalize_date_value(value, require_time=require_time, shift_months=months)


def update_date_range_string(value: str, months: int) -> str:
    if not isinstance(value, str):
        return value
    matches = list(DATE_FIND_RE.finditer(value))
    if len(matches) < 2:
        return value
    end_match = matches[1]
    end_text = end_match.group(0)
    parsed = parse_date_str(end_text)
    if not parsed:
        return value
    shifted = normalize_date_value(end_text, require_time=parsed.has_time, shift_months=months)
    return value[:end_match.start()] + shifted + value[end_match.end():]


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def normalize_cashier(value: str) -> str:
    if not isinstance(value, str):
        return value
    name = value.strip().lower()
    if name in ALLOWED_CASHIERS:
        return name
    if not name:
        return name
    idx = sum(ord(ch) for ch in name) % len(ALLOWED_CASHIERS)
    return ALLOWED_CASHIERS[idx]


def parse_amount_value(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.replace("\u202f", "").replace("\xa0", "").strip()
    text = text.replace(" TND", "").replace("TND", "").strip()
    text = text.replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def format_tnd(amount: float) -> str:
    text = f"{amount:,.2f}"
    text = text.replace(",", "\u202f").replace(".", ",")
    return f"{text} TND"


def build_header_map(header_row: list) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, value in enumerate(header_row):
        if not isinstance(value, str):
            continue
        key = value.strip()
        if not key or key in mapping:
            continue
        mapping[key] = idx
    return mapping


def is_numeric_value(value) -> bool:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(value, str) and value.strip().isdigit():
        return True
    return False


def find_header_row(ws: xlrd.sheet.Sheet) -> int:
    for r in range(ws.nrows):
        row = ws.row_values(r)
        if any(isinstance(v, str) and v.strip() == "Cashier" for v in row):
            return r
        if (
            any(isinstance(v, str) and v.strip() == "ID" for v in row)
            and any(isinstance(v, str) and v.strip() == "Username" for v in row)
        ):
            return r
    return 0


def find_footer_start(ws: xlrd.sheet.Sheet) -> int:
    markers = ("Filter Status :", "Date Range", "Report Result :")
    for r in range(ws.nrows):
        row = ws.row_values(r)
        for v in row:
            if isinstance(v, str) and any(m in v for m in markers):
                return r
    return ws.nrows


def find_date_cols(ws: xlrd.sheet.Sheet, header_row: int) -> set[int]:
    header = ws.row_values(header_row)
    return {i for i, v in enumerate(header) if isinstance(v, str) and v.strip() == "Date"}


def find_range_end_date(ws: xlrd.sheet.Sheet) -> ParsedDate | None:
    for r in range(ws.nrows):
        row = ws.row_values(r)
        if not any(isinstance(v, str) and "Date Range" in v for v in row):
            continue
        for v in row:
            if not isinstance(v, str):
                continue
            matches = list(DATE_FIND_RE.finditer(v))
            if len(matches) < 2:
                continue
            parsed = parse_date_str(matches[1].group(0))
            if parsed:
                return parsed
    return None


def copy_column_widths(src: xlrd.sheet.Sheet, dst) -> None:
    for colx, info in src.colinfo_map.items():
        dst.col(colx).width = info.width


def copy_row_height(src: xlrd.sheet.Sheet, dst, src_r: int, dst_r: int) -> None:
    info = src.rowinfo_map.get(src_r)
    if info is None:
        return
    dst_row = dst.row(dst_r)
    dst_row.height = info.height
    dst_row.height_mismatch = True


def generate_synthetic_file(src_path: str, out_path: str) -> None:
    rb = xlrd.open_workbook(src_path, formatting_info=True)
    src = rb.sheet_by_index(0)
    wb = copy(rb)
    ws = wb.get_sheet(0)

    # reset merges; we will rebuild them explicitly
    ws.merged_ranges[:] = []
    ws._Worksheet__merged_ranges[:] = []
    merged_rec = getattr(ws, "_Worksheet__merged_rec", None)
    if isinstance(merged_rec, list):
        merged_rec[:] = []

    copy_column_widths(src, ws)

    header_row = find_header_row(src)
    footer_start = find_footer_start(src)
    data_len = footer_start - header_row
    date_cols = find_date_cols(src, header_row)
    header_map = build_header_map(src.row_values(header_row))
    cashier_col = header_map.get("Cashier")
    id_col = header_map.get("ID")
    income_col = header_map.get("Income/Expense")
    payment_col = header_map.get("Payment Method")
    type_col = header_map.get("Transaction Type")
    comment_col = header_map.get("Comment")
    amount_cols = {idx for name, idx in header_map.items() if name in AMOUNT_HEADERS}

    range_end = find_range_end_date(src)
    new_end_dt = add_months(range_end.dt, MONTHS_TO_ADD) if range_end else None

    row_is_data = [False] * src.nrows
    for r in range(src.nrows):
        if r < header_row or r >= footer_start:
            continue
        row = src.row_values(r)
        if any(isinstance(v, str) and PAGE_RE.match(v.strip()) for v in row):
            continue
        if any(isinstance(v, str) and v.strip() == "Cashier" for v in row):
            continue
        if any(
            isinstance(v, str)
            and any(m in v for m in ("Filter Status :", "Date Range", "Report Result :"))
            for v in row
        ):
            continue
        if cashier_col is not None:
            value = row[cashier_col] if cashier_col < len(row) else None
            if isinstance(value, str) and value.strip() and not parse_date_str(value.strip()):
                row_is_data[r] = True
        elif id_col is not None:
            value = row[id_col] if id_col < len(row) else None
            if is_numeric_value(value):
                row_is_data[r] = True

    def first_non_empty(rows: list, col: int) -> str:
        for values in rows:
            value = values[col] if col < len(values) else None
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    data_rows = [src.row_values(r) for r in range(src.nrows) if row_is_data[r]]
    default_income = first_non_empty(data_rows, income_col) if income_col is not None else ""
    if not default_income:
        default_income = "Income"
    default_payment = first_non_empty(data_rows, payment_col) if payment_col is not None else ""
    if not default_payment:
        default_payment = "Cash"
    default_type = first_non_empty(data_rows, type_col) if type_col is not None else ""
    if not default_type:
        default_type = "Computer Incomes"
    default_comment = first_non_empty(data_rows, comment_col) if comment_col is not None else ""
    if not default_comment:
        default_comment = "(GAMEFY01)"

    page_cells_data = []
    page_cells_all = []
    for r in range(src.nrows):
        for c in range(src.ncols):
            v = src.cell_value(r, c)
            if isinstance(v, str) and PAGE_RE.match(v.strip()):
                page_cells_all.append((r, c))
                if header_row <= r < footer_start:
                    page_cells_data.append((r, c))
                break
    total_pages = len(page_cells_all) + len(page_cells_data)
    # cache xf_idx values from the template sheet before overwriting
    xf_idx_map: list[list[int]] = []
    for r in range(src.nrows):
        row = ws._Worksheet__rows.get(r)
        row_xf: list[int] = []
        for c in range(src.ncols):
            cell = row._Row__cells.get(c) if row else None
            row_xf.append(cell.xf_idx if cell else 0)
        xf_idx_map.append(row_xf)

    page_counter = 1

    def build_cell(
        dst_r: int,
        c: int,
        xf_idx: int,
        cell: xlrd.sheet.Cell,
        value,
        force_text: bool,
    ) -> object:
        if force_text:
            text = "" if value is None else str(value)
            return StrCell(dst_r, c, xf_idx, wb.add_str(text))
        if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK) or value == "":
            return BlankCell(dst_r, c, xf_idx)
        if cell.ctype == xlrd.XL_CELL_BOOLEAN:
            return BooleanCell(dst_r, c, xf_idx, int(value))
        if cell.ctype == xlrd.XL_CELL_ERROR:
            return ErrorCell(dst_r, c, xf_idx, int(value))
        if cell.ctype == xlrd.XL_CELL_NUMBER:
            return NumberCell(dst_r, c, xf_idx, float(value))
        text = value if isinstance(value, str) else str(value)
        return StrCell(dst_r, c, xf_idx, wb.add_str(text))

    def write_cell(src_r: int, dst_r: int, c: int, shift_dates: bool, context: str) -> None:
        nonlocal page_counter
        cell = src.cell(src_r, c)
        value = cell.value
        is_data = row_is_data[src_r] if src_r < len(row_is_data) else False

        if is_data and cashier_col is not None and c == cashier_col:
            value = normalize_cashier(value)

        if is_data and c in date_cols and isinstance(value, str):
            value = normalize_date_value(
                value,
                require_time=True,
                shift_months=MONTHS_TO_ADD if shift_dates else 0,
            )

        if is_data and c in amount_cols:
            amount = parse_amount_value(value)
            if amount is None:
                amount = 0.0
            value = format_tnd(amount)

        if is_data and income_col is not None and c == income_col:
            if is_blank(value):
                value = default_income
            elif isinstance(value, str):
                value = value.strip()

        if is_data and payment_col is not None and c == payment_col:
            if is_blank(value):
                value = default_payment
            elif isinstance(value, str):
                value = value.strip()

        if is_data and type_col is not None and c == type_col:
            if is_blank(value):
                value = default_type
            elif isinstance(value, str):
                value = value.strip()

        if is_data and comment_col is not None and c == comment_col:
            if is_blank(value):
                value = default_comment
            elif isinstance(value, str):
                value = value.strip()

        if context in ("header", "footer") and new_end_dt and isinstance(value, str):
            parsed = parse_date_str(value)
            if parsed and parsed.dt == range_end.dt:
                value = format_date_value(new_end_dt, include_time=parsed.has_time)

        if context == "footer" and isinstance(value, str):
            value = update_date_range_string(value, MONTHS_TO_ADD)

        if isinstance(value, str) and PAGE_RE.match(value.strip()):
            value = f"Page {page_counter}/{total_pages}"
            page_counter += 1

        force_text = False
        if is_data and (
            c in amount_cols
            or c in date_cols
            or c in (cashier_col, income_col, payment_col, type_col, comment_col)
        ):
            force_text = True

        xf_idx = xf_idx_map[src_r][c] if src_r < len(xf_idx_map) else 0
        dst_row = ws.row(dst_r)
        dst_row.insert_cell(c, build_cell(dst_r, c, xf_idx, cell, value, force_text))

    def copy_row(src_r: int, dst_r: int, shift_dates: bool, context: str) -> None:
        copy_row_height(src, ws, src_r, dst_r)
        for c in range(src.ncols):
            write_cell(src_r, dst_r, c, shift_dates, context)

    # header rows
    for r in range(header_row):
        copy_row(r, r, shift_dates=False, context="header")

    # original data
    for r in range(header_row, footer_start):
        copy_row(r, r, shift_dates=False, context="data")

    # appended data
    for r in range(header_row, footer_start):
        copy_row(r, r + data_len, shift_dates=True, context="data")

    # footer rows
    for r in range(footer_start, src.nrows):
        copy_row(r, r + data_len, shift_dates=False, context="footer")

    # rebuild merged ranges
    def add_merge(rr_lo: int, rr_hi: int, cc_lo: int, cc_hi: int) -> None:
        if rr_hi - rr_lo <= 1 and cc_hi - cc_lo <= 1:
            return
        ws.merged_ranges.append((rr_lo, rr_hi, cc_lo, cc_hi))
        ws._Worksheet__merged_ranges.append((rr_lo, rr_hi, cc_lo, cc_hi))

    for rlo, rhi, clo, chi in src.merged_cells:
        if rhi <= header_row:
            add_merge(rlo, rhi, clo, chi)
        elif rlo >= footer_start:
            add_merge(rlo + data_len, rhi + data_len, clo, chi)
        else:
            add_merge(rlo, rhi, clo, chi)
            add_merge(rlo + data_len, rhi + data_len, clo, chi)

    if os.path.exists(out_path):
        os.remove(out_path)
    wb.save(out_path)


def main() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    in_dir = os.path.join(root, "excel")
    out_dir = os.path.join(root, "excel_synthetic")
    os.makedirs(out_dir, exist_ok=True)

    for name in SOURCE_FILES:
        src_path = os.path.join(in_dir, name)
        out_path = os.path.join(out_dir, name)
        generate_synthetic_file(src_path, out_path)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
