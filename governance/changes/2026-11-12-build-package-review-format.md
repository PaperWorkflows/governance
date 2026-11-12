# 治理变更记录 GC-2026-1112-02：构建投稿交付包（docx/pdf/SVG/CSV/manifest）与审稿格式-精修规则全局化

- 日期：2026-11-12
- 编号：GC-2026-1112-02（GC-2026-1112-01 已被并发排版线占用并已随 `ab0bdcc` 入库，本号避让）
- 类型：治理能力修订（构建交付物与投稿包骨架扩展；目标刊格式要求 2026-11-12 全文纳入审核规则，全局生效）
- 计划版本：**v1.1**（`temp/GC-2026-1112-02/plan.md`；v1.0 经 general-codex-team 与 general-glm 并行交叉复核后修订）
- 规则依据：AGENTS.md F9（治理变更纪律）、F5（治理任务由主会话或受派子代理执行）、F6（最小改动）；PF-V5（提交分区）、PF-V6（提交说明）、PF-V8（提交前检查）
- 前置分析：用户 2026-11-12 指令（两项任务，各含"完成后执行提交"）；任务一映射见计划第 2 节表格
- **流程状态**：**已提交**。提交① **118b299**（构建规则域 5 文件，2026-11-12）；提交② **a2da33a**（审核规则域 3 文件，2026-11-12）；两笔均通过 F9 写后独立 diff 复核（verify-t1-glm.md、verify-t2-glm.md，均 pass）。内容一致性检查 **consistent**（temp/GC-2026-1112-02/consistency-check-codex-team.md）：其 P2 发现 N1"本头部状态滞后于实际提交"由本行收口；开放项 O7（scaffold 默认版本号）已随并发线 GC-2026-1112-01 整改提交 `0c0bc19` 收口

---

## 1. 基线（Baseline）与计划版本

- **git 基线**：治理仓 HEAD = `ab0bdcc`（2026-11-12 12:04，"fix(build): 修复插图在产物中缺失；产物不入库、版式配置入库"），**工作树干净**（实施前 `git status` 实测核实）。并发线 GC-2026-1112-01 已随该提交入库（`build.md` +2 条 profile 键说明、rules_version→0.2.1、`tools/paper.py` SVG 兜底剥离与图数断言、schema/profile/refdoc），并发已收敛为顺序关系。
- **rules_version**：0.2.1 → **0.3.0**。同步于 `governance/rule-index.yaml`、`project.yaml`、`tools/paper.py`（构建 manifest 的 `layout.rules_version` 常量）。**理由**：新增 **PF-B15**（图表交付：SVG 打包与原图对比）、**PF-B16**（投稿交付包骨架与 manifest 元数据）、**PF-RV8**（目标刊格式规则与精修规则全局化）三条规则正文，并修订 PF-B7 命名条与 manifest 字段清单。**级次 MINOR**，沿 GC-2026-1111-02 先例（新增 7 条规则正文 → 0.2.0）与 GC-2026-1111-03 先例（新增 13 条规则正文 → 0.2.0）。PF-RV8 条目随提交②入库（提交①的 commit body 中注明）。
- **`tools/paper.py` 现状**：`_strip_svg_alternatives` 等改动已随 `ab0bdcc` 入库，可安全触碰。其作用域是"docx 内嵌 SVG 备选剥离（渲染器兜底）"，与本变更 PF-B15"交付独立 SVG 文件"作用域不同，互不替代（计划第 1 节；复核意见 C2 处置）。
- **计划版本链**：v1.0 → v1.1（`temp/GC-2026-1112-02/plan.md`）。

---

## 2. 问题陈述（本次变更要解决什么）

