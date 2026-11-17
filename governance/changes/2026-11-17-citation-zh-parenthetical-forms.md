# 治理变更记录 GC-2026-1117-04：中文括号式文内引注形态补登记（citation.in_text_forms zh_paren_* 三键）

- 日期：2026-11-17
- 编号：GC-2026-1117-04
- 类型：治理能力修订（`stie.yaml` citation `in_text_forms` 新增 `zh_paren_single` / `zh_paren_double` / `zh_paren_multi` 三可选键 + schema 同步 + verify_layout baseline 剥离补三行 + rules_version PATCH 升版 0.3.7→0.3.8）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、F6（最小改动）；著录基线 PF-W11/PF-W12；核验入口 PF-RV7/PF-RV8；版本规则 PF-V1/PF-V3/PF-V5/PF-V6
- 规则版本：**0.3.7 → 0.3.8（PATCH）**

---

## 1. 基线（Baseline）

- **git 基线（写盘时刻）**：治理仓 HEAD 为 `master` 当前状态（工作区已修改 5 个文件 + 1 个新记录，尚未提交）。**基线说明**：今日已有 GC-2026-1117-03 在同一日完成，本编号 04 为同日顺延。
- **rules_version 前后**：0.3.7 → **0.3.8（PATCH）**。同步五处（四文件）：`project.yaml` L3、`governance/rule-index.yaml` L2、`tools/paper.py` L383（scaffold 缺省）+ L587（scaffold 调用点，一对必须同改——GC-2026-1113-03 先例）、`templates/paper/paper.yaml` L17。PATCH 判据 = 既有条款 `in_text_forms` 扩充可选子键、无新增规则号、rule-index 无条目增删；先例：GC-2026-1114-02 同类操作从 0.3.2→0.3.3。
- **论文侧基线**：十篇 `paper.yaml` `rules_version` 现状（本次不改任何论文仓文件，见 PF-V5）。论文侧铺开由主会话另行派单。
- **升版理由（PATCH）**：与 GC-2026-1114-02 完全同型——"既有 `in_text_forms` 对象扩充可选子键 + schema 同步，无新增规则号"。

## 2. 现状取证（问题陈述与证据，2026-11-17 实测）

### 2.1 触发：审查断链——"中文引注偏离登记形式"

| # | 证据 | 位置 |
|---|---|---|
| E1 | `stie.yaml` `citation.in_text_forms` 现有 `zh_single` / `zh_double` / `zh_multi` 三键仅登记**叙述式**形态（`张三（2020）` / `张三和李四（2020）` / `张等（2020）`），值中无全角括号 | `templates/layout/profiles/stie.yaml` L151-153 |
| E2 | 审查因 E1 判定"中文引注偏离登记形式"，悬置待裁 | 读审记录（触发本变更） |
| E3 | 全库 10 篇论文实际一律使用中文**括号式**：`（张三，2020）`（全角括号 + 全角逗号）；多引以全角分号 `；` 并列 | 全库实测 |

### 2.2 provenance 查证：范文实证两种形态并存

| # | 证据 | 位置 |
|---|---|---|
| E4 | **P1 build-record L2481-2482** 明确记载："文内形态按范文实测**两种**：括号式 `（Gorelick et al.，2017）` / `（Dwork & Roth，2014）`（全角括号+全角逗号，多引以全角分号`；`并列）与叙述式 `Surname 等（2025）`（作者作主语，年份全角括号）；全文统一使用此两形态。" | `papers/P1-SETDEBATE-20251110/build-record.md` L2481-2483 |
| E5 | **P8 body/README.md L25**："中文文内引用使用全角括号，如'（陈军等，2022）'" | `papers/P8-CDC-DELTALAKE-20261113/body/README.md` L25 |
| E6 | 刊方 S14 条款句（`governance/review.md` L96-97 等）仅给出叙述式示例，**未禁止/未登记括号式**；括号式为**范文实测形态**（通过审稿范文 PDF 参考文献段旁侧实测），适用 **PF-W12**（范本实证优先于条文） | `governance/review.md` S14 条款句 |

### 2.3 与英文 PF-B14 裁决的边界

