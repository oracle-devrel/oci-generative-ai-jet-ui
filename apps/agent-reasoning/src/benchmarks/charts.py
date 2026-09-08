"""
Benchmark Chart Generator - Publication Quality

Generates beautiful dark-theme PNG charts from benchmark results.
Designed for README embeds and documentation.
Requires matplotlib: pip install matplotlib
"""

import os
from datetime import datetime
from typing import Dict, List

CHARTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "benchmarks",
    "charts",
)

# ── Visual Design System ──────────────────────────────────────────────────────

# Dark theme palette (GitHub-dark inspired)
BG_COLOR = "#0d1117"
SURFACE_COLOR = "#161b22"
BORDER_COLOR = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_MUTED = "#484f58"
GRID_COLOR = "#21262d"
ACCENT_GLOW = "#58a6ff"

# Strategy colors - vibrant on dark backgrounds
STRATEGY_COLORS = {
    "standard": "#8b949e",  # Neutral gray
    "cot": "#58a6ff",  # Blue
    "tot": "#bc8cff",  # Purple
    "react": "#f778ba",  # Pink
    "recursive": "#56d364",  # Green
    "reflection": "#3fb950",  # Emerald
    "consistency": "#d29922",  # Amber
    "decomposed": "#f85149",  # Red
    "least_to_most": "#79c0ff",  # Sky
    "refinement": "#e3b341",  # Gold
    "complex_refinement": "#a371f7",  # Violet
}

# Friendly display names
STRATEGY_LABELS = {
    "standard": "Standard",
    "cot": "Chain of Thought",
    "tot": "Tree of Thoughts",
    "react": "ReAct",
    "recursive": "Recursive LM",
    "reflection": "Self-Reflection",
    "consistency": "Self-Consistency",
    "decomposed": "Decomposed",
    "least_to_most": "Least-to-Most",
    "refinement": "Refinement Loop",
    "complex_refinement": "Complex Pipeline",
}


