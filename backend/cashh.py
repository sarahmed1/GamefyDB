from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment


VALID_TYPES = [
    "Member Transactions",
    "Computer Incomes",
    "Playstation Incomes",
    "Ticket Incomes",
    "USB Data Incomes",
    "Order Incomes",
    "Stock Transactions",
]


def parse_amount(value: object) -> float | None:
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None

    cleaned = (
        text.replace("TND", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )

    try:
        return float(cleaned)
    except ValueError:
        return None


def split_date_time(value: object) -> tuple[str, str]:
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return "", ""

    parts = text.split()
    date_part = parts[0].replace(".", "/")
    time_part = parts[1] if len(parts) > 1 else "00:00:00"
    return date_part, time_part


def load_from_html(input_path: Path) -> pd.DataFrame:
    tables = pd.read_html(str(input_path))
    if not tables:
        raise ValueError(f"No table found in HTML file: {input_path}")

    expected = {
        "Cashier",
        "Date",
        "Income/Expense",
        "Payment Method",
        "Transaction Type",
        "Amount",
        "Comment",
    }

    selected = None
    for table in tables:
        if isinstance(table.columns, pd.MultiIndex):
            table.columns = [" ".join([str(x) for x in tup if str(x) != "nan"]).strip() for tup in table.columns]
        cols = {str(c).strip() for c in table.columns}
        if expected.issubset(cols):
            selected = table.copy()
            break

    if selected is None:
        selected = tables[0].copy()

    selected = selected.fillna("")
    for col in expected:
        if col not in selected.columns:
            selected[col] = ""

    return selected[[
        "Cashier",
        "Date",
        "Income/Expense",
        "Payment Method",
        "Transaction Type",
        "Amount",
        "Comment",
    ]]


def load_from_xls(input_path: Path) -> pd.DataFrame:
    df = pd.read_excel(str(input_path), header=None)

    df = df[df[0].notna()]
    df = df[df[0] != "Cashier"]
    df = df[~df[0].astype(str).str.contains("Page", na=False)]
    df = df[~df[0].astype(str).str.contains(r"\d{2}/\d{2}/\d{4}", na=False)]

    df_fixed = pd.DataFrame(
        {
            "Cashier": df[0],
            "Date": df[4],
            "Income/Expense": df[9],
            "Payment Method": df[11],
            "Transaction Type": df[21],
            "Amount": df[40],
            "Comment": df[50],
        }
    ).reset_index(drop=True)

    return df_fixed.fillna("")


def normalize(df_fixed: pd.DataFrame) -> pd.DataFrame:
    df_fixed = df_fixed.copy().fillna("")

    df_fixed = df_fixed[df_fixed["Cashier"] != "Cashier"]
    df_fixed = df_fixed[
        ~df_fixed["Cashier"].astype(str).str.contains(r"\d{2}/\d{2}/\d{4}", na=False)
    ]
    df_fixed = df_fixed[~df_fixed["Comment"].astype(str).str.contains("Page", na=False)]

    if "Transaction Type" in df_fixed.columns:
        df_fixed = df_fixed[df_fixed["Transaction Type"].isin(VALID_TYPES)]

    split = df_fixed["Date"].apply(split_date_time)
    df_fixed[["Date", "Time"]] = pd.DataFrame(split.tolist(), index=df_fixed.index)

    df_fixed["Amount"] = df_fixed["Amount"].apply(parse_amount)

    ordered = [
        "Cashier",
        "Date",
        "Time",
        "Income/Expense",
        "Payment Method",
        "Transaction Type",
        "Amount",
        "Comment",
    ]
    return df_fixed[ordered].reset_index(drop=True)


def format_excel(output_path: Path) -> None:
    wb = load_workbook(str(output_path))
    ws = wb.active

    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.column_dimensions[column_letter].width = max_length + 2

    wb.save(str(output_path))


def pick_default_input(project_root: Path) -> Path:
    candidates = [
        project_root / "data" / "Cash DATA 01-09-2025.xls",
        project_root / "cash" / "cash_lastmonth_xls.xls",
        project_root / "data" / "test.html",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("No cash input file found in expected locations.")


def main() -> None:
    project_root = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        description="Cash report cleaner (prefers HTML, falls back to XLS)."
    )
    parser.add_argument("--input", type=str, default="", help="Input report path (.html/.xls/.xlsx)")
    parser.add_argument("--output", type=str, default="", help="Output .xlsx path")
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else pick_default_input(project_root)
    ext = input_path.suffix.lower()

    if ext in {".html", ".htm"}:
        source_df = load_from_html(input_path)
    elif ext in {".xls", ".xlsx"}:
        source_df = load_from_xls(input_path)
    else:
        raise ValueError("Unsupported input extension. Use .html, .htm, .xls or .xlsx")

    cleaned = normalize(source_df)

    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = project_root / "cash" / f"cash_fixed_{timestamp}.xlsx"

    cleaned.to_excel(str(output_path), index=False)
    format_excel(output_path)

    print(f"Input file: {input_path}")
    print(f"Rows cleaned: {len(cleaned)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()