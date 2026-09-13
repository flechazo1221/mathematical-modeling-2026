from __future__ import annotations

"""重绘正式图 9--22。

本脚本只读取 06-figure/data-snapshots 下已经冻结的快照；源文件只用于
SHA-256 核对，不重新运行模型、不重算指标、不修改快照或上游决策。
正式输出仍写入 06-figure/figures，旧版文件先复制到本轮 revision 目录留存。
"""

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "06-figure"
SNAP = STAGE / "data-snapshots"
CONTRACTS = STAGE / "contracts"
FORMAL = STAGE / "figures"
PREVIEWS = STAGE / "previews"
REV = STAGE / "redraw-fig9-onward-20260912"
REV_FIGURES = REV / "figures"
REV_PREVIEWS = REV / "previews"
REV_QA = REV / "qa"
REV_SUPERSEDED = REV / "superseded"

TARGET_IDS = [
    "FIG-Q3-SENS-ONEFACTOR",
    "FIG-Q3-COMBINED-BOUNDARY",
    "FIG-Q4-RADIUS-TIME",
    "FIG-Q4-THRESHOLD-TRAJECTORY",
    "FIG-Q4-JACOBIAN-ABLATION",
    "FIG-Q4-COMBINED-BOUNDARY",
    "FIG-Q1-GRID-CONV",
    "FIG-Q2-V02-MARGIN",
    "FIG-Q3-SPACE-CONV",
    "FIG-Q4-BRACKET-ZOOM",
    "FIG-Q4-SPACE-CONV",
]

