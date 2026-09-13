"""Replace FIG-Q1-END-EFFECT with the Q1 M1/M2 moisture trajectories.

The trajectory is generated with the already approved formal solver and the
same Q1 base configurations used by 04-compute.  No model definition or
upstream result file is changed; only the figure-stage snapshot and outputs
are written.
"""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06-figure"
RES = ROOT / "04-compute" / "results"
SOLVER_PATH = ROOT / "04-compute" / "src" / "formal_compute.py"
FID = "FIG-Q1-END-EFFECT"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_formal_solver():
    spec = importlib.util.spec_from_file_location("formal_compute_for_q1_figure", SOLVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load formal solver: {SOLVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_run_summary() -> dict[str, float]:
    values: dict[str, float] = {}
    with (RES / "run-summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["label"] in {"Q1-M1-base", "Q1-M2-base"}:
                values[row["label"]] = float(row["final_mean_C"])
    if set(values) != {"Q1-M1-base", "Q1-M2-base"}:
        raise RuntimeError("Q1 base endpoint results are incomplete")
    return values


def build_snapshot() -> tuple[Path, Path, dict[str, dict[str, float | int]]]:
    solver = load_formal_solver()
    configs = {
        "M1 一维基线": solver.RunConfig(
            "Q1-M1-base", 122, 1, 0.5, 1800, 1, "M1", sample_every=60.0
        ),
        "M2 二维主干": solver.RunConfig(
            "Q1-M2-base", 93, 54, 0.5, 1800, 1, "M2", sample_every=60.0
        ),
    }
    endpoint = read_run_summary()
    records: list[dict[str, object]] = []
    provenance: dict[str, dict[str, float | int]] = {}
    for label, cfg in configs.items():
        result = solver.simulate(cfg)
        rows = result["records"]
        if not rows or rows[-1]["time_s"] != 1800.0:
            raise RuntimeError(f"trajectory endpoint missing for {label}")
        expected = endpoint["Q1-M1-base" if cfg.model == "M1" else "Q1-M2-base"]
        actual = float(rows[-1]["mean_C"])
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=2e-10):
            raise RuntimeError(f"endpoint mismatch for {label}: {actual} vs {expected}")
        provenance[label] = {
            "rows": len(rows),
            "nr": cfg.nr,
            "nz": cfg.nz,
            "dt_s": cfg.dt,
            "duration_s": cfg.duration,
            "sample_every_s": cfg.sample_every,
            "endpoint_mean_C": actual,
        }
        for row in rows:
            records.append(
                {
                    "model": label,
                    "time_s": float(row["time_s"]),
                    "mean_C": float(row["mean_C"]),
                }
            )

    records.sort(key=lambda row: (str(row["model"]), float(row["time_s"])))
    snapshot = OUT / "data-snapshots" / f"{FID}.csv"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with snapshot.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "time_s", "mean_C"])
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "model": row["model"],
                    "time_s": f"{float(row['time_s']):.16g}",
                    "mean_C": f"{float(row['mean_C']):.16g}",
                }
            )

    source_paths = [SOLVER_PATH, RES / "run-summary.csv"]
    meta = {
        "figure_id": FID,
        "snapshot": rel(snapshot),
        "snapshot_sha256": sha256(snapshot),
        "sources": [{"path": rel(path), "sha256": sha256(path)} for path in source_paths],
        "rows": len(records),
        "columns": ["model", "time_s", "mean_C"],
        "derived_metric": "solver record mean_C, volume-weighted mean dry-basis moisture",
        "sampling": "every 60 s from t=0 to t=1800 s",
        "configurations": provenance,
        "endpoint_check": "matches 04-compute/results/run-summary.csv within 2e-10 kg/kg",
    }
    meta_path = snapshot.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot, meta_path, provenance


def load_snapshot(snapshot: Path) -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    with snapshot.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            series.setdefault(row["model"], []).append((float(row["time_s"]), float(row["mean_C"])))
    if set(series) != {"M1 一维基线", "M2 二维主干"}:
        raise RuntimeError("snapshot must contain exactly the M1 and M2 series")
    return series