| # | 说明 | 位置 |
|---|---|---|
| E7 | **英文引注** 2026-11-13 已按 PF-B14 provenance 裁定："刊物明示的 S14 登记形式（半角 `(Smith, 2020)`）优先于范文个案（全角）"（P3 build-record R21）——**英文维持半角形态，范文全角回退** | P3 build-record R21 |
| E8 | **中文引注**本次补登记的是**括号式**为范文实测形态——与英文裁决逻辑相反。不冲突：中文 S14 仅示例叙述式（不排斥括号式），英文 S14 明示半角括号式形态（禁止全角）。两者 provenance 判断依据不同，裁决方向自然不同。 | 本文登记 vs P3 build-record R21 |

## 3. 精确变更清单（逐文件；6 modified + 1 新记录）

| # | 文件 | 变更 |
|---|---|---|
| 1 | `templates/layout/profiles/stie.yaml` | `citation.in_text_forms` 八键（含 L159 `joint_corporate_separator`）后新增三可选键（L160-162）：`zh_paren_single: "（张三，2020）"` / `zh_paren_double: "（张三和李四，2020）"` / `zh_paren_multi: "（张等，2020）"`，每个带 provenance 注释：`[JT]` 范文实证（引 P1 build-record L2481-2482），注"刊方 S14 条款句仅示例叙述式；括号式为范文实证形态，PF-W12；与英文括号式半角形态并存不冲突" |
| 2 | `schemas/layout-profile.schema.json` | `citation.properties.in_text_forms.properties` 增三个可选属性：`zh_paren_single` / `zh_paren_double` / `zh_paren_multi`（type: string, description 含 provenance），`additionalProperties: false` 不变，不入 required（L644 加逗号 + 三行新属性） |
| 3 | `tools/verify_layout.py` | section_b baseline 剥离清单补三行嵌套 pop：`...in_text_forms...properties.pop("zh_paren_single", None)  # GC-2026-1117-04` 等，紧跟 L97 `joint_corporate_separator` pop 之后（L98-100）。**机理口径（与 GC-2026-1114-02 §3-4 同型）**：该行不影响 B 组 PASS/FAIL——基线保真原则（baseline 语义等价上一代 schema，防新键 load-bearing 测试对本键静默退化）；B 组对 stie 的拒绝由顶层键 pop 承载 |
| 4 | `project.yaml` / `governance/rule-index.yaml` / `tools/paper.py`（L383 + L587）/ `templates/paper/paper.yaml` | rules_version 0.3.7 → **0.3.8**（五处、四文件） |
| 5 | `governance/changes/2026-11-17-citation-zh-parenthetical-forms.md` | 本记录（新建） |

**不改**：`draft.yaml` / `gbt7713-2-2022.yaml`（三可选键缺省合法）；`governance/review.md`（S14 条款句不改，真值源在 profile，PF-B11）；`governance/writing.md`（S13/S14 汇总句不改，PF-B11）；`tools/make_refdoc.py`（citation 零消费实测，先例 GC-2026-1114-02 同结论）；`tools/paper.py` 其余逻辑（L4420 `--version` 帮助文本为 paper_version 示例，豁免）；`templates/paper/references.bib`（本变更不涉文后条目模板）；`papers/` 下任何论文仓文件（PF-V5）。

**PF-B3 结构身份键合规**：`citation` 为 PF-B3 结构身份键，L2 仍不可覆写（PF-B13，构建失败）；本次为治理层 F9 流程对 `citation.in_text_forms` 增可选子键，属 profile 版本化动作，未赋予论文级覆写能力。

## 4. 理由（Rationale）

1. **解决审查断链**：E1 登记的三种叙述式形态 + E3 全库实际使用的括号式形态，补登记使 profile 真值源覆盖两种实测形态（PF-B11 单一真值源），审查不再悬置。
2. **provenance 确证**：E4（P1 build-record）是范文实证直接证据，E5（P8 README）是项目实践佐证——括号式为已验证形态，适用 PF-W12（范本实证优先）。
3. **与英文裁决不冲突**：E7 vs E8——英文 S14 明示半角括号形态（先例 PF-B14 裁定半角优先），中文 S14 仅示例叙述式（本次补登记括号式）。两事同因审查触发、异因 provenance 判断、平行处理。
4. **schema 同步义务**：`additionalProperties: false` 下 profile 加键必须同步 schema（PF-B3），否则 A 组校验失败。
5. **版本 PATCH**：与 GC-2026-1114-02 同为"既有规则正文/字段扩充 + schema/profile 新键，无新增规则号"。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 不登记，维持审查悬置 | 全库 10 篇已使用括号式，不登记则每轮审查重复断链；G-2026-1114-02 先例证明登记是唯一收敛路径 |
| 将中文括号式视为"范文偏差"强制回改叙述式 | 违反 PF-W12 范文实证优先；回改 10 篇正文触发 PF-B7 冻结与重建，成本收益不成比例 |
| 在 writing.md / review.md 写文字说明、不进 profile/schema | 无机器可校验真值源，评审仍靠记忆；违反 PF-B11 单一真值源原则 |
| 用单一 `zh_paren` 键 + 多值示例 | 单著者/双著者/多著者形态不同（逗号 vs 和 vs 等），单键无法区分，多值示例非结构化登记 |
| 强制中文用全角括号、英文用半角括号（不登记具体形态） | 仅解决形式层面，仍缺少 profile 键值与 schema 校验，同上文第三方案问题 |