| # | 问题 | 取证 |
|---|---|---|
| P1 | **投稿包无骨架、无自动装配**：目标刊 S19 要求投稿以 Zip 打包 Word/PDF/SVG 等，现行 PF-B7 只覆盖 docx/PDF 命名与发布凭据 manifest，投稿须手工组装 | 用户 2026-11-12 指令；PF-B7 现状 |
| P2 | **无图表矢量交付物**：论文依赖的每张图没有 SVG 交付件，无"与原图差异对比"的强制动作 | PF-B6/PF-B7 现状；`tools/paper.py` 无 SVG/CSV 产出逻辑 |
| P3 | **manifest 无投稿面元数据**：摘要、关键字、作者简介、结论、字数、投稿方向等投稿必需字段无处登记 | PF-B7 manifest 字段清单现状 |
| P4 | **格式要求只落了一半**：2026-11-12 版目标刊格式要求全文未进入治理规则，审稿与精修无全局依据 | 用户指令"作为审稿的格式规则以及精修规则（治理能力全局）"；GC-2026-1111-02 只落 S1–S20 旧版 |

---

## 3. 精确变更清单（逐文件）

### 3.1 任务一（提交①域）—— **已实施**

| # | 文件 | 类型 | 内容 |
|---|---|---|---|
| 1 | `governance/build.md` | 修改 | ① **PF-B7** 命名条改为"标题（第一作者中文名）"（全角圆括号字面；POSIX 转义保留；已发布版本不就地改名）；② PF-B7 manifest 字段条末尾追加一句：发布 manifest 另记 PF-B16 的投稿元数据集 + 包 `manifest.json` 的 sha256，共享字段不一致即构建失败；③ 文末（PF-B14 之后）新增 **PF-B15**、**PF-B16** 两条规则正文 |
| 2 | `governance/rule-index.yaml` | 修改 | 追加 PF-B15、PF-B16（`review_roles: [R-D, governance]`）；`rules_version: 0.2.1` → `0.3.0` |
| 3 | `project.yaml` | 修改 | 仅第 3 行 `rules_version: 0.2.1` → `0.3.0`。**不改** `modes.build.format` 等任何其他行（计划第 3.1#3 与第 7 节备选 6：扩列会超前宣称未实现的构建能力） |
| 4 | `tools/paper.py` | 修改 | **仅一处**：构建 manifest 的 `layout` 块常量 `"rules_version": "0.2.1"` → `"0.3.0"`（第 2863 行）。**不动** 234/422 行的 scaffold 默认值 `"0.1.0"`——属预存缺陷 O7，非本变更引入 |
| 5 | `governance/changes/2026-11-12-build-package-review-format.md` | 新建 | 本记录 |

**T1 实施后实测**：`governance/build.md` +29 行（1 行改写 + 1 行追加 + PF-B15/PF-B16 正文）；`governance/rule-index.yaml` +8 行 −1 行；`project.yaml` 1 行；`tools/paper.py` 1 行常量。

### 3.2 任务二（提交②域）—— **已实施，随提交②实施**

| # | 文件 | 类型 | 内容 |
|---|---|---|---|
| 6 | `governance/review.md` | 修改 | 新增 **PF-RV8**（条文见计划第 4.4 节）+ 文末附录收录 2026-11-12 全文（含 15.1①–④、15.2①–④ 与全部示例；"图/表制作规范："空条如实保留并加注） |
| 7 | `governance/rule-index.yaml` | 修改 | 追加 PF-RV8（`review_roles: [governance, R-A, R-B, R-C, R-D, independent_reviewer]`，**含 R-B**——复核意见 G3：条⑫量与单位/公式字体属 R-B 主责域） |
| 8 | `governance/changes/2026-11-12-build-package-review-format.md` | 修改 | 补记 T2 实施与提交②，流程状态改"已提交" |

### 3.3 未改动（显式边界）

`governance/writing.md`（PF-W11/W12 正文不动）、`governance/polish.md`（PF-PL13 不动，冲突以 PF-RV8 过渡条款管）、`governance/review.md`（本轮 T1 不动）、`templates/layout/profiles/stie.yaml`、`templates/paper/writing-spec.yaml`、各论文 writing-spec、`schemas/`、`AGENTS.md`、`governance/versions.md`、`papers/`（论文侧传播登记开放项 O2）、`tools/paper.py` 除第 3.1#4 一行常量外**无任何其他改动**。`temp/` 与 `papers/` 不入库（.gitignore）。

