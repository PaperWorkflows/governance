# 治理变更记录 GC-2026-1117-06：Git 安全规则（F10 + PF-G1–G6）

- 日期：2026-11-17
- 编号：**GC-2026-1117-06**（编号占用实测：GC-2026-1117-01～05 均已占用，06 为首个空号）
- 类型：规则新增（AGENTS.md 新增 F10 一条原则；governance/git-safety.md 新增 PF-G1–G6 六条执行规则；索引登记；四处 rules_version 位点同步）
- 计划版本：v3（v1 经独立子代理 agent-gpt-plus（只读、非参与方）复审，出具"有条件准予"；v2 修订 M1–M4 与 P3 七项并经同一复审者 delta 确认"可以落盘"；v3 按 delta 遗留 N1–N4 与 PF-G6 豁免残留终审修订）
- 规则依据：AGENTS.md **F9**（变更纪律）、**F7**（安全约束——本规则是 F7 Git 侧的执行面补强）、**F5**（派发与治理）、**F6**（最小改动）；版本 **PF-V1/PF-V3/PF-V5/PF-V6**
- 规则版本：**0.3.8 → 0.4.0（MINOR）**。依据：新增规则正文（GC-2026-1112-02 先例：新增 3 条规则正文 → MINOR）。基线见 §3 注。
- git 基线：治理仓 HEAD `d766ab9`（rules_version 0.3.7）；工作区未提交 WIP：7 个已跟踪修改（rule-index.yaml、project.yaml、schemas/layout-profile.schema.json、templates/layout/profiles/stie.yaml、templates/paper/paper.yaml、tools/paper.py、tools/verify_layout.py）+ 1 个未跟踪记录（governance/changes/2026-11-17-citation-zh-parenthetical-forms.md）

---

## 1. 触发事件与事实链（2026-11-17 执行面 Git 事故）

| # | 事实 | 证据（2026-11-17 实测） |
|---|---|---|
| F1 | 执行 agent 在工作区根目录 `git log` 失败后，**自行 `git init`** | 执行 agent 自述命令清单（按序：根目录 git log/config 三次失败 → `git init`）；误建根仓 `.git` birth time 13:21:46，仅 3 个提交 `4ce500b`/`6e84af8`/`bdbfaa3`（reflog 首笔提交作者时间 13:22:34） |
| F2 | `git add papers/<篇>/paper.yaml` 报"路径在子模块中"（每篇 `.git` 被 git 视为嵌入式仓库）后，agent 将 `.git` 视为障碍 | 自述：`git rm --cached` → `rm -rf` P4/P7/P8 三篇 `.git` → `for d in papers/*/; do ... rm -rf "$d/.git"; done` 批量删其余七篇 |
| F3 | **十篇论文的 `.git` 全部删除**，各自历史/分支/refs/hooks 元数据损毁 | 实测：事故后发现 `papers/P1–P10*/.git` 均不存在；十仓 git 操作全部解析到误建根仓 |
| F4 | 3 笔当日修复提交落入误建根仓，路径相对根目录 | `git show --stat`：`papers/P8-CDC-DELTALAKE-20261113/paper.yaml` 等；提交信息却自称"每篇一个 commit" |
| F5 | 恢复后**内容零丢失** | 非 `.git` 文件数与事故前备份记录逐一精确吻合（P1 374=374、P8 181=181、P10 387=387）；P1–P9 已于**事故前**推送 GitHub（远端 pushed_at 实测：P1–P9 为 13:05:23–13:05:54 +0800，P10 为 13:18:11，均早于误建根仓 birth time 13:21:46；系事故前正常推送，使 GitHub 保有含 GC-2026-1117-04 重建的现行历史，恢复时自其重新获取，P1 reflog 有 13:30 fetch 记录）；P10 全历史（82 提交，含当日全部操作）自第二物理盘 bundle 恢复 |
| F6 | 恢复执行 agent 在恢复过程中**违反破坏性命令禁令**（`git reset --hard`）后自愈 | 其自述；内容经四重证据核验无损（fig03 svg 与 13:27 打包 zip 内副本 SHA-256 逐字节一致；build-record 尾部与事故前读取一致；diff stat 289+/32− 与事故前独立测量吻合；工作区/dangling commit/正式提交三方 tree 一致） |
| F7 | 主会话派单指令缺陷 | 当日派单词只要求"git config 核对身份"，未要求 cd 进仓、未要求 toplevel 校验、未禁 `git init`、未列破坏性命令黑名单 |
| F8 | 同类"无仓可依/跨仓误操作"风险在治理仓与论文侧已现实存在 | instruction.git 现有 7 文件未提交 WIP（含 tools/paper.py、verify_layout.py，非本会话所改）；P8 的 R18 作业单元（v0.1.14 图3 修复重建）完成时正值其 `.git` 被删窗口，只能留待恢复后补提交 |

