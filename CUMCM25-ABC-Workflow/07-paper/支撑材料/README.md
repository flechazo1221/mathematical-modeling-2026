# 支撑材料说明

- `code/`：完整计算入口及交接构建代码。
- `data/`：题目四份原始 XLSX 附件。
- `results/`：全量结果、中间结果和多光束门状态。
- `logs/`：复现清单、完整运行日志、独立复核与恢复记录。
- `AI工具使用详情.pdf`：按 2026 规则整理的 AI 使用详情。

原项目结构下运行：

```text
python 04-compute/src/run_compute.py --project-root .
```

若仅解压本支撑包，请把 `code/` 恢复为 `04-compute/src/`、`data/` 恢复为 `input/B题/附件/`，并在项目根目录运行上述命令。随机种子、环境版本、输入输出哈希和结果行数见 `logs/复现清单.json`。

