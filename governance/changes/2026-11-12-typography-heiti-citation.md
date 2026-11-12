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

- **rules_version**：0.2.0 → **0.2.1**。同步于 `project.yaml`、`governance/rule-index.yaml`、`tools/paper.py`（manifest 常量）及 P1–P7 的 `paper.yaml`。理由：PF-B11/PF-B12 规则正文扩充 + schema/profile 新键；无新增规则号。
- **git 基线**：治理仓 `d908695`（工作树干净，2026-11-12 核实）。本变更为**单一治理提交**（PF-V5，不与他号混号），可独立 `git revert` 恢复。
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
| 3 | `templates/layout/profiles/stie.yaml` | 修改 | 同 4 键显式化（与 L0 同值，deep_merge 同值不产生覆写日志） |
| 4 | `tools/layoutlib.py` | 修改 | `merged_role()` 暴露 `heading_bold`/`caption_bold`/`abstract_label_alignment`（缺省 None = 未声明） |
| 5 | `tools/make_refdoc.py` | 修改 | AbstractTitle：align 取 `abstract_label_alignment`（缺省 center）、bold 取 `heading_bold`（缺省 True）；Heading1–5 与 Heading{N}Char：bold 取 `heading_bold`；Caption/ImageCaption/TableCaption：bold 取 `caption_bold`；`self_check` 增 `heading1_bold`/`abstract_title_bold`/`abstract_title_alignment`/`table_caption_bold` 4 项并纳入 pass 判定 |
| 6 | `tools/paper.py` | 修改 | ① 新增 `_apply_citation_superscript`（含 `_CITATION_PATTERN`/`_superscript_run_parts`）：跳过 pStyle∈{Bibliography, SourceCode} 段与 `<m:oMath>/<m:oMathPara>` span；模式 `\[\d{1,3}(?:-\d{1,3})*(?:,\d{1,3}(?:-\d{1,3})*)*\]`（1–3 位数字、逗号后无空格）；run 拆分，引用片段复制原 rPr 并按 ECMA-376 顺序插入 `<w:vertAlign w:val="superscript"/>`；已有 vertAlign 的 run 不重复处理；含 drawing/fldChar 等的 run 不动。② `_cmd_build_docx_impl` 在 `_harden_tables` 后调用（受 `citation.numeric_superscript` 驱动），计数入 notes（`citation_superscript_marked`）。③ `_assert_layout_landing` 增断言：`*_bold_off`（Heading1–5/AbstractTitle/Caption×3 显式 `w:b val=0`）、`abstract_title_alignment`、`citation_superscript_coverage`（非排除段内全部引用 run 须带上标；计数 0 记 note 不 fail）。④ manifest `rules_version` → 0.2.1 |
| 7 | `tools/verify_layout.py` | 修改 | B 组 baseline 剥离清单补 4 新键；D 组负例 +3（`heading_bold_restored`/`abstract_title_centered`/`citation_superscript_removed`）；新增 H 组正例（P4 区间 `[12, 40]` 不得上标；7 篇 docx 引用计数 == markdown 源计数（双侧剔除 Bibliography））。产物端匹配一律空白容错（pandoc 重序列化为 `w:val="0" />` 形态） |
| 8 | refdoc ×3 | 再生成 | 确定性重生成；**diff 已逐样式块复核**：仅 `word/styles.xml` 变化，仅 AbstractTitle/Heading1–5(+Char)/Caption×3 九个样式块的 `w:b(/bCs)` 翻转与 AbstractTitle `w:jc` 翻转；Title/Subtitle/Author/Normal/Abstract/Bibliography/BlockText/AuthorBio 不变 |
| 9 | `governance/build.md` | 修改 | PF-B11 增一条（角色粗体与摘要标签对齐为 profile 键 + 黑体不加粗理由）；PF-B12 增一条（引用上标 + coverage 断言） |
| 10 | `governance/rule-index.yaml`、`project.yaml` | 修改 | rules_version → 0.2.1 |
| 11 | `governance/changes/2026-11-12-typography-heiti-citation.md` | 新建 | 本记录 |

### 论文侧（受派子代理执行；每篇独立提交，PF-V5）

| # | 范围 | 变更 |
|---|---|---|
| 12 | P1–P7 `paper.yaml` | `rules_version` → 0.2.1；**提交限定 `git add paper.yaml build-record.md`**（P1/P2/P3 工作树有并发未提交改动，不得裹挟） |
| 13 | P1–P7 | `build docx` + `build pdf`（pending 草稿就地重建）；`build-record.md` 各追加一节 |

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
| R6 | 引用被 pandoc 拆进相邻 run → 漏上标 | coverage 断言**失败可见**（构建失败），不静默；实测 7 篇无此形态 |
| R7 | PF-B7 已发布版本保护触发 | 7 篇均 pending（已核实）；若重建报 PF-B7 错误即停并按 PF-V3 升版 |
| R8 | pandoc 重序列化形态差异 | 产物端全部正则空白容错（沙箱首建曾因 `<w:b w:val="0" />` 全 null 失败，已修并复跑通过） |
| R9 | 论文侧提交裹挟并发改动 | 提交限定 `git add paper.yaml build-record.md`（复核 NOTE 采纳） |

## 7. 恢复方式（Recovery）

- 治理仓：单一治理提交，`git revert <commit>` 即整体回滚（refdoc 为二进制入库，revert 一并还原；回滚后无需再生成）。
- 论文侧：7 篇各自独立提交，按篇 `git revert paper.yaml` 后重建即恢复旧排版。
- 工作区不做整体回滚（F7 保留现场）；沙箱与测试脚本留存 `temp/GC-2026-1112-01/`。

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

### 8.1 全量复跑（论文侧 P1–P7 重建后回填）

（待论文侧子代理重建后回填：verify_layout 全项、7/7 build 断言、视觉验收结论。）

## 9. 实施阶段独立复核

（待实施完成后由未参与子代理复核代码 diff 与文档一致性，结论回填。）

## 10. 开放项

1. P5/P6/P7 正文无 [N] 引用（著者-出版年制，与 stie profile S13 一致）：上标规则对它们是**未触发**而非未生效；coverage 断言记 0 计数 note。
2. P1 约 11 处叙述性引用（"参考文献 [1]–[8]"、"Hu 等[7]"）与表段 `Dung [1]` 按用户全局指令一并上标——与 GB/T 7714"叙及文献序号可不入角标"的通行做法存在**已登记偏离**；如需细分（仅句末引用上标）须另行立项并修订 profile 键语义。
3. P2/P1 顺序编码制正文与 stie profile `citation.style: gb-7714-author-date` 的**体例冲突**（GC-02 开放项 22 延续）：本变更只解决"形式"（上标），不改"体例"；投稿前须一次文字级大改，须单独授权。
4. 引用被拆进相邻 run 的极端形态不重连（R6）：coverage 断言可见失败，出现时再扩展处理器。
5. `citation_superscript` 键当前仅 L0/L1 声明；L2 不可覆写（citation 为结构身份键，PF-B3）——论文级关闭上标须走 profile 版本化。

---

*GC-2026-1112-01。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B11/PF-B12；验证入口 tools/verify_layout.py（含 H 组）；沙箱证据 temp/GC-2026-1112-01/。*
