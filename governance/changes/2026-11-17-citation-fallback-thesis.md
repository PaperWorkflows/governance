# 治理变更记录 GC-2026-1117-01：citation.fallback_entry_forms 新增 thesis 键（学位论文 [D] 形态）

- 日期：2026-11-17
- 编号：GC-2026-1117-01
- 类型：治理能力修订（`stie.yaml` `citation.fallback_entry_forms` 新增 thesis 键 + schema description 更新 + references.bib 头注释修订 + rules_version PATCH 升版 0.3.3→0.3.4）
- 计划：`temp/GC-2026-1117-01/plan.md`（**计划版本 v1.0.0**，补正后按 plan-review C1–C7 执行）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、F6（最小改动）；著录基线 PF-W6/PF-W11；核验入口 PF-RV7/PF-RV8；版本规则 PF-V1/PF-V3/PF-V5/PF-V6
- 规则版本：**0.3.3 → 0.3.4（PATCH）**

---

## 1. 基线（Baseline）

- **git 基线（写盘时刻）**：治理仓 HEAD `4188cbc`（docs(governance): GC-2026-1116-08 同步完成登记——8 仓工作流已同步且 CI 全部转绿）；工作树有上一代理留存的未提交变更（7 修改 + 1 新建）。
- **rules_version 前后**：0.3.3 → **0.3.4（PATCH）**。同步五处：`project.yaml` L3、`governance/rule-index.yaml` L2、`tools/paper.py` L377 + L581、`templates/paper/paper.yaml` L17。
- **论文侧基线（测量时刻）**：十篇 `paper.yaml` 均 **0.3.3**。论文侧铺开（0.3.3→0.3.4 逐篇同步）由主会话另行派单，**本变更治理提交只含治理仓 7 个已修改文件 + 1 个新变更记录，不含任何论文仓内容**（PF-V5）。
- **升版理由（PATCH）**：与 GC-2026-1114-01 同型——"既有规则正文扩充 + schema/profile 新键，无新增规则号"。

## 2. 现状取证（问题陈述与证据）

| # | 问题 | 证据（2026-11-17 实测） |
|---|---|---|
| E1 | P10 huangkui2014 条使用 `[D]` 类型标识但不在登记集合内 | PF-RV7 机械核对失败：登记集合 = 刊方四模板（[M]/[J]/[C]∥/[EB/OL]）+ fallback 四键（law/regulation/standard/standard_online），不含 [D] |
| E2 | 刊方投稿格式未禁 [D] | PF-RV8 附录 15.2 仅列四模板但不声明"仅允许"；S13 声明"著录格式应符合 GB/T7714—2015"，GB 体系下 [D] 为合法标识 |
| E3 | fallback_entry_forms 缺少 thesis 键 | stie.yaml L164–167 仅四键；schema L652 description 枚举"four keys" |
| E4 | schema description 失准（新增 thesis 后） | L652 逐字"the four venue-silent document types: keys law [Z] / regulation [Z] / standard [S] / standard_online [S/OL]"——新增 thesis 后"four"与枚举均过期 |
| E5 | references.bib 头注释 type code 示例不含 [D] | L4 列表 `[J]/[C]//[Z]/[S]/[EB/OL]/[S/OL]` 无 [D] |

## 3. 精确变更清单（逐文件；8 个文件 = 7 修改 + 1 新建）

