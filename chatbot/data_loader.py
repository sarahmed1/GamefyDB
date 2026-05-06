from dataclasses import dataclass, field
import pandas as pd
from pathlib import Path
import warnings

CSV_MAP = {
    "fact_transaction": "output/powerbi_star/fact_transaction.csv",
    "fact_session": "output/powerbi_star/fact_session.csv",
    "dim_member": "output/powerbi_star/dim_member.csv",
    "forecast_revenue": "output/forecasts/forecast_revenue.csv",
    "session_volume": "output/forecasts/session_volume.csv",
    "member_segments": "output/forecasts/member_segments.csv",
    "member_loyalty": "output/forecasts/member_loyalty.csv",
    "anomalies": "output/forecasts/anomalies.csv",
    "peak_hours_by_hour": "output/forecasts/peak_hours_by_hour.csv",
    "peak_hours_by_day": "output/forecasts/peak_hours_by_day.csv",
    "stock_replenishment": "output/forecasts/stock_replenishment.csv",
}


@dataclass
class DataContext:
    tables: dict = field(default_factory=dict)
    summary: str = ""
    schemas: str = ""


def load_data(base_dir: str = ".") -> DataContext:
    ctx = DataContext()
    base = Path(base_dir)
    for key, rel_path in CSV_MAP.items():
        path = base / rel_path
        if path.exists():
            ctx.tables[key] = pd.read_csv(path)
        else:
            warnings.warn(f"CSV not found, skipping: {path}")
    ctx.schemas = _build_schemas(ctx.tables)
    ctx.summary = _build_summary(ctx.tables)
    return ctx


def _build_schemas(tables: dict) -> str:
    if not tables:
        return ""
    lines = ["Available tables and their columns:\n"]
    for key, df in tables.items():
        cols = ", ".join(f"{c} ({t})" for c, t in zip(df.columns, df.dtypes))
        lines.append(f"- {key}: {cols}")
    return "\n".join(lines)


def _build_summary(tables: dict) -> str:
    parts = []
    if "fact_transaction" in tables:
        df = tables["fact_transaction"].copy()
        income = df[df["type"] == "Income"]["amount"].sum()
        df["date"] = pd.to_datetime(df["date"])
        if len(df) > 0:
            date_range = f"{df['date'].min().date()} to {df['date'].max().date()}"
        else:
            date_range = "no data"
        parts.append(f"Total revenue: {income:,.2f} TND | Data range: {date_range}")
    if "dim_member" in tables:
        parts.append(f"Total members: {len(tables['dim_member'])}")
    if "member_loyalty" in tables:
        dist = tables["member_loyalty"]["loyalty_tier"].value_counts().to_dict()
        top5 = tables["member_loyalty"].nlargest(5, "total_tnd")[["username", "total_tnd"]].to_dict("records")
        parts.append(f"Loyalty tiers: {dist}")
        parts.append(f"Top 5 members by revenue: {top5}")
    if "anomalies" in tables:
        df = tables["anomalies"].copy()
        df["date"] = pd.to_datetime(df["date"])
        recent = df[df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        parts.append(f"Recent anomalies (last 7 days): {len(recent)}")
    return "\n".join(parts)


def recent_anomaly_count(ctx: DataContext) -> int:
    if "anomalies" not in ctx.tables:
        return 0
    df = ctx.tables["anomalies"].copy()
    df["date"] = pd.to_datetime(df["date"])
    return len(df[df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=7)])
