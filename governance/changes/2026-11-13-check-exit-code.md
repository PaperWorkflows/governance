# 治理变更记录 GC-2026-1113-05：check 失败静默放行修复——`cmd_check`/`cmd_materials_check` 显式退出码（P1）

- 日期：2026-11-13
- 编号：**GC-2026-1113-05**（编号占用实测核对：01 他线 PDF 导出确定性 `37a6037`/`dc3e658`；02 插图矢量化 `3259220`/`cb783a1`/`75ae414`；03 rules_version 0.3.1 升版 `ea6c1c6`；04 materials 多格式识别 `5ce1288`；05 空位，本记录启用）
- 类型：工具缺陷修复（`tools/paper.py` 两个命令函数；**零规则正文修改**，rules_version 保持 **0.3.1**）
- 计划版本：无独立计划草案——主会话已实测定位缺陷（status=fail 而 exit=0），本记录为实施 + 自测 + 独立核验收口
- 规则依据：AGENTS.md **F9**（变更纪律）、**F5/F6**（最小改动、只显式 add）；**PF-B12**（落地校验——凡不可校验即不得静默放行，本缺陷的直接违反项）；**PF-B3**（无静默降级）；版本依据 `governance/versions.md` PF-V3/PF-V5（治理提交不含论文内容）
- 基线（2026-11-13 实施时实测）：治理仓 HEAD `5ce1288`（GC-2026-1113-04）；`git status --short` 仅他线 `authors/registry.yaml` 在途未提交——**本提交严禁 stage**；`tools/paper.py` 6 089 行
- 流程状态：主会话缺陷定位 → **实施 + 自测 + 独立核验（本记录收口）**

---

## 1. 缺陷定位（P1 定级依据）

`cmd_check`（修复前 L809）结尾 `return emit({...})` 不带退出码，`emit(payload, code=0)` 默认 0；`cmd_materials_check`（修复前 L1129）在重复判定 `status="fail"` 时同样 `emit(payload)` 无 code。派发链 `main()` L6085–6086 `code = cmds[args.command](args); raise SystemExit(code)` 忠实透传函数返回值——函数返回 0，进程即 exit 0。

**存量实测（HEAD `5ce1288`，`python3 -I`）**：

- `paper.py check --paper papers/P9-SIGNALING-ECRL-20261113` → `status=fail`（`body_chapters` 缺 6 个骨架成员 + `metadata` authors bio 缺 address）而 **exit=0**；P1–P8 pass/exit 0。
- `materials check` 九篇均 pass/exit 0（GC-2026-1113-04 后无重复），fail 分支无实测触发样本，但代码路径与 cmd_check 同构。

**定级 P1 的理由**：任何以退出码为判据的消费方——CI 流水线、`&&` 链式脚本、主会话派工后的门禁断言——都会把 `check` 的失败当通过。PF-B12 要求不可校验/校验失败必须显式失败；PF-B3 要求无静默降级。失败静默放行使 `check` 作为质量闸门的名义功能与实际行为背离，且无任何告警面。这不是可用性瑕疵，而是闸门失效。

## 2. 精确变更清单（函数级；`tools/paper.py`，净 +7/−2 行）

| # | 位置（修复后行号） | 变更前 | 变更后 |
|---|---|---|---|
| 1 | L809–812 `cmd_check()` 结尾 | `return emit({...})`（code 默认 0） | `return emit({..., "results": results}, 0 if overall == "pass" else 2)` + 两行 GC 编号注释。`overall == "pass"` → exit 0；`overall == "fail"` → exit 2。函数内已有的 error 早返回（`--paper` 缺失 exit 2、目录不存在 exit 2）不变 |
| 2 | L1129–1133 `cmd_materials_check()` 结尾 | `return emit(payload)`（code 默认 0） | `return emit(payload, 0 if status == "pass" else 2)` + 两行 GC 编号注释。`status == "pass"` → exit 0；`status == "fail"`（发现重复/title 近重）→ exit 2。上方 `MaterialsFormatError` 解析失败路径（`status=fail` + error，exit 2）不变 |

**不改**：输出 JSON 结构（`status`/`results`/`duplicate_identifiers` 等键保持原样，闸门方读取逻辑不受影响）；`emit` 函数本身（`code=0` 默认值及其余全部调用方）；其余命令退出码语义（review/writing/experiments/build/package 等不在本笔范围）；九篇论文仓任何文件（只读核查）；`tools/verify_layout.py`（其退出码本就正确）。

## 3. 理由

