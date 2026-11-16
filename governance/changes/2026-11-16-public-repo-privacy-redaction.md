# 治理变更记录 GC-2026-1116-01：治理仓公开化前的作者数据清除（privacy redaction before public release）

- 日期：2026-11-16
- 编号：GC-2026-1116-01
- 类型：数据合规修订（公开仓 PII 清除 + git 历史重写）
- 触发：用户指令“9 个论文仓库和治理能力仓库都推送到 github.com/PaperWorkflows 组织下，治理能力作为公共仓库”，推送后按用户要求审计公开仓是否夹带用户数据与论文信息。
- 规则依据：AGENTS.md F7（保留现场）/ F9（治理变更纪律）；仓库分工（论文私有仓承载全量作者信息，治理公开仓不承载）

> 本记录按“只写类型与计数、不写字面值”的原则撰写，避免把待清除的数据又写回仓库。完整映射表存于本地工作副本（不入库）。

---

## 1. 审计结论（推送后立即执行，只读）

治理仓 `PaperWorkflows/governance` 已推为 **public**，审计发现：

| 类别 | 结果 |
|---|---|
| 作者中文姓名 | 5 位作者全名出现在历史提交中，合计约 450 个提交命中（单人最高 252） |
| 作者英文姓名 | 2 种拼写及其大小写变体共 5 种形态，合计约 290 个提交命中 |
| 个人邮箱 | 4 个地址（2 个 QQ 邮箱、1 个 Gmail、1 个 189.cn 邮箱），合计约 150 个提交命中 |
| 工作单位 | 2 个单位全称，合计约 140 个提交命中 |
| 电话号码 | 1 个 11 位号码（schema 示例值），47 个提交命中 |
| 论著正文内容 | **0 命中**：摘要、结论、体系名称等稿件特征串在全库历史零命中，稿件正文未泄漏 |
| 各篇运作元数据 | 论文编号（P1–P9）、版本号、评审轮次、字数等**有**命中；属治理记录固有内容，非稿件内容，本次不清除 |

`temp/` 目录被 `.gitignore` 忽略（0 个被跟踪文件），其中的作者数据未进入仓库；本地副本另做一次同映射脱敏，防止后续不慎入库。9 个论文仓均为 **private**，按仓库分工可载全量作者信息，无需处理（已逐个核实 visibility）。

## 2. 处置

1. **即时止血**：`gh api -X PATCH repos/PaperWorkflows/governance -f private=true`，公开访问立即停止（推送至暴露不足 10 分钟）。
2. **当前树脱敏**：PII 字符串按统一映射表替换为占位符（`作者A`–`作者E` / `Author A`–`Author B` / `<邮箱已脱敏>` / `<单位已脱敏>` / `<电话已脱敏>` / `P1-EXAMPLE-20251110`），涉及 9 个被跟踪文件。
3. **`authors/registry.yaml` 整体替换**为结构占位条目（该文件无任何工具消费，仅 `templates/layout/registry.yaml` 被 layoutlib 使用），并加注“真实作者数据只登记在论文私有仓 authors.yaml”。
4. **历史重写**：`git filter-repo --replace-text` 以同一映射表清除全部历史提交的 blob 与提交信息。
5. **验证后重新公开**：新克隆全历史复扫零命中后方可 `private=false`（见 §5）。

## 3. 精确变更清单

| 文件 | 变更 |
|---|---|
| `authors/registry.yaml` | 真实作者条目 → 占位条目 + 分工说明注释 |
| `SKELETON-PLAN.md` | 示例作者中文名/英文名/仓库名拼音 → 作者A / Author A / EXAMPLE |
| `tools/metalayout.py` | 契约注释示例英文名 → `ZHANG San` / `Author A` |
| `tools/paper.py` | CLI 帮助示例仓库名与作者拼音 → `P1-EXAMPLE-20251110` / `EXAMPLE` |
| `schemas/author.schema.json` | 电话示例值 → `13800000000`（库内既有占位） |
| `governance/changes/2026-11-1{1,2,3,4}-*.md`（5 个） | 历史记录中出现的姓名/邮箱/单位片段脱敏 |
| `README.md` | 示例仓库名 → `P1-EXAMPLE-20251110` |
| `templates/paper/authors.yaml` | 契约注释示例正/误序英文名 → `ZHANG San` / `San ZHANG` |
| `governance/changes/2026-11-16-public-repo-privacy-redaction.md` | 本记录（新增） |

映射表规则（长键优先，避免子串抢先）：个人邮箱（4 个）→ `<邮箱已脱敏>`；11 位电话号码 → `<电话已脱敏>`；单位全称（2 个）→ `<单位已脱敏>`；作者中文姓名（5 人）→ `作者A`–`作者E`；对应英文姓名及大小写变体 → `Author A`–`Author B` / `AUTHOR A` / `EXAMPLE`；含第一作者拼音的示例仓库名 → `P1-EXAMPLE-20251110`。

保留不脱敏项（非本项目用户数据）：`janssenkm@users.noreply.github.com`（用户自选的公开提交身份）、`git@github.com`、`zhangsan@example.com`、`13800000000`、`stie@mail.sysu.edu.cn`（刊方公开邮箱）、`huangxd@163.com`（刊方示例）。

## 4. 理由

1. 公开仓不得承载可识别到自然人的数据；论文私有仓才是作者信息的唯一登记处（仓库分工既定）。
2. 历史提交同样构成公开内容，仅改当前树不够，必须重写历史。
3. `temp/` 已被忽略且未推送，无需处理。
4. 稿件正文零命中，说明“论文侧与治理侧分离”执行有效；问题集中在治理记录把作者数据当成了示例与登记对象。

## 5. 验证方法与结果

| # | 验证项 | 方法 | 结果 |
|---|---|---|---|
| a | 当前树 PII | 19 类模式 `grep -rl`（排除 `.git/`、`temp/`） | 零命中 |
| b | 结构完整 | `py_compile` 四个工具 + `paper.py validate` + `build docx` | 全部通过 |
| c | 历史重写 | `git filter-repo --replace-text` 后 `git clone --no-local` 新仓，全历史复扫 19 类模式 | 零命中 |
| d | 远端一致 | force push 后经 `gh api` 取远端默认分支树复扫 | 零命中 |
| e | 重新公开 | 仅当 c/d 均零命中后执行 `private=false` | 见执行记录 |

## 6. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | GitHub 对已推送对象有缓存，force push 后旧 SHA 短期内仍可能可访问 | 重新公开前保留私有状态观察；如需彻底清除，联系 GitHub Support 请求清除缓存视图 |
| R2 | 历史重写使本地 commit SHA 全变 | 本地为唯一工作副本，重写前已确认无其他克隆/协作者 |
| R3 | 脱敏把历史记录改成占位符，语义可读性下降 | 统一映射表 + 本节存档；真实数据仍可由论文私有仓与本地 `authors.txt` 取回 |
| R4 | 论文私有仓含全量作者信息 | 属既定分工；已核实 9 仓 visibility=private |

## 7. 恢复方式

- 本地重写前状态：重写前以 `git bundle create` 全量备份；重写命令与映射表见 §2/§3。
- 远端：重新公开用 `gh api -X PATCH repos/PaperWorkflows/governance -f private=false`；回退到暴露状态（不推荐）直接执行同一命令即可。