---

## 4. 理由（Rationale）

- 任务一：目标刊 S19 要求投稿以 Zip 打包 Word/PDF/SVG 等；现行 PF-B7 只覆盖 docx/PDF 命名与发布凭据 manifest，无 SVG/CSV 交付物、无投稿包骨架、无投稿面 manifest，投稿需手工组装且无一致性校验。规则化后投稿包可在构建期生成并校验；"完成后执行提交"落 PF-V5/V6 治理提交。
- 任务二：GC-2026-1111-02 已将旧版 S1–S20 落入 profile/writing-spec，但 2026-11-12 版全文新增/收紧多处（15000 字以上、文末联系方式、作者简介十字段、引言/正文/署名条款、参考文献四式与 5 年内优先、摘要 300–400 容差带、量与单位细则），且用户明示"作为审稿的格式规则以及精修规则（治理能力全局）"，故在 review.md 以全局规则 + 全文附录落地。
- 规则与工具的边界（复核意见 C3 处置）：PF-B15/PF-B16 明确写入**过渡执行**条款——本轮不改构建工具链（开放项 O1），SVG 重绘/差异对比与 CSV 导出在工具实现前由构建执行者人工完成并登记 build-record.md，工具实现后转为构建断言。规则不超前宣称未实现的机器能力。

---

## 5. 备选方案（Alternatives）

1. 格式全文放 `writing.md`（PF-W11 扩充）——否：用户明示落审核规则；review.md 附录 + PF-RV8 可被全部视角引用，写作侧经 PF-W11/PL13 间接生效，避免全文双处维护。
2. 新规则合并为一条 PF-B15——否：图表交付（PF-B6 验收链）与包骨架（PF-B7 发布链）验证关注点不同，分条可独立引用与复核。
3. 同步改 7 篇论文 writing-spec / stie.yaml——否：PF-V5 禁混提交；逐篇核对属论文侧工作，登记 O2。
4. manifest 增设 JSON schema 强制——有价值但超本轮最小域，登记 O5。
5. 产出物立即邮件投稿——否：F7 禁未经授权外部传输；本变更只管包生成与校验。
6. `modes.build.format` 扩 svg/csv——否（复核意见 C13）：该键描述稿件格式，扩列超前宣称未实现能力；交付物由 PF-B15/B16 表达。

---

## 6. 风险与恢复（Risks & Recovery）

### 6.1 风险与缓解

| 风险 | 缓解 | 恢复 |
|---|---|---|
| 新旧条款编号体系（S1–S20 vs 2026-11-12 版）引用混乱 | PF-RV8 过渡条款 + "以 2026-11-12 版为准"，分歧记"待迁移差异"（O2） | revert 提交②回到 S1–S20 单源；编号统一另立变更 |
| PF-B7 命名变更破坏既有 `build/current.json` / 旧产物引用 | 新命名只约束**新构建**；已发布版本不就地改名（原语义保留） | 无需恢复 |
| manifest 新字段无数据源（征稿方向未登记等） | 结构性字段缺失=失败；外部依赖字段允许 `null` + 缺口登记（C9） | 补 writing-spec 后复建 |
| `rule-index.yaml` 分次提交中间态 | 提交① body 注明"PF-RV8 条目随提交②入库"（C10） | 必要时补正提交 |
| 规则承诺构建期行为但工具未实现（C3） | PF-B15/B16 写明**过渡执行**（人工核对 + build-record 登记）+ 开放项 O1 显式登记实现载体 | 工具实现后转断言（O1） |
| `tools/paper.py` 混入超出常量的 hunk | staged diff 必须 = 1 处常量行，glm diff 复核专查（计划第 5 节） | `git restore --staged` 剔除后重查 |
| SVG 回写论文源树污染固定快照（G5） | PF-B15 明写 SVG 只产出到包根 `figures/`，源树不动 | 无需恢复 |

