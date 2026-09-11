# 紧凑论文图与防重叠布局

需要紧凑、轻量、系统论文式排版时读取。它是一种视觉语言，不覆盖数据语义、图表合同或期刊硬约束。

## 可采用的视觉语言

- 去掉上、右轴线；保留浅灰细虚线主网格。
- 同一系列跨图保持颜色、marker、line style 或 hatch 不变。
- 多面板只保留一个顶部共享图例；图例不得与总标题占用同一垂直带。
- 面板编号锚定 axes fraction，统一物理偏移。
- 优先 SVG/PDF 矢量正文图，同时输出至少 300 DPI PNG 预览。
- 颜色之外必须有 marker、线型或纹理，保证灰度可辨。

不要机械照搬归一化、对数轴、缺失类别或固定单栏尺寸；这些选择仍由数据语义和 figure contract 决定。

## 标签密度先于尺寸

先统计每个轴的类别数、最长标签字符数、行数和旋转角，再定画布：

- `类别数 <= 6` 且短标签：可用单行水平标签。
- `7–12` 个类别：优先缩写、分组带或 30–45° 旋转；不要同时保留多行长标签。
- `>12` 个类别：拆成语义一致的小面板、使用矩阵/热图，或增加物理宽度；不得仅靠缩小字号解决。
- 中文标签、数学公式和双语标签按长标签处理；最终字号不得低于 6 pt。
- 公式表格使用 mathtext/LaTeX 语法，例如 `$d(n)=\frac{q}{\sqrt{n^2-\sin^2\theta_0}}$`，不要显示 `sqrt(...)`、`theta_0` 等代码式文本。

若缩写标签，必须在轴标题、图注或分组标签中解释。不得省略类别。

## 顶部区域预算

共享图例、总标题和面板标题必须占三条不同的垂直带。优先调用：

```python
from layout_tools import apply_compact_paper_style, add_shared_legend_safe

apply_compact_paper_style(lang="zh")
fig.suptitle("核心问题", y=0.90)
add_shared_legend_safe(fig, axes, y=0.99, ncol=4)
fig.subplots_adjust(top=0.72)
```

如果图例换成两行，增加顶部预算或移到图外侧；不要让 `bbox_inches="tight"` 代替布局设计，因为它只能扩大画布，不能消除对象之间的碰撞。

## 分组分类轴

密集分类轴用短刻度表达组内变量，用额外分组标签表达上层类别：

```python
from layout_tools import set_grouped_category_ticks

set_grouped_category_ticks(
    ax,
    tick_labels=["10R", "10M", "15R", "15M"] * 3,
    groups=[("W1", 0, 3), ("W2", 4, 7), ("W3", 8, 11)],
    rotation=45,
)
```

这比 `W1\n10°/reasoned` 重复 12 次更易读，同时完整保留所有类别。

## 表格

- 先把长状态或说明按语义换行，再绘表；不要依赖自动裁切。
- 数学列用 mathtext；列标题使用自然语言。
- 每行高度至少容纳实际行数，长说明列分配更大列宽。
- 运行 `audit_layout(fig)` 检查单元格文字是否越界；发生溢出时优先增加行高/列宽或语义换行，不要把字号压到 6 pt 以下。

## 必过闭环

1. `finalize_compact_figure(fig)` 后再放面板编号。
2. `audit_layout(fig)` 必须没有 FAIL；WARN 逐项人工确认或修复。
3. 渲染彩色和灰度预览，以最终纸面尺寸逐张检查。
4. 检查标题—图例、刻度—分组标签、面板编号—标题、公式—单元格四类高频碰撞。
5. 任何调整都回到源代码重绘，不在 PNG 上手工修改。