1. **P1 不留静默放行**：退出码是 `check` 与自动化消费方之间的唯一契约面。status=fail + exit=0 使契约断裂，且断裂方向恰好是最危险的方向（假通过）。
2. **exit 2 而非 exit 1**：与本工具既有错误路径对齐——`emit(..., 2)` 已用于 error 早返回、`materials add` 重复 identifier 报 duplicate 亦用 exit 1 之外的约定（实测 `materials add` 重复 → exit 1），而 `check` 族既有失败/错误语义统一为 2；选用 2 使"校验失败"与"用法/存在性错误"同码，消费方只需判 `!= 0`，无需区分失败类型。
3. **最小改动**：只动两个函数的结尾 return，不改 emit、不改派发链、不改任何其他命令——爆炸半径限于两个 check 命令的退出码一途。

## 4. 备选与否准

| 备选 | 否准理由 |
|---|---|
| A. 只在治理记录挂开放项（"已知 fail exit=0，消费方自行读 JSON"），本笔不修 | 否准：P1 级缺陷不留静默放行。要求每个消费方自行解析 JSON status 是把工具契约缺陷转嫁给使用方，且 `&&`/CI 场景根本无法逐层解析；PF-B12/PF-B3 均要求显式失败信号 |
| B. 改 `emit` 全局按 payload `status` 派生退出码（status=fail → 2） | 否准：爆炸半径覆盖全部命令的 status 语义——`status="ok"`/`"error"`/`"fail"` 在各命令中含义不一（如部分命令 `status="error"` 已显式传 2，重复 add 走 exit 1 的 duplicate 语义），全局派生会改变本笔范围外命令的退出码行为，违背最小改动与"不改其他命令退出码语义"的约束 |
| C. 用 exit 1 表示 fail | 否准：本文件既有失败/错误路径已统一 exit 2（`emit(..., 2)` 遍布各命令）；新引入第三套失败码会增加消费方判据分支，无收益 |

## 5. 风险与边界

| 风险/边界 | 现状与缓解 |
|---|---|
| 依赖 `check` exit=0 的外部链（脚本/CI/派工断言）将开始看到失败 | **这正是本笔目的**：P9 的失败本就是事实（骨架缺失 + metadata 缺陷），此前被 exit 0 掩盖。P1–P8 不受影响（实测 exit 0 不变） |
| P9 将开始以非零退出 | 如实暴露存量骨架缺陷；P9 论文文件**不得修改**（论文线在途，只记录不修），由论文线另行处理 |
| `materials check` fail 分支（发现重复）此前无实测样本 | 已用 /tmp 合成负例补齐验证（list 同 id、keyed 块内同 sha256，均 fail/exit 2，见 §7） |
| `cmd_review_debate` 内 L1957–2101 死代码（旧 CLI parser 副本，含 check 注册表） | 不可达、不影响行为；两个派发表（L2065/2071 死副本与 L6053/6059 活副本）都指向同一函数体，修复自动覆盖，不在本笔清理（GC-2026-1113-04 §2 已留档） |
| 他线在途 `authors/registry.yaml` 被误 stage | 提交只显式 add 3 个目标文件，禁 `git add -A`/`commit -a`；提交前 `git status --short` + `git diff --cached --name-only` 双重复核（§7 l） |

## 6. 恢复方法（Recovery）

- **revert 优先**：本变更为单笔提交，`git revert <commit>` 即恢复旧退出码行为（PF-B12 违反随复原，属预期回退成本）；**禁止** `--hard` 与历史改写（F7）。
- 论文侧无回滚动作：九篇零改动（只读核查）。
- /tmp 下的验证副本（`/tmp/gcexit/`）为一次性测试产物，随 `/tmp` 清理，不入库。

## 7. rules_version 不升版的理由

本笔为工具缺陷修复，**零规则正文修改**（`governance/` 下规则文件未动一字）。按 GC-2026-1112-06 先例（零规则正文修改不升版）与 GC-2026-1113-04 §8 同构结论，rules_version 保持 **0.3.1**。PF-B12/PF-B3 是本笔援引的既有规则，本笔是其执行面修复，不产生新的规则声明。

## 8. 验证矩阵（2026-11-13 实测，全部 `python3 -I`）

基线 HEAD `5ce1288`；修复后 HEAD 工作区。九篇路径 `/home/author_a/workspaces/PaperWorkflows/papers/<P*>`。

