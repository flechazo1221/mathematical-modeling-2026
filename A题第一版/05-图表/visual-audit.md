# 视觉与程序审计

- 当前论文图：13 张（正文 10 张、附录 3 张）均有 SVG、600 DPI PNG、彩色预览和灰度预览。
- 程序检查：保留图均通过 `check_figure.py --min-dpi 300 --strict`；图4、图5、图15和图16已按用户要求重绘。
- 人工视觉检查：已逐图查看彩色联系表；无中文方框、裁切、图例遮挡或数据越界。FIG-VAL-BALANCE-RESIDUAL 已按团队决定移出活动论文图表集并归档。
- FIG-Q2-MODEL-ABLATION：M2、M3、M4分别绘制0–3 h最大含水率时间轨迹，采用三个并列子图并共享相同坐标范围，便于横向比较。
- FIG-Q2-GRID-CONV：固定 `dt=5 s`，扩展为 `n_r=42,62,93,140,175,210` 六组，新增相邻变化面板；数据来自隔离补算包，未覆盖正式 COMPUTE 结果。
- FIG-Q3-SPACE-CONV、FIG-Q4-SPACE-CONV：固定 `dt=60 s`，均扩展为 `n_r=63,93,140,175,210` 五组径向网格；新增数据来自隔离补算包，未覆盖正式 COMPUTE 结果。
- FIG-Q1-END-EFFECT 本轮按用户要求由端点哑铃图改为 M1 一维基线与 M2 二维主干的平均含水率—时间曲线；将黑体标题‘图2：一维与二维模型平均含水率随时间变化’移至图下方居中，进一步放大标题、坐标轴标签和横纵轴刻度数字，并加粗横纵坐标轴主框线与刻度线，保留灰色虚线网格辅助线；使用 0–1800 s、60 s 采样，末值与 run-summary.csv 校验通过，未改动其他图。
- 灰度检查：类别同时使用线型/marker；阈值、失败和右删失以虚线、叉号和文字冗余表达。
- 解释边界：V02 窄裕量改用正文文字披露；V06 有限裕量、Q3 三个与 Q4 一个 72 h 未达标情景、Jacobian 消融失败均显式保留；守恒残差保留在验证表和证据记录中，不制作独立论文图。
- S0：未使用 supplemental-extensions 的结果制作任何图。
- C1：未触发；所有保留图的对数轴均由正式需求明确指定。本轮仅按团队决定移除低信息增益图件，未改变模型、指标或数值。
- 当前工作流接管检测：`current-pipeline-verification.json` 返回 `PASS`；活动清单为13张图，旧图8/10/13均不在活动清单；图4为3模型×19个时间点，图5为6组径向网格，图15/16各为5组径向网格。

## 逐图程序结果

- FIG-Q1-C-FIELD: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q1-END-EFFECT: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q2-C-PROFILES: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q2-MODEL-ABLATION: PASS; PNG 600.0 DPI; SVG/PDF/彩色/灰度预览齐全。
- FIG-Q2-GRID-CONV: PASS; PNG 600.0 DPI; SVG/PDF/彩色/灰度预览齐全。
- FIG-Q3-THRESHOLD-TRAJECTORY: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-BRACKET-ZOOM: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-SENS-ONEFACTOR: PASS; PNG 600.0 DPI；五面板独立纵轴、每组5个实际计算点；横轴标出30–120 min或0.8x–1.2x具体扰动值；pref=0.8x与指数=1.2x的实际时刻为73.4 h/102.7 h；不将72 h写作达标上限；SVG/彩色/灰度预览齐全。
- FIG-Q4-RADIUS-TIME: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-THRESHOLD-TRAJECTORY: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q1-GRID-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-SPACE-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-SPACE-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-JACOBIAN-ABLATION 已按团队决定移出活动论文图表集；V10 数值和失败结论改由正文、验证表及可恢复归档承载。
- FIG-Q4-IMPLEMENTATION-AGREEMENT 已按团队决定移出活动论文图表集；双实现差值与报告值改由正文、证据表及可恢复归档承载。
