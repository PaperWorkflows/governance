# 治理变更记录 GC-2026-1114-01：法律法规 / 规章与规范性文件 / 标准三类文献文后条目回落模板落账（citation.fallback_entry_forms）

- 日期：2026-11-14
- 编号：GC-2026-1114-01
- 类型：治理能力修订（venue profile 新增 citation.fallback_entry_forms 键 + schema 同步 + PF-W6/PF-W11/PF-RV7 规则正文扩充 + rules_version PATCH 升版 + 论文侧 paper.yaml 版本同步待铺开）
- 计划：`temp/GC-2026-1114-01/plan.md`（**计划版本 v0.3.0**；v0.2.0 为 round 1 整改版、v0.1.0 为初稿）；本记录按 plan v0.3.0 §3 精确变更清单由原计划起草人写盘（2026-11-14）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、F5（论文侧工作由受派子代理执行）、F6（最小改动）；版式 PF-B3/PF-B11/PF-B12/PF-B13；著录基线 PF-W11/PF-W12；核验入口 PF-RV7/PF-RV8；版本规则 PF-V1/PF-V3/PF-V5/PF-V6
- 规则版本：**0.3.1 → 0.3.2（PATCH，主会话裁定）**

---

## 1. 基线（Baseline）

- **git 基线（写盘时刻）**：治理仓 HEAD `405307c`（docs(governance): GC-2026-1113-05 §8e 判重链措辞订正；其 parent 为 `04d8671`；工作树除本变更 11 文件外干净）。**基线更正说明（写盘后独立验证 P3）**：计划阶段测量基线为 `04d8671`，其后并发治理线提交 `405307c`（2026-11-14 01:09，GC-2026-1113-05 记录措辞订正）仅改 `governance/changes/2026-11-13-check-exit-code.md` 一行（+1/−1，`git show 405307c --stat` 实测），与本变更 11 文件零交集，diff 内容不受影响。
- **rules_version 前后**：0.3.1 → **0.3.2（PATCH）**。同步五处：`project.yaml` L3、`governance/rule-index.yaml` L2、`tools/paper.py` L290（scaffold 缺省）+ L478（scaffold 调用点，一对必须同改——GC-2026-1113-03 §3 先例）、`templates/paper/paper.yaml` L17。
- **论文侧基线（测量时刻 2026-11-14 夜）**：九篇 `layout_profile` 均 stie、`rules_version` 均 **0.3.0**；在途改动为移动靶（该时刻脏篇 P1/P2/P4/P7/P9），**执行时须逐篇实测**。论文侧铺开（0.3.0→0.3.2 逐篇同步 + build-record 登记 + 按需重建判定）按 plan §3.2 由主会话另行派单，**本变更治理提交不含任何论文仓内容**（PF-V5）。
- **升版理由（PATCH）**：仓内惯例 = 新增规则号 → MINOR；既有规则正文扩充 → PATCH。正确先例两条：① GC-2026-1112-01 记录自述"PF-B11/PF-B12 规则正文扩充 + schema/profile 新键；无新增规则号"→ 0.2.0→0.2.1；② `ea6c1c6`（GC-2026-1113-03）PF-B12 一条规则正文扩充 → 0.3.0→0.3.1。`ab0bdcc` 不可引为"纯修复→PATCH"先例（`git show ab0bdcc` 实测其为混号提交，提交信息第三部分明载 GC-2026-1112-01 的 schema、profile、refdoc 与断言改动随该提交一并入库）。本变更三规则（PF-W6/PF-W11/PF-RV7）均内容扩充、无新增规则号，rule-index 无条目增删 → PATCH。论文侧 0.3.0→0.3.2 一步到位（0.3.1/0.3.2 均未传播论文侧）。

## 2. 现状取证（问题陈述与证据）

