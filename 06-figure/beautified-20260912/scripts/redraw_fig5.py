from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.ticker import FormatStrFormatter, MultipleLocator
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
FIG_ID = "FIG-Q2-GRID-CONV"

SOURCE = ROOT / "06-figure" / "data-snapshots" / f"{FIG_ID}.csv"
SOURCE_META = ROOT / "06-figure" / "data-snapshots" / f"{FIG_ID}.meta.json"
TARGET_SNAPSHOT = OUT / "data-snapshots" / f"{FIG_ID}.csv"
TARGET_META = OUT / "data-snapshots" / f"{FIG_ID}.meta.json"
TARGET_CONTRACT = OUT / "contracts" / f"{FIG_ID}.json"
TARGET_FIGURES = OUT / "figures"
TARGET_PREVIEWS = OUT / "previews"

for directory in (TARGET_SNAPSHOT.parent, TARGET_CONTRACT.parent, TARGET_FIGURES, TARGET_PREVIEWS):
    directory.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_tick_font(axis) -> None:
    for label in (*axis.get_xticklabels(), *axis.get_yticklabels()):
        label.set_fontproperties(FONT_ARIAL)
        label.set_fontsize(8.2)


def frame(axis) -> None:
    axis.set_facecolor("white")
    axis.grid(False)
    axis.tick_params(
        axis="both",
        which="both",
        direction="in",
        top=True,
        right=True,
        length=4,
        width=0.7,
        color="#333333",
    )
    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_color("#333333")
        spine.set_linewidth(0.75)


mpl.rcParams.update(
    {
        "font.family": ["Arial", "SimSun"],
        "font.size": 8.5,
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    }
)

FONT_SONG = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")
FONT_HEI = FontProperties(fname=r"C:\Windows\Fonts\simhei.ttf")
FONT_ARIAL = FontProperties(fname=r"C:\Windows\Fonts\arial.ttf")


