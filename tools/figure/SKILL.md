---
name: figure
description: Create or revise evidence-driven statistical and scientific data figures when the user asks to plot data, choose a chart, prepare a publication figure, or audit an existing chart. Do not use for diagrams, decorative illustrations, or workflow-level claim approval.
---

# 科研可视化工具

`SKILL_ROOT` 是套件根目录。脚本从 `tools/figure/scripts/` 读取，用户数据保持只读，输出写入用户项目。

## 最小工作流

1. 剖析真实数据的字段、类型、样本量、缺失、分组、分布、异常值、单位和时间/空间顺序。可运行 `scripts/profile_data.py`。
2. 用一句话声明图要回答的问题，并记录字段、筛选、聚合、变换、误差定义、尺寸和格式。多面板或高风险图读取 [figure_contract.md](references/guides/figure_contract.md)。
3. 依据数据语义与论证目标选图；不确定或用户指定图型可能误导时读取 [chart_selection.md](references/chart-types/chart_selection.md)。不为表面多样性设置图数或图型配额。
4. 使用最终物理尺寸绘制。颜色需色盲友好并辅以线型、标记或纹理；误差必须说明 SD、SEM、CI、样本量和检验口径。
5. 导出 SVG，以及至少 300 DPI PNG（官方规范另有要求时从其规定）。不得通过手工修改位图改变数据表达。
6. 导出前运行 `scripts/visual_qa.py` 的 `audit_layout(fig)`，导出后运行 `scripts/check_figure.py --strict`；再以论文实际显示尺寸检查彩色和灰度预览。多面板图必须逐区放大核对数值标注、图例、边框及背景层：数值文本须完整且不得与图例/边框重叠；窄柱或窄图元放不下完整文本时应外置标注并预留空间；除非重叠色块本身编码数据，否则不得叠加半透明背景，分区优先用边界线、括号或互不重叠的色块。发现问题必须改源代码、重渲并复查，不得仅凭格式检查 PASS 交付。

## 渐进加载

- 数据剖析解释：[data_profiling.md](references/guides/data_profiling.md)
- 图型选择与反误导：[chart_selection.md](references/chart-types/chart_selection.md)、[viz_pitfalls.md](references/design/viz_pitfalls.md)
- 绘图配方与 API：[plot_recipes.md](references/api-templates/plot_recipes.md)、[api.md](references/api-templates/api.md)
- 期刊规格与交付检查：[journal_specs.md](references/quality/journal_specs.md)、[publication_checklist.md](references/quality/publication_checklist.md)
- 视觉复核：[visual_review.md](references/quality/visual_review.md)
- MATLAB：按需使用 `references/roles/编程手/scripts/` 下的出版绘图工具。

每张保留图必须服务于一个明确问题、模型验证或主张。不得隐藏失败样本、选择有利参数、重定义指标或用不相关的双轴制造关系。