| # | 验证项 | 方法 | 结果 |
|---|---|---|---|
| a | 语法完整 | `python3 -I -m py_compile tools/paper.py` | 通过 |
| b | check 九篇退出码矩阵（修复后） | `paper.py check --paper` ×9 | P1–P8 **pass/exit 0**；**P9 fail/exit 2**（缺陷修复：修复前 P9 fail/exit 0，实测对照成立） |
| c | materials check 九篇（修复后） | `materials check --paper` ×9 | P1–P9 全 **pass/exit 0**（total 4/4/3/4/15/10/12/3/1，与 GC-2026-1113-04 §9c 一致） |
| d | 合成负例·list 同 id | `/tmp/gcexit/duplist/`（list 内 `id: X-1` 两条）跑 `materials check` | **status=fail，dups=1，exit=2** |
| e | 合成负例·keyed 块内同 sha256 | `/tmp/gcexit/dupkeyed2/`（`figures:` 块内两条无 id 条目、同 sha256）跑 `materials check` | **status=fail，dups=1，exit=2**。注：判重键为 identifier→id→title→sha256 首命中回退链（GC-04 设计），条目带 `id` 时 sha256 分支不可达，故负例条目按无 id 构造以命中 sha256 兜底键 |
| f | 合成对照·keyed 跨块同 sha256 | `/tmp/gcexit/dupkeyed_cross/`（figures/tables 各一条同 sha256） | pass/exit 0——跨块不合并语义保持，无误报 |
| g | 不误杀·P1 check | `check --paper P1` | pass/**exit 0**（防"把 pass 也改成非零"的反向错误） |
| h | 不误杀·materials list | `materials list --paper P2` | exit 0 |
| i | 不误杀·error 早返回 | `check --paper /nonexistent`；`check` 无 `--paper` | 均 exit 2（`status=error` JSON 不变），早返回路径未受影响 |
| j | 不误杀·解析失败路径 | `/tmp/gcexit/broken/`（语法错误 materials.yaml）跑 `materials check` | status=fail + error，exit 2（与 GC-04 行为一致） |
| k | 链面回归·build 前置断言 | 不真重建（避 soffice 并发）；`check --paper P1` 等价验证 metadata 闸 + grep 证实 build/package 无内部调用 `cmd_check`/`cmd_materials_check`（全仓 grep `cmd_check(`/`cmd_materials_check(`：仅函数定义 L719/L1060、两处派发表——活表 L6053/L6059 与 `cmd_review_debate` 内死副本 L2065/L2071、治理文档各 1 处） | P1 pass/exit 0；无内部调用方，build/package 链不受影响 |
| l | 链面回归·verify_layout | `python3 -I tools/verify_layout.py` 修复前后各跑一次 | 修复前后输出**完全一致**：TOTAL 27，PASS 26，FAIL 1。该 FAIL（H. citation count parity，P1=31/0）为 HEAD 存量状态（HEAD 干净快照 + 同一批 papers 对照实测复现同结果），非本笔引入；根因为论文侧在途：P1 `body/paper.md` mtime 18:55 晚于 `build/v0.4.10` 15:08，paper.md 无 `[N]` 引注而存量 docx 有 31 处——属论文线重建事项，不在本笔（不得修改 papers/、不得真重建）。verify_layout 仅 importlib 调用 `_assert_layout_landing`/`_inject_paper_title_header`，函数级不可达本笔改动 |
| m | 论文侧零改动 | 九篇只读核查（check/materials check 均为只读路径） | 零写入 |
| n | 提交域 | 提交前 `git status --short` + `git diff --cached --name-only` | 仅 3 个目标文件入暂存区；`authors/registry.yaml` 未 stage |

## 9. 独立核验注记

1. **P9 存量缺陷只记录不修**：P9 的 `check` fail（`body_chapters` 缺 01-introduction…06-conclusion 六个骨架成员；`metadata`：`authors.yaml#authors.'author_e'` bio 缺 address、venue S17）为论文线在途状态，本笔仅使其退出码诚实（fail → exit 2），未改 P9 任何文件。
2. **GC-2026-1113-04 §10 第 1 项括号注记升级**：同笔将该条从"（注：cmd_check fail 时退出码为 0 是 HEAD 既有行为，与本笔无关，不在本变更范围）"升级为显式开放项，标注 P1 定级、状态"已由 GC-2026-1113-05 修复闭合（2026-11-13）"并指向本记录。
3. **verify_layout 1 FAIL 为存量**：与派单预期（27 PASS/0 FAIL）不符处已如实记录（§8 l），附 HEAD 同环境对照证据，责任域划归论文线重建事项。

---

*GC-2026-1113-05。规则依据：AGENTS.md F9/F5/F6；PF-B12（落地校验）/PF-B3；版本依据 governance/versions.md PF-V3/PF-V5；基线 5ce1288；先例 GC-2026-1112-06（零规则正文修改不升版）；check 失败静默放行修复（净 +7/−2 行，tools/paper.py 两函数），rules_version 保持 0.3.1。*