def _apply_dark_theme():
    """Configure matplotlib with a polished dark theme."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            # Figure
            "figure.facecolor": BG_COLOR,
            "figure.edgecolor": BG_COLOR,
            "figure.dpi": 200,
            # Axes
            "axes.facecolor": SURFACE_COLOR,
            "axes.edgecolor": BORDER_COLOR,
            "axes.labelcolor": TEXT_PRIMARY,
            "axes.titlecolor": TEXT_PRIMARY,
            "axes.grid": True,
            "axes.grid.which": "major",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            # Grid
            "grid.color": GRID_COLOR,
            "grid.linewidth": 0.6,
            "grid.alpha": 0.5,
            # Text
            "text.color": TEXT_PRIMARY,
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 10,
            # Ticks
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            # Legend
            "legend.facecolor": SURFACE_COLOR,
            "legend.edgecolor": BORDER_COLOR,
            "legend.fontsize": 8,
            "legend.labelcolor": TEXT_PRIMARY,
            # Save
            "savefig.facecolor": BG_COLOR,
            "savefig.edgecolor": BG_COLOR,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.3,
        }
    )

    return plt


def _get_color(strategy: str) -> str:
    return STRATEGY_COLORS.get(strategy, "#8b949e")


def _get_label(strategy: str) -> str:
    return STRATEGY_LABELS.get(strategy, strategy.title())


def _add_watermark(fig, text="Agent Reasoning Benchmark"):
    """Add subtle branding watermark."""
    fig.text(
        0.99,
        0.01,
        text,
        fontsize=7,
        color=TEXT_MUTED,
        ha="right",
        va="bottom",
        alpha=0.6,
        fontstyle="italic",
    )


def _format_ms(val: float) -> str:
    if val >= 1000:
        return f"{val / 1000:.1f}s"
    return f"{val:.0f}ms"


def _draw_gradient_bar(ax, x, height, width, color, alpha=0.9):
    """Draw a bar with subtle gradient effect using layered rectangles."""
    import matplotlib.patches as mpatches
    from matplotlib.colors import to_rgba

    base = to_rgba(color, alpha)
    highlight = to_rgba(color, min(alpha + 0.1, 1.0))

    # Main bar
    bar = mpatches.FancyBboxPatch(
        (x - width / 2, 0),
        width,
        height,
        boxstyle=mpatches.BoxStyle.Round(pad=0, rounding_size=width * 0.15),
        facecolor=base,
        edgecolor="none",
        zorder=3,
    )
    ax.add_patch(bar)

    # Highlight strip on left edge
    strip_w = width * 0.08
    strip = mpatches.FancyBboxPatch(
        (x - width / 2, 0),
        strip_w,
        height,
        boxstyle=mpatches.BoxStyle.Round(pad=0, rounding_size=strip_w * 0.5),
        facecolor=highlight,
        edgecolor="none",
        zorder=4,
    )
    ax.add_patch(strip)


def ensure_charts_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


# ── Chart Generators ──────────────────────────────────────────────────────────


def generate_agent_benchmark_charts(
    results: List[Dict],
    model: str = "",
    output_dir: str = None,
) -> List[str]:
    """
    Generate publication-quality PNG charts from benchmark results.

    Args:
        results: List of dicts with keys:
            task_name, strategy, total_ms, ttft_ms, tps, token_count, success
        model: Model name for titles
        output_dir: Override output directory

    Returns:
        List of paths to generated PNG files
    """
    try:
        plt = _apply_dark_theme()
        import matplotlib.patches as mpatches
        import matplotlib.ticker as ticker
        from matplotlib.colors import to_rgba
    except ImportError:
        print("matplotlib not installed. Run: pip install matplotlib")
        return []

    save_dir = output_dir or CHARTS_DIR
    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    successful = [r for r in results if r.get("success", True)]
    if not successful:
        return []

    generated = []
    model_label = model or "Unknown Model"

    # ── Chart 1: Latency by Strategy ──────────────────────────────────────

    fig, ax = plt.subplots(figsize=(14, 6))

    strategies = [r.get("strategy", "?") for r in successful]
    latencies = [r.get("total_ms", 0) for r in successful]
    task_names = [r.get("task_name", "?") for r in successful]
    bar_colors = [_get_color(s) for s in strategies]

    x_pos = range(len(successful))
    bar_width = 0.65

    # Draw gradient bars
    for i, (lat, color) in enumerate(zip(latencies, bar_colors)):
        _draw_gradient_bar(ax, i, lat, bar_width, color)

    # Value labels above bars
    for i, val in enumerate(latencies):
        ax.text(
            i,
            val + max(latencies) * 0.02,
            _format_ms(val),
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
            color=TEXT_PRIMARY,
        )

    ax.set_xlim(-0.5, len(successful) - 0.5)
    ax.set_ylim(0, max(latencies) * 1.15)
    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(
        [f"{t[:18]}\n{_get_label(s)}" for t, s in zip(task_names, strategies)],
        rotation=0,
        ha="center",
        fontsize=7.5,
    )
    ax.set_ylabel("Total Latency", fontsize=11, fontweight="bold")
    ax.set_title(
        "Response Latency by Strategy",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.text(
        0.5,
        1.02,
        model_label,
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color=TEXT_SECONDARY,
    )
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_ms(x)))

    _add_watermark(fig)
    plt.tight_layout()
    path = os.path.join(save_dir, f"benchmark_latency_{timestamp}.png")
    plt.savefig(path, dpi=200)
    plt.close()
    generated.append(path)

    # ── Chart 2: Throughput (TPS) ─────────────────────────────────────────

    fig, ax = plt.subplots(figsize=(14, 6))

    tps_values = [r.get("tps", 0) for r in successful]

    for i, (tps, color) in enumerate(zip(tps_values, bar_colors)):
        _draw_gradient_bar(ax, i, tps, bar_width, color)

    for i, val in enumerate(tps_values):
        ax.text(
            i,
            val + max(tps_values) * 0.02,
            f"{val:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
            color=TEXT_PRIMARY,
        )

    ax.set_xlim(-0.5, len(successful) - 0.5)
    ax.set_ylim(0, max(tps_values) * 1.15 if max(tps_values) > 0 else 1)
    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(
        [f"{t[:18]}\n{_get_label(s)}" for t, s in zip(task_names, strategies)],
        rotation=0,
        ha="center",
        fontsize=7.5,
    )
    ax.set_ylabel("Tokens / Second", fontsize=11, fontweight="bold")
    ax.set_title(
        "Throughput by Strategy",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.text(
        0.5,
        1.02,
        model_label,
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color=TEXT_SECONDARY,
    )

    _add_watermark(fig)
    plt.tight_layout()
    path = os.path.join(save_dir, f"benchmark_tps_{timestamp}.png")
    plt.savefig(path, dpi=200)
    plt.close()
    generated.append(path)

    # ── Chart 3: TTFT vs Latency Scatter ──────────────────────────────────

    fig, ax = plt.subplots(figsize=(10, 8))

    for r in successful:
        s = r.get("strategy", "?")
        color = _get_color(s)
        ttft = r.get("ttft_ms", 0)
        total = r.get("total_ms", 0)

        # Outer glow
        ax.scatter(
            ttft,
            total,
            c=color,
            s=200,
            alpha=0.15,
            edgecolors="none",
            zorder=3,
        )
        # Main dot
        ax.scatter(
            ttft,
            total,
            c=color,
            s=80,
            alpha=0.9,
            edgecolors="white",
            linewidth=0.5,
            zorder=4,
        )
        # Label
        ax.annotate(
            f"{r.get('task_name', '?')[:14]}",
            (ttft, total),
            textcoords="offset points",
            xytext=(10, 5),
            fontsize=7,
            color=TEXT_SECONDARY,
            arrowprops=dict(arrowstyle="-", color=TEXT_MUTED, lw=0.5),
        )

    ax.set_xlabel("Time to First Token (ms)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Total Latency (ms)", fontsize=11, fontweight="bold")
    ax.set_title(
        "TTFT vs Total Latency",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.text(
        0.5,
        1.02,
        model_label,
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color=TEXT_SECONDARY,
    )

    # Diagonal reference line (y = x means TTFT == total latency)
    lims = [
        max(ax.get_xlim()[0], ax.get_ylim()[0]),
        min(ax.get_xlim()[1], ax.get_ylim()[1]),
    ]
    if lims[1] > lims[0]:
        ax.plot(lims, lims, "--", color=TEXT_MUTED, lw=0.8, alpha=0.5, zorder=1)

    # Build legend from unique strategies
    seen = set()
    handles = []
    for r in successful:
        s = r.get("strategy", "?")
        if s not in seen:
            seen.add(s)
            handles.append(mpatches.Patch(color=_get_color(s), label=_get_label(s)))
    ax.legend(
        handles=handles,
        loc="upper left",
        framealpha=0.8,
        borderpad=0.8,
    )

    _add_watermark(fig)
    plt.tight_layout()
    path = os.path.join(save_dir, f"benchmark_scatter_{timestamp}.png")
    plt.savefig(path, dpi=200)
    plt.close()
    generated.append(path)

    # ── Chart 4: Strategy Summary (grouped metrics) ───────────────────────

    strategy_stats = {}
    for r in successful:
        s = r.get("strategy", "?")
        if s not in strategy_stats:
            strategy_stats[s] = {"latency": [], "tps": [], "ttft": []}
        strategy_stats[s]["latency"].append(r.get("total_ms", 0))
        strategy_stats[s]["tps"].append(r.get("tps", 0))
        strategy_stats[s]["ttft"].append(r.get("ttft_ms", 0))

    if len(strategy_stats) > 1:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        strats = sorted(strategy_stats.keys())
        x = list(range(len(strats)))
        colors = [_get_color(s) for s in strats]

        # Panel titles and data
        panels = [
            ("Avg Latency", "latency", _format_ms),
            ("Avg Throughput", "tps", lambda v: f"{v:.1f}"),
            ("Avg TTFT", "ttft", _format_ms),
        ]

        for ax, (title, key, fmt) in zip(axes, panels):
            vals = [sum(strategy_stats[s][key]) / len(strategy_stats[s][key]) for s in strats]

            for i, (v, c) in enumerate(zip(vals, colors)):
                _draw_gradient_bar(ax, i, v, 0.6, c)

            for i, v in enumerate(vals):
                ax.text(
                    i,
                    v + max(vals) * 0.03,
                    fmt(v),
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    fontweight="bold",
                    color=TEXT_PRIMARY,
                )

            ax.set_xlim(-0.5, len(strats) - 0.5)
            ax.set_ylim(0, max(vals) * 1.2 if max(vals) > 0 else 1)
            ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
            ax.set_xticks(x)
            ax.set_xticklabels(
                [_get_label(s) for s in strats],
                rotation=35,
                ha="right",
                fontsize=7.5,
            )
            # Format y-axis for ms-based panels
            if key in ("latency", "ttft"):
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _format_ms(v)))

        fig.suptitle(
            "Strategy Comparison",
            fontsize=15,
            fontweight="bold",
            y=1.02,
        )
        fig.text(
            0.5,
            0.98,
            model_label,
            ha="center",
            fontsize=10,
            color=TEXT_SECONDARY,
        )

        _add_watermark(fig)
        plt.tight_layout()
        path = os.path.join(save_dir, f"benchmark_summary_{timestamp}.png")
        plt.savefig(path, dpi=200)
        plt.close()
        generated.append(path)

    # ── Chart 5: Strategy Heatmap (if enough data) ────────────────────────

    if len(strategy_stats) >= 3:
        fig, ax = plt.subplots(figsize=(10, 6))

        strats = sorted(strategy_stats.keys())
        metrics = ["Latency (ms)", "Throughput (tok/s)", "TTFT (ms)"]

        data = []
        for s in strats:
            avg_lat = sum(strategy_stats[s]["latency"]) / len(strategy_stats[s]["latency"])
            avg_tps = sum(strategy_stats[s]["tps"]) / len(strategy_stats[s]["tps"])
            avg_ttft = sum(strategy_stats[s]["ttft"]) / len(strategy_stats[s]["ttft"])
            data.append([avg_lat, avg_tps, avg_ttft])

        import numpy as np

        data_arr = np.array(data)

        # Normalize each column 0-1 for heatmap
        norm_data = np.zeros_like(data_arr)
        for col in range(data_arr.shape[1]):
            col_min = data_arr[:, col].min()
            col_max = data_arr[:, col].max()
            if col_max > col_min:
                norm_data[:, col] = (data_arr[:, col] - col_min) / (col_max - col_min)
            else:
                norm_data[:, col] = 0.5

        # For latency and TTFT, lower is better - invert
        norm_data[:, 0] = 1 - norm_data[:, 0]  # latency
        norm_data[:, 2] = 1 - norm_data[:, 2]  # ttft

        from matplotlib.colors import LinearSegmentedColormap

        cmap = LinearSegmentedColormap.from_list(
            "agent_heatmap",
            ["#f85149", "#d29922", "#56d364"],  # red -> amber -> green
        )

        ax.imshow(norm_data, cmap=cmap, aspect="auto", vmin=0, vmax=1)

        ax.set_xticks(range(len(metrics)))
        ax.set_xticklabels(metrics, fontsize=10, fontweight="bold")
        ax.set_yticks(range(len(strats)))
        ax.set_yticklabels([_get_label(s) for s in strats], fontsize=9)

        # Annotate cells with actual values
        for i in range(len(strats)):
            for j in range(len(metrics)):
                val = data_arr[i, j]
                txt = _format_ms(val) if j != 1 else f"{val:.1f}"
                text_color = "#0d1117" if norm_data[i, j] > 0.5 else TEXT_PRIMARY
                ax.text(
                    j,
                    i,
                    txt,
                    ha="center",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color=text_color,
                )

        ax.set_title(
            "Performance Heatmap",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        ax.text(
            0.5,
            1.05,
            f"{model_label}  |  Green = Better",
            transform=ax.transAxes,
            ha="center",
            fontsize=9,
            color=TEXT_SECONDARY,
        )

        # Remove grid for heatmap
        ax.grid(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)

        _add_watermark(fig)
        plt.tight_layout()
        path = os.path.join(save_dir, f"benchmark_heatmap_{timestamp}.png")
        plt.savefig(path, dpi=200)
        plt.close()
        generated.append(path)

    return generated


def generate_comparison_charts(
    ollama_results: Dict[str, List],
    oci_results: List,
    model: str = "",
    output_dir: str = None,
) -> List[str]:
    """Generate multi-model comparison charts (Ollama vs OCI)."""
    try:
        plt = _apply_dark_theme()
        import matplotlib.patches as mpatches
    except ImportError:
        return []

    save_dir = output_dir or CHARTS_DIR
    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated = []

    # Collect per-model averages
    model_avgs = {}
    for model_name, results in ollama_results.items():
        success = [r for r in results if hasattr(r, "success") and r.success]
        if success:
            model_avgs[model_name] = {
                "latency": sum(r.latency_ms for r in success) / len(success),
                "tps": sum(r.tps for r in success) / len(success),
                "ttft": sum(r.ttft_ms for r in success) / len(success),
            }

    oci_success = [r for r in oci_results if hasattr(r, "success") and r.success]
    if oci_success:
        model_avgs["OCI GenAI"] = {
            "latency": sum(r.latency_ms for r in oci_success) / len(oci_success),
            "tps": sum(r.tps for r in oci_success) / len(oci_success),
            "ttft": sum(r.ttft_ms for r in oci_success) / len(oci_success),
        }

    if len(model_avgs) < 2:
        return []

    models = list(model_avgs.keys())
    model_colors = ["#58a6ff", "#56d364", "#f85149", "#d29922", "#bc8cff"]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    x = list(range(len(models)))
    c = model_colors[: len(models)]

    panels = [
        ("Avg Latency", "latency", _format_ms),
        ("Avg Throughput", "tps", lambda v: f"{v:.1f} tok/s"),
        ("Avg TTFT", "ttft", _format_ms),
    ]

    for ax, (title, key, fmt) in zip(axes, panels):
        vals = [model_avgs[m][key] for m in models]

        for i, (v, color) in enumerate(zip(vals, c)):
            _draw_gradient_bar(ax, i, v, 0.55, color)

        for i, v in enumerate(vals):
            ax.text(
                i,
                v + max(vals) * 0.03,
                fmt(v),
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color=TEXT_PRIMARY,
            )

        ax.set_xlim(-0.5, len(models) - 0.5)
        ax.set_ylim(0, max(vals) * 1.2 if max(vals) > 0 else 1)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(models, fontsize=9)

    fig.suptitle(
        "Multi-Model Comparison",
        fontsize=15,
        fontweight="bold",
        y=1.02,
    )

    _add_watermark(fig)
    plt.tight_layout()
    path = os.path.join(save_dir, f"comparison_{timestamp}.png")
    plt.savefig(path, dpi=200)
    plt.close()
    generated.append(path)

    return generated
