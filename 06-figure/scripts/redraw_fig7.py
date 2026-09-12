"""Redraw FIG-Q3-BRACKET-ZOOM without changing its frozen data or claim."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FormatStrFormatter
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "06-figure"
SOURCE = ROOT / "04-compute" / "results" / "q3-threshold-trajectory.csv"
RUN_SUMMARY = ROOT / "04-compute" / "results" / "run-summary.csv"
SNAPSHOT = FIGURE_DIR / "data-snapshots" / "FIG-Q3-BRACKET-ZOOM.csv"
CONTRACT = FIGURE_DIR / "contracts" / "FIG-Q3-BRACKET-ZOOM.json"
FIGURES = FIGURE_DIR / "figures"
PREVIEWS = FIGURE_DIR / "previews"
FIG_ID = "FIG-Q3-BRACKET-ZOOM"
THRESHOLD = 0.149999  # frozen Q3 full-domain threshold: 0.15 - 1e-6


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_frozen_data() -> pd.DataFrame:
    """Use the existing snapshot as plotting input and verify it against source rows."""
    snapshot = pd.read_csv(SNAPSHOT)
    expected_columns = ["time_s", "max_C"]
    if list(snapshot.columns) != expected_columns:
        raise AssertionError(f"unexpected snapshot columns: {list(snapshot.columns)}")
    if len(snapshot) != 6:
        raise AssertionError(f"FIG-Q3-BRACKET-ZOOM must retain 6 samples, got {len(snapshot)}")

    source = pd.read_csv(SOURCE)
    for row in snapshot.itertuples(index=False):
        candidates = source[source["time_s"].eq(row.time_s)]
        if candidates.empty or not np.isclose(
            candidates["max_C"].to_numpy(dtype=float),
            float(row.max_C),
            rtol=0.0,
            atol=1e-15,
        ).any():
            raise AssertionError(f"snapshot row is not present in source: {row}")
    return snapshot


def read_frozen_event_times() -> tuple[float, float]:
    summary = pd.read_csv(RUN_SUMMARY)
    row = summary.loc[summary["label"].eq("Q3-M3-nr210")]
    if len(row) != 1:
        raise AssertionError("expected exactly one Q3-M3-nr210 row in run-summary.csv")
    interpolated = float(row.iloc[0]["interpolated_event_time_s"])
    reported = float(row.iloc[0]["reported_event_time_s"])
    if not np.isclose(interpolated, 206818.71137262788, rtol=0.0, atol=1e-12):
        raise AssertionError("unexpected frozen interpolated event time")
    if not np.isclose(reported, 206820.0, rtol=0.0, atol=1e-12):
        raise AssertionError("unexpected frozen reported event time")
    return interpolated, reported


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    data = validate_frozen_data()
    interpolated, reported = read_frozen_event_times()

    mpl.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "text.color": "#000000",
            "axes.labelcolor": "#000000",
            "axes.titlecolor": "#000000",
            "xtick.color": "#000000",
            "ytick.color": "#000000",
            "legend.labelcolor": "#000000",
            "axes.unicode_minus": False,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": FIG_ID,
        }
    )

    # The curve is one data series: keep it solid. Point colors and markers
    # identify the six retained sampling times and survive grayscale printing.
    point_colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#7B2CBF", "#007C91"]
    point_markers = ["o", "s", "^", "D", "P", "X"]

    fig, ax = plt.subplots(figsize=(6.7, 4.2), dpi=600)
    fig.subplots_adjust(left=0.135, right=0.985, bottom=0.19, top=0.80)

    ax.plot(
        data["time_s"],
        data["max_C"],
        color="#005AB5",
        linestyle="-",
        linewidth=1.7,
        zorder=2,
    )
    for color, marker, row in zip(point_colors, point_markers, data.itertuples(index=False)):
        ax.plot(
            row.time_s,
            row.max_C,
            linestyle="None",
            marker=marker,
            markersize=5.5,
            markerfacecolor=color,
            markeredgecolor="#000000",
            markeredgewidth=0.55,
            zorder=3,
        )

    # Reference lines are not data curves; their black redundant line styles
    # make the threshold, interpolated event, and conservative report distinct.
    ax.axhline(
        THRESHOLD,
        color="#000000",
        linewidth=0.85,
        linestyle=(0, (5, 2.5)),
        zorder=1,
    )
    ax.axvline(
        interpolated,
        color="#000000",
        linewidth=0.85,
        linestyle=(0, (1.5, 2)),
        zorder=1,
    )
    ax.axvline(
        reported,
        color="#000000",
        linewidth=0.95,
        linestyle=(0, (6, 2)),
        zorder=1,
    )

    ax.set_xlabel("时间 t (s)", fontsize=9.5, color="#000000", labelpad=7)
    ax.set_ylabel("最大干基含水率 C (kg/kg)", fontsize=9.5, color="#000000", labelpad=8)
    ax.set_xticks(data["time_s"].tolist())
    ax.set_xticklabels([str(int(x)) for x in data["time_s"]])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.6f"))
    ax.tick_params(
        axis="both",
        which="major",
        direction="out",
        length=3.2,
        width=0.65,
        colors="#000000",
        labelsize=7.4,
    )
    ax.grid(axis="both", color="#000000", linewidth=0.45, alpha=0.14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#000000")
        ax.spines[side].set_linewidth(0.75)

    legend_handles = [
        Line2D([0], [0], color="#000000", linewidth=0.85, linestyle=(0, (5, 2.5)), label="阈值 C = 0.149999"),
        Line2D([0], [0], color="#000000", linewidth=0.85, linestyle=(0, (1.5, 2)), label=f"插值时刻 {interpolated:.4f} s"),
        Line2D([0], [0], color="#000000", linewidth=0.95, linestyle=(0, (6, 2)), label=f"保守报告 {reported:.0f} s"),
    ]
    legend = fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.57, 0.895),
        ncol=3,
        frameon=False,
        fontsize=7.5,
        columnspacing=1.35,
        handlelength=2.2,
        handletextpad=0.45,
        borderaxespad=0.0,
    )
    for text in legend.get_texts():
        text.set_color("#000000")

    fixed_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fig.savefig(FIGURES / f"{FIG_ID}.svg", metadata={"Date": "2026-01-01T00:00:00"})
    fig.savefig(
        FIGURES / f"{FIG_ID}.pdf",
        dpi=600,
        metadata={"CreationDate": fixed_date, "ModDate": fixed_date},
    )
    fig.savefig(FIGURES / f"{FIG_ID}.png", dpi=600)
    fig.savefig(PREVIEWS / f"{FIG_ID}-color.png", dpi=600)
    plt.close(fig)

    formal_color = Image.open(FIGURES / f"{FIG_ID}.png").convert("RGB")
    ImageOps.grayscale(formal_color).save(PREVIEWS / f"{FIG_ID}-grayscale.png", dpi=(600, 600))

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["target_formats"] = ["svg", "png", "pdf"]
    CONTRACT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "figure_id": FIG_ID,
                "source_sha256": sha256(SOURCE),
                "snapshot_sha256": sha256(SNAPSHOT),
                "png_sha256": sha256(FIGURES / f"{FIG_ID}.png"),
                "svg_sha256": sha256(FIGURES / f"{FIG_ID}.svg"),
                "pdf_sha256": sha256(FIGURES / f"{FIG_ID}.pdf"),
                "sample_count": len(data),
                "font": "SimSun",
                "data_claim_status": "unchanged",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