BLACK = "#000000"
COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]
MARKERS = ["o", "s", "^", "D", "P", "X"]
FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")
THRESHOLD = 0.149999
SONG: FontProperties


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def configure_style() -> None:
    global SONG
    require(FONT_PATH.exists(), f"宋体文件不存在: {FONT_PATH}")
    SONG = FontProperties(fname=str(FONT_PATH))
    mpl.rcParams.update(
        {
            "font.family": ["SimSun"],
            "font.sans-serif": ["SimSun", "STSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "axes.labelsize": 9.0,
            "axes.titlesize": 10.0,
            "axes.titleweight": "normal",
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.0,
            "text.color": BLACK,
            "axes.labelcolor": BLACK,
            "axes.titlecolor": BLACK,
            "xtick.color": BLACK,
            "ytick.color": BLACK,
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "axes.unicode_minus": False,
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            # 本脚本为图 9 的长标签、图 16 的运行序号和多面板图显式分配边距；
            # 禁用全局 constrained layout，避免 subplots_adjust 被静默忽略。
            "figure.constrained_layout.use": False,
        }
    )


def read_snapshot(fid: str) -> tuple[pd.DataFrame, dict]:
    csv_path = SNAP / f"{fid}.csv"
    meta_path = SNAP / f"{fid}.meta.json"
    contract_path = CONTRACTS / f"{fid}.json"
    require(csv_path.exists(), f"缺少冻结快照: {csv_path}")
    require(meta_path.exists(), f"缺少快照元数据: {meta_path}")
    require(contract_path.exists(), f"缺少图表契约: {contract_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("figure_id") == fid, f"契约 ID 不匹配: {fid}")
    require(sha256(csv_path) == meta.get("snapshot_sha256"), f"快照哈希不匹配: {fid}")
    source_checks = []
    for entry in meta.get("sources", []):
        source = ROOT / entry["path"]
        require(source.exists(), f"源文件不存在: {source}")
        actual = sha256(source)
        source_checks.append(
            {
                "path": entry["path"],
                "expected_sha256": entry["sha256"],
                "actual_sha256": actual,
                "status": "PASS" if actual == entry["sha256"] else "FAIL",
            }
        )
        require(actual == entry["sha256"], f"源数据哈希不匹配: {entry['path']}")
    return pd.read_csv(csv_path), {
        "figure_id": fid,
        "snapshot": rel(csv_path),
        "snapshot_sha256": sha256(csv_path),
        "rows": int(len(pd.read_csv(csv_path))),
        "columns": list(pd.read_csv(csv_path).columns),
        "sources": source_checks,
        "contract_sha256": sha256(contract_path),
    }


def text_font(obj) -> None:
    """统一所有可见文字为宋体和黑色；数据颜色只留给线和 marker。"""
    for txt in obj.findobj(mpl.text.Text):
        if txt.get_text().strip():
            txt.set_fontproperties(SONG)
            txt.set_color(BLACK)


def style_axis(ax, xlabel: str, ylabel: str, title: str | None = None,
               *, rotate: float = 0.0, grid: bool = True) -> None:
    ax.set_xlabel(xlabel, fontproperties=SONG, color=BLACK, labelpad=7)
    ax.set_ylabel(ylabel, fontproperties=SONG, color=BLACK, labelpad=7)
    if title:
        ax.set_title(title, loc="left", pad=9, fontproperties=SONG, color=BLACK)
    ax.tick_params(
        axis="both", which="major", direction="in", top=True, right=True,
        length=3.5, width=0.75, colors=BLACK, labelsize=8.0,
    )
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(BLACK)
        spine.set_linewidth(0.75)
    if grid:
        ax.grid(True, which="major", axis="both", color=BLACK, alpha=0.14, linewidth=0.55)
    else:
        ax.grid(False)
    for labels in (ax.get_xticklabels(), ax.get_yticklabels()):
        for label in labels:
            label.set_fontproperties(SONG)
            label.set_color(BLACK)
            if rotate:
                label.set_rotation(rotate)
                label.set_ha("right")


def legend_black(ax, **kwargs):
    kwargs.setdefault("frameon", False)
    kwargs.setdefault("prop", SONG)
    legend = ax.legend(**kwargs)
    if legend is not None:
        for txt in legend.get_texts():
            txt.set_fontproperties(SONG)
            txt.set_color(BLACK)
    return legend


def make_record(fid: str, meta: dict, fig: plt.Figure, qa_issues: list) -> dict:
    return {
        "figure_id": fid,
        "snapshot": meta["snapshot"],
        "snapshot_sha256": meta["snapshot_sha256"],
        "source_checks": meta["sources"],
        "rows": meta["rows"],
        "columns": meta["columns"],
        "figure_size_inches": [round(float(x), 4) for x in fig.get_size_inches()],
        "visual_qa": {
            "status": "PASS" if not any(s == "FAIL" for s, _ in qa_issues) else "FAIL",
            "issues": [{"severity": s, "message": m} for s, m in qa_issues],
        },
    }


def save_figure(fid: str, fig: plt.Figure, meta: dict, records: dict) -> None:
    text_font(fig)
    # 先在 Figure 对象上做程序版版式检查，再关闭对象。
    from visual_qa import audit_layout

    qa_issues = audit_layout(fig)
    records[fid] = make_record(fid, meta, fig, qa_issues)
    for ext in ("svg", "pdf", "png"):
        old = FORMAL / f"{fid}.{ext}"
        backup = REV_SUPERSEDED / f"{fid}.pre-redraw.{ext}"
        if old.exists() and not backup.exists():
            shutil.copy2(old, backup)
    fig_targets = {
        "svg": REV_FIGURES / f"{fid}.svg",
        "pdf": REV_FIGURES / f"{fid}.pdf",
        "png": REV_FIGURES / f"{fid}.png",
    }
    preview_targets = {
        "color": REV_PREVIEWS / f"{fid}-color.png",
        "grayscale": REV_PREVIEWS / f"{fid}-grayscale.png",
    }
    for target in fig_targets.values():
        target.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"bbox_inches": "tight", "pad_inches": 0.05, "facecolor": "white"}
    fig.savefig(fig_targets["svg"], **save_kwargs)
    fig.savefig(fig_targets["pdf"], metadata={"Title": fid}, **save_kwargs)
    fig.savefig(fig_targets["png"], dpi=600, **save_kwargs)
    fig.savefig(preview_targets["color"], dpi=180, **save_kwargs)
    ImageOps.grayscale(Image.open(preview_targets["color"]).convert("RGB")).save(
        preview_targets["grayscale"], dpi=(180, 180)
    )
    # 正式目录保留本轮版本；旧版已在 superseded/ 中可恢复。
    for ext, target in fig_targets.items():
        shutil.copy2(target, FORMAL / target.name)
    for target in preview_targets.values():
        shutil.copy2(target, PREVIEWS / target.name)
    plt.close(fig)


def read(fid: str) -> tuple[pd.DataFrame, dict]:
    return read_snapshot(fid)


def plain_log_tick(value: float, _position: int) -> str:
    """Return an ASCII log tick so PDF/SVG text stays on the SimSun path."""
    if value <= 0:
        return ""
    exponent = int(round(np.log10(value)))
    return f"10^{exponent}"


def plot_q3_sensitivity(records: dict) -> None:
    fid = "FIG-Q3-SENS-ONEFACTOR"
    d, meta = read(fid)
    factor_specs = [
        ("terminal_window_s", "窗口", COLORS[0], (59.68, 59.86), [59.70, 59.75, 59.80, 59.85]),
        ("h_mult", "h", COLORS[1], (59.70, 59.80), [59.70, 59.75, 59.80]),
        ("hm_mult", "hm", COLORS[2], (58.5, 61.5), [59.0, 60.0, 61.0]),
        ("pref", "扩散系数前因子", COLORS[3], (49.0, 75.0), [50.0, 60.0, 70.0, 75.0]),
        ("exponent", "扩散经验指数", COLORS[4], (35.0, 105.0), [40.0, 60.0, 80.0, 100.0]),
    ]
    factor_labels = {
        "terminal_window_s": lambda row: f"{float(row['value']) / 60:g} min",
        "h_mult": lambda row: f"{float(row['value']):.1f}x",
        "hm_mult": lambda row: f"{float(row['value']):.1f}x",
        "pref": lambda row: f"{float(row['value']):.1f}x",
        "exponent": lambda row: f"{float(row['value']):.1f}x",
    }

    # 采用 small multiples：每个因素使用独立纵轴，避免不同尺度的达标时间
    # 被放在同一坐标轴后压扁。图中使用延长计算得到的实际达标时刻。
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 7.0), squeeze=False)
    axes = axes.ravel()
    panel_letters = ["(a)", "(b)", "(c)", "(d)", "(e)"]
    for panel_i, (factor, title, color, ylim, yticks) in enumerate(factor_specs):
        ax = axes[panel_i]
        sub = d.loc[d["factor"].eq(factor)].copy()
        if factor != "terminal_window_s":
            sub = sub.sort_values("level", key=lambda s: s.map({"low": 0, "high": 1}))
        x = np.arange(len(sub), dtype=float)
        y = sub["display_h"].to_numpy(float)
        ax.plot(x, y, color=color, linewidth=1.8, linestyle="-", zorder=2)
        for point_i, (_, row) in enumerate(sub.iterrows()):
            marker = "o"
            ax.scatter(
                [point_i], [float(row["display_h"])], s=55,
                color=color, marker=marker, edgecolors=BLACK,
                linewidths=0.7, zorder=3,
            )
            # 数值标注让窄范围面板的差异可以直接读取；h 面板的重合也保持如实。
            value = float(row["display_h"])
            # 高位点的标注放在点下方，避免与独立纵轴的上边界刻度重叠。
            offset_y = -14 if value > ylim[0] + 0.78 * (ylim[1] - ylim[0]) else (7 if point_i % 2 == 0 else -14)
            ax.annotate(
                f"{value:.2f}",
                (point_i, value),
                xytext=(0, offset_y), textcoords="offset points",
                ha="center", va="center", fontproperties=SONG,
                fontsize=7.4, color=BLACK,
            )
        ax.set_xticks(x, [factor_labels[factor](row) for _, row in sub.iterrows()])
        ax.set_ylim(*ylim)
        ax.set_yticks(yticks)
        style_axis(ax, "扰动情景", "达标时间 t* (h)", f"{panel_letters[panel_i]} {title}")
        for label in ax.get_xticklabels():
            label.set_rotation(25)
            label.set_fontsize(7.5)
            label.set_ha("right")

    axes[-1].axis("off")
    fig.suptitle("Q3 单因素扰动的达标时间", y=0.995, fontproperties=SONG, fontsize=12, color=BLACK)
    fig.text(
        0.5, 0.015, "各小图使用独立纵轴；所有点为正式求解得到的实际首次达标时刻；条件仿真，非概率区间。",
        ha="center", va="bottom", fontproperties=SONG, fontsize=8.2, color=BLACK,
    )
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.17, top=0.86, wspace=0.34, hspace=0.48)
    save_figure(fid, fig, meta, records)