| # | 问题 | 证据（2026-11-14 实测） |
|---|---|---|
| E1 | 刊方对法律法规、政策文件、标准规范三类文献无文后条目模板 | PF-RV8 附录 15.2 仅四模板（专著[M]/期刊[J]/会议[C]∥/预印本[EB/OL]） |
| E2 | PF-W6 是指针不是规范 | writing.md 原句 "Citation style follows paper configuration. GB/T 7714-2025 registered as relevant current basis; precise clause mapping pending until implemented." |
| E3 | PF-W11 回落列表漏著录规则本体 | 原列表 (GB/T 7713.2-2022 附录 B, CY/T 170-2019, GB/T 3179-2009) 全为版式/出版标准 |
| E4 | 项目内无机器可校验条目模板 | stie.yaml citation 块（L138–L153）与 schema citation 块（L270–L313）均无 fallback_entry_forms |
| E5 | 三类文献写法靠评审临时归一 | P5 首轮 RC-02（RC.md L85/L86/L133：15 条类型标识全部缺失→补 19 条；fix-dispositions.md L59）；P3 v0.3.16 R18（build-record.md L2208 节、标准决策 L2220）标准号作著者、政府文件不带出版地出版者——均逐篇人工决策 |
| E6 | 存量 [EB/OL] 与刊方④模板有差异 | P5/P8 现产 [EB/OL] 条目缺（更新日期）与"网址："前缀（开放项 7，按决策 A 待迁移） |
| E7 | schema citation additionalProperties: false | 新键必须同步 schema，否则 stie 加键即校验失败（PF-B3） |

## 3. 精确变更清单（逐文件；净 +26/−8 行 + 新记录，`git diff --stat` 实测）

| # | 文件 | 变更 |
|---|---|---|
| 1 | `templates/layout/profiles/stie.yaml` | citation 块（in_text_forms 之后、references 之前，+8 行）新增 `fallback_entry_forms` **四键**：`law`（[Z] 法律法规）/`regulation`（[Z] 规章与规范性文件）/`standard`（[S] 标准号置首，允许可选尾缀"（引用日期 {access_date}）"）/`standard_online`（[S/OL]，author 二形态均可：标准号置首或发布机构）；每键带 provenance 注释（[GB]/[GB]+[JT]）；**在线法律/政策文本不设键**，以 citation 块内注释交叉引用刊方④[EB/OL] 模板（单一真值源） |
| 2 | `governance/writing.md` | PF-W6：指针句改写为三条可执行条款（著录按论文配置；刊方未规定类型以 profile `citation.fallback_entry_forms` 为绑定真值源，在线法律/政策④交叉引用不重复登记；每条文献类型标识按 GB/T 7714 取用）。PF-W11：回落列表补 **GB/T 7714（管辖著录）**，与前三项版式标准相区分；适用版次按 profile `citation.standard_edition` 登记 |
| 3 | `governance/review.md` | PF-RV7 机械核对清单增一项：文后条目文献类型标识在位且取自登记集合（刊方四模板 + profile `citation.fallback_entry_forms`），给实际值不得断言 |
| 4 | `schemas/layout-profile.schema.json` | citation.properties 增可选属性 `fallback_entry_forms`（object，additionalProperties: {type: string}，四键 description）；citation 整体 `additionalProperties: false` 不变；draft/gbt7713 缺省不声明仍合法 |
| 5 | `templates/paper/references.bib` | 头注释补两条：每条须含 GB/T 7714 文献类型标识（type code），取自刊方模板或 profile `citation.fallback_entry_forms` |
| 6 | `tools/verify_layout.py` | section_b（L96）baseline 剥离清单补一行 `…pop("fallback_entry_forms", None)  # GC-2026-1114-01`（紧邻既有 numeric_superscript pop 行）。**机制口径（round 2 更正，主会话终局裁决）**：该行**不影响 B 组 PASS/FAIL**——B 组对 stie 的拒绝由既有顶层键 pop（figures/tables/references/pagination/punctuation/author_bio_layout，根级 additionalProperties: false）承载，新 citation 子键的拒绝被顶层错误掩盖；保留该行理由是**基线保真**（baseline 语义上应等价"上一代 schema"，使"新键可证 load-bearing"测试对本键不静默退化）+ 与 GC-2026-1112-01 同型先例一致（该变更 item 7 亦同步更新 verify_layout）。其余逻辑（A/C/D/E/F/G/H）零改动 |
| 7 | `project.yaml` / `governance/rule-index.yaml` / `tools/paper.py`（L290+L478）/ `templates/paper/paper.yaml` | rules_version 0.3.1 → **0.3.2**（五处、四文件；paper.py 一对同改） |
| 8 | `governance/changes/2026-11-14-citation-fallback-entry-forms.md` | 本记录（新建） |

