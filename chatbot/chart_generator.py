import sys
import plotly.express as px
import pandas as pd


_DARK = dict(paper_bgcolor="#0f172a", plot_bgcolor="#1e293b", font_color="#e2e8f0")


def make_chart(chart_spec: dict, tables: dict):
    try:
        source = chart_spec.get("source")
        if not source or source not in tables:
            return None

        df = tables[source].copy()

        filter_expr = chart_spec.get("filter", "")
        if filter_expr:
            df = df.query(filter_expr)

        x = chart_spec.get("x")
        y = chart_spec.get("y")
        title = chart_spec.get("title", "")
        chart_type = chart_spec.get("type", "bar")

        if not x or not y:
            return None
        if x not in df.columns or y not in df.columns:
            return None

        # Group + count if y column is non-numeric
        if not pd.api.types.is_numeric_dtype(df[y]):
            df = df.groupby(x).size().reset_index(name=y)

        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, title=title)
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=title)
        else:
            fig = px.bar(df, x=x, y=y, title=title)

        fig.update_layout(**_DARK)
        return fig

    except Exception as e:
        print(f"Chart error: {e}", file=sys.stderr)
        return None