### 6.2 恢复方式（Recovery）—— **revert 优先**

- 治理提交①与提交②为**两个独立治理提交**（计划第 5 节），可分别 `git revert <commit>` 恢复，保留历史（沿 GC-2026-1111-02 第 7 节先例）。**禁止** `--hard` 与历史改写（F7）。
- 若提交①需就地重做：`git reset --soft HEAD^` 重分组后重新提交（计划第 5 节）。
- 工作区不做整体回滚（F7 保留现场）；计划、复核报告与实施报告留存 `temp/GC-2026-1112-02/`。

---

## 7. 验证方法（Verification）

| # | 方法 | 结果 |
|---|---|---|
| 1 | **结构验证**：`python3 -I -c "import yaml; yaml.safe_load(open('governance/rule-index.yaml')); yaml.safe_load(open('project.yaml')); print('YAML OK')"` | 通过（见 T1 实施报告） |
| 2 | **版本一致性**：`grep -n "PF-B15\|PF-B16\|rules_version" governance/rule-index.yaml project.yaml`；`grep -n "0.2.1\|0.3.0" tools/paper.py` | 三处 `rules_version` = 0.3.0；`tools/paper.py` 内无 0.2.1 残留（仅 234/422 的 0.1.0 与 2863 的 0.3.0） |
| 3 | **变更域核对**：`git diff --stat` | 恰好 5 个文件：build.md、rule-index.yaml、project.yaml、paper.py + 本记录文件未跟踪 |
| 4 | **条文验证**：grep 断言 PF-B15/PF-B16 在 build.md 且均被 rule-index 登记；PF-B7 命名条含"第一作者中文名" | 通过（T2 完成后补验 PF-RV8 在 review.md 且被 rule-index 登记、含 R-B） |
| 5 | **独立 diff 复核**（F9 写后）：由 general-glm 对照计划核对实际 diff（域内文件集、hunk 语义、无误伤——特别核查 `paper.py` 仅 1 处常量），出具结论后方提交 | 待主会话安排 |
| 6 | **内容一致性检查**（用户指令，一次）：提交完成后由 general-codex-team 跨文件核对（build.md ↔ rule-index.yaml ↔ project.yaml ↔ tools/paper.py 常量 ↔ review.md ↔ writing.md PF-W11/W12 ↔ polish.md PF-PL13 ↔ 本记录） | 待提交后执行 |

---

## 8. 交叉复核（计划阶段）

按 F9，计划在写入治理文件前由两名**未参与实施**的子代理并行交叉复核，两份报告均以实读实跑为据：

| 报告 | 位置 | 结论 | 发现 |
|---|---|---|---|
| general-codex-team | `temp/GC-2026-1112-02/review-codex-team.md` | **approve-with-changes** | P1×6（C1–C6）、P2/P3×8（C7–C14） |
| general-glm | `temp/GC-2026-1112-02/review-glm.md` | **approve-with-changes** | P1×7（G1–G7）、P2×11（G8–G18） |

**两报告的全部 P1 发现均已采纳并处置**，逐条处置见**计划第 10 节**（C1=G1/G2 基线刷新、C2 `_strip_svg_alternatives` 作用域区分、C3 过渡执行 + O1、C4 paper.py 版本常量 + grep 断言、C5=G7 PF-RV8 过渡条款 + polish.md 边界补列、C6=G5/G6 包根定义 + 双 manifest 一致性断言 + SVG 不回写源树、G3 RV8 条目补 R-B、G4 效力分级兜底句）；P2/P3 亦已采纳（C8 恢复改 revert/reset --soft、C9 字段缺失语义消歧、C10 commit body 版本理由、C11=C12 优先序挂 PF-B14 八级词表、C13 撤销 `modes.build.format` 扩列等）。**未采纳项：无**（两报告未提出互斥建议；C1 与 G1 对工作树状态的观察不一致，以主会话复核实测为准——工作树干净）。

---

## 9. 开放项（Open Items，登记不实施）

