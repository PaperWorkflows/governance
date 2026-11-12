# 治理变更记录 GC-2026-1112-01：全局排版三则（摘要标签左对齐 / 正文 [N] 引用上标 / 黑体标题不加粗）

- 日期：2026-11-12
- 编号：GC-2026-1112-01
- 类型：治理能力修订（版式 profile 新增 4 键 + refdoc 生成器落地 + 构建后处理 + 构建期断言）
- 规则依据：AGENTS.md F9（治理变更纪律）、F5（论文侧工作由受派子代理执行）、F6（最小改动）；版式语义扩充 PF-B11/PF-B12
- 用户指令（2026-11-12）：三项排版修正进入全局排版规范，构建 docx|pdf 时自动应用，无需逐篇手动设置：
  1. 摘要 / Abstract / 关键词 / Keywords 标签左对齐（不居中）；
  2. 正文 [N] 引用与正文同样式并设置为上标（现状：与正文同样式、无上标）；
  3. 使用黑体的部分（标题）不设置加粗。
- 前置分析与计划：`temp/GC-2026-1112-01/plan.md`；F9 计划独立复核：`temp/GC-2026-1112-01/plan-review-round1.md`（结论 PASS、无阻塞、10 NOTE，复核子代理未参与计划制定，以实读实跑为据；沙箱原型验证 LibreOffice 可开、31/31 上标）。

---

## 1. 基线（Baseline）与计划版本

- **rules_version**：0.2.0 → **0.2.1**。同步于 `project.yaml`、`governance/rule-index.yaml`、`tools/paper.py`（manifest 常量与脚手架缺省值）、`templates/paper/paper.yaml` 及 P1–P7 的 `paper.yaml`。理由：PF-B11/PF-B12 规则正文扩充 + schema/profile 新键；无新增规则号。
- **版本快照补记（收口时世界状态，2026-11-12）**：并发治理线 GC-2026-1112-02（提交 `118b299`）已把 `project.yaml`/`rule-index.yaml`/构建 manifest 常量推至 **0.3.0**。本变更整改批次将 `templates/paper/paper.yaml` 与脚手架缺省值**直接同步至 0.3.0**（与已提交规则世界一致，避免制造新偏差）；**P1–P7 `paper.yaml` 仍为 0.2.1**（各篇独立提交，属 GC-2026-1112-02 的论文侧铺开范围，见开放项 9）；P6/P7 重建产物 manifest 记 0.3.0、P1–P5 记 0.2.1（工具代际差，全部产物经现行断言与 verify_layout 验证通过）。
- **git 基线**：治理仓 `d908695`（工作树干净，2026-11-12 核实）。
- **实际提交形态（与原计划偏差，如实登记）**：本变更的治理侧文件**并非按计划以单一 PF-V5 提交落地**。同一工作区的一条**并发治理线**（插图缺失修复）于 2026-11-12 12:04 以混号提交 `ab0bdcc`（15 文件）落盘，其中**包含本变更全部 14 个治理文件**（连同其提交说明"三、四"两部分对本变更的两处实施期修正）与其自身的插图修复（提交说明"一、二"，另涉 `governance/changes/2026-11-11-layout-standards.md` +53 行）。PF-V5"单一变更单一提交"在该提交上不成立，恢复方式相应改写（见 §7）；实施阶段独立复核晚于该提交完成（F9 时序偏差，见 §9）。
- **论文侧基线**（2026-11-12 实测）：7 篇当前版本 manifest `review_status` 均为 **pending**（PF-B7 已发布保护不触发，可就地重建）；`build/` 产物已不入库（GC-02 开放项 23 已由提交 `d908695` 闭环），重建不弄脏论文工作树；**P1/P2/P3 工作树存在并发精修线的未提交正文改动**，论文侧提交必须限定 `git add paper.yaml build-record.md`。

## 2. 现状取证（问题陈述）