| # | 文件 | 变更 |
|---|---|---|
| 1 | `templates/layout/profiles/stie.yaml` | citation `fallback_entry_forms` 块（L168，4 空格缩进）新增 `thesis` 键：`thesis: "{author}, {year}. {title}[D]. {place}: {school}."`，provenance 注释 `[GB] 学位论文`，尾部标记（GC-2026-1117-01） |
| 2 | `schemas/layout-profile.schema.json` | L652 description 更新：`four` → `five`，追加 `/ thesis [D]`，尾部追加 `GC-2026-1117-01 增 thesis [D].`；schema JSON 结构（`additionalProperties: {type: string}`）**不变** |
| 3 | `templates/paper/references.bib` | L4 type code 示例列表由 `[J]/[C]//[Z]/[S]/[EB/OL]/[S/OL]` 扩展为 `[J]/[C]//[Z]/[S]/[S/OL]/[D]/[EB/OL]`，补入 `[D]` |
| 4 | `project.yaml` L3 | `rules_version: 0.3.3` → `0.3.4` |
| 5 | `governance/rule-index.yaml` L2 | `rules_version: 0.3.3` → `0.3.4` |
| 6 | `tools/paper.py` L377 + L581 | L377 `rules_version: str = "0.3.3"` → `"0.3.4"`；L581 `rules_version="0.3.3"` → `"0.3.4"` |
| 7 | `templates/paper/paper.yaml` L17 | `rules_version: 0.3.3` → `0.3.4` |
| 8 | `governance/changes/2026-11-17-citation-fallback-thesis.md` | 本记录（新建） |

**不改**：`governance/writing.md`、`governance/review.md`、`tools/verify_layout.py`（L96 pop 整体 `fallback_entry_forms`，thesis 随父对象被拒，B 组 PASS 且细目不变）、`tools/make_refdoc.py`、`draft.yaml`、`gbt7713-2-2022.yaml`、`papers/` 下任何论文仓文件（PF-V5）。

**执行偏差登记**：上一代理在执行本变更时，误将 `papers/` 下 P1–P9 共九篇 `paper.yaml` 的 `rules_version` 从 0.3.3 改为 0.3.4（越权修改论文仓）。变更记录初稿声称论文侧"零改动""尚未铺开"与事实不符，已被独立验证员裁定"不可提交"。执行回退后，九篇 `paper.yaml` 已恢复为 0.3.3（`git checkout -- paper.yaml`），回退后 `git status` 确认九篇工作树无未暂存变更。本次治理提交仅含上述 7 个修改文件 + 1 个新建变更记录。

## 4. 理由（Rationale）

1. **解决 [D] 不在登记集合**：P10 huangkui2014 为 `@mastersthesis`（硕士学位论文，经 CNKI CDMD-10673-1014338342 确认），使用 [D] 标识——GB/T 7714 学位论文合法类型标识。补入 thesis 键使 [D] 入登记集合。
2. **来源等级清晰**：刊方 S16 模板未涉及学位论文形态，构成"刊方未规定"场景，触发 [GB] 回落链（非 [SC] 自选）。
3. **schema 校验不影响**：`fallback_entry_forms` 为 `additionalProperties: {type: string}`，新增任意字符串键 forward 校验通过；description 更新仅文档级，不改结构。
4. **CI 无感**：A 组 forward 0 错（实测模拟）；B 组 backward thesis 随父对象被拒（一条 additional property 错误），错误计数与细目不变（实测模拟）。
5. **版本 PATCH**：与 GC-2026-1114-01 同为"既有规则正文扩充 + schema/profile 新键，无新增规则号"。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 删除 huangkui2014 引文 | huangkui2014 是 P10 §5.1 实质引文（云南省早期"一张图"核心数据库研究），删引文断证据链，违反 PF-W1 真实性 |
| 在 body/paper.md 中将 [D] 改挂 [M] | `@mastersthesis` 非正式出版图书，改 [M] 属事实错误，违反 PF-W1 |
| 维持 [D] 登记为开放项 | PF-RV4 规定 P1 问题"必须修复并复验"，不得仅记录并放行 |
| 在 P10 `build/layout.yaml` 中覆盖 citation 规则 | `citation` 为 PF-B3 结构身份键，L2 不可覆写（PF-B13），出现即构建失败 |

**拟取方案**：在 stie.yaml `fallback_entry_forms` 新增 `thesis` 键。

## 6. 两个口径决策（主会话裁定，照登）

