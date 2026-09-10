from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "input" / "B题" / "附件"
OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

META = {
    "附件1.xlsx": ("SiC", 10, "#0072B2", "-"),
    "附件2.xlsx": ("SiC", 15, "#D55E00", "--"),
    "附件3.xlsx": ("Si", 10, "#009E73", "-."),
    "附件4.xlsx": ("Si", 15, "#CC79A7", ":"),
}


def read_inputs():
    frames = []
    summaries = []
    grids = []
    for filename, (material, angle, color, linestyle) in META.items():
        path = INPUT / filename
        raw = pd.read_excel(path, sheet_name="Sheet1")
        sigma = pd.to_numeric(raw.iloc[:, 0], errors="coerce")
        refl = pd.to_numeric(raw.iloc[:, 1], errors="coerce")
        frame = pd.DataFrame({
            "attachment": filename.removesuffix(".xlsx"),
            "material": material,
            "angle_deg": angle,
            "sigma_cm_inv": sigma,
            "R_percent": refl,
        })
        frames.append(frame)
        grids.append(sigma.to_numpy())
        finite = np.isfinite(sigma) & np.isfinite(refl)
        step = np.diff(sigma[finite])
        summaries.append({
            "attachment": filename.removesuffix(".xlsx"),
            "material": material,
            "angle_deg": angle,
            "rows": len(frame),
            "missing": int((~finite).sum()),
            "zero": int((refl == 0).sum()),
            "above_100": int((refl > 100).sum()),
            "valid_0_to_100": int(((refl > 0) & (refl <= 100)).sum()),
            "R_min": float(np.nanmin(refl)),
            "R_q1": float(np.nanquantile(refl, 0.25)),
            "R_median": float(np.nanmedian(refl)),
            "R_q3": float(np.nanquantile(refl, 0.75)),
            "R_max": float(np.nanmax(refl)),
            "step_min": float(np.nanmin(step)),
            "step_median": float(np.nanmedian(step)),
            "step_max": float(np.nanmax(step)),
        })
    all_data = pd.concat(frames, ignore_index=True)
    summary = pd.DataFrame(summaries)
    common_grid = all(np.array_equal(grids[0], grid) for grid in grids[1:])
    return all_data, summary, common_grid