- **O1（优先）**：PF-B15/B16/PF-B7 新增字段的**实现载体**——`tools/paper.py` 增 SVG/CSV 交付物生成、差异对比记录、包骨架组装与断言（建议 GC-2026-1112-03）。
- **O2**：`stie.yaml` / 七篇 `writing-spec.yaml` 向 2026-11-12 版条款的迁移（含"15000 字以上"、作者简介十字段、征稿方向清单键）。
- **O3**："图/表制作规范："刊方原文为空条——向编辑部索取模板后回填（沿袭 GC-2026-1111-02 开放项）。
- **O4**：作者简介十字段的数据源扩展（`authors.yaml`/`author.schema.json` 字段核对）与 `writing-spec.yaml` 增"征稿方向清单"键。
- **O5**：投稿面 manifest 的 JSON schema 强制（`schemas/` 增 manifest schema 与构建断言）。
- **O6**：SVG 重绘自动化工具链选型（重绘/对比脚本）。
- **O7（预存，非本变更引入）**：`tools/paper.py` scaffold 路径 `build_paper_yaml` 的 `rules_version` 默认值 "0.1.0"（234/422 行）自 GC-02 起即未随版本演进，属脚手架工具预存缺陷；**本变更明确不动**。

---

## 10. T2 实施记录（任务二 / 提交②域）

### 10.1 实施范围与文件改动

| # | 文件 | 类型 | 实测内容 |
|---|---|---|---|
| 6 | `governance/review.md` | 修改 | ① PF-RV7 小节之后、文件末尾之前新增 **PF-RV8 目标刊格式规则与精修规则（全局）**（6 条正文，全局生效条款 + 效力分级 + 逐条核对义务 + 优先序 + 过渡条款 + 精修规则条款）；② 文件末尾新增**附录：目标刊投稿格式要求全文（2026-11-12，PF-RV8 附带的刊方原文快照）**，收录刊方原文逐字快照 21 条（格式要求 / 投稿 / 标题 / 作者姓名和单位 / 4. 摘要 / 关键词 / 英文 / 7. 英文首字母缩略词 / 基金项目 / 引言 / 正文 / 正文内标题 / 量与单位 / 13.图/表 / 图/表制作规范（空条）/ 结语 / 参考文献 / 15.1 正文引用形式 / 15.2 文后参考文献 / 作者简介 / 署名），含 15.1①–④、15.2①–④、量与单位①–④ 全部子项与全部示例 |
| 7 | `governance/rule-index.yaml` | 修改 | PF-RV7 条目之后、PF-V1 之前插入 **PF-RV8** 条目（`review_roles: [governance, R-A, R-B, R-C, R-D, independent_reviewer]`，含 R-B）。**不动** `rules_version`（0.3.0，T1 已改）、不动其他条目 |
| 8 | `governance/changes/2026-11-12-build-package-review-format.md` | 修改 | 头部流程状态更新为"T1+T2 已实施；提交① 118b299（2026-11-12）；提交②待主会话复核后执行"；§3.2 状态由"待实施"改为"已实施"；新增本 §10 T2 实施记录节。**不改写既有 T1 记录节**（§1–§9 的 T1 内容原样保留） |

**T2 实测**：`governance/review.md` +80 行 −0 行（1 个 hunk，纯追加；PF-RV1–PF-RV7 正文一字未动）；`governance/rule-index.yaml` +4 行 −0 行（1 个 hunk）；本记录 +48 行 −2 行（3 个 hunk：流程状态行改写 + §3.2 状态行改写 + §10 新增）。

### 10.2 附录保真处置