- **决策 A（schema description 更新）**：采纳审查报告 C2 选项①——将 schema description 更新（改 four→five、补 thesis/[D]）纳入变更清单。理由：与 GC-2026-1114-01 先例一致（该先例将四键名写入 description），描述与实际键集合同步可避免后续维护混淆。
- **决策 B（P10 重渲染判定）**：是否补"昆明"（出版地）由 P10 侧重渲染派单按新模板裁定，本计划不预裁。原计划 §9.2 的"因 [S] 是可选尾缀"论据不成立（已修正），是否补入交由执行派单。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 治理仓并发线在途改动被裹挟 | 提交前 `git status --short` + `git diff --cached --name-only`，只 add 本记录 §3 八个文件；禁 `-A`/`-a` |
| R2 | thesis 缩进错误导致 YAML 解析失败 | 实测 4 空格与既有四键对齐（C1 补正后），stie.yaml 解析验证兜底 |
| R3 | 漏改 rules_version 声明位 | 五处同步 + grep 全仓对账（实测 §9-d） |
| R4 | 论文侧同步裹挟在途改动 | 论文侧铺开另行派单（PF-V5），本变更治理提交不含论文仓内容 |
| R5 | B 组错误计数变化导致 CI 误报 | 实测 thesis 随 `fallback_entry_forms` 整体被 baseline 拒绝，错误数 3→3、细目不变 |

## 8. 恢复方式（Recovery）

**治理仓**：本变更为单笔纯治理提交（§3 八个文件），整体恢复用 `git revert <commit>`；若需部分回退，按下表逐文件取 `HEAD^`：

| # | 文件 | 恢复命令路径 |
|---|---|---|
| 1 | `project.yaml`（L3） | `git checkout HEAD^ -- project.yaml` |
| 2 | `governance/rule-index.yaml`（L2） | `git checkout HEAD^ -- governance/rule-index.yaml` |
| 3 | `tools/paper.py`（L377 + L581） | `git checkout HEAD^ -- tools/paper.py` |
| 4 | `templates/paper/paper.yaml`（L17） | `git checkout HEAD^ -- templates/paper/paper.yaml` |
| 5 | `templates/layout/profiles/stie.yaml`（citation 块 fallback_entry_forms thesis 键） | `git checkout HEAD^ -- templates/layout/profiles/stie.yaml` |
| 6 | `schemas/layout-profile.schema.json`（L652 description） | `git checkout HEAD^ -- schemas/layout-profile.schema.json` |
| 7 | `templates/paper/references.bib`（L4 头注释） | `git checkout HEAD^ -- templates/paper/references.bib` |
| 8 | `governance/changes/2026-11-17-citation-fallback-thesis.md`（本记录） | `git rm governance/changes/2026-11-17-citation-fallback-thesis.md`（revert 时连带移除） |

- **提交前回退（当前状态，文件未暂存）**：已跟踪 7 个文件逐个 `git checkout HEAD -- <path>` 还原；本记录为 untracked，直接删除即恢复。**论文侧 9 篇已回退（见§执行偏差登记），P10 不受影响。**
- 禁止 `--hard` 与任何历史改写（AGENTS.md F7 保留现场）。

**论文侧**：本变更治理提交不含任何论文仓内容（PF-V5）。实际执行期间 P1–P9 的 `paper.yaml` 曾误改（0.3.3→0.3.4），已于提交前全部回退（`git checkout -- paper.yaml`），回退后九篇工作树干净。**papers/ 侧在本次治理提交中最终零改动**。论文侧铺开（十篇 rules_version 0.3.3→0.3.4 逐篇同步）尚未执行，由主会话另行派单。铺开若已执行后需撤：按篇 `git revert <paper sync commit>`（仅撤回该篇 paper.yaml 与 build-record 登记节），不回退已提交的既有正文/PKG。

- 工作区不做整体回滚（F7）；计划、复核与整改记录留存 `temp/GC-2026-1117-01/`。

## 9. 验证方法与结果（2026-11-17 落盘后实测）

**改动前基线（同命令）**：`TOTAL 27 PASS 27 FAIL 0`、A 组 `14 targets, 0 failed`、B 组 `stie.yaml: 3 errors; gbt7713-2-2022.yaml: 1 errors`、C 组三 profile `in_sync=True self_check=True`（exit 0）。