def export_snapshots(data, summary, common_grid):
    data.to_csv(OUT / "data-audit-raw-snapshot.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "data-audit-summary.csv", index=False, encoding="utf-8-sig")
    contract = {
        "figure_id": "FIG-DATA-AUDIT-DEBUG",
        "question": "四附件原始光谱、异常记录、分布与采样网格呈现何种数据质量结构？",
        "source_files": [f"input/B题/附件/{name}" for name in META],
        "transformations": [
            "按附件原顺序读取全部记录",
            "仅计算描述统计与相邻波数差分",
            "不删除、不裁剪、不补值、不平滑",
        ],
        "fixed_windows_cm_inv": {"W1": [600, 1600], "W2": [1600, 2800], "W3": [2800, 3800]},
        "common_wavenumber_grid": bool(common_grid),
        "target_formats": ["png", "svg"],
        "minimum_dpi": 300,
        "final_size_inches": [7.2, 5.0],
    }
    (OUT / "FIG-DATA-AUDIT-DEBUG.contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def add_panel(ax, label):
    ax.text(-0.10, 1.04, label, transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="bottom")


def build_figure(data, summary, common_grid):
    global plt
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "svg.fonttype": "none",
    })
    fig = plt.figure(figsize=(7.2, 5.0), constrained_layout=True)
    gs = fig.add_gridspec(3, 2, width_ratios=(1.45, 1), height_ratios=(1, 1, 1))
    ax_spectrum = fig.add_subplot(gs[:, 0])
    ax_counts = fig.add_subplot(gs[0, 1])
    ax_box = fig.add_subplot(gs[1, 1])
    ax_step = fig.add_subplot(gs[2, 1])

    windows = ((600, 1600, "W1"), (1600, 2800, "W2"), (2800, 3800, "W3"))
    for lo, hi, label in windows:
        ax_spectrum.axvline(lo, color="#B8B8B8", linewidth=0.55, linestyle=":", zorder=0)
        ax_spectrum.text((lo + hi) / 2, 106.5, label, ha="center", va="top", color="#555555")
    ax_spectrum.axvline(windows[-1][1], color="#B8B8B8", linewidth=0.55,
                        linestyle=":", zorder=0)
    for filename, (material, angle, color, linestyle) in META.items():
        name = filename.removesuffix(".xlsx")
        d = data[data["attachment"] == name]
        ax_spectrum.plot(d["sigma_cm_inv"], d["R_percent"], color=color,
                         linestyle=linestyle, linewidth=0.75,
                         label=f"{name}  {material}/{angle}°")
        zeros = d[d["R_percent"] == 0]
        ax_spectrum.scatter(zeros["sigma_cm_inv"], zeros["R_percent"], s=18,
                            marker="x", linewidth=1.2, color=color, zorder=4)
    over = data[data["R_percent"] > 100]
    # 连续的262个异常点若逐点使用空心描边，会在出版尺寸下堆成虚假的粗色块。
    # 用完整异常区间的浅色带表达覆盖范围，并稀疏显示定位点；计数仍取全量记录。
    over_x = over["sigma_cm_inv"].to_numpy()
    over_y = over["R_percent"].to_numpy()
    ax_spectrum.plot([over_x.min(), over_x.max()], [105.0, 105.0], color="#D55E00",
                     linewidth=2.0, solid_capstyle="butt",
                     label=f"附件2 R>100%区间（n={len(over)}）", zorder=3)
    ax_spectrum.axhline(100, color="#444444", linestyle="--", linewidth=0.7)
    ax_spectrum.set_xlim(390, 4010)
    ax_spectrum.set_ylim(-4, 109)
    ax_spectrum.set_xlabel(r"波数 $\sigma$ (cm$^{-1}$)")
    ax_spectrum.set_ylabel("原始反射率 R (%)")
    ax_spectrum.set_title("四附件原始光谱与固定建模窗口")
    ax_spectrum.grid(alpha=0.18)
    ax_spectrum.legend(frameon=False, loc="upper right", bbox_to_anchor=(0.99, 0.88), ncol=1)
    add_panel(ax_spectrum, "a")

    labels = [f"{r.material}\n{int(r.angle_deg)}°" for r in summary.itertuples()]
    x = np.arange(len(summary))
    ax_counts.bar(x - 0.22, summary["zero"], width=0.22, color="#0072B2", label="零值")
    ax_counts.bar(x, summary["above_100"], width=0.22, color="#D55E00", label=">100%")
    ax_counts.bar(x + 0.22, summary["missing"], width=0.22, color="#999999", label="缺失")
    for i, value in enumerate(summary["above_100"]):
        if value:
            ax_counts.text(i + 0.18, value - 10, str(int(value)), ha="left", va="center",
                           color="#9C4300", fontweight="bold", clip_on=False)
    ax_counts.set_ylim(0, 340)
    ax_counts.set_xticks(x, labels)
    ax_counts.set_ylabel("记录数")
    ax_counts.set_title("异常与缺失计数（每附件 n=7469）")
    ax_counts.grid(axis="y", alpha=0.22)
    ax_counts.legend(frameon=False, ncol=3, loc="upper left")
    add_panel(ax_counts, "b")

    box_data = [data.loc[data["attachment"] == name.removesuffix(".xlsx"), "R_percent"].dropna().to_numpy()
                for name in META]
    bp = ax_box.boxplot(box_data, orientation="vertical", widths=0.55, patch_artist=True,
                        showfliers=False, whis=(0, 100))
    for patch, (_, (_, _, color, _)) in zip(bp["boxes"], META.items()):
        patch.set_facecolor(color); patch.set_alpha(0.35); patch.set_edgecolor(color)
    ax_box.axhline(100, color="#444444", linestyle="--", linewidth=0.7)
    ax_box.set_xticks(np.arange(1, 5), labels)
    ax_box.set_ylabel("反射率 R (%)")
    ax_box.set_title("全量分布（须线为实际最小—最大值）")
    ax_box.grid(axis="y", alpha=0.22)
    add_panel(ax_box, "c")

    step_values = []
    for filename in META:
        name = filename.removesuffix(".xlsx")
        sigma = data.loc[data["attachment"] == name, "sigma_cm_inv"].to_numpy()
        step_values.append(np.diff(sigma))
    parts = ax_step.violinplot(step_values, positions=np.arange(1, 5), widths=0.65,
                               showmeans=False, showmedians=True, showextrema=True)
    for body, (_, (_, _, color, _)) in zip(parts["bodies"], META.items()):
        body.set_facecolor(color); body.set_edgecolor(color); body.set_alpha(0.4)
    ax_step.set_xticks(np.arange(1, 5), labels)
    ax_step.set_ylabel(r"相邻波数差 $\Delta\sigma$ (cm$^{-1}$)")
    grid_text = "四附件网格完全一致" if common_grid else "附件网格不一致"
    ax_step.set_title(f"采样步长分布；{grid_text}")
    ax_step.grid(axis="y", alpha=0.22)
    add_panel(ax_step, "d")

    fig.suptitle("B题原始数据整理：全谱、异常、分布与采样网格", fontsize=11)
    fig.savefig(OUT / "FIG-DATA-AUDIT-DEBUG.svg", bbox_inches="tight")
    fig.savefig(OUT / "FIG-DATA-AUDIT-DEBUG.png", dpi=360, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    raw_snapshot = OUT / "data-audit-raw-snapshot.csv"
    summary_snapshot = OUT / "data-audit-summary.csv"
    extract_only = "--extract-only" in sys.argv
    if extract_only or not (raw_snapshot.exists() and summary_snapshot.exists()):
        all_data, summary, common_grid = read_inputs()
        export_snapshots(all_data, summary, common_grid)
    else:
        all_data = pd.read_csv(raw_snapshot)
        summary = pd.read_csv(summary_snapshot)
        grids = [g["sigma_cm_inv"].to_numpy() for _, g in all_data.groupby("attachment", sort=False)]
        common_grid = all(np.array_equal(grids[0], grid) for grid in grids[1:])
    if not extract_only:
        build_figure(all_data, summary, common_grid)
    print(summary.to_string(index=False))
    print(f"common_wavenumber_grid={common_grid}")