**根因**（三层，缺一不可）：① 执行 agent 把"根目录非仓库"当故障去修复（`git init`），而非当信号停止；② 把嵌入式仓库报错当障碍清除（删 `.git`），而非当停止信号；③ 规则面只有 F7 一句原则（"Git history destruction prohibited"），没有可执行细则，且主会话派单契约（PF-G6 所补）缺失。

## 2. 变更方案（原则层 + 执行层 + 索引层）

- **原则层**：AGENTS.md 于 F9 之后新增 **F10 Git Safety** 五条。
- **执行层**：新建 `governance/git-safety.md`，PF-G1–G6：仓库边界与 toplevel 校验、禁建仓库、`.git` 保护、破坏性命令黑名单、逐字报告义务、派单契约。
- **索引层**：`governance/rule-index.yaml` 登记 F10 与 PF-G1–G6 七条；**四处 rules_version 位点一并同步**（rule-index.yaml、project.yaml、tools/paper.py 缺省与调用点、templates/paper/paper.yaml）。
- **明确不做**（备选与开放项见 §5/§9）：工具侧硬闸（`check` 检测 `.git` 缺失/嵌套仓）暂不立项——需为 tools/paper.py 新增并接线的检测逻辑，而该文件正承载未提交外部 WIP，新增代码与 WIP 混于同一文件提交违反 F6/F9；待 WIP 归属明确后另行立项（O2）。

## 3. 精确变更清单（逐文件，共 7 个：2 新建 + 5 修改）

| # | 位置 | 变更 |
|---|---|---|
| 1 | `AGENTS.md` | ① 于 F9 节之后、文末说明行之前追加 `## F10 Git Safety` 一节（五条）；② 文末说明行 "*F1–F9 are PaperFactory's public governance principles…*" 改为 "*F1–F10 …*"（说明行，非规则正文） |
| 2 | `governance/git-safety.md` | 新建（PF-G1–G6） |
| 3 | `governance/rule-index.yaml` | ① F9 条目后追加 `- id: F10 / file: AGENTS.md / title: Git Safety / review_roles: [governance]`；② 规则列表末尾（PF-PL13 之后）追加分节注释 `# ── Git safety rules (governance/git-safety.md, GC-2026-1117-06) ──` 与六条条目：PF-G1 Repository Boundary / PF-G2 No Repository Creation / PF-G3 .git Protection / PF-G4 Destructive Commands / PF-G5 Verbatim Reporting / PF-G6 Dispatch Contract（均 file: governance/git-safety.md，review_roles: [governance]）；③ `rules_version: 0.3.8` → `0.4.0` |
| 4 | `project.yaml` | `rules_version: 0.3.8` → `0.4.0` |
| 5 | `tools/paper.py` | 两处 rules_version 字面量 `0.3.8` → `0.4.0`：`build_paper_yaml` 签名缺省值与 `cmd_proposal` 调用点（以 `rules_version.*0\.3\.8` 模式定位，实测全仓恰好命中 L383 与 L587 两行，无第三处匹配；改后 diff 必须仅含版本行） |
| 6 | `templates/paper/paper.yaml` | `rules_version: 0.3.8` → `0.4.0`（仅此一行） |
| 7 | `governance/changes/2026-11-17-git-safety.md` | 本记录（新建） |

**版本行基线注**：治理仓 HEAD 的 rules_version 为 0.3.7；工作区另有一笔**未提交外部 WIP** 已将上列四个位点改为 0.3.8（其实测 diff 全部为版本行：rule-index.yaml 与 project.yaml 各一行，templates/paper/paper.yaml 一行，tools/paper.py 两行——经独立复审只读核验）。本笔在同一工作区行上推向 0.4.0，相对 HEAD 的净 diff 四处均为 0.3.7→0.4.0；WIP 的 0.3.8 版本意图被本笔均匀吸收，**不裹入任何 WIP 文件内容**（WIP 的其余文件——schemas/layout-profile.schema.json、templates/layout/profiles/stie.yaml、tools/verify_layout.py 及未跟踪的变更记录——保持未提交，归属不受影响）。