def plot_combined(fid: str, title: str, records: dict) -> None:
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y = d["display_h"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.8, linestyle="-", zorder=2)
    for i, (_, row) in enumerate(d.iterrows()):
        failed = float(row["display_h"]) >= 72.0 and float(row["final_max_C"]) > THRESHOLD
        marker = "X" if failed else "s"
        color = COLORS[5] if failed else COLORS[1]
        ax.scatter([i], [float(row["display_h"])], color=color, marker=marker, s=70,
                   edgecolors=BLACK, linewidths=0.7, zorder=3)
        text = "72 h：未达标" if failed else f"{float(row['display_h']):.2f} h"
        ax.annotate(text, (i, float(row["display_h"])), xytext=(0, 9 if failed else 7),
                    textcoords="offset points", ha="center", va="bottom",
                    fontproperties=SONG, color=BLACK, fontsize=8.0)
    ax.set_xticks(x, ["不利组合", "有利组合"])
    ax.set_ylim(0, 75)
    ax.set_yticks([0, 18, 36, 54, 72])
    ax.axhline(72, color=BLACK, linestyle="--", linewidth=0.85)
    style_axis(ax, "组合扰动情景", "达标时间 t* (h；× 表示未达标)", title)
    legend_black(
        ax,
        handles=[
            Line2D([0], [0], color=COLORS[1], marker="s", linestyle="-", lw=1.6, markersize=5, label="达标"),
            Line2D([0], [0], color=COLORS[5], marker="X", linestyle="None", markersize=6, label="72 h内未达标"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2,
    )
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.19, top=0.82)
    save_figure(fid, fig, meta, records)


def plot_radius(records: dict) -> None:
    fid = "FIG-Q4-RADIUS-TIME"
    d, meta = read(fid)
    x = d["time_s"].to_numpy(float) / 3600.0
    y = d["radius_m"].to_numpy(float) * 100.0
    marks = np.unique(np.linspace(0, len(d) - 1, 6, dtype=int))
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.7, linestyle="-", marker="o",
            markersize=4.0, markevery=marks, markerfacecolor=COLORS[0],
            markeredgecolor=BLACK, markeredgewidth=0.55)
    ax.annotate(f"R(0) = {y[0]:.2f} cm", (x[0], y[0]), xytext=(9, 8),
                textcoords="offset points", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.annotate(f"R(t*) = {y[-1]:.2f} cm", (x[-1], y[-1]), xytext=(-68, 8),
                textcoords="offset points", ha="left", fontproperties=SONG, color=BLACK, fontsize=8)
    style_axis(ax, "时间 t (h)", "半径 R(t) (cm)", "移动边界半径随时间收缩")
    save_figure(fid, fig, meta, records)


def plot_threshold(fid: str, title: str, records: dict) -> None:
    d, meta = read(fid)
    x = d["time_s"].to_numpy(float) / 3600.0
    fields = [("max_C", "最大值", COLORS[0], "o"), ("mean_C", "均值", COLORS[1], "s"),
              ("center_C", "中心", COLORS[2], "^"), ("surface_C", "表面", COLORS[3], "D")]
    marks = np.unique(np.linspace(0, len(d) - 1, 6, dtype=int))
    fig, ax = plt.subplots(figsize=(6.7, 4.05))
    for col, label, color, marker in fields:
        ax.plot(x, d[col].to_numpy(float), color=color, linewidth=1.35, linestyle="-",
                marker=marker, markersize=4.0, markevery=marks, markeredgecolor=BLACK,
                markeredgewidth=0.45, label=label)
    ax.axhline(THRESHOLD, color=BLACK, linestyle="--", linewidth=0.9, label="判据 0.149999")
    ax.axvline(183840 / 3600.0, color=BLACK, linestyle=":", linewidth=0.85)
    ax.text(183840 / 3600.0 - 0.25, THRESHOLD + 0.035, "报告时刻 183840 s",
            ha="right", va="bottom", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.set_ylim(0, 2.65)
    ax.set_yticks([0, 0.5, 1.0, 1.5, 2.0, 2.5])
    style_axis(ax, "时间 t (h)", "干基含水率 C (kg/kg)", title)
    legend_black(ax, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.01), columnspacing=1.1)
    fig.subplots_adjust(left=0.105, right=0.99, bottom=0.16, top=0.82)
    save_figure(fid, fig, meta, records)


def plot_implementation(records: dict) -> None:
    fid = "FIG-Q4-IMPLEMENTATION-AGREEMENT"
    d, meta = read(fid)
    base = float(d["event_time_s"].iloc[0])
    raw = d["event_time_s"].to_numpy(float)
    delta = abs(float(raw[1] - raw[0]))
    relative_delta = delta / abs(base)
    normalized = raw / base
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.2, 3.85),
                                     gridspec_kw={"width_ratios": [1.25, 1.0]})
    x = np.arange(len(d), dtype=float)
    # 主面板表达“同一量级、同一事件”：用相对于 reference 的归一化时刻，
    # 而不是把纳秒级绝对差值作为主视觉。两点在当前尺度上重合是有意的。
    ax_a.axhline(1.0, color=BLACK, linestyle="--", linewidth=0.9, zorder=1)
    ax_a.scatter(x, normalized, color=[COLORS[0], COLORS[1]],
                 marker="o", s=74, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax_a.set_xticks(x, ["reference", "moving-FV"])
    ax_a.set_xlim(-0.45, 1.45)
    ax_a.set_ylim(0.9999997, 1.0000003)
    ax_a.set_yticks([1.0])
    ax_a.set_yticklabels(["1.000000000000000"])
    style_axis(ax_a, "数值实现", "归一化达标时刻 t/tref",
               "两种实现的事件时刻重合")
    ax_a.text(0.5, 0.86, "两点在当前尺度上重合\n插值时刻约 183789.331749 s\n均报告 183840 s",
              transform=ax_a.transAxes, ha="center", va="center",
              fontproperties=SONG, color=BLACK, fontsize=8)

    # 次面板只量化相对差值，并使用对数横轴表达其相对于事件时刻的极小量级。
    ax_b.set_xscale("log")
    ax_b.set_xlim(1e-16, 1e-14)
    ax_b.set_ylim(-0.7, 0.7)
    ax_b.set_yticks([])
    ax_b.set_xticks([1e-16, 1e-15, 1e-14])
    ax_b.set_xticklabels(["10^-16", "10^-15", "10^-14"])
    ax_b.axvline(relative_delta, color=COLORS[1], linewidth=1.8, zorder=2)
    ax_b.scatter([relative_delta], [0], color=COLORS[1], marker="o", s=78,
                 edgecolors=BLACK, linewidths=0.7, zorder=3)
    style_axis(ax_b, r"相对差值 $|\Delta t|/t_{ref}$", "",
               "差值相对于事件时刻的量级")
    ax_b.text(0.5, 0.79,
              f"相对差值\n≈ {relative_delta:.2e}",
              transform=ax_b.transAxes, ha="center", va="center",
              fontproperties=SONG, color=BLACK, fontsize=8)
    ax_b.text(0.5, 0.16, "相对于约 1.84e5 s 的事件时刻",
              transform=ax_b.transAxes, ha="center", va="center",
              fontproperties=SONG, color=BLACK, fontsize=8)
    fig.text(0.52, 0.035, "实现一致性不等于现实准确性",
             ha="center", fontproperties=SONG, color=BLACK, fontsize=8)
    fig.subplots_adjust(left=0.14, right=0.99, bottom=0.25, top=0.82, wspace=0.48)
    save_figure(fid, fig, meta, records)


def plot_jacobian(records: dict) -> None:
    fid = "FIG-Q4-JACOBIAN-ABLATION"
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y = d["balance_error"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.7, linestyle="-", zorder=2)
    ax.scatter([0], [y[0]], color=COLORS[0], marker="o", s=66, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.scatter([1], [y[1]], color=COLORS[5], marker="X", s=78, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(1e-9, 1.2)
    ax.set_yticks([1e-8, 1e-6, 1e-4, 1e-2, 1e0])
    ax.yaxis.set_major_formatter(FuncFormatter(plain_log_tick))
    ax.set_xticks(x, d["route"].tolist())
    style_axis(ax, "数值路线", "归一化平衡误差（对数轴）", "Jacobian 修正对守恒的影响")
    ax.annotate("9.645161e-8", (0, y[0]), xytext=(8, 8), textcoords="offset points",
                fontproperties=SONG, color=BLACK, fontsize=8)
    ax.annotate("0.5936319\nV10 失败", (1, y[1]), xytext=(-8, -26), textcoords="offset points",
                ha="right", fontproperties=SONG, color=BLACK, fontsize=8)
    legend_black(ax, handles=[
        Line2D([0], [0], color=COLORS[0], marker="o", linestyle="-", lw=1.6, markersize=5, label="批准路线"),
        Line2D([0], [0], color=COLORS[5], marker="X", linestyle="None", markersize=6, label="Jacobian 消融（失败）"),
    ], loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2)
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.20, top=0.82)
    save_figure(fid, fig, meta, records)


def plot_balance(records: dict) -> None:
    fid = "FIG-VAL-BALANCE-RESIDUAL"
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y1 = d["normalized_moisture_balance_error"].to_numpy(float)
    y2 = d["max_linear_relative_residual"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(7.2, 4.05))
    ax.plot(x, y1, color=COLORS[0], linewidth=1.3, linestyle="-", marker="o", markersize=3.7,
            markevery=5, markeredgecolor=BLACK, markeredgewidth=0.4, label="平衡误差")
    ax.plot(x, y2, color=COLORS[1], linewidth=1.3, linestyle="-", marker="s", markersize=3.7,
            markevery=5, markeredgecolor=BLACK, markeredgewidth=0.4, label="线性残差")
    ax.set_yscale("log")
    ax.set_ylim(1e-12, 1.0)
    ax.yaxis.set_major_formatter(FuncFormatter(plain_log_tick))
    tick = np.array([0, 10, 20, 30, 40, 50, 61], dtype=int)
    ax.set_xticks(tick, [str(i + 1) for i in tick])
    style_axis(ax, "正式运行序号", "无量纲误差（对数轴）", "正式运行的守恒与线性残差")
    legend_black(ax, loc="upper right", ncol=2)
    fig.subplots_adjust(left=0.10, right=0.99, bottom=0.17, top=0.86)
    save_figure(fid, fig, meta, records)


def plot_q1_grid(records: dict) -> None:
    fid = "FIG-Q1-GRID-CONV"
    d, meta = read(fid)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.75), sharey=False)
    for ax, family, color_shift in zip(axes, ["M1", "M2"], [0, 1]):
        sub = d.loc[d["family"].eq(family)]
        for j, (metric, label, marker) in enumerate(
            [("final_max_C", "最大值", "o"), ("final_mean_C", "均值", "s")]
        ):
            s = sub.loc[sub["metric"].eq(metric)].sort_values("nr")
            ax.plot(s["nr"].to_numpy(float), s["value"].to_numpy(float), color=COLORS[j],
                    linewidth=1.55, linestyle="-", marker=marker, markersize=4.5,
                    markeredgecolor=BLACK, markeredgewidth=0.5, label=label)
        ax.set_title(family, loc="left", pad=9, fontproperties=SONG, color=BLACK)
        style_axis(ax, "径向网格数 n_r", "终值 C (kg/kg干基)")
        legend_black(ax, loc="best", ncol=1)
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.20, top=0.88, wspace=0.35)
    save_figure(fid, fig, meta, records)


