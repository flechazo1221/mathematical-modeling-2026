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
5. 紧凑论文图优先使用轻量边框、共享图例和稳定系列身份，但尺寸必须由标签密度决定，不能先压缩后容忍重叠。分类标签多、中文较长、表格含公式或标题与图例同置顶部时，读取 [compact_layout.md](references/design/compact_layout.md)，使用 `scripts/layout_tools.py` 的安全布局函数。
6. 导出 SVG，以及至少 300 DPI PNG（官方规范另有要求时从其规定）。不得通过手工修改位图改变数据表达。
7. 在导出前对仍在内存中的 Figure 运行 `audit_layout(fig)`；任何缺字、刻度重叠、标题—图例碰撞、表格文字溢出或半透明背景叠色都必须回改。随后运行 `scripts/check_figure.py --strict`，并以论文实际显示尺寸逐区放大检查彩色和灰度预览：多位数字须逐字符完整可读且不得与图例、边框重叠；窄柱或窄图元放不下完整文本时应外置标注并预留空间；除非重叠色块本身编码数据，否则分区优先用边界线、括号或互不重叠的色块。失败则修改源代码、重渲并复查，不得仅凭格式检查 PASS 交付。

## CUMCM 正式图表配置

当任务针对 CUMCM 项目的 `06-figure/` 或 H3 已批准的正式图表时，额外执行：

1. 数据曲线使用高对比度、兼顾色盲和灰度打印的颜色；坐标轴、网格、
   标题、图例、刻度和说明文字统一使用黑色。同一类曲线保持一致的实线
   约定，用颜色和 marker 区分时间点或情景。
2. 中文优先使用宋体或已验证的等价字体；变量、单位、刻度、图例和图注
   保持一致。删除无关副标题、装饰性备注和重复说明，将限制条件放入图注
   或正文。
3. 美化只能改变版式、字体、标注和显示层单位，不能改变数据源、冻结快照、
   坐标范围、采样点、单位、指标定义、失败情景或主张类别。禁止为了平滑
   曲线而插值、删点、重算或掩盖异常；科学异常应返回 COMPUTE/EVIDENCE。
4. 正式输出统一提供 SVG、PDF 和 PNG；本项目默认 PNG 至少 600 DPI，并提供
   彩色及灰度预览。交付 PDF 时检查字体嵌入。
5. 运行视觉、程序、数据三类检查：视觉检查版式与字形，程序检查格式、
   尺寸、DPI、字体和 JSON，数据检查源文件/快照/输出哈希及主张—图文件映射。
   所有警告必须记录，不能用“美观”覆盖 QA 结果。
6. 清理图像前，交叉核对当前 manifest、contract、图注、论文/附录引用和
   用户指定范围。明显过期文件先移入可恢复归档；不能仅因文件未出现在单个
   manifest 中就永久删除。历史修订目录应保留，且不得修改上游证据。
7. 批量重绘只能保留一个受控渲染进程，避免重复进程争用同一输出文件；
   渲染结束后重新核验整批文件和 handoff 哈希。

当已有 COMPUTE/EVIDENCE/H3/FIGURE 成果后进行模型或图表修订，先建立版本化
revision 目录和依赖矩阵；旧 manifest、快照、handoff 和图稿作为可追溯基线，
只有依赖发生变化的图才重绘，且必须等待新的 H3 批准后再作为正式图使用。

## 渐进加载

- 数据剖析解释：[data_profiling.md](references/guides/data_profiling.md)
- 图型选择与反误导：[chart_selection.md](references/chart-types/chart_selection.md)、[viz_pitfalls.md](references/design/viz_pitfalls.md)
- 紧凑系统论文风格与防重叠布局：[compact_layout.md](references/design/compact_layout.md)
- 绘图配方与 API：[plot_recipes.md](references/api-templates/plot_recipes.md)、[api.md](references/api-templates/api.md)
- 期刊规格与交付检查：[journal_specs.md](references/quality/journal_specs.md)、[publication_checklist.md](references/quality/publication_checklist.md)
- 视觉复核：[visual_review.md](references/quality/visual_review.md)
- MATLAB：按需使用 `references/roles/编程手/scripts/` 下的出版绘图工具。

每张保留图必须服务于一个明确问题、模型验证或主张。不得隐藏失败样本、选择有利参数、重定义指标或用不相关的双轴制造关系。