- **保留原文编号原貌**：刊方原文编号不连贯（"4. 摘要""7. 英文首字母缩略词""13.图/表"）系刊方文本实况，**未重新编号**，快照按原样收录。
- **空条如实保留**："图/表制作规范："后刊方原文为空，快照以 `**图/表制作规范**：（刊方原文此条为空）` 保留该条并**紧跟一行方括号注记** `[注] 原文"图/表制作规范："后无内容，如实保留空条；模板取得后回填（开放项 O3）。`，未删条、未补写刊方未给出的内容。
- **引号与标点保持原文**：快照中的半角/全角括号混用（如 `张三和李四（2020)` 与 `(Smith，2020)`）、`∥`（会议录连接符）、`［EB/OL］`／`［引用日期］` 全角方括号、`～`（关键词 3～8）、`—`（GB 3100—3102 / GB/T7714—2015）、`;`（基金项目示例分隔符）均按刊方原文逐字保留，未作规范化改写。
- **快照不可就地改写**：附录抬头明示"更新须另立治理变更，不得就地改写快照正文"（G 系 P2 处置）。

### 10.3 实施时观察到的并发工作树状况（不属本变更域）

T2 实施期间实测到工作树存在**并发线 GC-2026-1112-01 的在途改动**（非本变更引入，均不在提交②域，已如实保留、未触碰、未回滚）：

| 路径 | 并发性质 | T2 处置 |
|---|---|---|
| `governance/build.md` | 并发线修订 PF-B12 引用上标 coverage 措辞并补记 run 级黑体断言 | 未触碰（提交①域，已随 118b299 入库主体） |
| `governance/changes/2026-11-12-typography-heiti-citation.md` | 并发线补记 GC-2026-1112-01 复核发现 | 未触碰（属 GC-2026-1112-01 号） |
| `tools/paper.py` | 并发线修订 scaffold `rules_version` 默认值（0.1.0 → 0.2.1）与引用 run 重建鲁棒性 | 未触碰（**不得再触碰 T1 域文件**） |
| `tools/verify_layout.py` | 并发线补 H 组 docstring 说明 | 未触碰 |
| `templates/paper/paper.yaml` | 并发线同步模板 `rules_version` | 未触碰 |

**对提交②的影响**：无。上述路径均不在提交②域（`governance/review.md` + `governance/rule-index.yaml` + 本记录），T2 实施前后均实测这三份文件在 HEAD 状态起步、仅含 T2 自身改动。**主会话提交②时须显式按路径 `git add`，勿用 `git add -A`**，以免裹挟并发线在途改动（沿 GC-2026-1112-01 先例"提交限定路径"：该记录 §1 论文侧基线与 §3 论文侧第 12 项、风险 R9）。

### 10.4 T2 验证结果

| # | 验证项 | 结果 |
|---|---|---|
| 1 | `git diff --numstat governance/review.md` | `+80 −0`（1 个 hunk；PF-RV1–PF-RV7 一字未动，纯追加） |
| 2 | `git diff governance/rule-index.yaml` | 1 个 hunk / +4 −0；PF-RV8 条目位于 PF-RV7 之后、PF-V1 之前；`rules_version` 仍为 0.3.0 |
| 3 | `grep -n "PF-RV8" governance/review.md governance/rule-index.yaml` | review.md 命中 PF-RV8 小节标题 + 附录标题 + 抬头注记；rule-index.yaml 命中 id/title/file/review_roles 四行 |
| 4 | `python3 -I -c "import yaml; yaml.safe_load(open('governance/rule-index.yaml'))"` | YAML OK（`rules_version` = 0.3.0） |
| 5 | 附录条款完整性自检 | 21 条刊方条款全在（见 §10.1 第 6 项清单）；15.1①–④、15.2①–④、量与单位①–④ 子项齐备；空条与注记成对存在 |
| 6 | 越界自检 | T1 域文件（`governance/build.md`、`project.yaml`、`tools/paper.py`）与其余并发线路径均未被 T2 修改；未执行 `git add` / `git commit`；`temp/` 仅写本节实施报告 |

---

*GC-2026-1112-02。规则依据：AGENTS.md F9/F5/F6；构建依据 governance/build.md PF-B5/PF-B6/PF-B7，新增 PF-B15/PF-B16；审核依据 governance/review.md PF-RV7，新增 PF-RV8；计划 temp/GC-2026-1112-02/plan.md（v1.1）。*