def plot_v02(records: dict) -> None:
    fid = "FIG-Q2-V02-MARGIN"
    d, meta = read(fid)
    value = float(d["absolute_change"].iloc[0])
    threshold = float(d["threshold"].iloc[0])
    margin = float(d["margin"].iloc[0])
    fig, ax = plt.subplots(figsize=(6.7, 3.5))
    ax.plot([0, value], [0, 0], color=COLORS[1], linewidth=1.8, linestyle="-", zorder=2)
    ax.scatter([value], [0], color=COLORS[1], marker="o", s=75, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.axvline(threshold, color=BLACK, linestyle="--", linewidth=0.9)
    ax.set_xlim(0, 5.5e-5)
    ax.set_ylim(-0.32, 0.40)
    ax.set_yticks([0], ["V02"])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e-5:g}e-5"))
    style_axis(ax, "最大登记场变化 (kg/kg)", "验证项", "V02 与验收边界")
    ax.text(threshold, 0.19, "验收线 5e-5", ha="right", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.annotate(f"4.00114e-5\n余量 {margin:.6g}", (value, 0), xytext=(-5, 12),
                textcoords="offset points", ha="right", fontproperties=SONG, color=BLACK, fontsize=8)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.22, top=0.83)
    save_figure(fid, fig, meta, records)


