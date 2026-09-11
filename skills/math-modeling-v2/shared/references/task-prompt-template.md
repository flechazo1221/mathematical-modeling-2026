# 独立阶段任务提示模板

主控创建新任务时使用以下结构，不附带上游聊天历史：

```text
使用 $<STAGE_SKILL> 完成本阶段。

PROJECT_ROOT: <ABSOLUTE_PROJECT_ROOT>

允许读取：
- <INPUT_PATHS>

唯一允许写入：
- <STAGE_OUTPUT_DIRECTORY>

已批准人工决议：
- <DECISION_PATHS_AND_HASHES>

必须生成：
- <REQUIRED_OUTPUTS>
- handoff.json

停止条件：
- 完成本阶段后停止，不进入下一阶段。
- 缺少关键输入时返回 BLOCKED。
- 发现可修正问题时返回 FAIL 和精确证据。
- 不得修改上游文件或人工决议。
```

使用创建新任务而不是 fork。若运行环境没有创建任务能力，主控输出上述提示供用户手动创建，不得声称已实现上下文隔离。