| # | 问题 | 取证（2026-11-12 实测） |
|---|---|---|
| P1 | 摘要/Abstract/关键词/Keywords 标签居中 | `make_refdoc.py` AbstractTitle `align: "center"`；7 篇正文均以 `::: {custom-style="AbstractTitle"}` 标注该 4 段标签（每篇 ×4），产物随之居中 |
| P2 | 正文 [N] 引用无上标 | pandoc 按字面文本排出；产物 `<w:t>` 无 `vertAlign`。docx 实测引用计数：P1=31（含参考文献导语叙述性 4 处与表段 `Dung [1]`）、P2=83、P3=13、P4=0、P5=0、P6=0、P7=0；**Bibliography 段内命中 0**（参考文献条目无 [N] 前缀） |
| P3 | 黑体标题被设置加粗（伪加粗） | `make_refdoc.py` AbstractTitle/Heading1–5(+Char)/Caption×3 共 9 个样式块 `bold: True`；Title/Subtitle（题名黑体）无 b 元素（本就不粗），不在变更内 |
| P4 | 误伤形态（上标规则必须排除） | P4 数学区间 `[12, 40]`（逗号后带空格）×4；P4 `$\sigma \in [0, 1]$`（公式 → OMML `<m:t>`，非 `<w:t>`）；P6/P7 参考文献 GB/T 7714 引用日期 `[2026-11-11]`（4 位数字，均在 Bibliography 段内） |

## 3. 精确变更清单（逐文件，治理仓）

| # | 文件 | 类型 | 内容 |
|---|---|---|---|
| 1 | `schemas/layout-profile.schema.json` | 修改 | typography 增 `heading_bold`/`caption_bold`（bool）、`abstract_label_alignment`（enum left/center/right）；citation 增 `numeric_superscript`（bool）。全部可选：缺省 = 生成器保持 GC-2026-1112-01 之前的行为（粗体开、标签居中），旧 profile 兼容 |
| 2 | `templates/layout/profiles/draft.yaml` | 修改 | L0 全局基线补 4 键（`heading_bold: false`、`caption_bold: false`、`abstract_label_alignment: left`、`citation.numeric_superscript: true`），来源标注 `[TD]+用户指示`（PF-B14：用户指示不得表述为本刊要求） |
| 3 | `templates/layout/profiles/stie.yaml` | 修改 | typography 3 键显式化（`heading_bold`/`caption_bold`/`abstract_label_alignment`，与 L0 同值，deep_merge 同值不产生覆写日志）；`citation.numeric_superscript` 经 L0 继承、本档不重复声明（功能无损——文档复核 P3-2 勘误：原清单误写"同 4 键"） |
| 4 | `tools/layoutlib.py` | 修改 | `merged_role()` 暴露 `heading_bold`/`caption_bold`/`abstract_label_alignment`（缺省 None = 未声明） |
| 5 | `tools/make_refdoc.py` | 修改 | AbstractTitle：align 取 `abstract_label_alignment`（缺省 center）、bold 取 `heading_bold`（缺省 True）；Heading1–5 与 Heading{N}Char：bold 取 `heading_bold`；Caption/ImageCaption/TableCaption：bold 取 `caption_bold`；`self_check` 增 `heading1_bold`/`abstract_title_bold`/`abstract_title_alignment`/`table_caption_bold` 4 项并纳入 pass 判定 |
| 6 | `tools/paper.py` | 修改 | ① 新增 `_apply_citation_superscript`（含 `_CITATION_PATTERN`/`_superscript_run_parts`）：跳过 pStyle∈{Bibliography, SourceCode} 段与 `<m:oMath>/<m:oMathPara>` span；模式 `\[\d{1,3}(?:-\d{1,3})*(?:,\d{1,3}(?:-\d{1,3})*)*\]`（1–3 位数字、逗号后无空格）；run 拆分，引用片段复制原 rPr 并按 ECMA-376 顺序插入 `<w:vertAlign w:val="superscript"/>`；已有 vertAlign 的 run 不重复处理；含 drawing/fldChar 等的 run 不动；**非单一 `<w:t>` 形态的 run 原样跳过**（实施复核 P2-2 处置：防重建截断 run 内首个 `</w:t>` 之后的内容）。② `_cmd_build_docx_impl` 在 `_harden_tables` 后调用（受 `citation.numeric_superscript` 驱动），计数入 notes（`citation_superscript_marked`）。③ `_assert_layout_landing` 增断言：`*_bold_off`（Heading1–5/AbstractTitle/Caption×3 显式 `w:b val=0`）、**`heiti_run_direct_bold_absent`（run 级直接加粗检查，实施复核 P1-1 处置——`**关键词：**` 类 markdown 会让 pandoc 注入 `<w:b />` 绕过样式级断言，P6/P7 实测命中）**、`abstract_title_alignment`、`citation_superscript_coverage`（非排除段内全部引用 run 须带上标；计数 0 记 note 不 fail）。④ manifest `rules_version` → 0.2.1；脚手架缺省 rules_version 同步 0.2.1（文档复核 P1-2 处置） |
| 7 | `tools/verify_layout.py` | 修改 | B 组 baseline 剥离清单补 4 新键；D 组负例 +3（`heading_bold_restored`/`abstract_title_centered`/`citation_superscript_removed`）；新增 H 组正例（P4 区间 `[12, 40]` 不得上标；7 篇 docx 引用计数 == markdown 源计数（双侧剔除 Bibliography））。产物端匹配一律空白容错（pandoc 重序列化为 `w:val="0" />` 形态）。**计划外修正（并发线作出、随 `ab0bdcc` 落盘，登记于提交说明"四"）**：H 组 `docs` 键原取 `d.parent.parent.name`（得到 "build"，七篇折叠为一键且 `paper_root/key` 解析到不存在的 `papers/build`），已改 `d.parents[2].name` 并附注释 |
| 8 | refdoc ×3 | 再生成 | 确定性重生成；**diff 已逐样式块复核**：仅 `word/styles.xml` 变化，仅 AbstractTitle/Heading1–5(+Heading1–5Char)/Caption×3 共 **14 个物理样式块**（9 段落样式 + 5 联动字符样式）的 `w:b(/bCs)` 翻转与 AbstractTitle `w:jc` 翻转；Title/Subtitle/Author/Normal/Abstract/Bibliography/BlockText/AuthorBio 不变（代码复核以 `ab0bdcc^` 旧档反向实证：缺键缺省=旧行为，再生成字节一致） |
| 9 | `governance/build.md` | 修改 | PF-B11 增一条（角色粗体与摘要标签对齐为 profile 键 + 黑体不加粗理由）；PF-B12 增一条（引用上标 + coverage 断言） |
| 10 | `governance/rule-index.yaml`、`project.yaml` | 修改 | rules_version → 0.2.1 |
| 11 | `governance/changes/2026-11-12-typography-heiti-citation.md` | 新建 | 本记录 |