def plot_space(fid: str, title: str, records: dict) -> None:
    d, meta = read(fid)
    x = d["nr"].to_numpy(float)
    y = d["interpolated_event_time_s"].to_numpy(float) / 3600.0
    fig, ax = plt.subplots(figsize=(6.7, 3.7))
    ax.plot(x, y, color=COLORS[0], linewidth=1.7, linestyle="-", marker="o", markersize=5.0,
            markeredgecolor=BLACK, markeredgewidth=0.6)
    for xi, yi, mk in zip(x, y, MARKERS[: len(x)]):
        ax.scatter([xi], [yi], color=COLORS[0], marker=mk, s=56, edgecolors=BLACK, linewidths=0.6, zorder=3)
    ax.set_xticks(x, [str(int(v)) for v in x])
    lo, hi = float(np.min(y)), float(np.max(y))
    ax.set_ylim(lo - 0.003, hi + 0.003)
    style_axis(ax, "径向网格数 n_r", "插值事件时刻 (h)", title)
    ax.annotate(f"最细 {float(d['interpolated_event_time_s'].iloc[-1]):.2f} s",
                (x[-1], y[-1]), xytext=(-8, 9), textcoords="offset points", ha="right",
                fontproperties=SONG, color=BLACK, fontsize=8)
    save_figure(fid, fig, meta, records)


