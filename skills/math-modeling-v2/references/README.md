# 参考资料导航

本目录采用渐进式加载。先确定当前阶段，只读取对应角色入口；遇到具体任务再读取一份或少量参考文件。

## 根目录

- `SKILL_ROOT`：本仓库根目录，只读。
- `PROJECT_ROOT`：用户项目目录，所有产物写入这里。

任何参考文档中的相对路径均以该文档所在目录为基准；入口 Skill 另有明确根目录约定时从其约定。旧角色指南通过 `../../..` 回到 `SKILL_ROOT`。

## 三角色

| 阶段 | 入口 | 固定交付物 |
|---|---|---|
| 旧版建模指南 | `roles/建模手/ROLE.md` | 仅作参考；新工作流使用 `skills/math-modeling-design/` |
| 旧版编程指南 | `roles/编程手/ROLE.md` | 仅作参考；新工作流使用 COMPUTE 与 FIGURE skills |
| 旧版论文指南 | `roles/论文手/ROLE.md` | 仅作参考；新工作流使用 `skills/math-modeling-paper/` |

## 按任务加载

| 任务 | 读取 |
|---|---|
| 选模型 | `roles/建模手/references/建模设计理论.md` |
| 查具体算法 | `算法索引.md`，再读取一个匹配的 `../assets/*.md` |
| Python/MATLAB 实现 | `roles/编程手/references/工作流程.md` |
| MATLAB 工具箱与出图 | `roles/编程手/references/MATLAB规范.md` |
| 可视化 | `../tools/figure/SKILL.md` |
| 图型选择与科研绘图避坑 | `../tools/figure/references/chart-types/chart_selection.md` |
| Subagent 调度与阶段质检 | `Subagent调度.md` |
| 论文结构 | `roles/论文手/references/章节模板.md` |
| Word 格式 | `roles/论文手/references/论文格式规范.md` |
| LaTeX 格式 | `roles/论文手/references/LaTeX格式规范.md` |

## 工具

| 工具 | 入口 |
|---|---|
| 科研可视化 | `../tools/figure/SKILL.md` |
| 双引擎论文搜索 | `../tools/paper_search/SKILL.md` |
| PDF | `../tools/pdf/SKILL.md` |
| Excel | `../tools/xlsx/SKILL.md` |
| DOCX | `../tools/docx/SKILL.md` |
| LaTeX | `../tools/latex/SKILL.md` |

外部论文只在确有需要时搜索和读取，并保留来源。