### 论文侧（受派子代理执行；每篇独立提交，PF-V5）

| # | 范围 | 变更 |
|---|---|---|
| 12 | P1–P7 `paper.yaml` | `rules_version` → 0.2.1；**提交限定 `git add paper.yaml build-record.md`**（P1/P2/P3 工作树有并发未提交改动，不得裹挟） |
| 13 | P1–P7 | `build docx` + `build pdf`（pending 草稿就地重建）；`build-record.md` 各追加一节 |
| 14 | P6/P7 `body/paper.md`（实施复核 P1-1 处置） | 摘要区标签去除 markdown `**` 加粗记号（`**关键词：**`→`关键词：`、`**Keywords:**`→`Keywords:`；P7 同处含尾随空格一并保留原样），**文字逐字不变**；随后重建并提交（`git add body/paper.md build-record.md`）。pandoc 会为 `**…**` 注入 run 级 `<w:b />` 直接格式化，使黑体标签实际仍渲染伪加粗、且绕过样式级断言——配套断言 `heiti_run_direct_bold_absent` 已加（见 §3 第 6 项修订） |
| 15 | P1 manifest 凭据修复（文档复核 P2-3 处置） | 治理侧 12:15 确定性抽验曾以 docx-only 重建覆写 P1 `build/v0.4.0/manifest.json`（双工件凭据缺失、产物字节无损）。处置**触发停止条件，已原样还原**：论文侧代理按指令重跑 `build pdf` 后 docx/pdf 字节均变（工具链已从 0.2.1 代漂移至 0.3.0 代——新增断言与 GC-2026-1112-02 规则改变了 docx 包内容；PDF 侧 soffice 本无时间戳定点化），"字节确定性重建"前提失效。已恢复 P1 为干预前状态（docx/pdf 与账本一致、manifest 为 12:15 docx-only 代，凭据缺口登记为开放项 8），两代产物留档 `temp/GC-2026-1112-01/p1-*`。PDF 时间戳定点化或全量 0.3.0 代重建，见开放项 8 |

