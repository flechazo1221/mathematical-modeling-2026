from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "06-figure"
REV = STAGE / "beautified-20260912"
RES = ROOT / "04-compute" / "results"
SOURCE_CONV = RES / "convergence.csv"
SOURCE_VAL = RES / "validation-register.csv"
SOURCE_SNAPSHOT = STAGE / "data-snapshots" / "FIG-Q3-TIME-CONV.csv"
SOURCE_META = STAGE / "data-snapshots" / "FIG-Q3-TIME-CONV.meta.json"
SOURCE_CONTRACT = STAGE / "contracts" / "FIG-Q3-TIME-CONV.json"
FIG_ID = "FIG-Q3-TIME-CONV"

for directory in (
    REV / "contracts",
    REV / "data-snapshots",
    REV / "figures",
    REV / "previews",
    REV / "superseded",
):
    directory.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_frozen_inputs() -> tuple[pd.DataFrame, pd.Series]:
    """Validate existing evidence and snapshot; do not recompute model output."""
    contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    meta = json.loads(SOURCE_META.read_text(encoding="utf-8"))
    require(contract["figure_id"] == FIG_ID, "unexpected figure contract")
    require(sha256(SOURCE_SNAPSHOT) == meta["snapshot_sha256"], "frozen snapshot hash mismatch")

    source_hashes = {item["path"]: item["sha256"] for item in meta["sources"]}
    require(source_hashes["04-compute/results/convergence.csv"] == sha256(SOURCE_CONV), "convergence source changed")
    require(source_hashes["04-compute/results/validation-register.csv"] == sha256(SOURCE_VAL), "validation source changed")

    snapshot = pd.read_csv(SOURCE_SNAPSHOT)
    convergence = pd.read_csv(SOURCE_CONV)
    expected = convergence[
        (convergence["scope"] == "Q3")
        & (convergence["family"] == "M3")
        & (convergence["metric"].isin(["t_star_space", "t_star_time"]))
    ][snapshot.columns].reset_index(drop=True)
    observed = snapshot.reset_index(drop=True)
    require(list(observed.columns) == list(expected.columns), "snapshot schema changed")
    for column in ("scope", "family", "metric", "acceptance_pair"):
        require(observed[column].tolist() == expected[column].tolist(), f"snapshot category mismatch: {column}")
    for column in ("base", "fine", "absolute_change"):
        require(
            np.allclose(observed[column].to_numpy(float), expected[column].to_numpy(float), rtol=0.0, atol=1e-10),
            f"snapshot numeric mismatch: {column}",
        )

    validation = pd.read_csv(SOURCE_VAL)
    v06 = validation.loc[validation["id"] == "V06"].iloc[0]
    require(v06["status"] == "PASS", "V06 validation status changed")
    require("48 s" in str(v06["evidence"]) and "60 s" in str(v06["evidence"]), "V06 acceptance evidence changed")

    time_row = observed.loc[observed["metric"] == "t_star_time"].iloc[0]
    require(bool(time_row["acceptance_pair"]), "time-refinement pair is not accepted")
    return observed, time_row