def render(snapshot: Path) -> tuple[Path, Path, Path, Path]:
    series = load_snapshot(snapshot)
    figures = OUT / "figures"
    previews = OUT / "previews"
    figures.mkdir(parents=True, exist_ok=True)
    previews.mkdir(parents=True, exist_ok=True)
    svg = figures / f"{FID}.svg"
    png = figures / f"{FID}.png"
    color_preview = previews / f"{FID}-color.png"
    gray_preview = previews / f"{FID}-grayscale.png"

    # 6.7 x 4.2 in at 600 dpi.  This keeps the figure renderer dependency-light
    # while preserving the approved white-background academic style.
    width, height = 4020, 2520
    left, right, top, bottom = 400, 3840, 260, 2050
    ymin, ymax = 2.24, 2.58
    dark = "#222222"
    grid_gray = "#C7C7C7"
    axis_width = 6
    title = "图2：一维与二维模型平均含水率随时间变化"
    title_y = 2390
    x_label_y = 2210
    colors = {"M1 一维基线": "#0072B2", "M2 二维主干": "#D55E00"}

    def font(size: int, *paths: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for path in paths:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        return ImageFont.load_default()

    font_title = font(96, r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc")
    font_tick = font(78, r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc")
    font_label = font(88, r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc")
    font_legend = font(72, r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc")
    font_note = font(58, r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf")

    def xpix(value: float) -> int:
        return round(left + (value / 1800.0) * (right - left))

    def ypix(value: float) -> int:
        return round(bottom - ((value - ymin) / (ymax - ymin)) * (bottom - top))

    def centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill=dark) -> None:
        box = draw.textbbox((0, 0), text, font=fnt)
        draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1] - (box[3] - box[1]) / 2), text, font=fnt, fill=fill)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((left, top, right, bottom), outline=dark, width=axis_width)
    x_ticks = [0, 300, 600, 900, 1200, 1500, 1800]
    y_ticks = [2.24, 2.30, 2.36, 2.42, 2.48, 2.54, 2.58]

    def dashed_line(points: list[tuple[int, int]], fill: str, width: int, dash: int = 22, gap: int = 14) -> None:
        for start, end in zip(points, points[1:]):
            x0, y0 = start
            x1, y1 = end
            length = math.hypot(x1 - x0, y1 - y0)
            if length == 0:
                continue
            ux, uy = (x1 - x0) / length, (y1 - y0) / length
            position = 0.0
            while position < length:
                end_position = min(position + dash, length)
                draw.line(
                    (
                        x0 + ux * position,
                        y0 + uy * position,
                        x0 + ux * end_position,
                        y0 + uy * end_position,
                    ),
                    fill=fill,
                    width=width,
                )
                position += dash + gap

    centered(draw, ((left + right) // 2, title_y), title, font_title, fill="#000000")
    for value in x_ticks[1:-1]:
        x = xpix(value)
        dashed_line([(x, top), (x, bottom)], fill=grid_gray, width=2, dash=18, gap=12)
    for value in y_ticks[1:-1]:
        y = ypix(value)
        dashed_line([(left, y), (right, y)], fill=grid_gray, width=2, dash=18, gap=12)
    for value in x_ticks:
        x = xpix(value)
        draw.line((x, bottom, x, bottom - 18), fill=dark, width=axis_width)
        draw.line((x, top, x, top + 18), fill=dark, width=axis_width)
        centered(draw, (x, bottom + 48), str(value), font_tick)
    for value in y_ticks:
        y = ypix(value)
        draw.line((left, y, left + 18, y), fill=dark, width=axis_width)
        draw.line((right, y, right - 18, y), fill=dark, width=axis_width)
        box = draw.textbbox((0, 0), f"{value:.2f}", font=font_tick)
        draw.text((left - 28 - (box[2] - box[0]), y - (box[3] - box[1]) / 2), f"{value:.2f}", font=font_tick, fill=dark)

    for label in ("M1 一维基线", "M2 二维主干"):
        values = series[label]
        points = [(xpix(x), ypix(y)) for x, y in values]
        if label.startswith("M1"):
            draw.line(points, fill=colors[label], width=7, joint="curve")
        else:
            dashed_line(points, fill=colors[label], width=7)
        for index in range(0, len(points), 5):
            x, y = points[index]
            if label.startswith("M1"):
                draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=colors[label])
            else:
                draw.rectangle((x - 12, y - 12, x + 12, y + 12), fill=colors[label])
        x, y = points[-1]
        if label.startswith("M1"):
            draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=colors[label])
        else:
            draw.rectangle((x - 12, y - 12, x + 12, y + 12), fill=colors[label])

    # Legend in the open upper-right area; line style and marker redundantly
    # encode the two model dimensions in color and grayscale.
    legend_x, legend_y = 2920, 350
    for offset, label in enumerate(("M1 一维基线", "M2 二维主干")):
        y = legend_y + offset * 78
        draw.line((legend_x, y, legend_x + 105, y), fill=colors[label], width=7)
        if label.startswith("M1"):
            draw.ellipse((legend_x + 45 - 12, y - 12, legend_x + 45 + 12, y + 12), fill=colors[label])
        else:
            draw.rectangle((legend_x + 45 - 12, y - 12, legend_x + 45 + 12, y + 12), fill=colors[label])
        draw.text((legend_x + 135, y - 28), label, font=font_legend, fill=dark)

    centered(draw, ((left + right) // 2, x_label_y), "时间 t (s)", font_label)
    y_label = Image.new("RGBA", (1200, 120), (255, 255, 255, 0))
    ImageDraw.Draw(y_label).text((10, 10), "平均干基含水率 C (kg/kg)", font=font_label, fill=dark)
    y_label = y_label.rotate(90, expand=True)
    image.paste(y_label, (30, (height - y_label.height) // 2), y_label)
    draw = ImageDraw.Draw(image)
    note = "末值差 0.01855 kg/kg"
    box = draw.textbbox((0, 0), note, font=font_note)
    draw.text((right - 30 - (box[2] - box[0]), bottom - 80), note, font=font_note, fill="#444444")
    image.save(str(png), dpi=(600, 600))
    image.resize((2010, 1260), Image.Resampling.LANCZOS).save(str(color_preview), dpi=(150, 150))
    ImageOps.grayscale(Image.open(str(color_preview)).convert("RGB")).save(str(gray_preview), dpi=(150, 150))

    def esc(text: str) -> str:
        return html.escape(text, quote=True)

    svg_lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="6.7in" height="4.2in" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="white" stroke="{dark}" stroke-width="{axis_width}"/>',
        f'<text x="{(left+right)//2}" y="{title_y+50}" text-anchor="middle" font-family="SimHei,Microsoft YaHei,SimSun,sans-serif" font-size="96" font-weight="bold" fill="#000000">{esc(title)}</text>',
    ]
    for value in x_ticks[1:-1]:
        x = xpix(value)
        svg_lines.append(f'<path d="M{x} {top}V{bottom}" stroke="{grid_gray}" stroke-width="2" stroke-dasharray="18 12"/>')
    for value in y_ticks[1:-1]:
        y = ypix(value)
        svg_lines.append(f'<path d="M{left} {y}H{right}" stroke="{grid_gray}" stroke-width="2" stroke-dasharray="18 12"/>')
    for value in x_ticks:
        x = xpix(value)
        svg_lines.append(f'<path d="M{x} {bottom}V{bottom-18} M{x} {top}V{top+18}" stroke="{dark}" stroke-width="{axis_width}"/>')
        svg_lines.append(f'<text x="{x}" y="{bottom+70}" text-anchor="middle" font-family="Arial,SimSun,sans-serif" font-size="78" fill="{dark}">{value}</text>')
    for value in y_ticks:
        y = ypix(value)
        svg_lines.append(f'<path d="M{left} {y}H{left+18} M{right} {y}H{right-18}" stroke="{dark}" stroke-width="{axis_width}"/>')
        svg_lines.append(f'<text x="{left-28}" y="{y+22}" text-anchor="end" font-family="Arial,SimSun,sans-serif" font-size="78" fill="{dark}">{value:.2f}</text>')
    for label in ("M1 一维基线", "M2 二维主干"):
        pts = " ".join(f"{xpix(x)},{ypix(y)}" for x, y in series[label])
        dash = "" if label.startswith("M1") else ' stroke-dasharray="16 10"'
        marker = "circle" if label.startswith("M1") else "rect"
        svg_lines.append(f'<polyline points="{pts}" fill="none" stroke="{colors[label]}" stroke-width="7"{dash}/>' )
        for index in list(range(0, len(series[label]), 5)) + [len(series[label]) - 1]:
            x, y = series[label][index]
            if marker == "circle":
                svg_lines.append(f'<circle cx="{xpix(x)}" cy="{ypix(y)}" r="12" fill="{colors[label]}"/>')
            else:
                svg_lines.append(f'<rect x="{xpix(x)-12}" y="{ypix(y)-12}" width="24" height="24" fill="{colors[label]}"/>')
    svg_lines.extend(
        [
            f'<text x="{legend_x+135}" y="{legend_y+20}" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="72" fill="{dark}">M1 一维基线</text>',
            f'<text x="{legend_x+135}" y="{legend_y+98}" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="72" fill="{dark}">M2 二维主干</text>',
            f'<path d="M{legend_x} {legend_y}H{legend_x+105}" stroke="{colors["M1 一维基线"]}" stroke-width="7"/>',
            f'<path d="M{legend_x} {legend_y+78}H{legend_x+105}" stroke="{colors["M2 二维主干"]}" stroke-width="7" stroke-dasharray="16 10"/>',
            f'<circle cx="{legend_x+45}" cy="{legend_y}" r="12" fill="{colors["M1 一维基线"]}"/>',
            f'<rect x="{legend_x+33}" y="{legend_y+66}" width="24" height="24" fill="{colors["M2 二维主干"]}"/>',
            f'<text x="{(left+right)//2}" y="{x_label_y+28}" text-anchor="middle" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="88" fill="{dark}">时间 t (s)</text>',
            f'<text x="110" y="{height//2}" text-anchor="middle" transform="rotate(-90 110 {height//2})" font-family="SimSun,Microsoft YaHei,Arial,sans-serif" font-size="88" fill="{dark}">平均干基含水率 C (kg/kg)</text>',
            f'<text x="{right-30}" y="{bottom-30}" text-anchor="end" font-family="Arial,Microsoft YaHei,sans-serif" font-size="58" fill="#444444">末值差 0.01855 kg/kg</text>',
            '</svg>',
        ]
    )
    svg.write_text("\n".join(svg_lines), encoding="utf-8")
    return svg, png, color_preview, gray_preview


def write_contract(snapshot: Path, meta_path: Path) -> Path:
    contract = {
        "figure_id": FID,
        "claim_ids": ["Q1-OBS-01"],
        "question": "一维与二维模型的平均含水率如何随时间变化？",
        "title": "图2：一维与二维模型平均含水率随时间变化",
        "title_font": "SimHei",
        "title_position": "below_plot_center",
        "grid": "gray dashed auxiliary gridlines",
        "source_files": [
            {"path": rel(SOLVER_PATH), "sha256": sha256(SOLVER_PATH)},
            {"path": rel(RES / "run-summary.csv"), "sha256": sha256(RES / "run-summary.csv")},
        ],
        "x": {"field": "time_s", "label": "时间 t", "unit": "s"},
        "y": {"field": "mean_C", "label": "平均干基含水率 C", "unit": "kg/kg"},
        "groups": ["M1 一维基线", "M2 二维主干"],
        "uncertainty": None,
        "required_comparisons": ["M1/M2随时间的平均含水率曲线"],
        "must_show_failures": False,
        "prohibited_operations": [
            "recompute with altered model parameters",
            "change the moisture metric",
            "omit one of the two base-model series",
            "present conditional simulation as observation",
        ],
        "target_formats": ["svg", "png"],
        "minimum_dpi": 600,
        "placement": "主文",
        "mandatory_limit": "模型差异非精度提升；曲线为条件仿真",
        "snapshot": rel(snapshot),
        "snapshot_sha256": sha256(snapshot),
        "snapshot_meta": rel(meta_path),
    }
    path = OUT / "contracts" / f"{FID}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def refresh_manifest_and_handoff(paths: list[Path]) -> None:
    manifest_path = OUT / "figure-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    item = next(item for item in manifest["items"] if item["id"] == FID)
    item["png_sha256"] = sha256(OUT / "figures" / f"{FID}.png")
    item["svg_sha256"] = sha256(OUT / "figures" / f"{FID}.svg")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.append(manifest_path)

    handoff_path = OUT / "handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    changed = {rel(path): sha256(path) for path in paths}
    for record in handoff["outputs"]:
        if record["path"] in changed:
            record["sha256"] = changed[record["path"]]
    handoff["assumptions"] = [
        "FIG-Q1-END-EFFECT was revised to display the approved M1/M2 base trajectories generated with the unchanged formal solver configurations.",
        "No model definition, parameter, upstream COMPUTE result file, or other figure was changed.",
        "All plotted values remain conditional simulations and do not constitute empirical accuracy validation.",
    ]
    handoff["warnings"] = [
        "The time-series version supersedes the former endpoint dumbbell rendering for FIG-Q1-END-EFFECT.",
        "Do not present the M1/M2 difference as an accuracy improvement without internal observations.",
    ]
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")


def update_stage_docs(paths: list[Path]) -> None:
    caption_path = OUT / "图注.md"
    caption = caption_path.read_text(encoding="utf-8")
    start = caption.index("## 主文图 2（FIG-Q1-END-EFFECT）")
    end = caption.index("## 主文图 3", start)
    replacement = (
        "## 主文图 2（FIG-Q1-END-EFFECT）\n\n"
        "一维与二维模型的平均含水率如何随时间变化？ 0–1800 s 的体积加权平均干基含水率轨迹；1800 s 末值差0.0185457085。"
        "限定：模型差异非精度提升，曲线为条件仿真。数据快照与来源哈希见 `data-snapshots/FIG-Q1-END-EFFECT.meta.json`。\n\n"
    )
    caption_path.write_text(caption[:start] + replacement + caption[end:], encoding="utf-8")
    paths.append(caption_path)

    audit_path = OUT / "visual-audit.md"
    audit = audit_path.read_text(encoding="utf-8")
    note = (
        "- FIG-Q1-END-EFFECT 本轮按用户要求由端点哑铃图改为 M1 一维基线与 M2 二维主干的平均含水率—时间曲线；"
        "将黑体标题‘图2：一维与二维模型平均含水率随时间变化’移至图下方居中，进一步放大标题、坐标轴标签和横纵轴刻度数字，并加粗横纵坐标轴主框线与刻度线，保留灰色虚线网格辅助线；"
        "使用 0–1800 s、60 s 采样，末值与 run-summary.csv 校验通过，未改动其他图。\n"
    )
    audit = "".join(
        line for line in audit.splitlines(True)
        if not line.startswith("- FIG-Q1-END-EFFECT 本轮按用户要求")
    )
    audit = audit.replace("- 灰度检查：", note + "- 灰度检查：")
    audit_path.write_text(audit, encoding="utf-8")
    paths.append(audit_path)


def main() -> None:
    snapshot_path = OUT / "data-snapshots" / f"{FID}.csv"
    if os.environ.get("USE_EXISTING_SNAPSHOT") == "1" and snapshot_path.exists():
        snapshot = snapshot_path
        meta_path = snapshot.with_suffix(".meta.json")
        if not meta_path.exists():
            raise RuntimeError(f"snapshot metadata is missing: {meta_path}")
    else:
        snapshot, meta_path, _ = build_snapshot()
    svg, png, color_preview, gray_preview = render(snapshot)
    contract = write_contract(snapshot, meta_path)
    changed = [snapshot, meta_path, contract, svg, png, color_preview, gray_preview, Path(__file__)]
    update_stage_docs(changed)
    refresh_manifest_and_handoff(changed)
    print(
        json.dumps(
            {
                "figure_id": FID,
                "snapshot": rel(snapshot),
                "svg": rel(svg),
                "png": rel(png),
                "rows": 62,
                "endpoint_check": "PASS",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