## 4. 理由（Rationale）

- 三项均为**版式层**修正，走既有架构：profile（声明）→ refdoc/构建后处理（实现）→ 构建期断言（PF-B12 落地校验）。论文正文零改动，构建即生效。
- 上标策略放**构建后处理**而非 pandoc Lua filter：paper.py 已有同构后处理先例（`_harden_tables` 等）；断言层需在 docx 上核对，Lua filter 无法复用该校验；样式条件（跳过 Bibliography 段）在 XML 后处理中表达更直接。
- 黑体不加粗以 **profile 键**而非生成器硬编码：PF-B11"profile 是唯一真值源"；缺省值=旧行为，未来某档若改宋体标题+加粗只需改 profile。
- 引用模式按实测误伤源反推（1–3 位数字、逗号后无空格、跳过 OMML/Bibliography/SourceCode）：GB/T 7714 顺序编码制多引用 `[1,3]` 惯例无空格；区间惯例带空格；引用日期为 4 位数字。

## 5. 备选方案（Alternatives）

| # | 方案 | 结论 |
|---|---|---|
| 1 | pandoc Lua filter 转换前改 AST | ⚠️ 拒：样式条件表达受限、新增工具链文件、断言仍须在 docx 层重做 |
| 2 | 直接硬编码改 make_refdoc（不加 profile 键） | ❌ 拒：违反 PF-B11"声明即真值源"，断言无期望值可比 |
| 3 | 正文侧手工标注（`^[1]^` / custom-style） | ❌ 拒：逐篇手改、新建正文要人记得标注——违背"无需手动设置" |
| 4 | 模式放宽（含空格逗号/4 位数字） | ❌ 拒：实测误伤 P4 区间与 P6/P7 引用日期 |

## 6. 风险（Risks）与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 区间/日期/公式误上标 | 模式限定 1–3 位 + 无空格逗号；OMML 不触碰；H 组正例断言 P4 区间不上标（沙箱合成用例实测：`[12, 40]`/`[2026-11-11]`/`[0, 1]` 全部保持正文，仅 `[3,5]`/`[7]` 上标） |
| R2 | 参考文献条目误上标 | 跳过 pStyle=Bibliography；实测 7 篇 Bibliography 段内命中 0 |
| R3 | 断言过严杀伤 P5/P6/P7（0 引用） | coverage 计数 0 → 记 note（`no_numeric_citations_in_body`）不 fail |
| R4 | refdoc 不同步致构建失败 | 变更内确定性再生成 ×3 + 构建期 `_assert_refdoc_in_sync` 兜底；diff 已逐块复核 |
| R5 | 字节确定性破坏 | 沙箱实测连建 2 次 sha256 一致（`fe5b534ca8b7…`） |
| R6 | 引用被 pandoc 拆进相邻 run → 漏上标 | **按复核实情改写（原表述过强）**：coverage 只约束单 run 完整引用，跨 run 拆分会静默通过构建；由 verify_layout H 组计数对账在验证期兜底（P4 实测存在该形态，见开放项 4）；处理器对非单一 `<w:t>` 形态原样跳过、绝不截断 |
| R7 | PF-B7 已发布版本保护触发 | 7 篇均 pending（已核实）；若重建报 PF-B7 错误即停并按 PF-V3 升版 |
| R8 | pandoc 重序列化形态差异 | 产物端全部正则空白容错（沙箱首建曾因 `<w:b w:val="0" />` 全 null 失败，已修并复跑通过） |
| R9 | 论文侧提交裹挟并发改动 | 提交限定 `git add paper.yaml build-record.md`（复核 NOTE 采纳） |

## 7. 恢复方式（Recovery）

