# 工作流与交接合同

## 权威状态

主控只以 `PROJECT_ROOT/.workflow/state.json` 为当前状态来源。各阶段完成后必须生成符合 `shared/schemas/handoff.schema.json` 的 `handoff.json`。

## 写入所有权

- 主控：`.workflow/`
- 队伍：`decisions/`
- selection：`00-selection/`
- intake：`01-intake/`
- 用户提供的文献原文：`literature/input/`（队伍只读输入，AI 不得改写）
- literature：`02-literature/`
- design：`02-design/`
- prototype：`03-prototype/`
- compute：`04-compute/`
- evidence：`05-evidence/`
- figure：`06-figure/`
- appendix：`07-appendix/`
- paper：`08-paper/`
- audit：`09-audit/`

输入附件只读。阶段不得直接修改上游目录；需要修正时返回精确证据和责任阶段。

## 状态

阶段回执只能为：

- `PASS`：必需产物存在，验证完成且不存在阻塞。
- `FAIL`：发现可修正的实质问题。
- `BLOCKED`：缺少完成当前结论所必需的输入、权限、依赖或证据。

没有可选工具或独立代理本身不自动构成 `BLOCKED`；只有因此无法验证核心正确性时才阻塞。

## 新任务要求

主控仅在用户明确允许创建独立任务后启动流水线。每个 AI 阶段使用新任务，提示必须包含：阶段 Skill、`PROJECT_ROOT`、允许读取的文件、唯一写入目录、已批准决议、必需输出和停止条件。不得使用 fork 把上游对话历史带入新阶段。

主控收到新任务 ID 后记录到 `.workflow/threads.json`。阶段完成后先验证回执和哈希，再更新状态。人类闸门未批准时停止，不创建下一任务。

H1 批准后必须进入 `WAITING_FOR_LITERATURE` 并结束当前轮次。主控可先通过文献获取 Skill 生成知网官方入口与可复制检索式，再等待用户打开页面并完成登录或验证码；用户明确页面就绪后，AI 可在该已授权会话中检索、筛选、登记并下载正常可访问的文献，但不得代做验证码、输入凭据或绕过付费与访问控制。用户自行提供文献仍是有效路径。至少一份受支持文献真实存在且用户完成来源集复核后，主控才可启动独立的 LITERATURE 阅读任务。LITERATURE 完成后必须进入 L1 人工审核，向队伍提交文献集合与总结审核包；只有 `decisions/L1-literature.json` 由真实队员设为 `TEAM_APPROVED` 后，DESIGN 才能启动。