**不改**：draft.yaml / gbt7713-2-2022.yaml（fallback 键 schema 可选，缺省合法）；`tools/make_refdoc.py`（不消费任何 `citation.*` 键，grep 零命中实测——P2-2 安全性实证）；paper.py / verify_layout.py 其余逻辑；`authors/registry.yaml`（他线在途）；`templates/layout/refdoc/*`（本变更不涉 typography，C 组 in_sync 实证 refdoc 字节未动）；papers/ 下任何论文仓（PF-V5）。

**PF-B3 结构身份键合规**：`citation` 为 PF-B3 结构身份键，L2 仍不可覆写（PF-B13，构建失败）；本次为治理层 F9 流程对该键新增可选子键，属 profile 版本化动作，未赋予论文级覆写能力。

## 4. 理由（Rationale）

1. 解决"指针不是规范"（E2）：三类文献条目模板固化为 profile 声明（PF-B11 单一真值源），PF-W6 改为指向该键。
2. 补齐回落链（E3）：GB/T 7714 管辖著录，版次按 profile `citation.standard_edition` 登记（stie=GB/T 7714-2015，现行 2025 版次随篇挂 unresolved 待编辑部确认——决策 B，不强行切版）。
3. 避免评审轮临时归一（E5）：模板落 profile 后评审只核对"取自登记集合"。
4. schema 同步义务（E7）。
5. 版本 PATCH：见 §1 升版理由。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 新建独立 `governance/citation-format.md` | 违反 PF-B11 单一真值源，声明漂移双头 |
| 只在 writing.md 写文本模板不进 profile | 无真值源与 schema 校验，退化回 E4/E5 |
| 本轮实现 tools/ 条目校验器 | 超最小域（F6），PF-RV7 人工核对先行，单独立项 |
| 强制切版 GB/T 7714-2025 | 刊方文本引 2015，不自行主张（决策 B） |
| 存量条目全量回改 | 触发 PF-B7 冻结与全量重建，成本收益不成比例（决策 A） |

## 6. 两个口径决策（主会话裁定，照登）

- **决策 A（存量过渡）**：新审核/精修按新规；存量已构建版本不回改；差异记"待迁移差异"不判违规。**与 PF-RV6 衔接**："待迁移差异"仅适用于后续不再触及的存量条目——任何一轮修复/精修触及某条文献（增删引文、条目改动）时，该条须同轮按新规执行。先例与情境差异：PF-RV8 过渡条款为规则迁移期宽容，本变更即模板落账本身，收敛点是"条目被触及即迁移"。
- **决策 B（GB/T 7714 版次）**：维持 stie 既有 `standard_edition: GB/T 7714-2015` + note（刊方文本引 2015；现行 2025 §9.3 著者-出版年制形态与本刊 S16 一致），不强行切版；随各篇 paper.yaml unresolved 挂"待编辑部确认"（现状仅 P5 已挂，其余铺开时补记）。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 治理仓并发线在途改动被裹挟 | 提交前 `git status --short` + `git diff --cached --name-only`，只 add 本记录 §3 十一文件；禁 `-A`/`-a` |
| R2 | 改 stie 漏改 schema | §3-4 同笔；verify_layout A 组 13 targets 兜底（实测已过） |
| R3 | 规则改写措辞歧义（误读为顺序编码） | 条款句内注明著者-出版年制（S13）；写盘后文档复核逐句核对 |
| R4 | 论文侧同步裹挟在途改动 | 提交一律限定 `git add paper.yaml build-record.md`；执行时刻逐篇实测（快照为移动靶），build-record 登记节记录执行时刻 git status 快照 |
| R5 | 模板语义收缩 | 四键 + 在线④注释逐字照登 plan §3.1-1；diff 复核逐条比对 |
| R6 | 编辑部落差反馈 | 挂篇级 unresolved + 开放项；不预判口径 |
| R7 | 模板/脚手架版本同步遗漏（GC-2026-1112-01 §10-8 教训） | 五处同步 + grep 全仓对账（实测 §9-d） |
| R8 | 版本声明位不同步 | 四声明位同笔改 0.3.2（实测 §9-d） |
| R9 | §3-6 pop 行漏执行 → B 组仍 PASS、新键拒绝被掩盖，属**静默**风险 | 由写盘后独立验证的 diff 核对捕获（该行不影响 B 组 PASS/FAIL——round 2 独立复核人三重实测证伪 v0.2.0"恒 FAIL"主张，2026-11-14：真实基线实跑 + 只读模拟 + 代码走读） |

