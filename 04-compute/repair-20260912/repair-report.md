# COMPUTE 哈希修复记录

## 范围

本次仅处理以下三个不一致对象，并更新 `04-compute/handoff.json` 中对应输出哈希：

- `04-compute/logs/extended.log`
- `04-compute/results/sensitivity-extended.csv`
- `04-compute/复现清单.json`

未改变 H1/H2/H3 的问题、模型、阈值、指标、主张、正式结果或补充路线地位；未制作正式论文图。

## 修复前证据

原文件副本及其 SHA-256 位于 `04-compute/repair-20260912/before/`。原扩展 CSV 与后续真实运行结果逐字节一致，SHA-256 均为 `f778eb33975d0df7eb3c25a54eb05cb46f3d5e2f797948cdbd7168eaf3038903`。这说明数值变化不是本次修复产生的；旧清单中登记的是更早版本的哈希。

## 已执行命令

在收到“不用复跑”的用户消息前，已完成一次真实扩展运行：

`C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe 04-compute/src/formal_compute.py --mode extended`

进程退出码为 0。收到消息后未再执行任何模型计算，仅更新元数据并进行只读核验。

## 扩展敏感性核验

CSV 共 4 行、11 个字段。四行分别对应原 72 h 内未达阈值的案例：Q3 `pref/low`、Q3 `exponent/high`、Q3 `combined_boundary_empirical/low`、Q4 `combined_boundary_empirical/low`。它们延长计算后的分钟级报告时刻分别为 73.4 h、102.7 h、128.33333333333334 h、88.43333333333334 h；最终 `max(C)` 均小于冻结阈值 0.149999，且报告秒数均为 60 s 的整数倍。

## 最终哈希

- `extended.log`: `0f6d90cb7d4b5f1d28f6d266f74135780cae7823d1060f78d522baaf11d26cfd`
- `sensitivity-extended.csv`: `f778eb33975d0df7eb3c25a54eb05cb46f3d5e2f797948cdbd7168eaf3038903`
- `复现清单.json`: `291f65c629479ad44b2ef49096f525254b0c3a68653b3ee42ccb3c5db3d1bdee`
- `handoff.json`: `21b736c942d5aa79ea08c4da9a93129854271f101c89c426dcbb79d9da73eb95`

## 独立验证

- 复现清单 inputs：16/16 存在且哈希一致。
- 复现清单 outputs：42/42 存在且哈希一致。
- handoff inputs：16/16 存在且哈希一致。
- handoff outputs：45/45 存在且哈希一致。
- handoff frozen decisions：2/2 存在且哈希一致。
- 合计 handoff 校验：63/63 一致，状态为 `PASS`。

`repair-20260912/` 是修复审计证据目录，不属于冻结 COMPUTE 正式输出集合，因此不纳入复现清单或 handoff 的 outputs，避免审计记录与清单形成自引用。

## 结论

修复后的扩展结果与修复前 CSV 完全一致，没有实质改变 H3 已批准结论。三个阻塞性哈希不一致已消除。