def copy_revision_inputs() -> None:
    shutil.copy2(SOURCE_SNAPSHOT, REV / "data-snapshots" / SOURCE_SNAPSHOT.name)
    meta = json.loads(SOURCE_META.read_text(encoding="utf-8"))
    meta["snapshot"] = f"06-figure/beautified-20260912/data-snapshots/{SOURCE_SNAPSHOT.name}"
    meta["snapshot_sha256"] = sha256(REV / "data-snapshots" / SOURCE_SNAPSHOT.name)
    (REV / "data-snapshots" / SOURCE_META.name).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    contract["snapshot"] = f"06-figure/beautified-20260912/data-snapshots/{SOURCE_SNAPSHOT.name}"
    contract["snapshot_sha256"] = sha256(REV / "data-snapshots" / SOURCE_SNAPSHOT.name)
    contract["visual_revision"] = "beautified-20260912-fig8"
    contract["visual_spec"] = {
        "data_curves": "high-contrast color; solid line; circle/square markers for base/fine time points",
        "non_data_elements": "black axes, grid, titles, legend, ticks and text",
        "font": "SimSun",
        "panels": "base/fine event time and absolute change against 60 s acceptance line",
        "data_claim_status": "unchanged",
    }
    (REV / "contracts" / SOURCE_CONTRACT.name).write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def configure_style() -> FontProperties:
    font_path = Path(r"C:\Windows\Fonts\simsun.ttc")
    require(font_path.exists(), f"宋体文件不存在: {font_path}")
    song = FontProperties(fname=str(font_path))
    mpl.rcParams.update(
        {
            "font.family": "SimSun",
            "font.sans-serif": ["SimSun", "STSong", "FangSong", "Microsoft YaHei", "Arial"],
            "font.size": 8.5,
            "axes.labelsize": 9.0,
            "axes.titlesize": 10.0,
            "axes.titleweight": "normal",
            "text.color": "#000000",
            "axes.labelcolor": "#000000",
            "axes.titlecolor": "#000000",
            "xtick.color": "#000000",
            "ytick.color": "#000000",
            "legend.fontsize": 8.0,
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
    return song


def black_axes(ax) -> None:
    ax.tick_params(
        axis="both",
        which="major",
        direction="in",
        top=True,
        right=True,
        length=3.5,
        width=0.7,
        colors="#000000",
        labelsize=8.2,
    )
    for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        tick.set_color("#000000")
        tick.set_fontproperties(FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc"))
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#000000")
        spine.set_linewidth(0.75)
    ax.grid(axis="y", color="#000000", alpha=0.14, linewidth=0.55)
    ax.grid(axis="x", visible=False)


def render(snapshot: pd.DataFrame, time_row: pd.Series, song: FontProperties) -> plt.Figure:
    blue = "#0072B2"
    orange = "#D55E00"
    base = float(time_row["base"])
    fine = float(time_row["fine"])
    delta = float(time_row["absolute_change"])

    fig, (ax_pair, ax_delta) = plt.subplots(
        1,
        2,
        figsize=(6.535, 3.85),
        gridspec_kw={"width_ratios": [1.42, 1.0], "wspace": 0.42},
    )
    fig.subplots_adjust(left=0.115, right=0.985, bottom=0.21, top=0.82)

    # Panel a: the two registered time-step results, connected by one solid data curve.
    x = np.array([0.0, 1.0])
    ax_pair.plot(x, [base, fine], color=blue, linewidth=1.85, linestyle="-", zorder=2)
    ax_pair.scatter([0], [base], color=blue, marker="o", s=62, edgecolors="black", linewidths=0.65, zorder=3)
    ax_pair.scatter([1], [fine], color=orange, marker="s", s=62, edgecolors="black", linewidths=0.65, zorder=3)
    ax_pair.set_title("细化前后阈值事件时刻", loc="left", pad=9, fontproperties=song, color="#000000")
    ax_pair.text(-0.12, 1.055, "a", transform=ax_pair.transAxes, fontproperties=song, fontweight="bold", color="#000000")
    ax_pair.set_xlabel("时间步设置", labelpad=7, fontproperties=song, color="#000000")
    ax_pair.set_ylabel("阈值事件时刻 t*（s）", labelpad=8, fontproperties=song, color="#000000")
    ax_pair.set_xlim(-0.28, 1.28)
    ax_pair.set_ylim(206650, 206750)
    ax_pair.set_xticks(x, ["Δt = 30 s\n基准", "Δt = 15 s\n细化"])
    ax_pair.set_yticks([206660, 206680, 206700, 206720, 206740])
    ax_pair.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}"))
    ax_pair.annotate(
        "",
        xy=(0.54, fine),
        xytext=(0.54, base),
        arrowprops={"arrowstyle": "<->", "color": "#000000", "linewidth": 0.9, "mutation_scale": 10},
        zorder=1,
    )
    ax_pair.text(
        0.61,
        (base + fine) / 2,
        "变化 47.5654 s",
        ha="left",
        va="center",
        fontproperties=song,
        fontsize=8.0,
        color="#000000",
        bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.9},
    )
    ax_pair.legend(
        handles=[
            Line2D([0], [0], color=blue, marker="o", linestyle="-", linewidth=1.6, markersize=5.0, label="Δt = 30 s（基准）"),
            Line2D([0], [0], color=orange, marker="s", linestyle="-", linewidth=1.6, markersize=5.0, label="Δt = 15 s（细化）"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=1,
        frameon=False,
        handlelength=1.8,
        borderaxespad=0.0,
        prop=song,
    )
    black_axes(ax_pair)

    # Panel b: the declared absolute change and the unchanged 60 s acceptance target.
    ax_delta.plot([0, 0], [0, delta], color=orange, linewidth=2.1, linestyle="-", zorder=2)
    ax_delta.scatter([0], [delta], color=orange, marker="s", s=67, edgecolors="black", linewidths=0.65, zorder=3)
    ax_delta.axhline(60, color="#000000", linewidth=1.0, linestyle="--", zorder=1)
    ax_delta.set_title("变化量与验收目标", loc="left", pad=9, fontproperties=song, color="#000000")
    ax_delta.text(-0.18, 1.055, "b", transform=ax_delta.transAxes, fontproperties=song, fontweight="bold", color="#000000")
    ax_delta.set_xlabel("时间步设置", labelpad=7, fontproperties=song, color="#000000")
    ax_delta.set_ylabel("事件时刻变化 |Δt*|（s）", labelpad=8, fontproperties=song, color="#000000")
    ax_delta.set_xlim(-0.45, 0.45)
    ax_delta.set_ylim(0, 65)
    ax_delta.set_xticks([0], ["30 s → 15 s"])
    ax_delta.set_yticks([0, 20, 40, 60])
    ax_delta.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}"))
    ax_delta.text(0.39, 60.8, "目标 60 s", ha="right", va="bottom", fontproperties=song, fontsize=8.0, color="#000000")
    ax_delta.annotate(
        "47.5654 s\n登记 48 s",
        xy=(0, delta),
        xytext=(18, 4),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontproperties=song,
        fontsize=8.0,
        color="#000000",
        arrowprops={"arrowstyle": "-", "color": "#000000", "linewidth": 0.75},
    )
    black_axes(ax_delta)

    return fig


def save_and_promote(fig: plt.Figure) -> dict[str, str]:
    fixed_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    revision_figures = REV / "figures"
    revision_previews = REV / "previews"
    formal_figures = STAGE / "figures"
    formal_previews = STAGE / "previews"
    for directory in (formal_figures, formal_previews):
        directory.mkdir(parents=True, exist_ok=True)

    # Keep the previous formal figure recoverable before promotion.
    for ext in ("png", "svg", "pdf"):
        old = formal_figures / f"{FIG_ID}.{ext}"
        backup = REV / "superseded" / f"{FIG_ID}.pre-redraw.{ext}"
        if old.exists() and not backup.exists():
            shutil.copy2(old, backup)

    outputs: dict[str, str] = {}
    for ext in ("svg", "pdf", "png"):
        target = revision_figures / f"{FIG_ID}.{ext}"
        kwargs = {"bbox_inches": "tight", "pad_inches": 0.05, "facecolor": "white"}
        if ext == "png":
            kwargs["dpi"] = 600
        if ext == "pdf":
            kwargs["metadata"] = {"CreationDate": fixed_date, "ModDate": fixed_date}
        fig.savefig(target, **kwargs)
        shutil.copy2(target, formal_figures / target.name)
        outputs[ext] = sha256(target)

    color_preview = revision_previews / f"{FIG_ID}-color.png"
    fig.savefig(color_preview, dpi=200, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    grayscale_preview = revision_previews / f"{FIG_ID}-grayscale.png"
    ImageOps.grayscale(Image.open(color_preview).convert("RGB")).save(grayscale_preview, dpi=(200, 200))
    shutil.copy2(color_preview, formal_previews / color_preview.name)
    shutil.copy2(grayscale_preview, formal_previews / grayscale_preview.name)
    outputs["color_preview"] = sha256(color_preview)
    outputs["grayscale_preview"] = sha256(grayscale_preview)
    plt.close(fig)

    manifest_path = STAGE / "figure-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    item = next(item for item in manifest["items"] if item["id"] == FIG_ID)
    item.update(
        {
            "pdf": f"06-figure/figures/{FIG_ID}.pdf",
            "png_sha256": sha256(formal_figures / f"{FIG_ID}.png"),
            "svg_sha256": sha256(formal_figures / f"{FIG_ID}.svg"),
            "pdf_sha256": sha256(formal_figures / f"{FIG_ID}.pdf"),
            "visual_revision": "beautified-20260912-fig8",
            "data_claim_status": "unchanged",
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    record = {
        "figure_id": FIG_ID,
        "status": "REDRAW_READY_PENDING_TEAM_REVIEW",
        "data_claim_status": "unchanged",
        "source_snapshot_sha256": sha256(SOURCE_SNAPSHOT),
        "source_files": {
            "04-compute/results/convergence.csv": sha256(SOURCE_CONV),
            "04-compute/results/validation-register.csv": sha256(SOURCE_VAL),
        },
        "plotted_time_pair": {
            "base_time_step_s": 30,
            "fine_time_step_s": 15,
            "base_event_time_s": 206723.71251173425,
            "fine_event_time_s": 206676.14712249584,
            "absolute_change_s": 47.56538923838525,
            "registered_change_s": 48,
            "acceptance_target_s": 60,
        },
        "visual_spec": {
            "data_curves": "high-contrast color; solid line; distinct markers",
            "non_data_elements": "black axes, grid, titles, legend, ticks and text",
            "font": "SimSun",
            "right_bottom_note": False,
            "coordinate_semantics": "unchanged metrics and units; no model recomputation",
        },
        "outputs": outputs,
    }
    (REV / "fig8-redraw-record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return outputs


def main() -> None:
    snapshot, time_row = verify_frozen_inputs()
    copy_revision_inputs()
    song = configure_style()
    fig = render(snapshot, time_row, song)
    outputs = save_and_promote(fig)
    print(
        json.dumps(
            {
                "figure_id": FIG_ID,
                "status": "REDRAW_READY_PENDING_TEAM_REVIEW",
                "source_snapshot_sha256": sha256(SOURCE_SNAPSHOT),
                "formal_png_sha256": sha256(STAGE / "figures" / f"{FIG_ID}.png"),
                "formal_svg_sha256": sha256(STAGE / "figures" / f"{FIG_ID}.svg"),
                "formal_pdf_sha256": sha256(STAGE / "figures" / f"{FIG_ID}.pdf"),
                "outputs": outputs,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
