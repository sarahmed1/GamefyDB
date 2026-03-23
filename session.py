from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment


def parse_duration_to_minutes(value: object) -> float | None:
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None

    hours_match = re.search(r"(\d+)\s*h", text, flags=re.IGNORECASE)
    mins_match = re.search(r"(\d+)\s*min", text, flags=re.IGNORECASE)

    if not hours_match and not mins_match:
        return None

    hours = int(hours_match.group(1)) if hours_match else 0
    minutes = int(mins_match.group(1)) if mins_match else 0
    return float(hours * 60 + minutes)


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


def load_from_html(input_path: Path) -> pd.DataFrame:
    tables = pd.read_html(str(input_path))
    if not tables:
        raise ValueError(f"No table found in HTML file: {input_path}")

    expected = {
        "Cashier",
        "Terminal",
        "Session Type",
        "Duration",
        "Order/Transfer",
        "USB Data",
        "Usage",
        "Discount",
        "Total Amount",
    }

    selected = None
    for table in tables:
        if expected.issubset(set(table.columns.astype(str))):
            selected = table.copy()
            break

    if selected is None:
        selected = tables[0].copy()

    selected = selected.fillna("")
    selected["Page"] = 1
    selected["PageDateTime"] = ""

    keep_columns = [
        "Page",
        "PageDateTime",
        "Cashier",
        "Terminal",
        "Session Type",
        "Free Time",
        "Paused",
        "Duration",
        "Order/Transfer",
        "Discount",
        "USB Data",
        "Usage",
        "Total Amount",
    ]

    for col in keep_columns:
        if col not in selected.columns:
            selected[col] = ""

    return selected[keep_columns]


def load_from_xls(input_path: Path) -> pd.DataFrame:
    df = pd.read_excel(str(input_path), header=None)

    timestamp_mask = df[0].astype(str).str.contains(
        r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", na=False
    )
    timestamp_indices = df[timestamp_mask].index

    if not timestamp_indices.empty:
        global_date = str(df.loc[timestamp_indices[0], 0])
    else:
        global_date = str(df.iloc[1, 31]) if pd.notna(df.iloc[1, 31]) else ""

    df["DateTime"] = None
    for idx in timestamp_indices:
        df.loc[idx, "DateTime"] = str(df.loc[idx, 0])

    df["DateTime"] = df["DateTime"].ffill().fillna(global_date)

    df["Page"] = 1
    for page_num, idx in enumerate(timestamp_indices, start=1):
        df.loc[idx:, "Page"] = page_num

    df = df[df[0].notna()]
    df = df[df[0] != "Cashier"]
    df = df[~df[0].astype(str).str.contains(r"\d{2}/\d{2}/\d{4}", na=False)]
    df = df[df[0] != "Session Reports"]

    df_fixed = pd.DataFrame(
        {
            "Page": df["Page"],
            "PageDateTime": df["DateTime"],
            "Cashier": df[0],
            "Terminal": df[4],
            "Session Type": df[9],
            "Free Time": df[12],
            "Paused": df[14],
            "Duration": df[20],
            "Order/Transfer": df[22],
            "Discount": df[30],
            "USB Data": df[27],
            "Usage": df[28],
            "Total Amount": df[32],
        }
    ).reset_index(drop=True)

    return df_fixed.fillna("")


def normalize(df_fixed: pd.DataFrame) -> pd.DataFrame:
    df_fixed = df_fixed.copy().fillna("")

    df_fixed = df_fixed[df_fixed["Cashier"] != "Cashier"]
    df_fixed = df_fixed[
        ~df_fixed["Cashier"].astype(str).str.contains(r"\d{2}/\d{2}/\d{4}", na=False)
    ]

    money_cols = ["Order/Transfer", "Discount", "USB Data", "Usage", "Total Amount"]
    for col in money_cols:
        df_fixed[col] = df_fixed[col].apply(parse_amount)

    df_fixed["Duration (min)"] = df_fixed["Duration"].apply(parse_duration_to_minutes)
    df_fixed["Free Time (min)"] = df_fixed["Free Time"].apply(parse_duration_to_minutes)
    df_fixed["Paused (min)"] = df_fixed["Paused"].apply(parse_duration_to_minutes)

    ordered = [
        "Page",
        "PageDateTime",
        "Cashier",
        "Terminal",
        "Session Type",
        "Free Time",
        "Paused",
        "Duration",
        "Free Time (min)",
        "Paused (min)",
        "Duration (min)",
        "Order/Transfer",
        "Discount",
        "USB Data",
        "Usage",
        "Total Amount",
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
        project_root / "data" / "test.html",
        project_root / "data" / "DATA session reports 01-09-2025.xls",
        project_root / "session" / "session_lastmonth_xls.xls",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError("No session input file found in expected locations.")


def main() -> None:
    project_root = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        description="Session report cleaner (prefers HTML, falls back to XLS)."
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
        output_path = project_root / "session" / f"session_fixed_{timestamp}.xlsx"

    cleaned.to_excel(str(output_path), index=False)
    format_excel(output_path)

    print(f"Input file: {input_path}")
    print(f"Rows cleaned: {len(cleaned)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()