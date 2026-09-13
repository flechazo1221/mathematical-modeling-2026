from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
FIGDIR = ROOT / "06-figure" / "figures"
PREV = ROOT / "06-figure" / "previews"
SNAP = ROOT / "06-figure" / "data-snapshots"
CONTRACT = ROOT / "06-figure" / "contracts"
FIGDIR.mkdir(exist_ok=True)
PREV.mkdir(exist_ok=True)
SNAP.mkdir(exist_ok=True)
CONTRACT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "Microsoft YaHei", "font.size": 9,
    "axes.unicode_minus": False, "svg.fonttype": "none",
})
BLUE, ORANGE, GREEN, BLACK, GRID = "#0072B2", "#E69F00", "#009E73", "#111111", "#D9D9D9"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_figure(fid: str, fig) -> None:
    fig.set_size_inches(9.5, 4.6)
    fig.savefig(FIGDIR / f"{fid}.svg", bbox_inches="tight")
    fig.savefig(FIGDIR / f"{fid}.pdf", bbox_inches="tight")
    fig.savefig(FIGDIR / f"{fid}.png", dpi=600, bbox_inches="tight")
    fig.savefig(PREV / f"{fid}-color.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    ImageOps.grayscale(Image.open(PREV / f"{fid}-color.png").convert("RGB")).save(PREV / f"{fid}-grayscale.png")


def write_snapshot(fid: str, df: pd.DataFrame, source: Path) -> None:
    path = SNAP / f"{fid}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    meta = {
        "figure_id": fid,
        "snapshot": path.relative_to(ROOT).as_posix(),
        "snapshot_sha256": sha(path),
        "sources": [{"path": source.relative_to(ROOT).as_posix(), "sha256": sha(source)}],
        "rows": len(df),
        "columns": list(df.columns),
    }
    (SNAP / f"{fid}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    contract_path = CONTRACT / f"{fid}.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["snapshot"] = path.relative_to(ROOT).as_posix()
    contract["snapshot_sha256"] = sha(path)
    contract["source_files"] = [{"path": source.relative_to(ROOT).as_posix(), "sha256": sha(source)}]
    contract["visual_revision"] = "user-revision-20260913"
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")


# Figure 4: one time trajectory per model, shown in separate comparable panels.
fid = "FIG-Q2-MODEL-ABLATION"
source4 = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-model-trajectories" / "q2-model-trajectories.csv"
df4 = pd.read_csv(source4)
write_snapshot(fid, df4, source4)
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.5), sharex=True, sharey=True)
styles = [(BLUE, "-", "o"), (ORANGE, "--", "s"), (GREEN, "-.", "^")]
model_order = list(df4["model"].drop_duplicates())
for ax, model, (color, ls, marker) in zip(axes, model_order, styles):
    group = df4[df4["model"] == model].sort_values("time_s")
    ax.plot(group.time_s / 3600, group.max_C, color=color, linestyle=ls, marker=marker,
            markersize=4, linewidth=1.5)
    ax.set_title(model)
    ax.set_xlabel("时间 (h)")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("全域最大干基含水率 (kg/kg)")
fig.suptitle("三个模型在不同时间的最大含水率轨迹", y=1.02)
fig.text(0.5, -0.01, "三幅子图使用相同坐标范围；仅比较模型输出差异，不代表现实准确率排序",
         ha="center", va="top", color="#444444")
fig.tight_layout()
save_figure(fid, fig)

# Figure 5: six radial-grid groups at the same formal dt=5 s.
fid = "FIG-Q2-GRID-CONV"
source5 = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "q2-space-dt5" / "field-grid-convergence.csv"
df5 = pd.read_csv(source5)
write_snapshot(fid, df5, source5)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"width_ratios": [1.25, 1]})
ax1.plot(df5.nr, df5.value, "o-", color=BLUE, linewidth=1.5, markersize=5)
ax1.set_xlabel("径向网格数 $n_r$")
ax1.set_ylabel("3 h 最大干基含水率 (kg/kg)")
ax1.set_title("六组网格的终值")
ax1.grid(axis="y", color=GRID, linewidth=0.6)
ax1.ticklabel_format(axis="y", style="plain", useOffset=False)
ax1.spines[["top", "right"]].set_visible(False)
ax1.set_xticks(df5.nr)
ax1.tick_params(axis="x", rotation=25)
for x, y in zip(df5.nr, df5.value):
    ax1.annotate(f"{y:.6f}", (x, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=7)
changes = df5.iloc[1:].copy()
ax2.plot(changes.nr, changes.adjacent_change, "o-", color=ORANGE, linewidth=1.5, markersize=5)
ax2.axhline(5e-5, color=BLACK, linestyle="--", linewidth=1.0, label="验收线 5e-5")
ax2.set_xlabel("径向网格数 $n_r$")
ax2.set_ylabel("相邻网格终值变化")
ax2.set_title("相邻变化逐步减小")
ax2.grid(axis="y", color=GRID, linewidth=0.6)
ax2.spines[["top", "right"]].set_visible(False)
ax2.set_xticks(changes.nr)
ax2.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
ax2.legend(frameon=False, fontsize=8)
ax2.annotate(f"最细变化 {changes.adjacent_change.iloc[-1]:.3e}",
             (changes.nr.iloc[-1], changes.adjacent_change.iloc[-1]),
             xytext=(-70, 18), textcoords="offset points", arrowprops={"arrowstyle": "->"}, fontsize=8)
fig.suptitle("M3 空间网格收敛：固定时间步长 dt=5 s", y=1.02)
fig.tight_layout()
save_figure(fid, fig)

# Appendix S2/S3: expanded five-level spatial convergence at fixed dt=60 s.
extra_space = ROOT / "04-compute" / "revision-grid-conv-20260913" / "results" / "space-extra-dt60" / "threshold-grid-extra.csv"
base_space = pd.read_csv(ROOT / "04-compute" / "results" / "threshold-grid-convergence.csv")
extra = pd.read_csv(extra_space)
space_all = pd.concat([base_space, extra], ignore_index=True).drop_duplicates(["scope", "nr"]).sort_values(["scope", "nr"])
for fid, scope in [("FIG-Q3-SPACE-CONV", "Q3"), ("FIG-Q4-SPACE-CONV", "Q4")]:
    df = space_all[space_all.scope == scope].copy()
    write_snapshot(fid, df, extra_space)
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.plot(df.nr, df.interpolated_event_time_s / 3600, "o-", color=BLUE, linewidth=1.5, markersize=5)
    ax.set_xlabel("径向网格数 $n_r$")
    ax.set_ylabel("插值事件时刻 (h)")
    ax.set_title(f"{scope} 空间网格收敛（五组网格，dt=60 s）")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xticks(df.nr)
    for x, y in zip(df.nr, df.interpolated_event_time_s / 3600):
        ax.annotate(f"{y:.4f}", (x, y), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=7)
    ax.text(0.01, 0.02, "仅表明空间离散稳定性，不替代时间步验证", transform=ax.transAxes, color="#444444")
    fig.tight_layout()
    save_figure(fid, fig)

print("REVISED_Q2_FIGURES_PASS")

