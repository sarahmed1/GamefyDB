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
    if "forecast_revenue" in tables:
        df = tables["forecast_revenue"]
        parts.append(_forecast_highlight(df, label="Revenue forecast", unit="TND"))
    if "session_volume" in tables:
        df = tables["session_volume"]
        parts.append(_forecast_highlight(df, label="Session volume forecast", unit="sessions"))
        parts.append("NOTE: fact_session has NO date column — use session_volume for trends over time.")
    if "fact_session" in tables:
        df = tables["fact_session"]
        avg_dur = df["duration_min"].mean() if "duration_min" in df.columns else 0
        types = df["session_type"].value_counts().to_dict() if "session_type" in df.columns else {}
        parts.append(f"Sessions (historical, no date column): {len(df)} total sessions, avg duration {avg_dur:.0f} min, types: {types}. Use for duration/type stats, NOT time-series charts.")
    if "anomalies" in tables:
        df = tables["anomalies"].copy()
        df["date"] = pd.to_datetime(df["date"])
        recent = df[df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        parts.append(f"Recent anomalies (last 7 days): {len(recent)}")
    return "\n".join(parts)


def _forecast_highlight(df: pd.DataFrame, label: str, unit: str) -> str:
    granularities = df["granularity"].unique().tolist() if "granularity" in df.columns else []
    bits = [f"{label} (future predictions only, {len(df)} rows, granularities={granularities}, columns: date, yhat, yhat_lower, yhat_upper)."]
    if "granularity" in df.columns and "yhat" in df.columns:
        weekly = df[df["granularity"] == "weekly"].sort_values("date").head(4)
        if len(weekly) > 0:
            vals = ", ".join(f"{row['date']}: {row['yhat']:.0f}" for _, row in weekly.iterrows())
            avg = weekly["yhat"].mean()
            bits.append(f"Next {len(weekly)} weeks ({unit}): {vals}. Avg ~{avg:.0f} {unit}/week.")
        monthly = df[df["granularity"] == "monthly"].sort_values("date").head(3)
        if len(monthly) > 0:
            vals = ", ".join(f"{row['date']}: {row['yhat']:.0f}" for _, row in monthly.iterrows())
            bits.append(f"Next {len(monthly)} months ({unit}): {vals}.")
    return " ".join(bits)


def recent_anomaly_count(ctx: DataContext) -> int:
    if "anomalies" not in ctx.tables:
        return 0
    df = ctx.tables["anomalies"].copy()
    df["date"] = pd.to_datetime(df["date"])
    return len(df[df["date"] >= pd.Timestamp.now() - pd.Timedelta(days=7)])