- **治理仓（按实际混号形态改写，原"单一提交可整体 revert"表述作废）**：`git revert ab0bdcc` 会**连带回滚并发线的插图修复**（投稿件硬伤修复），不可整体 revert。只回滚本变更的正确方式：`git checkout ab0bdcc^ -- <本变更 14 文件逐一路径>`（schema/profiles/refdoc×3/layoutlib/make_refdoc/paper.py/verify_layout/build.md/rule-index/project.yaml/本记录），随后 `python3 -I tools/make_refdoc.py` 再生成 refdoc（若 tools 曾被新键依赖污染则按文件还原即可）、重建论文侧。反向同理：只撤销插图修复不涉本变更。
- 论文侧：7 篇各自独立提交（P6/P7 另有标签源修正提交），按篇 `git revert <paper 提交>` 后重建即恢复旧排版。
- 工作区不做整体回滚（F7 保留现场）；沙箱、探针与复核报告留存 `temp/GC-2026-1112-01/`。

## 8. 验证方法（Verification）与结果

**沙箱（P1 输入副本，不触碰真实论文仓）实测**：

| # | 方法 | 结果 |
|---|---|---|
| 1 | `make_refdoc.py` 再生成 ×3 | status ok，3 档 self_check 全 True（新 4 项期望值逐项命中） |
| 2 | refdoc diff 逐样式块比对 | 仅 styles.xml、仅 9 个目标样式块、仅 bold/jc 翻转 |
| 3 | 沙箱 `build docx` | status ok、`layout_assertions: pass`；`*_bold_off`=9×"0"、`abstract_title_alignment`=left、`citation_superscript_marked`=31、`citation_superscript_coverage`=31（P1 源计数 31 一致） |
| 4 | 合成排除用例（区间/日期/公式 torture 段注入产物后跑处理器） | 仅 `[3,5]`、`[7]` 上标；`[12, 40]`、`[2026-11-11]`、`[0, 1]` 保持正文，run 原样未加 rPr |
| 5 | 沙箱 `build pdf` | status ok、`pdf_fonts_missing: []`、manifest rules_version 0.2.1；PDF 文本中引用上下文可见 |
| 6 | 确定性 | 连建 2 次 sha256 一致 |
| 7 | 全量复跑 | 见 §8.1（论文侧重建后执行） |
| 8 | 独立复核 | 计划阶段已完成（PASS）；实施阶段复核见 §9 |

### 8.1 全量复跑（论文侧 P1–P7 重建后实测回填）

| # | 方法 | 结果 |
|---|---|---|
| 1 | `python3 -I tools/verify_layout.py`（26 项，含 B 组新键反向、D 组 3 新负例、H 组 2 正例） | **TOTAL 26 PASS 26 FAIL 0**（主会话与文档复核代理各自独立复跑一致；新负例逐个恰好命中目标断言：`heading1_bold_off`/`abstract_title_alignment`/`citation_superscript_coverage`） |
| 2 | 7 篇 `build docx` + `build pdf` | 7/7 ok、`layout_assertions: pass`、`override_log_entries: 16`、manifest `rules_version: 0.2.1` |
| 3 | 引用上标落位 | **127 处**（P1 31/31、P2 83/83、P3 13/13；P4–P7 coverage=0 如实记 note）；H 组计数对账 docx==markdown 源全等 |
| 4 | 黑体不加粗落位 | `*_bold_off` 9 项 × 7 篇 = 63 项全 "0"；`abstract_title_alignment` 7/7 left |
| 5 | 误伤防护 | P4 区间 `[12, 40]` 3 处 run 无上标（H 组正例）；`[2026-11-11]`、OMML 内 `[0, 1]` 不受影响 |
| 6 | 视觉验收（PF-B6，visual-judge） | **6/6 PASS**：P1-p01/p02、P2-p01/p02（标签顶格左对齐、引用上标、标题无伪加粗）、P4-p11/p12（区间平排、OMML 正常） |
| 7 | 回归 | `paper.py check` 7/7 pass |
| 8 | 确定性 | P1 产物重建前后 sha256 一致（`fe5b534ca8b7262e…`）；沙箱连建 2 次一致 |
| 9 | PDF | 7 篇 pdf ok；P1/P2/P3 `pdf_fonts_missing: []`；P4–P7 缺失清单为 profile 声明但无用字的代码/公式字体（manifest limitation 如实登记） |

