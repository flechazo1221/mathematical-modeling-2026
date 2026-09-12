from __future__ import annotations

"""将 Q3/Q4 空间收敛证据排成一张双面板图。

只读取已经冻结的 Q3/Q4 快照和其共同源文件；不重算模型、不改变指标，
输出写入独立的 merge-q3-q4-space-conv-20260912 目录，原正式图和清单不覆盖。
"""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "06-figure"
SNAP = STAGE / "data-snapshots"
CONTRACT = STAGE / "contracts" / "FIG-Q3Q4-SPACE-CONV.json"
OUT = STAGE / "merge-q3-q4-space-conv-20260912"
FIGURES = OUT / "figures"
PREVIEWS = OUT / "previews"
QA = OUT / "qa"
FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")
BLACK = "#000000"
COLORS = {"Q3": "#0072B2", "Q4": "#D55E00"}
MARKERS = {"Q3": "o", "Q4": "s"}
FONT: FontProperties


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def configure_style() -> None:
    global FONT
    require(FONT_PATH.exists(), f"宋体文件不存在: {FONT_PATH}")
    FONT = FontProperties(fname=str(FONT_PATH))
    mpl.rcParams.update(
        {
            "font.family": ["SimSun"],
            "font.sans-serif": ["SimSun", "STSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "axes.labelsize": 9.0,
            "axes.titlesize": 9.5,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
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
            "figure.constrained_layout.use": False,
        }
    )


def read_snapshot(fid: str, expected_sha: str) -> tuple[pd.DataFrame, dict]:
    csv_path = SNAP / f"{fid}.csv"
    meta_path = SNAP / f"{fid}.meta.json"
    require(csv_path.exists(), f"缺少快照: {csv_path}")
    require(meta_path.exists(), f"缺少快照元数据: {meta_path}")
    require(sha256(csv_path) == expected_sha, f"快照哈希不匹配: {fid}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    require(meta.get("snapshot_sha256") == expected_sha, f"元数据哈希不匹配: {fid}")
    source = ROOT / "04-compute" / "results" / "threshold-grid-convergence.csv"
    require(source.exists(), f"缺少共同源文件: {source}")
    require(sha256(source) == "8ba2aa18d42e13169db3f569cb7a6c1d5e8fd836c7f6818a8d0eb42fefd811f6", "共同源文件哈希不匹配")
    data = pd.read_csv(csv_path)
    require(len(data) == 3 and set(data["scope"]) == {fid.split("-")[1]}, f"快照行或 scope 异常: {fid}")
    required = {"nr", "interpolated_event_time_s", "adjacent_change_s", "fixed_dt_s"}
    require(required.issubset(data.columns), f"快照缺少字段: {fid}")
    require(set(data["fixed_dt_s"].astype(int)) == {60}, f"时间步口径异常: {fid}")
    return data, meta


def style_axis(ax: plt.Axes, xlabel: str, ylabel: str | None, title: str) -> None:
    ax.set_title(title, fontproperties=FONT, color=BLACK, pad=8)
    ax.set_xlabel(xlabel, fontproperties=FONT, color=BLACK, labelpad=5)
    if ylabel:
        ax.set_ylabel(ylabel, fontproperties=FONT, color=BLACK, labelpad=6)
    ax.grid(True, color=BLACK, alpha=0.14, linewidth=0.55)
    for spine in ax.spines.values():
        spine.set_color(BLACK)
        spine.set_linewidth(0.75)
    for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        label.set_fontproperties(FONT)
        label.set_color(BLACK)


def plot_panel(ax: plt.Axes, data: pd.DataFrame, scope: str, title: str, ylabel: str | None) -> None:
    x = data["nr"].to_numpy(float)
    y = data["interpolated_event_time_s"].to_numpy(float) / 3600.0
    color = COLORS[scope]
    ax.plot(x, y, color=color, linewidth=1.7, linestyle="-", zorder=2)
    ax.scatter(x, y, color=color, marker=MARKERS[scope], s=50, edgecolors=BLACK,
               linewidths=0.65, zorder=3)
    ax.set_xticks(x, [str(int(value)) for value in x])
    ax.set_xlim(float(x.min()) - 8, float(x.max()) + 8)
    style_axis(ax, "径向网格数 n_r", ylabel, title)
    ax.yaxis.set_major_locator(MultipleLocator(1.0))
    final = float(data["interpolated_event_time_s"].iloc[-1])
    adjacent = float(data["adjacent_change_s"].iloc[-1])
    annotation_offset = (-8, -12) if scope == "Q3" else (-8, 10)
    annotation_va = "top" if scope == "Q3" else "bottom"
    ax.annotate(
        f"最细 {final / 3600:.2f} h\n相邻变化 {adjacent:.2f} s",
        (x[-1], y[-1]),
        xytext=annotation_offset,
        textcoords="offset points",
        ha="right",
        va=annotation_va,
        fontproperties=FONT,
        color=BLACK,
        fontsize=7.8,
    )


def main() -> None:
    configure_style()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(contract["figure_id"] == "FIG-Q3Q4-SPACE-CONV", "合并图契约 ID 异常")
    q3, q3_meta = read_snapshot("FIG-Q3-SPACE-CONV", contract["source_snapshots"][0]["sha256"])
    q4, q4_meta = read_snapshot("FIG-Q4-SPACE-CONV", contract["source_snapshots"][1]["sha256"])

    FIGURES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.85), sharey=True)
    plot_panel(axes[0], q3, "Q3", "（a）Q3 固定半径", "插值事件时刻 t* (h)")
    plot_panel(axes[1], q4, "Q4", "（b）Q4 收缩移动边界", None)
    axes[0].set_ylim(50.5, 58.2)
    fig.suptitle("Q3/Q4 事件时刻的空间网格收敛", fontproperties=FONT, color=BLACK, fontsize=10.5, y=0.98)
    fig.text(0.5, 0.005, "两面板均固定时间步 Δt = 60 s；仅检验空间离散数值稳定性",
             ha="center", va="bottom", fontproperties=FONT, color=BLACK, fontsize=7.8)
    fig.subplots_adjust(left=0.095, right=0.985, bottom=0.19, top=0.83, wspace=0.20)

    sys.path.insert(0, str(ROOT / "skills" / "math-modeling-v2" / "tools" / "figure" / "scripts"))
    from visual_qa import audit_layout

    issues = audit_layout(fig)
    require(not any(severity == "FAIL" for severity, _ in issues), f"程序版式检查失败: {issues}")
    save_kwargs = {"bbox_inches": "tight", "pad_inches": 0.05, "facecolor": "white"}
    formal = {}
    for ext in ("svg", "pdf", "png"):
        target = FIGURES / f"FIG-Q3Q4-SPACE-CONV.{ext}"
        if ext == "png":
            fig.savefig(target, dpi=600, **save_kwargs)
        elif ext == "pdf":
            fig.savefig(target, metadata={"Title": "FIG-Q3Q4-SPACE-CONV"}, **save_kwargs)
        else:
            fig.savefig(target, **save_kwargs)
        formal[ext] = {"path": str(target.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(target)}
    color = PREVIEWS / "FIG-Q3Q4-SPACE-CONV-color.png"
    gray = PREVIEWS / "FIG-Q3Q4-SPACE-CONV-grayscale.png"
    fig.savefig(color, dpi=180, **save_kwargs)
    ImageOps.grayscale(Image.open(color).convert("RGB")).save(gray, dpi=(180, 180))
    plt.close(fig)

    checker = ROOT / "skills" / "math-modeling-v2" / "tools" / "figure" / "scripts" / "check_figure.py"
    paths = [str(FIGURES / f"FIG-Q3Q4-SPACE-CONV.{ext}") for ext in ("pdf", "svg", "png")]
    result = subprocess.run([sys.executable, str(checker), *paths, "--min-dpi", "300", "--strict"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    qa_output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    (QA / "strict-figure-qa.log").write_text(qa_output, encoding="utf-8")
    require(result.returncode == 0, "check_figure.py --strict 未通过")

    record = {
        "status": "PASS",
        "figure_id": "FIG-Q3Q4-SPACE-CONV",
        "revision": "merge-q3-q4-space-conv-20260912",
        "source_snapshots": [
            {"figure_id": "FIG-Q3-SPACE-CONV", "sha256": q3_meta["snapshot_sha256"]},
            {"figure_id": "FIG-Q4-SPACE-CONV", "sha256": q4_meta["snapshot_sha256"]},
        ],
        "source_file_sha256": "8ba2aa18d42e13169db3f569cb7a6c1d5e8fd836c7f6818a8d0eb42fefd811f6",
        "data_claim_status": "unchanged",
        "fixed_dt_s": 60,
        "layout_qa": {"status": "PASS", "issues": [{"severity": s, "message": m} for s, m in issues]},
        "outputs": formal,
        "previews": {
            "color": str(color.relative_to(ROOT)).replace("\\", "/"),
            "grayscale": str(gray.relative_to(ROOT)).replace("\\", "/"),
        },
        "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "promotion_note": "本合并图为独立 FIGURE 版本；原 Q3/Q4 单图和 H3/EVIDENCE 清单未覆盖，待团队复核后决定是否替换。",
    }
    (OUT / "merge-record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "图注.md").write_text(
        "## 合并附录图（FIG-Q3Q4-SPACE-CONV）\n\n"
        "Q3 与 Q4 的事件时刻随空间网格如何稳定？左图为固定半径 Q3，右图为收缩移动边界 Q4；两者均固定时间步 60 s。"
        "最细网格 Q3 为 206818.7114 s、Q4 为 183789.3317 s；相邻细化变化分别为 35.1182 s 和 9.5187 s。"
        "限定：仅证明空间离散数值稳定，不替代时间步验证、守恒检查或现实准确性验证。\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "output": str(OUT.relative_to(ROOT)).replace("\\", "/")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