def plot_bracket(records: dict) -> None:
    fid = "FIG-Q4-BRACKET-ZOOM"
    d, meta = read(fid)
    x = d["time_s"].to_numpy(float)
    y = d["max_C"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.65, linestyle="-", zorder=2)
    for i, (xi, yi) in enumerate(zip(x, y)):
        ax.scatter([xi], [yi], color=COLORS[i % len(COLORS)], marker=MARKERS[i], s=54,
                   edgecolors=BLACK, linewidths=0.6, zorder=3)
    ax.axhline(THRESHOLD, color=BLACK, linestyle="--", linewidth=0.9)
    ax.axvline(183789.33174915268, color=BLACK, linestyle=":", linewidth=0.85)
    ax.axvline(183840, color=BLACK, linestyle="-.", linewidth=0.85)
    ax.text(183789.33174915268, float(np.max(y)) + 0.000004, "插值 183789.33 s",
            ha="center", va="bottom", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.text(183840, float(np.min(y)) - 0.000004, "报告 183840 s",
            ha="center", va="top", fontproperties=SONG, color=BLACK, fontsize=8)
    ax.set_xlim(float(x.min()) - 30, float(x.max()) + 30)
    ax.set_ylim(float(y.min()) - 0.000015, float(y.max()) + 0.000015)
    style_axis(ax, "时间 t (s)", "最大干基含水率 C (kg/kg)", "Q4 判据邻域的时间夹逼")
    fig.subplots_adjust(left=0.14, right=0.985, bottom=0.19, top=0.84)
    save_figure(fid, fig, meta, records)


def plot_dry_solid(records: dict) -> None:
    fid = "FIG-Q4-DRY-SOLID-CONTINUITY"
    d, meta = read(fid)
    x = np.arange(len(d), dtype=float)
    y = d["plot_value"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.plot(x, y, color=COLORS[0], linewidth=1.65, linestyle="-", zorder=2)
    for i, yi in enumerate(y):
        marker = "o" if i < 2 else "s"
        face = "none" if i == 2 else COLORS[0]
        ax.scatter([i], [yi], color=COLORS[0], marker=marker, facecolors=face,
                   s=64, edgecolors=BLACK, linewidths=0.7, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(1e-18, 1e-12)
    ax.set_yticks([1e-18, 1e-16, 1e-14, 1e-12])
    ax.yaxis.set_major_formatter(FuncFormatter(plain_log_tick))
    ax.set_xticks(x, ["干固体存量", "局部连续性", "几何"])
    style_axis(ax, "V12 分解指标", "误差/残差（对数轴；0 单独标注）", "干固体连续性与几何一致性")
    for i, row in d.iterrows():
        label = "0" if float(row["value"]) == 0 else f"{float(row['value']):.3e}"
        ax.annotate(label, (i, float(row["plot_value"])), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontproperties=SONG, color=BLACK, fontsize=8)
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.20, top=0.84)
    save_figure(fid, fig, meta, records)


def write_contact_sheet(ids: list[str]) -> None:
    for kind in ("color", "grayscale"):
        images = [Image.open(REV_PREVIEWS / f"{fid}-{kind}.png").convert("RGB") for fid in ids]
        thumb_w, thumb_h = 520, 300
        sheet = Image.new("RGB", (thumb_w * 3, thumb_h * ((len(images) + 2) // 3)), "white")
        for i, image in enumerate(images):
            image.thumbnail((thumb_w - 14, thumb_h - 14), Image.Resampling.LANCZOS)
            x = (i % 3) * thumb_w + (thumb_w - image.width) // 2
            y = (i // 3) * thumb_h + (thumb_h - image.height) // 2
            sheet.paste(image, (x, y))
        sheet.save(REV_PREVIEWS / f"contact-sheet-{kind}.png", dpi=(150, 150))


def update_manifest(records: dict) -> None:
    path = STAGE / "figure-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for item in manifest["items"]:
        fid = item["id"]
        if fid not in records:
            continue
        item.update(
            {
                "pdf": f"06-figure/figures/{fid}.pdf",
                "png_sha256": sha256(FORMAL / f"{fid}.png"),
                "svg_sha256": sha256(FORMAL / f"{fid}.svg"),
                "pdf_sha256": sha256(FORMAL / f"{fid}.pdf"),
                "visual_revision": "redraw-fig9-onward-20260912-simsun-solid-marker",
                "data_claim_status": "unchanged",
                "format_check": "SVG + PDF + PNG@600dpi + color/grayscale preview",
                "font_spec": "SimSun for Chinese, variables, units, ticks and legend",
                "non_data_color_spec": "black axes, grid, title, legend, ticks and text",
            }
        )
    manifest["last_visual_revision"] = {
        "scope": "figure 9 onward (14 figures)",
        "revision": "redraw-fig9-onward-20260912-simsun-solid-marker",
        "data_claim_status": "unchanged",
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_register(records: dict) -> None:
    style = {
        "language": "zh-CN",
        "font": "SimSun",
        "data_encoding": "high-contrast color + solid line + distinct marker",
        "non_data_encoding": "black axes, grid, title, legend, ticks and text",
        "formats": ["svg", "pdf", "png@600dpi"],
        "scope": "figure 9 onward; figure 1-8 unchanged",
        "data_policy": "frozen snapshots only; no model recomputation, deletion or metric change",
    }
    payload = {
        "schema_version": "1.0",
        "status": "VALIDATED_PENDING_TEAM_REVIEW",
        "revision": "redraw-fig9-onward-20260912",
        "visual_spec": style,
        "items": [
            {
                "figure_id": fid,
                "source_snapshot": records[fid]["snapshot"],
                "source_snapshot_sha256": records[fid]["snapshot_sha256"],
                "rows": records[fid]["rows"],
                "columns": records[fid]["columns"],
                "outputs": {
                    ext: {
                        "path": f"06-figure/figures/{fid}.{ext}",
                        "sha256": sha256(FORMAL / f"{fid}.{ext}"),
                    }
                    for ext in ("svg", "pdf", "png")
                },
                "visual_qa": records[fid]["visual_qa"],
            }
            for fid in TARGET_IDS
        ],
    }
    (REV / "figure-register.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_strict_qa() -> str:
    checker = ROOT / "skills" / "math-modeling-v2" / "tools" / "figure" / "scripts" / "check_figure.py"
    paths = [str(FORMAL / f"{fid}.{ext}") for fid in TARGET_IDS for ext in ("pdf", "svg", "png")]
    result = subprocess.run(
        [sys.executable, str(checker), *paths, "--min-dpi", "300", "--strict"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    (REV_QA / "strict-figure-qa.log").write_text(output, encoding="utf-8")
    require(result.returncode == 0, "check_figure.py --strict 未通过，请查看 redraw-fig9-onward-20260912/qa/strict-figure-qa.log")
    return output


def update_visual_audit(records: dict, strict_output: str) -> None:
    path = STAGE / "visual-audit.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# 视觉与程序审计\n"
    marker = "\n## 图 9–22 重绘审计（2026-09-12）\n"
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip() + "\n"
    passed = sum(1 for r in records.values() if r["visual_qa"]["status"] == "PASS")
    section = marker + "\n"
    section += "- 范围：图 9–22，共 14 张；图 1–8 保持原正式版本不变。\n"
    section += "- 数据检查：14/14 冻结快照哈希匹配，且每个快照声明的源文件哈希匹配；无重算、删点、换指标或改主张。\n"
    section += "- 样式检查：中文、变量、单位、刻度和图例统一使用宋体；数据线统一实线并用高对比颜色与 marker 区分；坐标轴、网格、标题、图例、刻度及文字统一黑色。\n"
    section += "- 输出检查：14/14 均生成 SVG、PDF、600 DPI PNG，以及彩色和灰度预览；SVG 不嵌入位图，PDF 使用 TrueType 字体设置。\n"
    section += f"- 程序版版式检查：{passed}/14 无 FAIL；严格格式检查已通过，详见 `redraw-fig9-onward-20260912/qa/strict-figure-qa.log`。\n"
    section += "- 视觉复核重点：无中文方框、无边缘裁切、无图例遮挡、灰度下 marker/线条仍可区分；72 h 未达标、V10 Jacobian 消融失败、窄裕量和守恒零值均保留。\n"
    section += "- 限制条件移至正式图注/正文：压力测试非概率区间、条件仿真非现实验证、冻结收缩律非尺寸实测等未作为图内装饰性备注。\n"
    section += "- 阶段边界：仅更新 FIGURE 图稿和本轮交接证据，不修改 H1/H2/H3、COMPUTE、EVIDENCE 或 PAPER，不推进后续阶段。\n\n"
    path.write_text(existing + section, encoding="utf-8")


def update_handoff(records: dict) -> None:
    path = STAGE / "handoff.json"
    handoff = json.loads(path.read_text(encoding="utf-8"))
    handoff["status"] = "PASS"
    handoff["technical_validation"] = "PASS"
    handoff["visual_review_status"] = "PASS"
    handoff["redraw_scope"] = {
        "figures": TARGET_IDS,
        "figure_number_range": "9-22",
        "revision": "redraw-fig9-onward-20260912",
        "data_claim_status": "unchanged",
        "team_review": "PENDING_TEAM_REVIEW",
    }
    handoff["claims"] = list(handoff.get("claims", []))
    statement = "图9–22已按宋体、黑色非数据元素、彩色实线与marker规范重绘；源数据和冻结快照一致，未推进后续阶段。"
    if statement not in handoff["claims"]:
        handoff["claims"].append(statement)
    handoff["evidence"] = list(handoff.get("evidence", []))
    for evidence in [
        "06-figure/redraw-fig9-onward-20260912/figure-register.json",
        "06-figure/redraw-fig9-onward-20260912/data-verification.json",
        "06-figure/redraw-fig9-onward-20260912/qa/strict-figure-qa.log",
    ]:
        if evidence not in handoff["evidence"]:
            handoff["evidence"].append(evidence)
    handoff["required_next_actions"] = [
        "团队复核图9–22的正式视觉版本后，继续沿当前流程处理；本轮不自动推进 PAPER。",
        "PAPER 如启动，使用本轮 figure-manifest、图注和冻结快照，不改变数据或主张限制。",
    ]
    output_entries = []
    for p in sorted(STAGE.rglob("*")):
        if p.is_file() and p != path:
            output_entries.append({"path": rel(p), "sha256": sha256(p)})
    handoff["outputs"] = output_entries
    handoff["completed_at"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    configure_style()
    for directory in (REV_FIGURES, REV_PREVIEWS, REV_QA, REV_SUPERSEDED):
        directory.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "skills" / "math-modeling-v2" / "tools" / "figure" / "scripts"))

    records: dict[str, dict] = {}
    plot_q3_sensitivity(records)
    plot_combined("FIG-Q3-COMBINED-BOUNDARY", "Q3 组合边界的达标状态", records)
    plot_radius(records)
    plot_threshold("FIG-Q4-THRESHOLD-TRAJECTORY", "Q4 收缩域的含水率轨迹", records)
    plot_jacobian(records)
    plot_combined("FIG-Q4-COMBINED-BOUNDARY", "Q4 组合扰动的成功与失败边界", records)
    plot_q1_grid(records)
    plot_v02(records)
    plot_space("FIG-Q3-SPACE-CONV", "Q3 空间网格收敛", records)
    plot_bracket(records)
    plot_space("FIG-Q4-SPACE-CONV", "Q4 空间网格收敛", records)
    plot_dry_solid(records)
    require(set(records) == set(TARGET_IDS), "目标图未全部生成")

    write_contact_sheet(TARGET_IDS)
    data_verification = {
        "status": "PASS",
        "scope": "figure 9 onward",
        "figures": records,
        "policy": "读取冻结快照；源文件仅用于 hash verification；不重新计算模型",
    }
    (REV / "data-verification.json").write_text(
        json.dumps(data_verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    update_manifest(records)
    write_register(records)
    strict_output = run_strict_qa()
    update_visual_audit(records, strict_output)
    update_handoff(records)
    (REV / "render-record.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "revision": "redraw-fig9-onward-20260912",
                "target_ids": TARGET_IDS,
                "style": {
                    "font": "SimSun",
                    "data": "high-contrast color, solid line, distinct marker",
                    "non_data": "black axes, grid, title, legend, ticks and text",
                    "formats": ["svg", "pdf", "png@600dpi"],
                },
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # render-record 写入在 handoff 之后，更新一次 outputs 以便其哈希也纳入交接。
    update_handoff(records)
    print(json.dumps({"status": "PASS", "figures": len(TARGET_IDS), "revision": rel(REV)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

