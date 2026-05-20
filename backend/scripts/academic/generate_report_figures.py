"""Generate the three figures requested for the PFE report chapter 1 & 2:

    docs/images/scrum_process.png
    docs/images/scrum_roles.png
    docs/images/gantt.png
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NAVY = "#1f3a68"
TEAL = "#2a9d8f"
AMBER = "#e9c46a"
CORAL = "#e76f51"
SLATE = "#264653"
LIGHT = "#f4f1de"


# ----------------------------------------------------------------------
# 1. Scrum process diagram
# ----------------------------------------------------------------------
def make_scrum_process() -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    def box(x, y, w, h, label, color, fontsize=10, text_color="white"):
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.05,rounding_size=0.15",
            linewidth=1.2, edgecolor=SLATE, facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold", wrap=True)

    def arrow(x1, y1, x2, y2, style="->", curve=0.0, color=SLATE, lw=1.6):
        connector = f"arc3,rad={curve}"
        ar = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle=style, mutation_scale=18,
            linewidth=lw, color=color,
            connectionstyle=connector,
        )
        ax.add_patch(ar)

    # Boxes (Product Backlog -> Sprint Planning -> Sprint Backlog -> Sprint -> Increment)
    box(0.2, 2.4, 2.0, 1.2, "Product\nBacklog", NAVY)
    box(2.6, 2.4, 2.0, 1.2, "Sprint\nPlanning", TEAL)
    box(5.0, 2.4, 2.0, 1.2, "Sprint\nBacklog", NAVY)

    # Sprint box (large, dashed border)
    sprint = FancyBboxPatch(
        (7.4, 1.4), 3.0, 3.2,
        boxstyle="round,pad=0.05,rounding_size=0.2",
        linewidth=1.6, edgecolor=SLATE, facecolor=LIGHT, linestyle="--",
    )
    ax.add_patch(sprint)
    ax.text(8.9, 4.25, "Sprint\n(2–4 weeks)", ha="center", va="center",
            fontsize=11, color=SLATE, weight="bold")

    # Inner Daily Scrum cycle
    daily = FancyBboxPatch(
        (7.7, 1.7), 2.4, 1.4,
        boxstyle="round,pad=0.04,rounding_size=0.12",
        linewidth=1.2, edgecolor=SLATE, facecolor=AMBER,
    )
    ax.add_patch(daily)
    ax.text(8.9, 2.4, "Daily\nScrum", ha="center", va="center",
            fontsize=10, color=SLATE, weight="bold")

    # Increment
    box(0.2, 0.2, 2.0, 1.2, "Increment", CORAL)

    # Review and Retrospective
    box(2.6, 0.2, 2.4, 1.2, "Sprint\nReview", TEAL)
    box(5.4, 0.2, 2.4, 1.2, "Sprint\nRetrospective", TEAL)

    # Arrows
    arrow(2.2, 3.0, 2.6, 3.0)         # Backlog -> Planning
    arrow(4.6, 3.0, 5.0, 3.0)         # Planning -> Sprint Backlog
    arrow(7.0, 3.0, 7.4, 3.0)         # Sprint Backlog -> Sprint
    arrow(7.85, 1.7, 7.85, 0.95, curve=-0.0)   # Sprint -> Review
    arrow(5.4, 0.8, 5.0, 0.8)         # Retrospective -> Review (visually L->R bar)
    arrow(2.6, 0.8, 2.2, 0.8)         # Review -> Increment
    arrow(1.2, 1.4, 1.2, 2.4)         # Increment -> Product Backlog (feedback)

    # Title
    ax.text(6.0, 5.5, "Scrum Process", ha="center", va="center",
            fontsize=15, color=SLATE, weight="bold")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "scrum_process.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 2. Scrum roles diagram
# ----------------------------------------------------------------------
def make_scrum_roles() -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    roles = [
        {
            "title": "Product Owner",
            "color": NAVY,
            "x": 0.5,
            "desc": [
                "• Owns the product vision",
                "• Manages the product backlog",
                "• Prioritises user stories by",
                "   business value",
                "• Validates each increment",
                "   delivered by the team",
            ],
        },
        {
            "title": "Scrum Master",
            "color": TEAL,
            "x": 4.25,
            "desc": [
                "• Facilitates the Scrum process",
                "• Removes impediments blocking",
                "   the team",
                "• Coaches the team on agile",
                "   practices",
                "• Ensures ceremonies are",
                "   respected",
            ],
        },
        {
            "title": "Development Team",
            "color": CORAL,
            "x": 8.0,
            "desc": [
                "• Self-organised and",
                "   cross-functional",
                "• Delivers the sprint increment",
                "• Estimates and commits to",
                "   user stories",
                "• Collaborates daily during",
                "   the sprint",
            ],
        },
    ]

    box_w, box_h = 3.5, 5.5
    for role in roles:
        x = role["x"]
        y = 0.4
        # Header strip
        header = FancyBboxPatch(
            (x, y + box_h - 0.9), box_w, 0.9,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=1.2, edgecolor=SLATE, facecolor=role["color"],
        )
        ax.add_patch(header)
        ax.text(x + box_w / 2, y + box_h - 0.45, role["title"],
                ha="center", va="center",
                fontsize=14, color="white", weight="bold")

        # Body
        body = FancyBboxPatch(
            (x, y), box_w, box_h - 0.9,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=1.2, edgecolor=SLATE, facecolor=LIGHT,
        )
        ax.add_patch(body)

        # Description text
        for i, line in enumerate(role["desc"]):
            ax.text(x + 0.2, y + box_h - 1.4 - i * 0.45, line,
                    ha="left", va="center", fontsize=10, color=SLATE)

    ax.text(6.0, 6.5, "Scrum Roles", ha="center", va="center",
            fontsize=16, color=SLATE, weight="bold")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "scrum_roles.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 3. Gantt chart
# ----------------------------------------------------------------------
def make_gantt() -> None:
    sprints = [
        ("Sprint 0 — Preparation",          "2026-02-02", "2026-02-14", NAVY),
        ("Sprint 1 — Loading & Cleaning",   "2026-02-15", "2026-03-02", TEAL),
        ("Sprint 2 — Star Schema & Export", "2026-03-03", "2026-03-12", TEAL),
        ("Sprint 3 — Power BI Dashboards",  "2026-03-13", "2026-04-16", AMBER),
        ("Sprint 4 — ML & Analytics",       "2026-04-17", "2026-05-06", CORAL),
        ("Sprint 5 — Conversational Assistant", "2026-05-07", "2026-05-17", CORAL),
    ]

    fig, ax = plt.subplots(figsize=(12, 5))

    labels = []
    for i, (label, start, end, color) in enumerate(sprints):
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        duration = (end_dt - start_dt).days + 1
        ax.barh(i, duration, left=mdates.date2num(start_dt),
                color=color, edgecolor=SLATE, height=0.55)
        # Annotate duration at the right end of each bar
        mid = mdates.date2num(start_dt) + duration / 2
        ax.text(mid, i, f"{duration} d", ha="center", va="center",
                color="white", fontsize=9, weight="bold")
        labels.append(label)

    ax.set_yticks(range(len(sprints)))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()

    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(axis="x", labelsize=9, rotation=30)

    ax.set_title("Project Gantt chart", fontsize=14, color=SLATE,
                 weight="bold", pad=15)
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    fig.savefig(OUT_DIR / "gantt.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 4. Org chart of Gamefy Academy
# ----------------------------------------------------------------------
def make_org_chart() -> None:
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.5)
    ax.axis("off")

    def node(x, y, w, h, label, color, fontsize=11, text_color="white"):
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.05,rounding_size=0.15",
            linewidth=1.2, edgecolor=SLATE, facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold")

    def line(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color=SLATE, linewidth=1.4)

    # Top: Owner / Manager
    owner_y = 5.4
    node(6.5, owner_y, 3.4, 0.9, "Owner / Manager\n(Mr. Aymen Jadallah)", NAVY)

    # Two intermediate groupings: owner-side account and staff accounts
    branch_y = 3.6
    node(2.5, branch_y, 2.6, 0.8, "Owner-side\naccount", TEAL)
    node(9.5, branch_y, 2.6, 0.8, "Staff accounts\n(point-of-sale)", TEAL)

    # Connect Owner -> two branches via a small T-bar
    bar_y = 4.6
    line(6.5, owner_y - 0.45, 6.5, bar_y)        # owner down
    line(2.5, bar_y, 9.5, bar_y)                  # horizontal bar
    line(2.5, bar_y, 2.5, branch_y + 0.4)         # to left branch
    line(9.5, bar_y, 9.5, branch_y + 0.4)         # to right branch

    # Under owner-side: admin
    node(2.5, 1.6, 2.6, 0.8, "admin\n(reserved for the owner)",
         AMBER, fontsize=10, text_color=SLATE)
    line(2.5, branch_y - 0.4, 2.5, 2.0)

    # Under staff: five named cashiers + shared profile, in two rows
    staff = [
        ("taktek",  6.2, 1.95),
        ("yassine", 8.0, 1.95),
        ("youssef", 9.8, 1.95),
        ("monta",   11.6, 1.95),
        ("guds",    7.1, 0.9),
        ("cashier\n(shared)", 9.0, 0.9),
    ]
    # T-bar under "Staff accounts"
    line(9.5, branch_y - 0.4, 9.5, 2.7)
    line(6.2, 2.7, 11.6, 2.7)
    for name, x, y in staff:
        is_shared = name.startswith("cashier")
        color = AMBER if is_shared else CORAL
        tc = SLATE if is_shared else "white"
        node(x, y, 1.5, 0.65, name, color, fontsize=9, text_color=tc)
        # vertical drop from horizontal bar
        if y > 1.5:
            line(x, 2.7, x, y + 0.35)
        else:
            # second row: drop from the row-1 horizontal at y=1.55
            line(x, 2.7, x, y + 0.35)

    ax.text(6.5, 6.25, "Organisational chart — Gamefy Academy",
            ha="center", va="center", fontsize=14, color=SLATE, weight="bold")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "org_chart.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 5. GIMSI five-phase diagram
# ----------------------------------------------------------------------
def make_gimsi() -> None:
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 4)
    ax.axis("off")

    phases = [
        ("1. Preliminary\nStudy",       NAVY),
        ("2. Opportunity\nStudy",       TEAL),
        ("3. Detailed\nStudy",          AMBER),
        ("4. Implementation",           CORAL),
        ("5. Permanent\nImprovement",   SLATE),
    ]

    w, h = 2.2, 1.4
    gap = 0.25
    total = len(phases) * w + (len(phases) - 1) * gap
    x0 = (13 - total) / 2

    centers = []
    for i, (label, color) in enumerate(phases):
        x = x0 + i * (w + gap)
        y = 1.2
        text_color = "white" if color != AMBER else SLATE
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.05,rounding_size=0.18",
            linewidth=1.2, edgecolor=SLATE, facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=11, color=text_color, weight="bold")
        centers.append((x + w / 2, y + h / 2, x, y))

    # Arrows between consecutive phases
    for i in range(len(phases) - 1):
        x1 = centers[i][2] + w
        x2 = centers[i + 1][2]
        y = centers[i][1]
        ar = FancyArrowPatch(
            (x1 + 0.02, y), (x2 - 0.02, y),
            arrowstyle="->", mutation_scale=18, linewidth=1.6, color=SLATE,
        )
        ax.add_patch(ar)

    # Feedback loop from "Permanent Improvement" back to "Preliminary Study"
    x_start = centers[-1][2] + w / 2
    x_end = centers[0][2] + w / 2
    feedback = FancyArrowPatch(
        (x_start, centers[-1][3]),
        (x_end, centers[0][3]),
        arrowstyle="->", mutation_scale=18,
        linewidth=1.4, color=SLATE, linestyle="--",
        connectionstyle="arc3,rad=-0.35",
    )
    ax.add_patch(feedback)
    ax.text((x_start + x_end) / 2, 0.25, "feedback",
            ha="center", va="center", fontsize=9, color=SLATE, style="italic")

    ax.text(6.5, 3.5, "GIMSI — Main phases", ha="center", va="center",
            fontsize=14, color=SLATE, weight="bold")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "gimsi.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 6. Sprint 1 dataflow (ingest -> clean)
# ----------------------------------------------------------------------
def make_sprint1_flow() -> None:
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 4.5)
    ax.axis("off")

    def box(x, y, w, h, label, color, fontsize=10, text_color="white"):
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.05,rounding_size=0.12",
            linewidth=1.2, edgecolor=SLATE, facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold")

    def arrow(x1, y1, x2, y2):
        ar = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="->", mutation_scale=18, linewidth=1.6, color=SLATE,
        )
        ax.add_patch(ar)

    # Files (left column)
    files = [
        "Cash DATA\n01-09-2025.xls",
        "DATA session\nreports.xls",
        "Stock DATA\n01-09-2025.xls",
        "memeber DATA\n01-09-2025.xls",
    ]
    fx = 1.4
    for i, name in enumerate(files):
        y = 3.6 - i * 0.85
        box(fx, y, 2.1, 0.65, name, AMBER, fontsize=9, text_color=SLATE)
        arrow(fx + 1.1, y, 5.0 - 0.8, 2.05)

    # Ingestor box
    box(5.0, 2.05, 1.8, 1.0,
        "ingest_all()\nxlrd + strip\nartefacts", NAVY, fontsize=10)

    # Arrow to cleaner
    arrow(5.0 + 0.95, 2.05, 8.0 - 0.95, 2.05)

    # Cleaner box
    box(8.0, 2.05, 1.9, 1.0,
        "clean_all()\nparse types +\nextract terminal", TEAL, fontsize=10)

    # Output: dict of typed DataFrames
    arrow(8.0 + 1.0, 2.05, 11.0 - 1.05, 2.05)
    box(11.0, 2.05, 2.1, 1.2,
        "dict[str, DataFrame]\n(typed, artefact-free)\n→ Sprint 2",
        CORAL, fontsize=9)

    # Title
    ax.text(6.5, 4.25,
            "Sprint 1 — Data flow (Extract + Transform stages of the ETL chain)",
            ha="center", va="center", fontsize=12, color=SLATE, weight="bold")

    # Light annotations under each stage
    ax.text(5.0, 1.35, "Extract", ha="center", va="center",
            fontsize=10, color=SLATE, style="italic")
    ax.text(8.0, 1.35, "Transform", ha="center", va="center",
            fontsize=10, color=SLATE, style="italic")
    ax.text(11.0, 1.25, "(Load: Sprint 2)", ha="center", va="center",
            fontsize=9, color=SLATE, style="italic")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "sprint1_flow.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 7. ML workflow (Sprint 4)
# ----------------------------------------------------------------------
def make_ml_workflow() -> None:
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5.5)
    ax.axis("off")

    def box(x, y, w, h, label, color, fontsize=10, text_color="white"):
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.05,rounding_size=0.12",
            linewidth=1.2, edgecolor=SLATE, facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold")

    def arrow(x1, y1, x2, y2, lw=1.5):
        ar = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="->", mutation_scale=16, linewidth=lw, color=SLATE,
        )
        ax.add_patch(ar)

    # Input: star schema (left)
    box(1.5, 4.0, 2.5, 0.9,
        "Star schema\nfact_transaction,\ndim_member",
        NAVY, fontsize=10)

    # Three ML modules (middle column)
    box(6.5, 4.5, 2.6, 0.85, "forecaster.py", TEAL, fontsize=11)
    box(6.5, 3.0, 2.6, 0.85, "segmenter.py", AMBER, fontsize=11, text_color=SLATE)
    box(6.5, 1.5, 2.6, 0.85, "anomaly_detector.py", CORAL, fontsize=11)

    # Output: CSVs (right column)
    csvs = [
        ("forecast_revenue.csv",        4.85),
        ("forecast_members.csv",        4.40),
        ("session_volume.csv",          3.95),
        ("peak_hours_by_hour.csv",      3.50),
        ("peak_hours_by_day.csv",       3.05),
        ("stock_replenishment.csv",     2.60),
        ("member_segments.csv",         2.15),
        ("member_loyalty.csv",          1.70),
        ("anomalies.csv",               1.25),
    ]
    for name, y in csvs:
        box(10.9, y, 2.0, 0.32, name, SLATE, fontsize=8)

    # Power BI consumer (far right)
    box(10.9, 0.55, 2.0, 0.45, "Power BI report",
        NAVY, fontsize=10)

    # Arrows: star schema -> three modules
    arrow(2.75, 4.0, 5.2, 4.5)
    arrow(2.75, 4.0, 5.2, 3.0)
    arrow(2.75, 4.0, 5.2, 1.5)

    # Arrows: forecaster.py -> first 6 CSVs
    for _, y in csvs[:6]:
        arrow(7.8, 4.5, 9.9, y)

    # Arrows: segmenter.py -> member_segments + member_loyalty
    arrow(7.8, 3.0, 9.9, csvs[6][1])
    arrow(7.8, 3.0, 9.9, csvs[7][1])

    # Arrows: anomaly_detector.py -> anomalies.csv
    arrow(7.8, 1.5, 9.9, csvs[8][1])

    # All CSVs -> Power BI
    for _, y in csvs:
        ax.plot([11.0, 11.0], [y - 0.16, 0.78], color=SLATE,
                linewidth=0.4, alpha=0.3)

    ax.text(6.5, 5.15, "Sprint 4 — analytics workflow",
            ha="center", va="center",
            fontsize=14, color=SLATE, weight="bold")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "ml_workflow.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 8. Weekday grouping illustration (anomaly detection)
# ----------------------------------------------------------------------
def make_weekday_grouping() -> None:
    import numpy as np
    rng = np.random.default_rng(7)
    weekday_colors = {
        0: "#7f8c8d",  # Mon
        1: "#7f8c8d",
        2: "#7f8c8d",
        3: "#7f8c8d",
        4: "#7f8c8d",
        5: CORAL,      # Sat
        6: TEAL,       # Sun
    }
    weekday_means = [55, 60, 58, 62, 70, 130, 105]
    n_weeks = 5
    days = []
    values = []
    colors = []
    for w in range(n_weeks):
        for d in range(7):
            base = weekday_means[d]
            noise = rng.normal(0, base * 0.07)
            days.append(w * 7 + d)
            values.append(max(10, base + noise))
            colors.append(weekday_colors[d])

    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.bar(days, values, color=colors, edgecolor=SLATE, linewidth=0.5)

    # Highlight Saturdays and Sundays specifically with annotations
    ax.text(5, 145, "Saturday: only compared against\nthe four other Saturdays",
            ha="center", fontsize=10, color=CORAL, weight="bold")
    ax.annotate("", xy=(5, 132), xytext=(5, 142),
                arrowprops=dict(arrowstyle="->", color=CORAL, linewidth=1.5))
    ax.text(20, 105, "Sundays form\ntheir own group",
            ha="center", fontsize=10, color=TEAL, weight="bold")
    ax.annotate("", xy=(20, 90), xytext=(20, 100),
                arrowprops=dict(arrowstyle="->", color=TEAL, linewidth=1.5))

    # Custom legend
    from matplotlib.patches import Patch
    legend_items = [
        Patch(facecolor="#7f8c8d", edgecolor=SLATE, label="Weekdays (Mon-Fri)"),
        Patch(facecolor=CORAL, edgecolor=SLATE, label="Saturdays"),
        Patch(facecolor=TEAL, edgecolor=SLATE, label="Sundays"),
    ]
    ax.legend(handles=legend_items, loc="upper left", fontsize=9, frameon=True)

    # X axis: weeks
    ax.set_xticks([w * 7 + 3 for w in range(n_weeks)])
    ax.set_xticklabels([f"Week {w + 1}" for w in range(n_weeks)], fontsize=10)
    ax.set_ylabel("Daily revenue (TND, illustrative)", fontsize=10, color=SLATE)
    ax.set_title("Day-of-week grouping — anomaly detection baseline",
                 fontsize=13, color=SLATE, weight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    fig.savefig(OUT_DIR / "weekday_grouping.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
# 9. Chatbot architecture (Sprint 5)
# ----------------------------------------------------------------------
def make_chatbot_arch() -> None:
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.5)
    ax.axis("off")

    def box(x, y, w, h, label, color, fontsize=10, text_color="white"):
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.05,rounding_size=0.12",
            linewidth=1.2, edgecolor=SLATE, facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold")

    def arrow(x1, y1, x2, y2, label=None, lw=1.5):
        ar = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="->", mutation_scale=16, linewidth=lw, color=SLATE,
        )
        ax.add_patch(ar)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my + 0.18, label, ha="center", va="center",
                    fontsize=8, color=SLATE, style="italic")

    # User (left)
    box(1.3, 3.5, 1.7, 0.9, "Owner\n(EN / FR / AR)", NAVY, fontsize=10)

    # Streamlit app
    box(4.3, 3.5, 2.0, 1.2, "Streamlit\napp.py", TEAL, fontsize=11)

    # Voice component (top)
    box(4.3, 5.4, 2.0, 0.7,
        "voice_component\n(Web Speech API)", AMBER,
        fontsize=9, text_color=SLATE)

    # DataContext (bottom-left)
    box(4.3, 1.3, 2.0, 0.9,
        "DataContext\n(11 CSV tables)", CORAL, fontsize=9)

    # Agent (middle)
    box(7.6, 3.5, 2.0, 1.2,
        "agent.py\nprompt + parse", TEAL, fontsize=11)

    # Chart generator
    box(7.6, 1.3, 2.0, 0.9,
        "chart_generator\n(Plotly Express)", CORAL, fontsize=9)

    # Gemini (right)
    box(10.7, 3.5, 1.8, 1.2,
        "Gemini API\n(gemini-3-flash)", NAVY, fontsize=11)

    # Arrows
    arrow(2.15, 3.5, 3.3, 3.5, "question")
    arrow(5.3, 3.5, 6.6, 3.5, "ask()")
    arrow(8.6, 3.5, 9.8, 3.5, "system prompt\n+ history")
    arrow(9.8, 3.2, 8.6, 3.2, "answer\n+ chart_spec")
    arrow(6.6, 3.2, 5.3, 3.2, "parsed reply")
    arrow(3.3, 3.2, 2.15, 3.2, "answer + chart")

    # Voice -> Streamlit
    arrow(4.3, 5.0, 4.3, 4.15, "transcript")

    # DataContext -> agent (schema/summary spliced into prompt)
    arrow(5.3, 1.7, 6.6, 3.0, "schema +\nsummary")

    # Agent -> chart_generator
    arrow(7.6, 2.85, 7.6, 1.8, "chart_spec")

    # Chart -> Streamlit (back up to the app)
    arrow(7.6, 1.8, 4.6, 2.85, "Plotly fig")

    ax.text(6.5, 6.15,
            "Sprint 5 — Conversational assistant: runtime architecture",
            ha="center", va="center",
            fontsize=13, color=SLATE, weight="bold")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "chatbot_arch.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    make_scrum_process()
    make_scrum_roles()
    make_gantt()
    make_org_chart()
    make_gimsi()
    make_sprint1_flow()
    make_ml_workflow()
    make_weekday_grouping()
    make_chatbot_arch()
    print(f"Wrote 9 figures to {OUT_DIR}")
