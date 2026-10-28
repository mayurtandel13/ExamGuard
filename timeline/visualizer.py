"""
Timeline Visualizer Module (Phase 8)
Generates Matplotlib visualization charts for post-exam behavioral activity over time,
including risk progression timelines, multi-modal signal breakdowns, and risk level pie charts.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np


class TimelineVisualizer:
    """
    Modular Behavioral Timeline Chart Visualizer utilizing Matplotlib.
    """

    @staticmethod
    def _extract_dfs(timeline_or_df, df_events=None):
        """Helper to accept either a BehavioralTimeline instance or Pandas DataFrames."""
        if hasattr(timeline_or_df, "get_risk_history_df") and hasattr(timeline_or_df, "get_events_df"):
            df_risk = timeline_or_df.get_risk_history_df()
            events_df = timeline_or_df.get_events_df()
        else:
            df_risk = timeline_or_df if isinstance(timeline_or_df, pd.DataFrame) else pd.DataFrame()
            events_df = df_events if isinstance(df_events, pd.DataFrame) else pd.DataFrame()

        return df_risk, events_df

    @staticmethod
    def _apply_theme_to_ax(ax, theme="dark"):
        """Applies consistent dark/light theme colors to Matplotlib axes, ticks, and spines."""
        is_dark = (theme == "dark")
        bg_color = "#111A2E" if is_dark else "#FFFFFF"
        text_color = "#E6EAF2" if is_dark else "#0F172A"
        grid_color = "#24304A" if is_dark else "#E1E6F0"
        spine_color = "#24304A" if is_dark else "#CBD5E1"
        tick_color = "#9AA6BD" if is_dark else "#5B6780"

        ax.set_facecolor(bg_color)
        ax.tick_params(colors=tick_color, which="both")
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        for spine in ax.spines.values():
            spine.set_color(spine_color)
        ax.grid(True, linestyle="--", alpha=0.4, color=grid_color)

    @staticmethod
    def _style_legend(leg, theme="dark"):
        if leg:
            is_dark = (theme == "dark")
            leg_bg = "#17223B" if is_dark else "#F0F3FA"
            leg_border = "#24304A" if is_dark else "#CBD5E1"
            leg_text = "#E6EAF2" if is_dark else "#0F172A"
            leg.get_frame().set_facecolor(leg_bg)
            leg.get_frame().set_edgecolor(leg_border)
            for text in leg.get_texts():
                text.set_color(leg_text)

    @staticmethod
    def generate_timeline_chart(timeline_or_df, df_events=None, figsize=(10, 4), theme="dark"):
        """
        Generates continuous Cheating Probability timeline chart with risk zone shading and event annotations.
        """
        df_risk, events_df = TimelineVisualizer._extract_dfs(timeline_or_df, df_events)

        fig, ax = plt.subplots(figsize=figsize)
        is_dark = (theme == "dark")
        fig.patch.set_facecolor("#111A2E" if is_dark else "#FFFFFF")

        if df_risk.empty:
            ax.set_title("Behavioral Timeline Progression (No Data Recorded)")
            ax.set_xlabel("Elapsed Time (seconds)")
            ax.set_ylabel("Cheating Probability Score")
            ax.set_ylim(0, 1.0)
            TimelineVisualizer._apply_theme_to_ax(ax, theme)
            return fig

        x_time = df_risk.get("rel_time_sec", pd.Series(range(len(df_risk))))
        y_prob = df_risk.get("cheating_probability", df_risk.get("cheating_score", pd.Series([0.0] * len(df_risk))))

        # Plot continuous probability curve
        curve_color = "#818CF8" if is_dark else "#312E81"
        ax.plot(x_time, y_prob, color=curve_color, linewidth=2.5, label="Cheating Probability")

        # Color-coded Risk Zone background shading
        ax.axhspan(0.00, 0.35, color="#10b981", alpha=0.15, label="LOW Risk (< 0.35)")
        ax.axhspan(0.35, 0.70, color="#f59e0b", alpha=0.15, label="MEDIUM Risk (0.35 - 0.70)")
        ax.axhspan(0.70, 1.00, color="#ef4444", alpha=0.15, label="HIGH Risk (>= 0.70)")

        # Risk Threshold lines
        ax.axhline(0.35, color="#10b981", linestyle="--", linewidth=1.0, alpha=0.7)
        ax.axhline(0.70, color="#ef4444", linestyle="--", linewidth=1.0, alpha=0.7)

        # Plot Event Markers
        if events_df is not None and not events_df.empty:
            for _, evt in events_df.iterrows():
                t_evt = evt.get("rel_time_sec", 0.0)
                sev = str(evt.get("severity", "LOW")).upper()

                color_map = {"LOW": "#3b82f6", "MEDIUM": "#f59e0b", "HIGH": "#dc2626", "CRITICAL": "#991b1b"}
                m_color = color_map.get(sev, "#6b7280")

                # Interpolate y score at event timestamp
                y_val = float(np.interp(t_evt, x_time, y_prob)) if not x_time.empty else 0.5

                ax.scatter(t_evt, y_val, color=m_color, s=70, zorder=5, edgecolors="white" if is_dark else "black", linewidth=1.2)
                ax.axvline(x=t_evt, color=m_color, linestyle=":", alpha=0.4)

        ax.set_title("Behavioral Risk Progression & Event Timeline", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Elapsed Time (seconds)", fontsize=10)
        ax.set_ylabel("Cheating Probability Score", fontsize=10)
        ax.set_ylim(0.0, 1.05)
        TimelineVisualizer._apply_theme_to_ax(ax, theme)
        leg = ax.legend(loc="upper left", fontsize=8)
        TimelineVisualizer._style_legend(leg, theme)
        fig.tight_layout()

        return fig

    @staticmethod
    def generate_signal_breakdown_chart(timeline_or_df, figsize=(10, 3), theme="dark"):
        """
        Generates multi-modal signal breakdown line plot over time.
        """
        df_risk, _ = TimelineVisualizer._extract_dfs(timeline_or_df)

        fig, ax = plt.subplots(figsize=figsize)
        is_dark = (theme == "dark")
        fig.patch.set_facecolor("#111A2E" if is_dark else "#FFFFFF")

        if df_risk.empty:
            ax.set_title("Multi-Modal Signal Breakdown (No Data)")
            TimelineVisualizer._apply_theme_to_ax(ax, theme)
            return fig

        x_time = df_risk.get("rel_time_sec", pd.Series(range(len(df_risk))))

        att_p = df_risk.get("attention_penalty", pd.Series([0.0] * len(df_risk)))
        head_p = df_risk.get("head_penalty", pd.Series([0.0] * len(df_risk)))
        kb_p = df_risk.get("keypress_penalty", pd.Series([0.0] * len(df_risk)))
        obj_f = df_risk.get("object_flag", pd.Series([0.0] * len(df_risk)))

        ax.plot(x_time, att_p, color="#38BDF8", linewidth=1.8, label="Attention Penalty (1 - Att)")
        ax.plot(x_time, head_p, color="#A78BFA", linewidth=1.8, label="Head Pose Penalty")
        ax.plot(x_time, kb_p, color="#F472B6", linewidth=1.8, label="Keypress Penalty")
        ax.plot(x_time, obj_f, color="#EF4444", linewidth=1.8, linestyle="--", label="Object Flag")

        ax.set_title("Multi-Modal Behavioral Signals Breakdown", fontsize=11, fontweight="bold")
        ax.set_xlabel("Elapsed Time (seconds)", fontsize=9)
        ax.set_ylabel("Penalty Signal (0 - 1)", fontsize=9)
        ax.set_ylim(-0.05, 1.05)
        TimelineVisualizer._apply_theme_to_ax(ax, theme)
        leg = ax.legend(loc="upper left", fontsize=8)
        TimelineVisualizer._style_legend(leg, theme)
        fig.tight_layout()

        return fig

    @staticmethod
    def generate_pie_chart(risk_dist, figsize=(4, 3), theme="dark"):
        """
        Generates risk level breakdown pie chart figure.
        """
        fig, ax = plt.subplots(figsize=figsize)
        is_dark = (theme == "dark")
        fig.patch.set_facecolor("#111A2E" if is_dark else "#FFFFFF")
        ax.set_facecolor("#111A2E" if is_dark else "#FFFFFF")

        labels = []
        sizes = []
        colors = []
        color_map = {"LOW": "#10b981", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}

        for k in ["LOW", "MEDIUM", "HIGH"]:
            v = risk_dist.get(k, 0.0)
            if v > 0:
                labels.append(f"{k} ({v:.1f}%)")
                sizes.append(v)
                colors.append(color_map[k])

        if not sizes:
            labels = ["LOW (100%)"]
            sizes = [100.0]
            colors = [color_map["LOW"]]

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            textprops={"fontsize": 8, "color": "#E6EAF2" if is_dark else "#0F172A"},
            wedgeprops={"edgecolor": "#111A2E" if is_dark else "#FFFFFF", "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_color("white")
            at.set_weight("bold")

        ax.set_title("Risk Level Distribution", fontsize=10, fontweight="bold", color="#E6EAF2" if is_dark else "#0F172A")
        fig.tight_layout()

        return fig

    @staticmethod
    def generate_full_dashboard(timeline_instance, figsize=(12, 7), theme="dark"):
        """
        Generates a 3-panel Matplotlib dashboard figure combining timeline, signal breakdown, and pie chart.
        """
        df_risk = timeline_instance.get_risk_history_df()
        events_df = timeline_instance.get_events_df()
        summary = timeline_instance.get_session_summary()
        is_dark = (theme == "dark")

        fig = plt.figure(figsize=figsize, layout="constrained")
        fig.patch.set_facecolor("#111A2E" if is_dark else "#FFFFFF")
        gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], width_ratios=[2.0, 1.0])

        # Panel 1: Top Main Timeline Chart
        ax1 = fig.add_subplot(gs[0, :])
        x_time = df_risk.get("rel_time_sec", pd.Series([0.0]))
        y_prob = df_risk.get("cheating_probability", pd.Series([0.0]))

        curve_color = "#818CF8" if is_dark else "#312E81"
        ax1.plot(x_time, y_prob, color=curve_color, linewidth=2.2, label="Cheating Probability")
        ax1.axhspan(0.00, 0.35, color="#10b981", alpha=0.15, label="LOW (< 0.35)")
        ax1.axhspan(0.35, 0.70, color="#f59e0b", alpha=0.15, label="MEDIUM (0.35 - 0.70)")
        ax1.axhspan(0.70, 1.00, color="#ef4444", alpha=0.15, label="HIGH (>= 0.70)")
        ax1.axhline(0.35, color="#10b981", linestyle="--", alpha=0.6)
        ax1.axhline(0.70, color="#ef4444", linestyle="--", alpha=0.6)

        if not events_df.empty:
            for _, evt in events_df.iterrows():
                t_evt = evt.get("rel_time_sec", 0.0)
                sev = str(evt.get("severity", "LOW")).upper()
                c_map = {"LOW": "#3b82f6", "MEDIUM": "#f59e0b", "HIGH": "#dc2626", "CRITICAL": "#991b1b"}
                y_v = float(np.interp(t_evt, x_time, y_prob)) if not x_time.empty else 0.5
                ax1.scatter(t_evt, y_v, color=c_map.get(sev, "#6b7280"), s=60, zorder=5, edgecolors="white" if is_dark else "black")

        ax1.set_title("Behavioral Risk Score Timeline", fontsize=11, fontweight="bold")
        ax1.set_xlabel("Elapsed Time (s)", fontsize=9)
        ax1.set_ylabel("Cheating Probability", fontsize=9)
        ax1.set_ylim(0.0, 1.05)
        TimelineVisualizer._apply_theme_to_ax(ax1, theme)
        leg1 = ax1.legend(loc="upper left", fontsize=8)
        TimelineVisualizer._style_legend(leg1, theme)

        # Panel 2: Bottom Left Signal Breakdown
        ax2 = fig.add_subplot(gs[1, 0])
        att_p = df_risk.get("attention_penalty", pd.Series([0.0]))
        head_p = df_risk.get("head_penalty", pd.Series([0.0]))
        kb_p = df_risk.get("keypress_penalty", pd.Series([0.0]))
        obj_f = df_risk.get("object_flag", pd.Series([0.0]))

        ax2.plot(x_time, att_p, color="#38BDF8", label="Attention Penalty")
        ax2.plot(x_time, head_p, color="#A78BFA", label="Head Pose Penalty")
        ax2.plot(x_time, kb_p, color="#F472B6", label="Keypress Penalty")
        ax2.plot(x_time, obj_f, color="#EF4444", linestyle="--", label="Object Flag")

        ax2.set_title("Multi-Modal Signal Penalties", fontsize=10, fontweight="bold")
        ax2.set_xlabel("Elapsed Time (s)", fontsize=8)
        ax2.set_ylabel("Signal Penalty", fontsize=8)
        ax2.set_ylim(-0.05, 1.05)
        TimelineVisualizer._apply_theme_to_ax(ax2, theme)
        leg2 = ax2.legend(loc="upper left", fontsize=7)
        TimelineVisualizer._style_legend(leg2, theme)

        # Panel 3: Bottom Right Pie Chart
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.set_facecolor("#111A2E" if is_dark else "#FFFFFF")
        risk_dist = summary.get("risk_distribution", {"LOW": 100.0, "MEDIUM": 0.0, "HIGH": 0.0})
        labels = [f"{k}\n{v:.1f}%" for k, v in risk_dist.items() if v > 0]
        sizes = [v for k, v in risk_dist.items() if v > 0]
        colors = [{"LOW": "#10b981", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}[k] for k, v in risk_dist.items() if v > 0]

        if not sizes:
            labels = ["LOW\n100%"]
            sizes = [100.0]
            colors = ["#10b981"]

        ax3.pie(
            sizes,
            labels=labels,
            colors=colors,
            startangle=140,
            textprops={"fontsize": 8, "color": "#E6EAF2" if is_dark else "#0F172A"},
            wedgeprops={"edgecolor": "#111A2E" if is_dark else "#FFFFFF", "linewidth": 1.5},
        )
        ax3.set_title("Risk Level Distribution", fontsize=10, fontweight="bold", color="#E6EAF2" if is_dark else "#0F172A")

        return fig

        return fig

    @staticmethod
    def save_visualization(fig, filepath):
        """Saves Matplotlib figure to image file."""
        fig.savefig(filepath, bbox_inches="tight", dpi=150)
        plt.close(fig)
        print(f"[TimelineVisualizer] Figure saved to '{filepath}'")
