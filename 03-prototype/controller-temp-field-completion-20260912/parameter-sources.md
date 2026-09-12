# 参数来源与敏感性口径

本补全原型只使用项目已经存在的来源登记。`0.8/1.0/1.2` 是围绕已批准公式或冻结边界值的审计扰动，不是由本题数据识别出的物性置信区间；所有非独立来源均标为不可识别，不得在论文中写成实测参数。

|参数|批准定义|项目来源|已有独立来源|迁移状态|本轮区间|
|---|---|---|---|---|---|
|rho|Q2/Q3: 650+128C; Q4: 760+90C (kg/m3)|02-design/contracts/model-q23-fixed.json; model-q4-m1-reference.json; model-q4-m2-moving-fv.json|P05 summary: cocoa real density 825.10 to about 696.25 kg/m3|NOT_TRANSFERABLE|0.8x, 1.0x, 1.2x approved formula; numerical envelope only|
|cp|Q2/Q3: 1450+2736C/(C+1); Q4: 1850+2150C/(C+1) (J/kg/K)|02-design/contracts/model-q23-fixed.json; model-q4-m1-reference.json; model-q4-m2-moving-fv.json|No independent project source located|UNSUPPORTED_IDENTIFICATION|0.8x, 1.0x, 1.2x approved formula; numerical envelope only|
|k|Q2/Q3: 0.21+0.38C/(C+1); Q4: 0.12+0.20C/(C+1) (W/m/K)|02-design/contracts/model-q23-fixed.json; model-q4-m1-reference.json; model-q4-m2-moving-fv.json|No independent project source located|UNSUPPORTED_IDENTIFICATION|0.8x, 1.0x, 1.2x approved formula; numerical envelope only|
|h|25 W/m2/K|decisions/H1-problem.json and approved contracts|P06 reports 5.34 W/m2/K; P08 reports 18.55 W/m2/K under different geometries|NOT_TRANSFERABLE_AS_THIS_MATERIAL|0.8x, 1.0x, 1.2x frozen value|
|hm|8e-7 m/s under Cs-Cinf convention|decisions/H1-problem.json and approved contracts|P06 reports 3.77e-8 m/s; P08 reports 0.007 m/s under different driving-force conventions|NOT_TRANSFERABLE_AS_THIS_DEFINITION|0.8x, 1.0x, 1.2x frozen value|

## 解释边界

- P05 的密度是可可豆而非本题药材；P06/P08 的 `h`、`hm` 来自不同几何、材料或驱动力定义，不能直接替换批准值。
- `cp`、`k` 没有本项目内可用于本题材料的独立测量或可靠区间；本轮只做条件敏感性。
- 因而本轮能回答“结果对参数扰动有多敏感”，不能回答“参数已经由数据识别”。
