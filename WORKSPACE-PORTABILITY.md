# 可移植工作区说明

本仓库已包含当前数学建模工作流继续运行所需的项目状态与技能套件。

## 已同步内容

- `skills/math-modeling-v2/`：工作流控制、共享 schema、阶段技能、脚本、算法索引和质量规范。
- `.workflow/`：当前工作流状态、任务记录、AI 使用记录和阶段日志。
- `decisions/`：H0、H1、L1 等人工决策记录。
- `00-selection/`、`01-intake/`、`02-literature/`：已完成阶段交付物、语料库、证据卡和交接文件。
- `literature/`：检索计划、候选清单、下载记录和用户提供的可读文献。
- 其他已提交的阶段文件与临时恢复记录。

## 另一台电脑上的继续方式

1. 克隆仓库并进入项目根目录。
2. 使用 Python 运行 `skills/math-modeling-v2/scripts/workflow_control.py --project-root <PROJECT_ROOT> status` 检查状态。
3. 当前状态应停在 L1 之后；先确认 `decisions/L1-literature.json` 和 `02-literature/handoff.json`，再按 `skills/math-modeling-v2/skills/math-modeling-design/SKILL.md` 创建新的 DESIGN 任务。
4. 将 `skills/math-modeling-v2` 视为仓库内技能源，不依赖原电脑的 `C:\Users\Lenovo\.codex\skills` 路径。

## 注意

`CUMCMThesis` 保留为嵌套 Git 仓库链接；外层仓库不包含其内部提交内容。若另一台电脑需要该模板内容，应单独初始化/克隆该嵌套仓库。