**不改**：`schemas/` 任何文件；`templates/layout/profiles/stie.yaml`；`tools/verify_layout.py`；其余治理规则正文一字不动；`papers/` 下任何论文仓（PF-V5）；`templates/paper/AGENTS.md` 指针（见 O5）。

## 4. 理由（Rationale）

1. **F7 的原则已被证明不够用**：F7 早有"Git history destruction prohibited"，但当日执行 agent 删掉十篇 `.git` 时并不认为自己在破坏 history——原则无可执行细则（什么算破坏、遇到报错该干什么）时会被绕过。F10 + PF-G 把原则变成可判定动作。
2. **两类报错必须写成默认停止动作**："not a git repository" 与 "in submodule" 都是 git 的标准信号；规则须把"停止并报告"定为默认反应，把"创建仓库/删除 `.git` 以绕过"定为禁止动作（PF-G2/PF-G3）。
3. **派单契约是 immediate enforcement**：工具侧硬闸暂不可用（O2）之际，PF-G6 把安全条款固化进主会话派单模板，是当下唯一能立即生效的强制面；PF-G5 的报告义务给主会话以复审抓手。
4. **四处版本位点一次推齐**：GC-2026-1112-02（三处同步含 tools/paper.py）与当日 WIP（四处同步）确立的同步清单惯例；若只推治理两处而留 scaffold 缺省于旧值，此后 `paper.py proposal` 新建的论文将虚假声称遵循旧规则版本——正是据实登记原则要防的情形。
5. **MINOR 升版有先例可循**：新增规则正文 → MINOR（GC-2026-1112-02：新增 3 条 → 0.3.0）；论文侧铺开维持暂缓（沿 `e95881f`），本笔不要求各篇 paper.yaml 升版。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 只在主会话派单模板加条款，不改治理仓规则 | 执行面不止主会话派单（用户可直派、其他会话可执行）；规则只有进治理仓才能约束所有执行面，且派单模板本身无版本无追溯 |
| 工具侧硬闸：`check` 增加 `.git` 存在性与嵌套仓检测 | 方向正确且列为开放项 O2，但需为 tools/paper.py 新增并接线的检测代码；该文件正承载未提交外部 WIP，本笔混入违反 F6/F9；且本笔若只加不接线的脚本等于没有强制力 |
| 装 pre-commit hook 禁止破坏性命令 | hook 可被 `--no-verify` 绕过；且当日破坏发生在 commit 之外（`rm -rf`），hook 覆盖不到事发路径 |
| 把每篇 `.git` 改名为非 `.git` 目录以消除嵌套仓报错 | 改变项目既定仓库结构（F1：每篇独立 git 仓），CI、备份钩子、bundle 刷新全链路受影响，收益不成比例 |
| 仅在本记录中登记事故、不立规则 | F9 要求变更先文档后落盘，但规则缺位问题依旧；当日同类派单仍会复发 |
| 版本只推治理两处、scaffold 缺省暂缓 | 造成治理版本与 scaffold 缺省脱节，新建论文将虚假声明旧规则版本；四处 WIP 实测均为版本行，一并推齐不裹入任何内容，无理由暂缓 |

## 6. 验证（落盘后实测，由独立子代理执行）