**实施复核整改后复测**：`heiti_run_direct_bold_absent` 探针实测 P1 通过、P6/P7 现产物命中 `AbstractTitle`（即 §3 第 14 项修复的对象）；multi-`<w:t>` run 保护探针确认 run 原样保留。P6/P7 源修正与重建由论文侧代理执行后，7 篇在含新断言的管线下复跑通过。

## 9. 实施阶段独立复核（两名未参与者，报告留存 temp/GC-2026-1112-01/）

**时序偏差（如实登记）**：混号提交 `ab0bdcc`（12:04）先于实施复核完成——F9"提交前复核"在该提交上不成立，复核实际为提交后追认 + 整改（文档复核 P2-4 指出，照登）。

### 9.1 代码复核（codex-team，报告 impl-review-code.md）——**PASS-with-notes**

- **P1-1（已处置）**：`*_bold_off`/`abstract_title_alignment` 只查 styles.xml 样式定义，run 级直接格式化可绕过——实测 P6/P7 标签 markdown `**关键词：**`/`**Keywords:**` 使 pandoc 注入 `<w:b />`，标签实际仍渲染伪加粗而构建 pass。处置：§3 第 6 项增 `heiti_run_direct_bold_absent` 断言（探针实测 P1 过、P6/P7 命中）+ §3 第 14 项论文侧源修正。
- **P2-1（已处置）**：拆 run 引用构建期盲区——coverage 只见单 run 完整引用，跨 run 拆分静默通过（P4 产物实存 pandoc 拆分形态）。处置：paper.py docstring、PF-B12 条款、本记录 R6 的表述改为如实版本；run 合并列入 §10 开放项。
- **P2-2（已处置）**：`_superscript_run_parts` 重建会丢弃 run 内首个 `</w:t>` 之后内容（多 `<w:t>`/`<w:br/>`）。处置：处理器加"非单一 `<w:t>` 形态原样跳过"保护 + 探针验证。
- **P2-3/P2-4（已处置）**：记录 §3-3"同 4 键"勘误（stie 实为 3 键，numeric_superscript 经 L0 继承）；§1 混号事实与 §7 恢复方式改写。
- **P3（备忘）**：vertAlign 插入锚缺 `eastAsianLayout`/`specVanish`（pandoc 不触发）；run 开标签属性含 `>` 时截断（同前）；H 组区间按 run 计数不揭示被拆的第 4 处——随开放项 2/6 一并观察。
- **实跑复核核心结果**：verify_layout 26/26；向后兼容字节级实证（新代码 + `ab0bdcc^` 旧档再生成 refdoc 与父提交入库件 sha256 一致 3/3）；refdoc 二进制 diff 与记录相符；P2 83/83 引用 run 结构合法。

### 9.2 文档复核（gpt-plus，报告 impl-review-docs.md）——**FAIL（2 P1）→ 整改后复验**

- **P1-1（已处置）**：混号提交事实未登记、§7 revert 表述与 git 事实相反 → §1/§7 已按事实改写（本节时序偏差亦照登）。
- **P1-2（已处置）**：`templates/paper/paper.yaml` `rules_version: null` 与 paper.py 脚手架缺省 `0.1.0` 未同步 → 均 0.2.1。
- **P2-1**（已处置）：verify_layout `parents[2]` 计划外修正 → §3 第 7 项登记。**P2-2**（本节即收口）：§8.1/§9 回填。**P2-3**（处置中）：P1 manifest docx-only 覆写 → §3 第 15 项，论文侧代理以 `build pdf` 恢复双工件 manifest 并补记账本。**P2-4**：F9 时序偏差 → 本节开头照登。
- **P3**：PF-B14 无"用户指示"等级（现标注诚实，开放项 7 收录）；§3-3 键数勘误（已改）；verify_layout docstring 缺 H 组（已补）。
- **核验通过项**：§3 清单 ↔ 提交 14 文件无遗漏；数字三处一致且独立复跑 26/26；PF-B11/B12 条款与实现逐点吻合；论文侧 7 仓提交范围/身份/顺序全部合规，P1 的 16 个并发脏文件未被裹挟。