## 6. 一个决策（主会话裁定，照登）

- **决策：补登记 + 升版 + 论文侧零改 + 后续铺开**：`zh_paren_single` / `zh_paren_double` / `zh_paren_multi` 三键以 `[JT] 范文实证` provenance 登记入 stie.yaml，schema 同步，rules_version PATCH 至 0.3.8；**不改任何论文仓文件**（PF-V5）；论文侧 `paper.yaml` `rules_version` 铺开列为开放项，由主会话另行派单（与 GC-2026-1117-03 §4.4 口径一致：论文侧正被并发修改，铺开须逐篇重建后升版本）。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 治理仓并发线在途改动被裹挟 | 提交前 `git status --short` + `git diff --cached --name-only`，只 add 本记录 §3 六文件；禁 `-A`/`-a` |
| R2 | 改 stie 漏改 schema（A 组即 FAIL） | §3-1/§3-2 同笔；A 组 13 targets 兜底 |
| R3 | §3-3 pop 行漏执行 → baseline 不再等价上一代 schema | 基线保真（见 §4-5），diff 核对是唯一捕获点——写盘后独立验证必查 |
| R4 | 行号漂移（并发提交触及目标文件） | Edit 文本匹配不依赖行号；失配即停手重测基线 |
| R5 | 与英文 PF-B14 裁决混淆 | provenance 注释与 §2.3 显式边界声明；审查记录逐项分列 |
| R6 | 版本残留 | 五处同步 + grep 全仓对账（验证 §9-d） |
| R7 | 论文侧铺开裹挟在途改动 | 论文侧铺开另行派单（PF-V5）；本变更治理提交不含论文仓内容 |

## 8. 恢复方式（Recovery）

**提交前回退（当前状态，文件未暂存）**：5 个已跟踪文件逐个 `git checkout HEAD -- <path>` 还原；本记录为 untracked，直接删除。禁 `--hard` 与任何历史改写（F7）。

**提交后整体恢复**：`git revert <commit>`（单笔纯治理提交）。部分回退逐文件 `git checkout HEAD^ -- <path>`：`templates/layout/profiles/stie.yaml`、`schemas/layout-profile.schema.json`、`tools/verify_layout.py`、`tools/paper.py`、`project.yaml`、`governance/rule-index.yaml`、`templates/paper/paper.yaml`；本记录 `git rm`（revert 连带移除）。

**论文侧**：本变更治理提交不含任何论文仓内容（PF-V5），**papers/ 侧在本变更内零改动、无回滚对象**；论文侧铺开（`rules_version` 0.3.7→0.3.8 + build-record 登记 + 按需重建判定）尚未执行，由主会话另行派单。铺开若已执行后需撤：按篇 `git revert <paper sync commit>`（仅撤该篇 paper.yaml 版本行与 build-record 登记节），不回退既有正文/PKG。计划、复核与整改记录留存 `temp/GC-2026-1117-04/`（gitignored）。

## 9. 验证方法与结果（2026-11-17 落盘后实测）