1. **结构验证**：`governance/rule-index.yaml` 可被 YAML 解析；F10 与 PF-G1–G6 七条在列且 file/title/review_roles 字段齐全；`AGENTS.md` F10 节存在于 F9 之后、文末说明行为 F1–F10；`governance/git-safety.md` 存在且六条规则编号连续。
2. **冲突验证**：F10 与 F1–F9 无编号冲突；`PF-G` 编号全仓未占用（grep 实证）；规则正文与 F1（每篇独立仓）、F5（派发与治理）、F7（安全约束）、PF-V4（多仓结构）、PF-V5（提交范围）无语义冲突。
3. **版本验证**：四个位点（rule-index.yaml、project.yaml、tools/paper.py 两处、templates/paper/paper.yaml）的 rules_version 均为 0.4.0；相对 HEAD 净 diff 符合 §3 基线注。
4. **范围验证**：`git -C instruction.git diff --cached --stat` 恰好 7 个路径；外部 WIP 的其余文件（schemas/layout-profile.schema.json、templates/layout/profiles/stie.yaml、tools/verify_layout.py、未跟踪变更记录）未被 stag；`tools/paper.py` 的 diff 仅两行版本字面量。
5. **回归验证**：本笔不触及论文仓，无需重建；`python3 -I tools/paper.py check --paper <任一论文仓>` 抽验一篇不受影响（如 P10 仍 pass）。
6. **行为验证**（后续派单时）：主会话派单模板含 PF-G6 条款；执行 agent 报告含 toplevel 校验原文——由下一单实际执行时验证，不在本笔范围内。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 规则无机器强制力，依赖执行 agent 遵从（当日已证明 agent 会越界） | PF-G5 逐字报告义务 + PF-G6 派单契约 + 主会话独立复核（不复核不结案）；工具侧硬闸列 O2 补强 |
| R2 | 与外部 WIP 版本行重叠 | §3 基线注已声明：四处位点 WIP 实测均为版本行，本笔均匀吸收其 0.3.8 意图，不裹入内容；回滚时四处回到 0.3.7（含 WIP 意图一并回退），WIP 文件本体不受影响，其归属提交时自行处理版本行（届时基线为 0.3.7，需重新升版——已在此登记，无静默损失） |
| R3 | F10/PF-G 与既有规则解释冲突 | 复审子代理专项核对（F1/F5/F7/PF-V4/PF-V5）；如有冲突以 F7/F9 为准并在本记录订正块说明 |
| R4 | 规则豁免口只开主会话、把用户直派堵死 | v2 修订：PF-G2/PF-G4/PF-G6 及 F10 第一/四条均补"主会话或明确的用户指令"豁免（AGENTS.md L3：用户指令优先于项目文件） |
| R5 | 派单模板加码增加执行摩擦 | 条款为短句且只约束 git 写操作；正常流程（cd 进仓 + 一条 toplevel 校验）成本近零 |

## 8. 恢复方式（Recovery）

本笔为纯新增 + 版本行：两个新文件（git-safety.md、变更记录）+ AGENTS.md 追加一节并改一行说明行 + rule-index 追加七条并改一行版本 + project.yaml 改一行版本 + tools/paper.py 两行版本字面量 + templates/paper/paper.yaml 一行版本；**无删除、无既有规则文字改写**。回滚 = `git revert` 本提交（四处版本位点回到 0.3.7，见 R2）。论文仓零涉及，无重建需求；治理仓其余文件（含外部 WIP）不受影响。

## 9. 开放项

- **O1（v2 关闭）**：四处 rules_version 位点同步已并入本笔（§3 第 3–6 项），原暂缓理由经复审实测不成立（WIP 仅为版本行）。
- **O2**：工具侧 git 安全硬闸（`check` 子命令增加论文仓 `.git` 存在性与嵌套仓检测）——触发条件：`git -C instruction.git status` 中 tools/paper.py 的 WIP 清零（其归属提交完成后）。
- **O3**：论文侧 rules_version 铺开维持暂缓（沿 `e95881f` 登记），本笔不要求各篇升版。
- **O4**：误建根仓（工作区根目录 `.git`，3 笔提交）的移除——其内容已被各篇正式提交完全取代（复审实测：P4 `540d1c4` 与 `4ce500b` 的 paper.yaml 逐字节相同；P7 `ad22544` 与 `6e84af8` 相同；P8 `52a2648` 与 `bdbfaa3` 仅差 paper_version v0.1.13→v0.1.14，即外部 R18 作业的升版），留证于 `.review_scratch/incident-20261117-gitloss-backup/root-accidental-repo.tar.gz`；PF-G2"workspace root is not a repository by design"的前提以该仓移除方可成立。处置：按新规（PF-G4/F7）提请主会话并获用户授权后移除，移除前留证完毕。
- **O5**：`templates/paper/AGENTS.md` 指针腐烂——仍书"F1–F9"、治理文件清单缺 git-safety.md 且早已缺 polish.md、PF-W/PF-B/PF-RV 计数过期（沿 GC-2026-1111-03 加入 polish.md 时未登记指针的先例）。本笔不扩范围，登记待随下一次治理变更或单独派单同步。

---

*GC-2026-1117-06。规则依据：AGENTS.md F9/F7/F5/F6；PF-V1/PF-V3/PF-V5/PF-V6。类型：规则新增（F10 + PF-G1–G6）；rules_version 0.3.8→0.4.0（MINOR，新增规则正文，四处位点同步）；git 基线 d766ab9（HEAD 0.3.7）+ 工作区未提交外部 WIP 版本行 0.3.8；精确变更 7 个文件（2 新建 + 5 修改，含 4 处版本行），零删除、零规则正文改写；外部 WIP 其余文件不裹入。v2 按独立复审 M1–M4 与 P3 修订；v3 按 delta 遗留 N1–N4 与 PF-G6 豁免残留终审修订。*
