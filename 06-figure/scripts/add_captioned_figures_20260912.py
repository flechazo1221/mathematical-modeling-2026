from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIGURE_ROOT = PROJECT_ROOT / "06-figure"
OUT_ROOT = FIGURE_ROOT / "captioned-20260912"
OUT_FIGURES = OUT_ROOT / "figures"
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")


# The first and fourth captions are supplied by the user-selected images.
# The remaining order follows the selected paper-figure sequence, with the
# appendix figures continuing as numeric captions.
FIGURES = [
    ("FIG-Q2-C-PROFILES", "图1：不同时刻的径向含水率分布"),
    ("FIG-Q1-C-FIELD", "图2：含水率的径向非均匀性"),
    ("FIG-Q1-END-EFFECT", "图3：二维端面效应对总体含水率的影响"),
    ("FIG-Q2-MODEL-ABLATION", "图4：三种模型在 3 h 时的全域最大干基含水率对比"),
    ("FIG-Q2-GRID-CONV", "图5：M3 终值的网格收敛性"),
    ("FIG-Q3-THRESHOLD-TRAJECTORY", "图6：全域最大含水率接近判据的过程"),
    ("FIG-Q3-BRACKET-ZOOM", "图7：插值时刻的前后点夹逼"),
    ("FIG-Q3-TIME-CONV", "图8：时间步细化结果"),
    ("FIG-Q3-SENS-ONEFACTOR", "图9：单因素扰动下的达标与失败"),
    ("FIG-Q3-COMBINED-BOUNDARY", "图10：组合边界下的达标情况"),
    ("FIG-Q4-RADIUS-TIME", "图11：移动边界半径收缩过程"),
    ("FIG-Q4-THRESHOLD-TRAJECTORY", "图12：收缩域达到全域判据的过程"),
    ("FIG-Q4-JACOBIAN-ABLATION", "图13：Jacobian 修正对守恒的影响"),
    ("FIG-Q4-COMBINED-BOUNDARY", "图14：组合扰动下的成功与失败边界"),
    ("FIG-Q1-GRID-CONV", "图15：M1/M2 场量的空间网格收敛"),
    ("FIG-Q3-SPACE-CONV", "图17：事件时刻的空间网格稳定性"),
    ("FIG-Q4-BRACKET-ZOOM", "图18：Q4 插值时刻与报告值对照"),
    ("FIG-Q4-SPACE-CONV", "图19：Q4 事件时刻的空间网格稳定性"),
]


USER_SELECTED = {
    "FIG-Q2-C-PROFILES": FIGURE_ROOT / "user-selected-20260912" / "figures" / "FIG-Q2-C-PROFILES.png",
    "FIG-Q2-MODEL-ABLATION": FIGURE_ROOT / "user-selected-20260912" / "figures" / "FIG-Q2-MODEL-ABLATION.png",
}

BEAUTIFIED_IDS = {
    "FIG-Q1-C-FIELD",
    "FIG-Q1-END-EFFECT",
    "FIG-Q2-GRID-CONV",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_path(figure_id: str) -> tuple[Path, str]:
    if figure_id in USER_SELECTED:
        return USER_SELECTED[figure_id], "user-selected-20260912"
    if figure_id in BEAUTIFIED_IDS:
        return FIGURE_ROOT / "beautified-20260912" / "figures" / f"{figure_id}.png", "beautified-20260912"
    return FIGURE_ROOT / "figures" / f"{figure_id}.png", "canonical-06-figure"


def load_font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"黑体字体不存在: {FONT_PATH}")
    return ImageFont.truetype(str(FONT_PATH), size=size)


def wrap_caption(caption: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    # Preserve the caption text while wrapping by rendered pixel width.
    lines: list[str] = []
    current = ""
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1), "white"))
    for char in caption:
        candidate = current + char
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [caption]


def add_caption(source: Path, destination: Path, caption: str) -> dict:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    width, height = image.size
    font_size = max(34, round(width * 0.025))
    font = load_font(font_size)
    max_text_width = round(width * 0.92)
    lines = wrap_caption(caption, font, max_text_width)
    draw_probe = ImageDraw.Draw(Image.new("RGB", (1, 1), "white"))
    line_boxes = [draw_probe.textbbox((0, 0), line, font=font) for line in lines]
    line_height = max(box[3] - box[1] for box in line_boxes)
    line_gap = max(12, round(font_size * 0.20))
    top_pad = max(20, round(font_size * 0.30))
    bottom_pad = max(24, round(font_size * 0.35))
    caption_height = top_pad + len(lines) * line_height + (len(lines) - 1) * line_gap + bottom_pad

    canvas = Image.new("RGB", (width, height + caption_height), "white")
    canvas.paste(image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    y = height + top_pad
    for line, box in zip(lines, line_boxes):
        text_width = box[2] - box[0]
        x = (width - text_width) // 2
        draw.text((x, y), line, font=font, fill="black")
        y += line_height + line_gap

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", dpi=(300, 300))
    return {
        "source": str(source),
        "source_sha256": sha256(source),
        "output": str(destination),
        "output_sha256": sha256(destination),
        "source_size": [width, height],
        "output_size": list(canvas.size),
        "caption": caption,
        "font": "SimHei",
        "font_path": str(FONT_PATH),
        "font_size_px": font_size,
        "color": "black",
        "alignment": "center",
        "position": "below-image",
    }


def main() -> None:
    OUT_FIGURES.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for figure_id, caption in FIGURES:
        source, source_group = source_path(figure_id)
        if not source.exists():
            raise FileNotFoundError(f"缺少源图: {source}")
        destination = OUT_FIGURES / f"{figure_id}.png"
        if figure_id in USER_SELECTED:
            # User supplied files already contain the requested caption style.
            with Image.open(source) as opened:
                opened.convert("RGB").save(destination, format="PNG", dpi=(300, 300))
            record = {
                "source": str(source),
                "source_sha256": sha256(source),
                "output": str(destination),
                "output_sha256": sha256(destination),
                "source_size": list(Image.open(source).size),
                "output_size": list(Image.open(destination).size),
                "caption": caption,
                "font": "SimHei (embedded in supplied image)",
                "color": "black",
                "alignment": "center",
                "position": "below-image",
                "preserved_user_supplied_caption": True,
            }
        else:
            record = add_caption(source, destination, caption)
        record["figure_id"] = figure_id
        record["source_group"] = source_group
        records.append(record)

    manifest = {
        "schema_version": "captioned-figures-1.0",
        "status": "DRAFT_DERIVATIVE",
        "note": "Presentation-only derivative; canonical figure data and handoffs were not overwritten.",
        "caption_style": {
            "font": "SimHei",
            "weight": "bold",
            "color": "black",
            "alignment": "center",
            "position": "below-image",
        },
        "n_figures": len(records),
        "figures": records,
    }
    (OUT_ROOT / "captioned-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# 带图注正式图件（派生版）",
        "",
        "统一格式：图注置于图片下方，黑体、加粗、黑色、居中。",
        "",
        "说明：Q2-C-PROFILES 与 Q2-MODEL-ABLATION 使用用户提供版本；其余 Q1/Q2 按已确认的美化优先级和正式目录回退规则取图。原始图件与正式交接文件未覆盖。",
        "",
    ]
    for figure_id, caption in FIGURES:
        lines.append(f"- `{figure_id}`：{caption}")
    (OUT_ROOT / "图注.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT_ROOT), "n_figures": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