### 9.3 复核后状态

两项复核的全部 P0=0；P1×3（代码 P1-1、文档 P1-1/P1-2）均已处置并复测；代码复核整体结论 PASS-with-notes。整改批次（模板/脚手架 rules_version、run 级断言、multi-t 保护、记录改写）构成提交后的**整改小提交**（治理文件仅限本变更相关路径）。论文侧 P6/P7 标签去粗已完成并实测：`heiti_run_direct_bold_absent`=0、`layout_assertions: pass`、文字逐字未变，提交 P6 `c2cf3f8` / P7 `6dd943e`（各仅 2 文件，工作树干净）。P1 manifest 恢复触发停止条件、现场已还原（§3 第 15 项、开放项 10）。

## 10. 开放项

1. P5/P6/P7 正文无 [N] 引用（著者-出版年制，与 stie profile S13 一致）：上标规则对它们是**未触发**而非未生效；coverage 断言记 0 计数 note。
2. P1 约 11 处叙述性引用（"参考文献 [1]–[8]"、"Hu 等[7]"）与表段 `Dung [1]` 按用户全局指令一并上标——与 GB/T 7714"叙及文献序号可不入角标"的通行做法存在**已登记偏离**；如需细分（仅句末引用上标）须另行立项并修订 profile 键语义。
3. P2/P1 顺序编码制正文与 stie profile `citation.style: gb-7714-author-date` 的**体例冲突**（GC-02 开放项 22 延续）：本变更只解决"形式"（上标），不改"体例"；投稿前须一次文字级大改，须单独授权。
4. **引用跨 run 合并未实现**（代码复核 P2-1 改口）：coverage 只约束单 run 完整引用；跨 run 拆分由 verify_layout H 组计数对账在验证期兜底（P4 已实测存在 pandoc 拆分形态）。实现 run 合并（或构建前 AST 归一）须另立项。
5. `citation.numeric_superscript` 键当前仅 L0/L1 声明；L2 不可覆写（citation 为结构身份键，PF-B3）——论文级关闭上标须走 profile 版本化。
6. **处理器健壮性备忘**（代码复核 P3）：vertAlign 插入锚未含 `eastAsianLayout`/`specVanish`；run 开标签属性含 `>` 时 `run_open` 截断；两者 pandoc 现行输出均不触发，出现即由断言/H 组兜底。
7. **PF-B14 来源等级词表无"用户指令"档**：本变更以 `[TD]+用户指示` 诚实标注（未冒充本刊要求）；结构化 provenance 收敛（GC-02 开放项 16）时应增补 `user_directive` 级。
8. 模板/脚手架 `rules_version` 已同步（文档复核 P1-2；同步目标按收口时规则世界取 0.3.0）；后续 rules_version bump 须把 `templates/paper/paper.yaml` 与 `build_paper_yaml` 缺省值列入同步清单。
9. **跨线版本偏差待收敛**：P1–P7 `paper.yaml` 仍 0.2.1，而规则世界（project.yaml/rule-index/构建 manifest 常量）已 0.3.0（GC-2026-1112-02，提交 `118b299`）；P6/P7 产物 manifest 记 0.3.0、P1–P5 记 0.2.1。向 0.3.0 的论文侧铺开（paper.yaml 同步 + 全量重建）属 GC-2026-1112-02 范围，须其线统一执行。
10. **P1 manifest 凭据缺口**：`build/v0.4.0/manifest.json` 为 docx-only 代（账本记的是更早的完整双工件 release，产物字节与账本一致）。根源是 PDF 转换无时间戳定点化 + 工具代际漂移使"确定性重建"不能跨代成立。收敛路径二选一：① 治理侧落地 PDF 时间戳定点化后按同代工具重试；② 随开放项 9 的 0.3.0 全量重建一并出双工件 manifest 并登记新 sha。两代产物已留档 `temp/GC-2026-1112-01/p1-{pre-restore-backup,post-restore-attempt}/`。

---

*GC-2026-1112-01。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B11/PF-B12；验证入口 tools/verify_layout.py（含 H 组）；沙箱证据 temp/GC-2026-1112-01/。*