| # | 验证项 | 方法（全部只读，`python3 -I` + 绝对路径） | 实测结果 |
|---|---|---|---|
| a | jsonschema 校验 stie.yaml against schema | `python3 -I -c` 用 jsonschema.Draft7Validator 对 stie.yaml 执行 forward 校验 | stie.yaml 校验通过（`zh_paren_single`/`zh_paren_double`/`zh_paren_multi` 均在 schema 声明内，无 additionalProperties 错误） |
| b | `grep -rln "in_text_forms" tools/` | 确认工具侧零消费 | 零命中（与 GC-2026-1114-02 同款结论，复验通过） |
| c | 语法完整 | `python3 -I -m py_compile tools/paper.py tools/verify_layout.py` | 均通过 |
| d | rules_version 对账 | `grep -rn '"0\.3\.7"' tools/paper.py project.yaml governance/rule-index.yaml templates/paper/paper.yaml` | 旧版号 `0.3.7` 残留 = 0（L4420 和 L6581 为 paper_version 示例文本，豁免） |
| e | 提交域 | `git status --short` + `git diff --stat`（写盘后、未暂存） | **5 modified + 1 新记录 = 6 文件**；无 papers/ 条目 |

## 10. 复核（F9）

- **计划阶段复核**：本变更为轻量级读审补正（无计划文件），审查断链 provenance 已由 P1 build-record L2481-2482 确证。
- **写盘后独立验证（待主会话派单，最终门禁）**：由未参与写盘的子代理核验实际 diff（逐文件逐键含 §3-3 三 pop 行在位——该行不影响 B 组输出，diff 核对是唯一捕获点）、§9 检查结果复跑一致、提交域合规（六文件、零论文仓触碰）；复核后方可 commit/push，主会话不得自批。

## 11. 开放项

1. **论文侧铺开**：十篇 `paper.yaml` `rules_version` 0.3.7→0.3.8 版本同步 + build-record 登记（含执行时刻 git status 快照）+ 按需重建判定，由主会话另行派单（PF-V5 每篇独立提交）。注：论文仓正被并发修改，铺开须逐篇重建后升版本（与 GC-2026-1117-03 §4.4 口径一致）。
2. **多引括号式并列**：全库实际使用全角分号 `；` 并列多引（如`（张三，2020；李四，2021）`），`in_text_forms` 三键仅覆盖单引形态，多引并列符（全角分号 vs 全角逗号）未在 profile 登记——属已有 S14 条款未尽项，非本次新建。
3. **英文叙述式未登记**：`in_text_forms` 现有 `en_single`/`en_double`/`en_multi` 均为括号式，英文叙述式（`Smith et al. (2020)`）未登记——刊方 S14 示例亦为括号式，暂无范文实证支撑，暂不补。

---

*GC-2026-1117-04。规则依据：AGENTS.md F9/F6；版式依据 governance/build.md PF-B3/PF-B11/PF-B12/PF-B13；著录基线 governance/writing.md PF-W11/PF-W12、governance/review.md PF-RV7/PF-RV8；版本依据 governance/versions.md PF-V1/PF-V3/PF-V5/PF-V6；无独立计划文件（轻量级读审补正）；规则版本 0.3.7 → 0.3.8（PATCH）。*

---

## 开放项处置记录（2026-11-17 主会话补记）

论文侧 `rules_version` 0.3.7→0.3.8 铺开后治理仓 rules_version 为 **0.3.8**，论文侧十篇的铺开列为开放项。
主会话于 2026-11-17 实测十篇现状后，决定**暂不执行铺开**，理由与前置条件如下，据实登记：

1. **铺开不是改一个字段就能完成的**。`rules_version` 的语义应为"该稿当前状态所遵循的规则版本"。
   多数 paper.yaml 在 GC-2026-1117-03 之前已随构建更新过版本，若只把 paper.yaml 的
   `rules_version` 改成 0.3.8 而不重建，等于让它们虚假声称遵循 0.3.8——正是 F6"据实登记"
   要避免的情况。
2. **正确做法是逐篇重建后再升版本**，即每篇：重建投稿包 → 复核四道闸门 → 升 `rules_version`
   → 独立提交（PF-V5 每篇独立提交）。这是一次批量操作，须由用户授权后按篇派单执行。
3. 实测发现的既存问题（铺开前须先处置）：
   - P5-AUDIT-EVIDENCE-20251111：工作树有未提交改动，铺开前须先厘清归属；
   - P3-SPATIAL-20251110：`paper_version` 与最新构建不一致；
   - P6-PROVISION-ALIGNMENT-20251111：`paper_version` 与最新构建不一致；
   - P8-CDC-DELTALAKE-20261113：`paper_version` 与最新构建不一致。
   即这些篇存在"paper.yaml 版本落后于已构建版本"的既存失配，铺开前须先查明原因。

结论：本开放项由"未执行"改登记为"**已判定暂缓，前置条件为逐篇重建＋既存失配查明＋用户授权批量派单**"。
