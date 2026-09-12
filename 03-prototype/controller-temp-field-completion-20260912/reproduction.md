# 复现说明

工作根目录为 `mathematical-modeling-2026`。使用项目缓存运行时，在仓库外层工作区执行：

```text
C:\Users\Linza\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe mathematical-modeling-2026/03-prototype/controller-temp-field-completion-20260912/run_completion.py
C:\Users\Linza\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe mathematical-modeling-2026/03-prototype/controller-temp-field-completion-20260912/finalize_handoff.py
```

第一条命令导入只读的批准基线和内部温度场候选，运行 48 个核心配对实例及 33 个候选参数审计实例；第二条命令由现有原始输出生成能量细化表、参数汇总、报告和 schema-compatible `handoff.json`。固定随机种子为 `20260912`；本任务没有使用随机抽样。

复现后应检查：`原始结果.csv` 核心行数 48、敏感性行数 33、`validation-register.csv` 无 FAIL、`input-manifest.json` 与 `handoff.json` 的 SHA-256 均匹配。所有生成文件应位于本目录，不得向正式 `04-compute` 或下游阶段写入。
