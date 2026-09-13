from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "06-figure"
SOURCE = ROOT / "04-compute" / "results" / "q2-samples.csv"
SNAPSHOT = FIGURE_DIR / "data-snapshots" / "FIG-Q2-C-PROFILES.csv"
FIGURES = FIGURE_DIR / "figures"
PREVIEWS = FIGURE_DIR / "previews"
FIG_ID = "FIG-Q2-C-PROFILES"
FIELDS = ["time_s", "radius_cm", "C_kg_per_kg"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[tuple[int, float, float]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sorted(
            (
                (
                    int(row["time_s"]),
                    float(row["radius_cm"]),
                    float(row["C_kg_per_kg"]),
                )
                for row in csv.DictReader(handle)
            ),
            key=lambda row: (row[0], row[1]),
        )


def same_numeric_rows(left: list[tuple[int, float, float]], right: list[tuple[int, float, float]]) -> bool:
    if len(left) != len(right):
        return False
    return all(
        a[0] == b[0]
        and abs(a[1] - b[1]) <= 1e-12
        and abs(a[2] - b[2]) <= 1e-12
        for a, b in zip(left, right)
    )


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    assert same_numeric_rows(rows(SOURCE), rows(SNAPSHOT)), "source and frozen figure snapshot differ"

    data = pd.read_csv(SOURCE)[FIELDS].sort_values(
        ["time_s", "radius_cm"], kind="stable"
    )
    mpl.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "text.color": "#000000",
            "axes.labelcolor": "#000000",
            "xtick.color": "#000000",
            "ytick.color": "#000000",
            "axes.unicode_minus": False,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "FIG-Q2-C-PROFILES",
        }
    )

    # 图线按半径分组；使用高对比彩色、统一实线，并用 marker 进一步区分半径。
    colors = ["#005AB5", "#E69F00", "#009E73", "#D55E00", "#7B2CBF"]
    linestyles = ["-"] * 5
    markers = ["o", "s", "^", "D", "P"]
    labels = ["r = 0 cm", "r = 0.5 cm", "r = 1 cm", "r = 1.5 cm", "r = 2 cm"]

    fig, ax = plt.subplots(figsize=(6.9, 4.5), dpi=600)
    fig.subplots_adjust(left=0.135, right=0.985, bottom=0.205, top=0.745)
    for i, (radius_cm, group) in enumerate(data.groupby("radius_cm", sort=True)):
        group = group.sort_values("time_s")
        ax.plot(
            group["time_s"] / 3600.0,
            group["C_kg_per_kg"],
            color=colors[i],
            linestyle=linestyles[i],
            linewidth=1.75,
            marker=markers[i],
            markersize=5.0,
            markerfacecolor=colors[i],
            markeredgecolor=colors[i],
            markeredgewidth=0.65,
            label=labels[i],
            zorder=3 + i * 0.01,
        )

    ax.set_xlim(0.45, 3.05)
    ax.set_ylim(0.92, 2.66)
    ax.set_xticks([0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    ax.set_yticks([1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6])
    ax.set_xlabel("时间 t（h）", fontsize=9.5, color="#000000", labelpad=7)
    ax.set_ylabel("干基含水率 C（kg/kg）", fontsize=9.5, color="#000000", labelpad=8)
    ax.tick_params(
        axis="both",
        which="major",
        direction="out",
        length=3.2,
        width=0.65,
        colors="#000000",
        labelsize=8.3,
    )
    for tick_label in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        tick_label.set_fontfamily("SimHei")
    ax.grid(axis="y", color="#000000", linewidth=0.5, alpha=0.15)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#000000")
        ax.spines[side].set_linewidth(0.75)

    fig.text(
        0.135,
        0.935,
        "M3",
        ha="left",
        va="top",
        fontsize=11.5,
        fontfamily="SimHei",
        color="#000000",
    )
    fig.text(
        0.175,
        0.935,
        "不同半径位置含水率随时间演化",
        ha="left",
        va="top",
        fontsize=11.5,
        fontfamily="SimSun",
        color="#000000",
    )
    legend = fig.legend(
        loc="upper center",
        bbox_to_anchor=(0.56, 0.835),
        ncol=3,
        frameon=False,
        prop={"family": "SimHei", "size": 8.0},
        columnspacing=1.45,
        handlelength=2.35,
        handletextpad=0.55,
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
    ImageOps.grayscale(formal_color).save(
        PREVIEWS / f"{FIG_ID}-grayscale.png", dpi=(600, 600)
    )
    print(
        {
            "figure_id": FIG_ID,
            "source_sha256": sha256(SOURCE),
            "snapshot_sha256": sha256(SNAPSHOT),
            "png_sha256": sha256(FIGURES / f"{FIG_ID}.png"),
            "svg_sha256": sha256(FIGURES / f"{FIG_ID}.svg"),
            "pdf_sha256": sha256(FIGURES / f"{FIG_ID}.pdf"),
            "right_bottom_note": False,
        }
    )


if __name__ == "__main__":
    main()