## 8. 恢复方式（Recovery）

**治理仓**：本变更为单笔纯治理提交（§3 十一文件，无并发混入预期），整体恢复用 `git revert <commit>`；若需部分回退，按下表逐文件取 `HEAD^`：

| 文件 | 恢复命令路径 |
|---|---|
| `project.yaml`（L3） | `git checkout HEAD^ -- project.yaml` |
| `governance/rule-index.yaml`（L2） | `git checkout HEAD^ -- governance/rule-index.yaml` |
| `tools/paper.py`（L290 + L478） | `git checkout HEAD^ -- tools/paper.py` |
| `tools/verify_layout.py`（section_b 一处 pop，L96） | `git checkout HEAD^ -- tools/verify_layout.py` |
| `templates/paper/paper.yaml`（L17） | `git checkout HEAD^ -- templates/paper/paper.yaml` |
| `templates/layout/profiles/stie.yaml`（citation 块 fallback_entry_forms） | `git checkout HEAD^ -- templates/layout/profiles/stie.yaml` |
| `governance/writing.md`（PF-W6/PF-W11） | `git checkout HEAD^ -- governance/writing.md` |
| `governance/review.md`（PF-RV7） | `git checkout HEAD^ -- governance/review.md` |
| `schemas/layout-profile.schema.json`（citation 块） | `git checkout HEAD^ -- schemas/layout-profile.schema.json` |
| `templates/paper/references.bib` | `git checkout HEAD^ -- templates/paper/references.bib` |
| `governance/changes/2026-11-14-citation-fallback-entry-forms.md` | 本记录：`git rm` 后删除（revert 时连带移除） |

- **提交前回退（当前状态，文件未暂存）**：已跟踪的 10 个文件逐个 `git checkout HEAD -- <path>` 还原；本记录为 untracked，直接删除即恢复。
- 禁止 `--hard` 与任何历史改写（AGENTS.md F7 保留现场）。

**论文侧**：本变更治理提交不含任何论文仓内容（PF-V5），**papers/ 侧在本变更内零改动、无回滚对象**；论文侧铺开（rules_version 同步）尚未执行。铺开若已执行后需撤：按篇 `git revert <paper sync commit>`（仅撤回该篇 paper.yaml 与 build-record 登记节），不回退已提交的既有正文/PKG。

- 工作区不做整体回滚（F7）；计划、复核与整改记录留存 `temp/GC-2026-1114-01/`。

## 9. 验证方法与结果（2026-11-14 落盘后实测）

**改动前基线（同命令）**：`TOTAL 27 PASS 27 FAIL 0`、A 组 `13 targets, 0 failed`、B 组 `stie.yaml: 1 errors; gbt7713-2-2022.yaml: 1 errors`、C 组三 profile `in_sync=True self_check=True`（exit 0）。

