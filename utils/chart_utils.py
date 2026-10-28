"""
Chart Utilities for generating Matplotlib plots for Post-Exam Behavioral Timeline Analysis
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


def generate_timeline_chart(df_timeseries, df_events):
    """
    Generates Matplotlib timeline figure showing Cheating Probability Score over time.
    """
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=100)
    fig.patch.set_facecolor("#0E1117")
    ax.set_facecolor("#161B22")

    if df_timeseries.empty:
        ax.text(0.5, 0.5, "No Session Data Available", color="white", ha="center", va="center")
        return fig

    t = df_timeseries["rel_time_sec"]
    score = df_timeseries["cheating_score"] * 100.0

    # Plot score line
    ax.plot(t, score, color="#58A6FF", linewidth=2.5, label="Cheating Probability Score (%)")

    # Risk Level Background Zones
    ax.axhspan(0, 35, color="#238636", alpha=0.25, label="Low Risk (0-35%)")
    ax.axhspan(35, 70, color="#D29922", alpha=0.25, label="Medium Risk (35-70%)")
    ax.axhspan(70, 100, color="#DA3633", alpha=0.25, label="High Risk (70-100%)")

    # Mark Events on Timeline
    if not df_events.empty:
        for idx, row in df_events.iterrows():
            evt_t = row["rel_time_sec"]
            severity = row.get("severity", "MEDIUM")
            marker_color = "#FF4D4D" if severity == "HIGH" else "#FFA500"
            ax.axvline(x=evt_t, color=marker_color, linestyle="--", alpha=0.6)

    ax.set_title("Post-Exam Behavioral Timeline & Risk Progression", color="#FFFFFF", fontsize=13, pad=12, fontweight="bold")
    ax.set_xlabel("Session Time (seconds)", color="#8B949E", fontsize=10)
    ax.set_ylabel("Cheating Score (%)", color="#8B949E", fontsize=10)

    ax.set_ylim(0, 105)
    ax.set_xlim(0, max(10, t.max() if not t.empty else 10))

    ax.tick_params(colors="#8B949E", which="both")
    ax.grid(True, color="#30363D", linestyle=":", alpha=0.6)

    # Custom Legend
    legend = ax.legend(facecolor="#21262D", edgecolor="#30363D", labelcolor="#C9D1D9", loc="upper left", fontsize=8.5)

    plt.tight_layout()
    return fig


def generate_pie_chart(risk_dist):
    """
    Generates pie chart showing risk level distribution percentage.
    """
    fig, ax = plt.subplots(figsize=(4.5, 3.5), dpi=100)
    fig.patch.set_facecolor("#0E1117")
    ax.set_facecolor("#0E1117")

    labels = ["Low", "Medium", "High"]
    values = [risk_dist.get("LOW", 0.0), risk_dist.get("MEDIUM", 0.0), risk_dist.get("HIGH", 0.0)]
    colors = ["#238636", "#D29922", "#DA3633"]

    # Filter out 0 values for clean plot
    non_zero = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not non_zero:
        ax.text(0.5, 0.5, "No Data", color="white", ha="center", va="center")
        return fig

    p_labels, p_vals, p_colors = zip(*non_zero)

    wedges, texts, autotexts = ax.pie(
        p_vals,
        labels=p_labels,
        autopct="%1.1f%%",
        startangle=140,
        colors=p_colors,
        textprops={"color": "#FFFFFF", "fontsize": 9},
        wedgeprops={"edgecolor": "#0E1117", "linewidth": 1.5},
    )

    for at in autotexts:
        at.set_color("#FFFFFF")
        at.set_weight("bold")

    ax.set_title("Risk Level Breakdown", color="#FFFFFF", fontsize=11, pad=8, fontweight="bold")
    plt.tight_layout()
    return fig
