# 视觉与程序审计

- 最终图：22/22 均有 SVG、600 DPI PNG、彩色预览和灰度预览。
- 程序检查：`check_figure.py --min-dpi 300 --strict` 对 22/22 PNG 返回 PASS；最终生成无缺字警告。
- 人工视觉检查：已逐图查看彩色联系表；无中文方框、裁切、图例遮挡或数据越界。跨运行残差图首轮标签拥挤，已保留全部点并改为稀疏标签后重渲。
- 灰度检查：类别同时使用线型/marker；阈值、失败和右删失以虚线、叉号和文字冗余表达。
- 解释边界：V02 窄裕量、V06 有限裕量、Q3 三个与 Q4 一个 72 h 未达标情景、Jacobian 消融失败、守恒残差均显式保留。
- S0：未使用 supplemental-extensions 的结果制作任何图。
- C1：未触发；所有对数轴均由正式需求明确指定，未做未批准的归一化、删减或解释性布局改变。

## 逐图程序结果

- FIG-Q1-C-FIELD: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q1-END-EFFECT: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q2-C-PROFILES: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q2-MODEL-ABLATION: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q2-GRID-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-THRESHOLD-TRAJECTORY: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-BRACKET-ZOOM: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-TIME-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-SENS-ONEFACTOR: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-COMBINED-BOUNDARY: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-RADIUS-TIME: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-THRESHOLD-TRAJECTORY: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-IMPLEMENTATION-AGREEMENT: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-JACOBIAN-ABLATION: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-COMBINED-BOUNDARY: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-VAL-BALANCE-RESIDUAL: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q1-GRID-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q2-V02-MARGIN: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q3-SPACE-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-BRACKET-ZOOM: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-SPACE-CONV: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
- FIG-Q4-DRY-SOLID-CONTINUITY: PASS; PNG 600.0 DPI; SVG/彩色/灰度预览齐全。