| # | 验证项 | 方法（全部只读） | 实测结果 |
|---|---|---|---|
| a | verify_layout 全量 | `python3 -I tools/verify_layout.py --paper-root <papers>` | **TOTAL 27 PASS 27 FAIL 0（exit 0）**；A 组 `13 targets, 0 failed`；**B 组 `PASS`，细目 `stie.yaml: 2 errors; gbt7713-2-2022.yaml: 1 errors`**（较基线 1 errors 多一条 `'fallback_entry_forms' was unexpected`，与 plan v0.3.0 §9 V2 期望一致）；C 组 `draft/gbt7713-2-2022/stie: in_sync=True self_check=True`（make_refdoc 不消费 citation.* 键实证——refdoc 字节未动） |
| b | B 组机理只读模拟 | `python3 -I -c`（baseline deepcopy + 顶层键 pop + 双 citation pop）对 stie 校验 | errors=2：①顶层键集合 `('author_bio_layout','figures','pagination','punctuation','references','tables'…)` additionalProperties 错误、②`Additional properties are not allowed ('fallback_entry_forms' was unexpected)`——证明拒绝由顶层键 pop 承载、新子键错误独立成条（掩盖与计数机理双重实证） |
| c | 语法完整 | `python3 -I -m py_compile tools/paper.py tools/verify_layout.py` | 均通过 |
| d | 解析与版本对账 | `python3 -I -c` 解析五个 YAML/JSON | stie.yaml OK（fallback 四键 law/regulation/standard/standard_online）；schema OK（citation.additionalProperties=False、fallback present=True）；project.yaml / rule-index.yaml / templates/paper/paper.yaml OK（rules_version=0.3.2）；`grep -n '"0.3.1"' tools/paper.py` 与 `rules_version: 0.3.1` 残留 = 0 |
| e | 提交域 | `git status --short` + `git diff --stat`（写盘后、未暂存） | **10 modified + 1 新记录 = 11 文件**，净 +26/−8 行 + 新记录；与 §3 清单逐一对应，无其他文件 |

## 10. 复核（F9）

- **计划阶段复核（两轮，均未通过原起草人）**：round 1 独立复核 FAIL（P1×2、P2×6）→ v0.2.0 整改（四键统一、PF-B3 合规段、E6 更正、PF-RV6 衔接、CLI 实测化、计划版本行等）；round 2 独立复核 FAIL（P1×1：F2D-1——v0.2.0 对 §3.1-11 的"B 组恒 FAIL"机制主张被三重实测证伪；P3×2：ab0bdcc 引文方式、执行时刻快照要求）→ **主会话终局裁决（返工熔断）**：接受复核人全部证据，技术方案不变、文字更正为"基线保真"口径，plan 升 v0.3.0；不再有 round 3 计划复核，**写盘后独立验证为最终门禁**。
- **写盘后独立验证（待主会话派单，最终门禁）**：由未参与计划制定、未经手写入的子代理核验实际 diff（逐文件逐键，含 §3-6 pop 行在位——该行不影响 B 组输出，diff 核对是唯一捕获点）、§9 检查结果复跑一致、提交域合规（十一文件、零论文仓触碰）；复核后方可 commit/push，主会话不得自批。

## 11. 开放项

1. 机器可校验条目模板消费器未落地：tools/ 尚无 .bib 条目/渲染表对模板的自动校验；本轮以 PF-RV7 人工核对 + 登记集合兜底，校验器单独立项。
2. GB/T 7714 版次定稿：维持 2015，各篇 unresolved 挂"待编辑部确认"；答复后如需切 2025 另立变更（仅改 standard_edition + note）。
3. 其他 profile（draft/gbt7713，numeric 制式）暂不登记 fallback 键；未来投向著者-出版年制刊物按需补键。
4. 各篇 writing-spec.yaml 与 profile 双轨对齐：writing-spec 现仅登记 `citation_style` 字符串；模板真值源在 profile（PF-B11），是否引用 profile 键留后续治理收敛。
5. 文内标注形式待编辑部确认（P5 unresolved 已挂账），本变更不涉。
6. `project.yaml` `open_decisions.citation_style_implementation: null`：建议随本变更收口记录为 closed（主会话可选补录，未列入本次提交）。
7. **存量 [EB/OL] 条目差异**：P5/P8 现产 [EB/OL] 缺（更新日期）与"网址："前缀——按决策 A 记"待迁移差异"，被触及的同轮迁新；④模板口径确认并入开放项 2。
8. **论文侧铺开**：九篇 paper.yaml 0.3.0→0.3.2 + build-record 登记（含执行时刻 git status 快照）+ 按需重建判定，按 plan §3.2 由主会话另行派单（PF-V5 每篇独立提交）。

---

*GC-2026-1114-01。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B3/PF-B11/PF-B12/PF-B13；著录基线 governance/writing.md PF-W6/PF-W11、governance/review.md PF-RV7/PF-RV8；版本依据 governance/versions.md PF-V1/PF-V3/PF-V5/PF-V6；计划 temp/GC-2026-1114-01/plan.md（v0.3.0，两轮独立复核 + 主会话终局裁决）；规则版本 0.3.1 → 0.3.2（PATCH）。*