def main() -> None:
    source_meta = json.loads(SOURCE_META.read_text(encoding="utf-8"))
    if sha256(SOURCE) != source_meta["snapshot_sha256"]:
        raise RuntimeError("源数据快照哈希与登记值不一致，停止重绘。")

    data = pd.read_csv(SOURCE)
    data = data[
        (data["scope"] == "Q2")
        & (data["family"] == "M3")
        & (data["metric"] == "final_max_C")
    ].sort_values("nr")
    expected_nr = [62, 93, 140]
    if data["nr"].tolist() != expected_nr or len(data) != 3:
        raise RuntimeError(f"图5数据范围异常：{data[['nr', 'nz']].to_dict('records')}")
    if data["nz"].nunique() != 1:
        raise RuntimeError("图5要求固定 nz，但源数据包含多个 nz。")

    # Preserve the exact frozen snapshot in the beautified output directory.
    shutil.copy2(SOURCE, TARGET_SNAPSHOT)
    target_meta = dict(source_meta)
    target_meta["snapshot"] = f"06-figure/beautified-20260912/data-snapshots/{FIG_ID}.csv"
    target_meta["snapshot_sha256"] = sha256(TARGET_SNAPSHOT)
    TARGET_META.write_text(json.dumps(target_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    contract = {
        "figure_id": FIG_ID,
        "claim_ids": ["Q2-OBS-02"],
        "question": "M3终值随网格如何收敛？",
        "source_files": source_meta["sources"],
        "x": "网格 nr×nz；nz固定为36",
        "y": "3 h 最大干基含水率 C（kg/kg）",
        "groups": ["Q2 M3 网格层级"],
        "uncertainty": "确定性数值解；相邻网格变化作为离散化诊断",
        "required_comparisons": ["网格收敛轨迹", "最细相邻变化与5×10⁻⁵验收线"],
        "must_show_failures": False,
        "prohibited_operations": [
            "recompute model",
            "change metric",
            "omit the narrow-margin annotation",
            "present conditional simulation as observation",
        ],
        "target_formats": ["svg", "pdf", "png"],
        "minimum_dpi": 600,
        "placement": "主文",
        "mandatory_limit": "必须标窄裕量PASS；数值收敛不等于现实准确性",
        "snapshot": target_meta["snapshot"],
        "snapshot_sha256": target_meta["snapshot_sha256"],
    }
    TARGET_CONTRACT.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")

    x = np.arange(len(data), dtype=float)
    y = data["value"].to_numpy(float)
    adjacent = data["adjacent_change"].to_numpy(float)[1:]
    nr = data["nr"].to_numpy(int)
    nz = int(data["nz"].iloc[0])
    threshold = 5e-5

    blue = "#1F5A94"
    orange = "#D97932"
    teal = "#2A8C82"
    grey = "#AAB7C2"

    fig = plt.figure(figsize=(6.9, 5.15), facecolor="white")
    grid = fig.add_gridspec(
        2,
        1,
        height_ratios=[2.55, 1.15],
        left=0.16,
        right=0.955,
        bottom=0.245,
        top=0.955,
        hspace=0.27,
    )
    ax = fig.add_subplot(grid[0, 0])
    ax2 = fig.add_subplot(grid[1, 0])

    # Main convergence trajectory: one y-axis, with grid resolution shown explicitly.
    ax.plot(x, y, color=blue, linewidth=1.8, zorder=2)
    ax.scatter(x[:-1], y[:-1], s=50, facecolor="white", edgecolor=blue, linewidth=1.7, zorder=3)
    ax.scatter([x[-1]], [y[-1]], s=62, facecolor=orange, edgecolor="white", linewidth=1.1, zorder=4)
    ax.set_xlim(-0.18, 2.18)
    ax.set_ylim(y.min() - 2.0e-5, y.max() + 2.2e-5)
    ax.set_xticks(x, [f"nr={a}, nz={nz}" for a in nr])
    ax.set_xlabel("空间网格（径向网格数 nr × 轴向网格数 nz）", fontproperties=FONT_HEI, fontsize=10.5, labelpad=8, color="#111111")
    ax.set_ylabel("3 h 最大干基含水率 C\n（kg/kg）", fontproperties=FONT_HEI, fontsize=10.5, labelpad=8, color="#111111")
    ax.yaxis.set_major_locator(MultipleLocator(5e-5))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.5f"))
    set_tick_font(ax)
    frame(ax)
    ax.text(
        0.02,
        0.91,
        "M3 · 时间步 Δt = 5 s · nz = 36 固定",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontproperties=FONT_SONG,
        fontsize=8.3,
        color="#333333",
    )
    legend = ax.legend(
        handles=[
            Line2D([0], [0], color=blue, linewidth=1.8, marker="o", markersize=4.6,
                   markerfacecolor="white", markeredgecolor=blue, label="M3 网格收敛轨迹"),
            Line2D([0], [0], color=orange, linewidth=0, marker="o", markersize=5.0,
                   markerfacecolor=orange, markeredgecolor="white", label="最细网格结果"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.02, 0.78),
        frameon=False,
        handlelength=2.2,
        handletextpad=0.6,
        borderaxespad=0.0,
        prop=FONT_HEI,
    )
    for legend_text in legend.get_texts():
        legend_text.set_fontproperties(FONT_HEI)
        legend_text.set_fontsize(8.0)
        legend_text.set_color("#000000")
    for xi, yi, label, dy in zip(x, y, [f"{v:.6f}" for v in y], [10, 10, 10]):
        ax.annotate(
            label,
            (xi, yi),
            xytext=(0, dy),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontproperties=FONT_ARIAL,
            fontsize=8.0,
            color=orange if xi == x[-1] else blue,
        )
    ax.annotate(
        "细化后变化减小",
        xy=(x[-1], y[-1]),
        xytext=(-60, -27),
        textcoords="offset points",
        ha="center",
        va="top",
        fontproperties=FONT_SONG,
        fontsize=8.0,
        color="#5B6870",
        arrowprops={"arrowstyle": "-", "color": "#7B8790", "lw": 0.7},
    )

    # Separate acceptance diagnostic avoids a misleading dual y-axis.
    pair_x = np.array([0.0, 1.0])
    delta_scaled = adjacent * 1e5
    ax2.bar(pair_x, delta_scaled, width=0.46, color=[grey, teal], edgecolor="white", linewidth=0.9, zorder=2)
    ax2.axhline(threshold * 1e5, color=orange, linestyle="--", linewidth=1.05, zorder=1)
    ax2.text(
        0.28,
        threshold * 1e5 + 0.18,
        "验收线 5 × 10$^{-5}$",
        ha="left",
        va="bottom",
        fontproperties=FONT_SONG,
        fontsize=8.0,
        color=orange,
    )
    ax2.set_xlim(-0.55, 1.55)
    ax2.set_ylim(0, 10.2)
    ax2.set_xticks(pair_x, [f"{nr[0]}×{nz} → {nr[1]}×{nz}", f"{nr[1]}×{nz} → {nr[2]}×{nz}"])
    ax2.set_xlabel("相邻网格对比（由粗到细）", fontproperties=FONT_HEI, fontsize=9.8, labelpad=8, color="#111111")
    ax2.set_ylabel("相邻网格变化 |ΔC|\n（×10$^{-5}$ kg/kg）", fontproperties=FONT_HEI, fontsize=9.5, labelpad=8, color="#111111")
    ax2.set_yticks([0, 5, 10])
    ax2.yaxis.set_major_formatter(FormatStrFormatter("%g"))
    set_tick_font(ax2)
    for label in ax2.get_xticklabels():
        label.set_fontproperties(FONT_ARIAL)
        label.set_fontsize(7.4)
    frame(ax2)
    for xi, value in zip(pair_x, delta_scaled):
        ax2.text(
            xi,
            value + 0.25,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontproperties=FONT_ARIAL,
            fontsize=8.2,
            color=teal if value <= threshold * 1e5 else "#5B6870",
        )
    ax2.text(
        1.49,
        8.85,
        "最细相邻变化 4.001 × 10$^{-5}$\n≤ 5 × 10$^{-5}$ · 窄裕量 PASS",
        ha="right",
        va="top",
        fontproperties=FONT_SONG,
        fontsize=8.0,
        color="#111111",
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "#F4F8FA", "edgecolor": teal, "linewidth": 0.8},
    )

    fig.text(
        0.50,
        0.075,
        "图 5：M3 网格细化下 3 h 最大干基含水率收敛性",
        ha="center",
        va="center",
        fontproperties=FONT_HEI,
        fontsize=13.2,
        color="#111111",
    )

    for extension in ("svg", "pdf"):
        fig.savefig(TARGET_FIGURES / f"{FIG_ID}.{extension}", bbox_inches="tight", pad_inches=0.08)
    fig.savefig(TARGET_FIGURES / f"{FIG_ID}.png", dpi=600, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(TARGET_PREVIEWS / f"{FIG_ID}-color.png", dpi=180, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    preview = Image.open(TARGET_PREVIEWS / f"{FIG_ID}-color.png").convert("RGB")
    ImageOps.grayscale(preview).save(TARGET_PREVIEWS / f"{FIG_ID}-grayscale.png")

    print(
        json.dumps(
            {
                "figure": FIG_ID,
                "rows": len(data),
                "fine_adjacent_change": float(adjacent[-1]),
                "threshold": threshold,
                "status": "PASS" if adjacent[-1] <= threshold else "FAIL",
                "outputs": [
                    str(TARGET_FIGURES / f"{FIG_ID}.svg"),
                    str(TARGET_FIGURES / f"{FIG_ID}.pdf"),
                    str(TARGET_FIGURES / f"{FIG_ID}.png"),
                ],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