| # | 验证项 | 方法（全部只读） | 实测结果 |
|---|---|---|---|
| a | verify_layout 全量 | `python3 -I tools/verify_layout.py --paper-root <papers>` | **TOTAL 27 PASS 27 FAIL 0（exit 0）**；A 组 `14 targets, 0 failed`；B 组 `PASS`，细目 `stie.yaml: 3 errors; gbt7713-2-2022.yaml: 1 errors`（与基线一致，thesis 不引入新错误）；C 组 `draft/gbt7713-2-2022/stie: in_sync=True self_check=True` |
| b | B 组机理只读模拟 | `python3 -I -c`（baseline deepcopy + 顶层键 pop + 双 citation pop）对 stie 校验 | errors=3（与变更前一致），细目不变——thesis 随 `fallback_entry_forms` 整体被拒 |
| c | 语法完整 | `python3 -I -m py_compile tools/paper.py tools/verify_layout.py` | 均通过 |
| d | 解析与版本对账 | `python3 -I -c` 解析五个 YAML/JSON | stie.yaml OK（fallback 五键 law/regulation/standard/standard_online/thesis）；schema OK（citation.additionalProperties=False、fallback present=True）；project.yaml / rule-index.yaml / templates/paper/paper.yaml OK（rules_version=0.3.4）；`grep -n '"0.3.3"' tools/paper.py` 与 `rules_version: 0.3.3` 残留 = 0 |
| e | 提交域 | `git status --short` + `git diff --stat`（写盘后、未暂存） | **7 modified + 1 新记录 = 8 文件**，与 §3 清单逐一对应，无其他文件 |

## 10. 复核（F9）

- **计划阶段复核**：独立审查裁定"需补正后执行"，补正项 C1–C7 全部落实（详见计划 `temp/GC-2026-1117-01/plan.md` 修订标记）。
- **写盘后独立验证**：本记录由计划起草人同时执行写盘；需待未参与计划制定、未经手写入的子代理复核实际 diff（逐文件逐键）与 §9 检查结果复跑一致、提交域合规（八文件、零论文仓触碰）；复核后方可 commit/push，主会话不得自批。

## 11. 开放项

1. **论文侧铺开**：十篇 `paper.yaml` 0.3.3→0.3.4 版本同步 + build-record 登记（含执行时刻 git status 快照）+ 按需重建判定，按 plan §8 由主会话另行派单（PF-V5 每篇独立提交）。注：P1–P9 曾在执行期间被误改，已回退；本次提交不包含任何论文仓文件。
2. **machine-checkable 条目模板消费器未落地**：tools/ 尚无 .bib 条目/渲染表对模板的自动校验；本轮以 PF-RV7 人工核对 + 登记集合兜底，校验器单独立项。
3. **GB/T 7714 版次定稿**：维持 stie 既有 `standard_edition: GB/T 7714-2015` + note（刊方文本引 2015；现行 2025 版次随篇挂 unresolved 待编辑部确认）。
4. **P6 [R/OL] 未登记类型**：P6 `SPINOSA 2025` 使用 [R/OL]（报告类），不纳入本变更范围，可在后续治理变更中处理（与 GC-2026-1114-02 开放项 1 一致）。
5. **references.bib 存量双斜杠笔误**：现列表 `[C]//[Z]` 疑为 `[C]∥` 劣化笔误，且刊方四模板之首 [M] 未列入——本变更不修，建议后续变更统一修正。
6. **P10 重渲染缺"昆明"问题**：huangkui2014 预渲染文本缺出版地"昆明"，由 P10 侧重渲染派单按新模板裁定是否补入，本计划不预裁。

---

*GC-2026-1117-01。规则依据：AGENTS.md F9/F6；版式依据 governance/build.md PF-B3/PF-B11/PF-B12/PF-B13；著录基线 governance/writing.md PF-W6/PF-W11、governance/review.md PF-RV7/PF-RV8；版本依据 governance/versions.md PF-V1/PF-V3/PF-V5/PF-V6；计划 temp/GC-2026-1117-01/plan.md（v1.0.0，补正后执行）；规则版本 0.3.3 → 0.3.4（PATCH）。*
