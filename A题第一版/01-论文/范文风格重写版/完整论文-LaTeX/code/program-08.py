from __future__ import annotations

"""Redraw FIG-Q3-THRESHOLD-TRAJECTORY without changing its frozen data.

The script intentionally reads the existing FIGURE snapshot and independently
checks it against the COMPUTE result before rendering.  It writes only the
figure-6 artwork, previews, and a small QA record; it never rewrites the data
snapshot or recomputes the model.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[2]
FIGURE = "FIG-Q3-THRESHOLD-TRAJECTORY"
FIG_DIR = ROOT / "06-figure" / "figures"
PREVIEW_DIR = ROOT / "06-figure" / "previews"
SNAPSHOT = ROOT / "06-figure" / "data-snapshots" / f"{FIGURE}.csv"
SOURCE = ROOT / "04-compute" / "results" / "q3-threshold-trajectory.csv"
CONTRACT = ROOT / "06-figure" / "contracts" / f"{FIGURE}.json"
RECORD_DIR = ROOT / "06-figure" / "redraw-fig6-20260912"

PNG = FIG_DIR / f"{FIGURE}.png"
SVG = FIG_DIR / f"{FIGURE}.svg"
PDF = FIG_DIR / f"{FIGURE}.pdf"
COLOR_PREVIEW = PREVIEW_DIR / f"{FIGURE}-color.png"
GRAY_PREVIEW = PREVIEW_DIR / f"{FIGURE}-grayscale.png"

THRESHOLD = 0.149999
REPORT_TIME_S = 206820.0
XMAX_H = 60.0
YMAX = 2.7

FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")
if not FONT_PATH.exists():
    raise FileNotFoundError(f"宋体字体文件不存在: {FONT_PATH}")
fontManager.addfont(str(FONT_PATH))
FONT = FontProperties(fname=str(FONT_PATH))

COLORS = {
    "max_C": "#0072B2",       # blue
    "mean_C": "#E69F00",      # orange
    "center_C": "#009E73",    # green
    "surface_C": "#D55E00",   # vermillion
}
LABELS = {
    "max_C": "最大值",
    "mean_C": "均值",
    "center_C": "中心",
    "surface_C": "表面",
}
MARKERS = {
    "max_C": "o",
    "mean_C": "s",
    "center_C": "^",
    "surface_C": "D",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_data() -> tuple[pd.DataFrame, dict]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source_expected = contract["source_files"][0]["sha256"]
    snapshot_expected = contract["snapshot_sha256"]
    source_actual = sha256(SOURCE)
    snapshot_actual = sha256(SNAPSHOT)
    if source_actual != source_expected:
        raise RuntimeError(
            f"原始结果哈希不匹配: expected={source_expected}, actual={source_actual}"
        )
    if snapshot_actual != snapshot_expected:
        raise RuntimeError(
            f"冻结快照哈希不匹配: expected={snapshot_expected}, actual={snapshot_actual}"
        )

    source_df = pd.read_csv(SOURCE)
    snapshot_df = pd.read_csv(SNAPSHOT)
    expected_columns = ["time_s", "max_C", "mean_C", "center_C", "surface_C"]
    if not set(expected_columns).issubset(source_df.columns) or list(snapshot_df.columns) != expected_columns:
        raise RuntimeError("源数据或冻结快照列结构发生变化")
    if len(source_df) != len(snapshot_df):
        raise RuntimeError("源数据与冻结快照行数不一致")
    source_values = source_df[expected_columns].to_numpy(dtype=float)
    snapshot_values = snapshot_df.to_numpy(dtype=float)
    max_abs_diff = float(np.max(np.abs(source_values - snapshot_values)))
    # The snapshot is a CSV projection of the source; decimal parsing can
    # differ by one floating-point ulp while preserving every plotted value.
    if not np.allclose(source_values, snapshot_values, rtol=0.0, atol=5e-15):
        raise RuntimeError(f"源数据与冻结快照数值不一致，最大绝对差={max_abs_diff}")

    checks = {
        "source_path": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": source_actual,
        "snapshot_path": SNAPSHOT.relative_to(ROOT).as_posix(),
        "snapshot_sha256": snapshot_actual,
        "columns": expected_columns,
        "rows": int(len(snapshot_df)),
        "data_equal": True,
        "max_abs_diff_after_csv_parse": max_abs_diff,
        "time_range_s": [float(snapshot_df.time_s.min()), float(snapshot_df.time_s.max())],
        "reported_time_s": REPORT_TIME_S,
        "threshold": THRESHOLD,
    }
    return snapshot_df, checks


def configure_text() -> None:
    plt.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def style_axes(ax, *, inset: bool = False) -> None:
    ax.set_facecolor("white")
    ax.tick_params(
        axis="both",
        which="both",
        colors="black",
        labelcolor="black",
        direction="out",
        length=3.0 if inset else 4.0,
        width=0.7,
        labelsize=6.5 if inset else 8.0,
    )
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(FONT)
        label.set_color("black")
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(0.7)
    ax.grid(True, color="black", alpha=0.14, linewidth=0.45)
    ax.set_axisbelow(True)


def draw_series(ax, data: pd.DataFrame, *, marker_indices: np.ndarray, linewidth: float, markersize: float) -> None:
    time_h = data.time_s.to_numpy(dtype=float) / 3600.0
    for column in ("max_C", "mean_C", "center_C", "surface_C"):
        ax.plot(
            time_h,
            data[column].to_numpy(dtype=float),
            color=COLORS[column],
            linestyle="-",
            linewidth=linewidth,
            marker=MARKERS[column],
            markersize=markersize,
            markevery=marker_indices,
            markerfacecolor=COLORS[column],
            markeredgecolor="black",
            markeredgewidth=0.45,
            label=LABELS[column],
            zorder=3,
        )


def render(data: pd.DataFrame) -> None:
    configure_text()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    RECORD_DIR.mkdir(parents=True, exist_ok=True)

    # Markers are a visual encoding only; every row remains in every line.
    marker_hours = np.array([0, 2, 4, 8, 12, 24, 36, 48, REPORT_TIME_S / 3600.0])
    time_hours = data.time_s.to_numpy(dtype=float) / 3600.0
    marker_indices = np.array([int(np.argmin(np.abs(time_hours - h))) for h in marker_hours])
    marker_indices = np.unique(marker_indices)

    fig, ax = plt.subplots(figsize=(6.535, 4.75), dpi=600)
    fig.patch.set_facecolor("white")
    draw_series(ax, data, marker_indices=marker_indices, linewidth=1.45, markersize=3.7)
    ax.axhline(
        THRESHOLD,
        color="black",
        linestyle="--",
        linewidth=0.9,
        label="判据 0.149999",
        zorder=2,
    )
    ax.axvline(
        REPORT_TIME_S / 3600.0,
        color="black",
        linestyle=":",
        linewidth=0.9,
        label="报告时刻 57.45 h",
        zorder=2,
    )
    ax.set_xlim(0, XMAX_H)
    ax.set_ylim(0, YMAX)
    ax.set_title(
        "全域含水率随时间的变化",
        fontproperties=FONT,
        fontsize=10.5,
        color="black",
        pad=8,
    )
    ax.set_xlabel("时间 t (h)", fontproperties=FONT, fontsize=9, color="black", labelpad=5)
    ax.set_ylabel("干基含水率 C (kg/kg)", fontproperties=FONT, fontsize=9, color="black", labelpad=5)
    style_axes(ax)

    handles = [
        Line2D(
            [0], [0], color=COLORS[c], linestyle="-", linewidth=1.45,
            marker=MARKERS[c], markersize=4.2, markerfacecolor=COLORS[c],
            markeredgecolor="black", markeredgewidth=0.45, label=LABELS[c],
        )
        for c in ("max_C", "mean_C", "center_C", "surface_C")
    ]
    handles += [
        Line2D([0], [0], color="black", linestyle="--", linewidth=0.9, label="判据 0.149999"),
        Line2D([0], [0], color="black", linestyle=":", linewidth=0.9, label="报告时刻 57.45 h"),
    ]
    legend = ax.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(0.99, 0.93),
        ncol=3,
        frameon=False,
        borderaxespad=0.25,
        handlelength=2.3,
        columnspacing=1.0,
        handletextpad=0.45,
        prop=FontProperties(fname=str(FONT_PATH), size=7.5),
    )
    for text in legend.get_texts():
        text.set_color("black")

    # A compact, explicitly labelled local view makes the threshold event legible
    # without changing the primary 0–60 h coordinate range.
    inset = ax.inset_axes([0.56, 0.16, 0.39, 0.38])
    draw_series(inset, data, marker_indices=marker_indices, linewidth=1.0, markersize=2.8)
    inset.axhline(THRESHOLD, color="black", linestyle="--", linewidth=0.7, zorder=2)
    inset.axvline(REPORT_TIME_S / 3600.0, color="black", linestyle=":", linewidth=0.7, zorder=2)
    inset.set_xlim(45, 60)
    inset.set_ylim(0.04, 0.17)
    inset.set_title("判据附近局部放大", fontproperties=FONT, fontsize=7.5, color="black", pad=3)
    inset.set_xlabel("t (h)", fontproperties=FONT, fontsize=6.5, color="black", labelpad=2)
    inset.set_ylabel("C", fontproperties=FONT, fontsize=6.5, color="black", labelpad=2)
    style_axes(inset, inset=True)

    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.12, top=0.91)
    for path, kwargs in (
        (SVG, {"format": "svg"}),
        (PDF, {"format": "pdf"}),
        (PNG, {"format": "png", "dpi": 600}),
        (COLOR_PREVIEW, {"format": "png", "dpi": 300}),
    ):
        fig.savefig(path, facecolor="white", **kwargs)
    plt.close(fig)

    ImageOps.grayscale(Image.open(COLOR_PREVIEW).convert("RGB")).save(
        GRAY_PREVIEW, dpi=(300, 300)
    )


def write_record(checks: dict) -> None:
    record = {
        "figure_id": FIGURE,
        "visual_revision": "redraw-fig6-20260912-title-simsun",
        "data_check": checks,
        "visual_contract": {
            "title": "全域含水率随时间的变化（黑色宋体）",
            "data_curves": "高对比彩色、统一实线、marker 冗余编码",
            "non_data_elements": "坐标轴、网格、刻度、轴标签、图例和标注统一黑色",
            "font": "SimSun / 宋体",
            "primary_xlim_h": [0, XMAX_H],
            "primary_ylim": [0, YMAX],
            "threshold": THRESHOLD,
            "reported_time_s": REPORT_TIME_S,
            "note_policy": "删除图内无关备注；限制条件保留在正式图注/正文",
        },
        "outputs": {
            "png_600dpi": PNG.relative_to(ROOT).as_posix(),
            "svg": SVG.relative_to(ROOT).as_posix(),
            "pdf": PDF.relative_to(ROOT).as_posix(),
            "color_preview": COLOR_PREVIEW.relative_to(ROOT).as_posix(),
            "grayscale_preview": GRAY_PREVIEW.relative_to(ROOT).as_posix(),
        },
    }
    for key, path in (
        ("png_sha256", PNG),
        ("svg_sha256", SVG),
        ("pdf_sha256", PDF),
        ("color_preview_sha256", COLOR_PREVIEW),
        ("grayscale_preview_sha256", GRAY_PREVIEW),
    ):
        record["outputs"][key] = sha256(path)
    (RECORD_DIR / "qa-report.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    data, checks = check_data()
    render(data)
    write_record(checks)
    print(json.dumps({
        "figure": FIGURE,
        "rows": checks["rows"],
        "data_equal": checks["data_equal"],
        "png_sha256": sha256(PNG),
        "svg_sha256": sha256(SVG),
        "pdf_sha256": sha256(PDF),
        "color_preview_sha256": sha256(COLOR_PREVIEW),
        "grayscale_preview_sha256": sha256(GRAY_PREVIEW),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

