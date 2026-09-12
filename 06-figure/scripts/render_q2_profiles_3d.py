from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "06-figure"
SNAPSHOT = FIGURE_DIR / "data-snapshots" / "FIG-Q2-C-PROFILES.csv"
FIGURES = FIGURE_DIR / "figures"
PREVIEWS = FIGURE_DIR / "previews"
FIG_ID = "FIG-Q2-C-PROFILES"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows: list[tuple[float, float, float]] = []
    with SNAPSHOT.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                (
                    float(row["time_s"]) / 3600.0,
                    float(row["radius_cm"]),
                    float(row["C_kg_per_kg"]),
                )
            )
    times = np.array(sorted({row[0] for row in rows}), dtype=float)
    radii = np.array(sorted({row[1] for row in rows}), dtype=float)
    z = np.full((len(radii), len(times)), np.nan, dtype=float)
    time_index = {value: i for i, value in enumerate(times)}
    radius_index = {value: i for i, value in enumerate(radii)}
    for time_h, radius_cm, value in rows:
        if not np.isnan(z[radius_index[radius_cm], time_index[time_h]]):
            raise ValueError("duplicate time-radius sample")
        z[radius_index[radius_cm], time_index[time_h]] = value
    if np.isnan(z).any():
        raise ValueError("time-radius samples do not form a complete rectangular grid")
    return times, radii, z


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    if not SNAPSHOT.exists():
        raise FileNotFoundError(SNAPSHOT)

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
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": FIG_ID,
        }
    )

    times_h, radii_cm, z = load_grid()
    x, y = np.meshgrid(times_h, radii_cm)
    cmap = mpl.colormaps["viridis"]
    norm = mpl.colors.Normalize(vmin=float(z.min()), vmax=float(z.max()))

    fig = plt.figure(figsize=(6.9, 5.0), dpi=600)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_proj_type("ortho")
    surface = ax.plot_surface(
        x,
        y,
        z,
        cmap=cmap,
        norm=norm,
        linewidth=0.28,
        edgecolor=(0.25, 0.25, 0.25, 0.45),
        antialiased=True,
        alpha=0.90,
        rcount=len(radii_cm),
        ccount=len(times_h),
    )
    # Exact frozen samples are overlaid so that the surface is auditable.
    ax.scatter(
        x.ravel(),
        y.ravel(),
        z.ravel(),
        c=z.ravel(),
        cmap=cmap,
        norm=norm,
        s=11,
        depthshade=False,
        edgecolors="#000000",
        linewidths=0.28,
    )

    ax.set_xlim(float(times_h.min()), float(times_h.max()))
    ax.set_ylim(float(radii_cm.min()), float(radii_cm.max()))
    # Use four regular z ticks and a small fixed margin.  The previous five
    # ticks were visually crowded by the chosen 3-D projection.
    z_ticks = [1.0, 1.5, 2.0, 2.5]
    ax.set_zlim(0.9, 2.7)
    ax.set_xticks(times_h)
    ax.set_yticks(radii_cm)
    ax.set_zticks(z_ticks)
    ax.set_xlabel("时间 t（h）", labelpad=8, fontsize=9.5)
    ax.set_ylabel("半径 r（cm）", labelpad=8, fontsize=9.5)
    ax.set_zlabel("干基含水率 C（kg/kg）", labelpad=17, fontsize=9.5)
    ax.tick_params(axis="both", which="major", labelsize=8.0, pad=1.5, colors="#000000")
    ax.tick_params(axis="z", which="major", labelsize=8.0, pad=7.0, colors="#000000")
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((1.0, 1.0, 1.0, 1.0))
        pane.set_edgecolor((0.0, 0.0, 0.0, 0.18))
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis._axinfo["grid"]["color"] = (0.0, 0.0, 0.0, 0.12)
    ax.view_init(elev=30, azim=-55)
    ax.set_box_aspect((1.55, 1.0, 1.05))

    fig.suptitle(
        "M3  不同时间—半径位置的含水率三维演化",
        x=0.46,
        y=0.965,
        fontsize=11.5,
        fontfamily="SimSun",
    )
    ax.text2D(0.02, 0.93, "点：冻结采样值", transform=ax.transAxes, fontsize=8.0, color="#000000")
    colorbar = fig.colorbar(surface, ax=ax, shrink=0.68, pad=0.12, aspect=19)
    colorbar.set_ticks(z_ticks)
    colorbar.set_label("C（kg/kg）", fontsize=8.8, labelpad=6, color="#000000")
    colorbar.ax.tick_params(labelsize=7.7, colors="#000000", length=2.5, width=0.55)
    colorbar.outline.set_edgecolor("#000000")
    colorbar.outline.set_linewidth(0.45)
    fig.subplots_adjust(left=0.0, right=0.92, bottom=0.02, top=0.92)

    fixed_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    svg_path = FIGURES / f"{FIG_ID}.svg"
    pdf_path = FIGURES / f"{FIG_ID}.pdf"
    png_path = FIGURES / f"{FIG_ID}.png"
    fig.savefig(svg_path, metadata={"Date": "2026-01-01T00:00:00"})
    fig.savefig(pdf_path, dpi=600, metadata={"CreationDate": fixed_date, "ModDate": fixed_date})
    fig.savefig(png_path, dpi=600)
    fig.savefig(PREVIEWS / f"{FIG_ID}-color.png", dpi=600)
    plt.close(fig)

    color = Image.open(png_path).convert("RGB")
    ImageOps.grayscale(color).save(PREVIEWS / f"{FIG_ID}-grayscale.png", dpi=(600, 600))
    print(
        {
            "figure_id": FIG_ID,
            "snapshot_sha256": sha256(SNAPSHOT),
            "png_sha256": sha256(png_path),
            "svg_sha256": sha256(svg_path),
            "pdf_sha256": sha256(pdf_path),
            "rows": int(z.size),
            "time_range_h": [float(times_h.min()), float(times_h.max())],
            "radius_range_cm": [float(radii_cm.min()), float(radii_cm.max())],
            "C_range_kg_per_kg": [float(z.min()), float(z.max())],
            "interpolation": False,
        }
    )


if __name__ == "__main__":
    main()
