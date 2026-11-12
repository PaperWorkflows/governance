# 治理变更记录 GC-2026-1112-05：《数智技术研究与应用》范文体例对齐（profile 十项 + 工具链 + schema + refdoc）

- 日期：2026-11-12
- 编号：GC-2026-1112-05（顺延 GC-2026-1112-04；原编号 GC-2026-1112-04 让位给同日 O9 线构建工具链变更记录）
- 类型：治理能力修订（stie venue profile 按通过审稿范文实测对齐；工具链 P1-a～P1-d 前置改造；schema 新键；refdoc 确定性再生成；论文侧 P1–P7 铺开）
- 规则依据：AGENTS.md F9（治理变更纪律）、F5（任务由主会话或受派子代理执行）、F6（最小改动）；版式语义 governance/build.md **PF-B3**（profile 分层与结构身份键版本化）、**PF-B10**（三层分层）、**PF-B11**（refdoc 为版式唯一实现载体）、**PF-B12**（落地校验与 mutation 回归）、**PF-B13**（L2 覆盖边界）、**PF-B14**（来源等级 provenance）；写作语义 PF-W11/PF-W12；版本语义 PF-V1/PF-V3；规则版本 0.3.0
- 用户终局裁决（2026-11-12，覆盖 final-recommendations.md 中与之冲突的建议）：**字号类一概保持现值**（sizes.* 全部、author_bio_layout.pt、页码字号等所有 pt 值一律不改，含 A-2 的 7.5→10.5 与 A-4 的 pt 部分均取消）；非字号项全部落地；最终裁决意见文档为历史记录，以本次任务书为准
- 用户最终补充指令（2026-11-12，插入执行）：通信作者按**三档规则**处理——① 单作者篇：通信作者=作者本人、\* 标注唯一作者；② 多作者篇且通信作者不在署名首位：挪至末位、\* 跟随本人、第一作者保持首位不动；③ 多作者篇且通信作者=署名首位（兼第一作者）：**保持不动**（署名顺序即身份认定：末位保第一作者、首位兼任不挪）。此前"通信作者=第一作者需停下报告"护栏取消，按第③档直接处理。其余阶段 2 流程不变。
- 前置分析：`temp/template-analysis-20261112/final-recommendations.md`（389 行终稿，第四章"A 档前置修改清单"与第五章"落地路径"为本记录直接依据）；范文样本《基于可信数据空间的航天卫星数据隐私计算与跨域合规流通机制-v4.5(1).pdf》（通过审稿投稿稿，20 页，只读）
- 流程状态：本记录与全部治理侧文件落盘（**未提交**）。按 F9，提交前由未参与变更的独立子代理复核实际 diff 与验证结果

---

## 1. 基线（Baseline）与版本

- **rules_version**：保持 **0.3.0**（project.yaml / governance/rule-index.yaml / tools/paper.py 常量一致，实施时实测）。理由：本变更**零规则正文修改**（build.md、rule-index.yaml、project.yaml 均未动），仅改 schema/tools/profile/refdoc 实现载体与数据值；沿 GC-2026-1112-03 先例（工具链实现、rules_version 保持）。
- **git 基线**：治理仓 master（实施前 `git status --short` = 仅 ` M authors/registry.yaml`，属他线，本变更未触碰）。
- **profile 版本化**：`page.margin.*` 属结构身份键（PF-B3/PF-B10 要求 profile 版本化）。`registry.yaml` 现无 profile 级版本字段（L-6，开放项），版本化以本变更记录文本承载。
- **范文身份**：通过审稿**作者投稿稿**，非编辑部终排稿（理由见 final-recommendations §1.1：Letter 纸型、非标字号、无页眉、无著录字段）。采信上限 = 审稿接受度，非终排规格；终排模板取得后须按同口径复核（L-3/开放项）。

## 2. 现状取证（问题陈述）

| # | 问题 | 取证（2026-11-12 实测） |
|---|---|---|
| P1 | stie profile 多项非字号键与通过审稿范文不符 | final-recommendations 第四章 A 档 7 项 + C 档 4 项；范文文本层/视觉/硬数据三份报告（temp/template-analysis-20261112/） |
| P2 | A-3（header→none）被工具链阻断：header=none 时 refdoc 生成不出 | 沙箱实证：`make_refdoc.py` self_check 无条件要求 header 部件含占位符，none 时 `any()` 对空序列返回 False → `self_check.pass=false` → 退出码 2（P1-a）；verify_layout D 组 `header_reference_removed` 负例与 E 组转义检查依赖 header 部件（P1-c-1/P1-d） |
| P3 | 表头灰底（C-1）无 schema 承载 | `tables` 域 `additionalProperties: false`，未知键构建失败；生成器 firstRow 条件格式仅写 tcBorders，无 `w:shd` |
| P4 | 回归工具的边距突变字面量硬编码 25.4mm | verify_layout D 组 `margins_removed` 突变 `w:top="1440"`（=25.4mm）；profile 改 20mm 后该字面量在新产物中不存在 → mutation no-op → 误报 FAIL（P2-2） |

## 3. 精确变更清单（逐文件）

| # | 文件 | 类型 | 内容 |
|---|---|---|---|
| 1 | `schemas/layout-profile.schema.json` | 修改 | `figures` 域新增 `caption_bilingual`（boolean，缺省 false）；`tables` 域新增 `header_fill`（string，pattern `^(?:#[0-9A-Fa-f]{6}\|none)$`，缺省 none，生成器落实缺省）与 `caption_bilingual`（boolean，缺省 false）。`additionalProperties: false` 语义保持 |
| 2 | `tools/make_refdoc.py` | 修改 | ① `_apply_three_line`：当 `tables.header_fill != "none"` 时在 firstRow 条件格式 `tcPr` 的 `tcBorders` 之后、`vAlign` 之前写入 `<w:shd w:val="clear" w:color="auto" w:fill="XXXXXX"/>`（去 `#` 后大写）；"none"/缺省不写。② self_check `header_placeholder` 按 `pagination.header != "none"` 条件化：none 断言「无 header part」、其他模式断言占位符存在（P1-a）。③ self_check 新增 2 项并纳入 pass 判定：`no_header_reference_when_none`（none 模式 docxml 不含 `<w:headerReference`）、`first_row_shd`（header_fill 非 none 时 firstRow 含 w:fill） |
| 3 | `tools/verify_layout.py` | 修改 | ① D 组 `margins_removed` 突变字面量改按被测 profile 边距动态换算 twips（P2-2）。② D 组 `header_reference_removed` 负例条件化：仅 `header_mode != "none"` 运行；none 模式替换为**正向断言**（产物 `word/document.xml` 解压后不含 `w:headerReference`；检索解压后内容而非 zip 原始字节——deflate 下字面量不可见，首版自写 bug 已修，2026-11-12）。③ E 组标题转义检查：无 header part 时跳过并记 visible note（P1-d） |
| 4 | `templates/layout/profiles/stie.yaml` | 修改 | 逐键见下方「§3.1 profile 变更表」；逐键 provenance 注释更新为 [JT] 范文实测 2026-11-12（附 final-recommendations 引用）；文件头追加 2026-11-12 变更说明 |
| 5 | `templates/layout/refdoc/stie.docx` | 再生成 | 确定性重生成（固定 zip 时间戳与 core.xml 日期）；draft/gbt7713 refdoc 保持不变（字节级验证，见 §8） |

### 3.1 profile 变更表（stie.yaml，共 M4 十项 + 字号类保持）

| # | 键 | 改前 | 改后 | provenance（来源等级 → 理由） |
|---|---|---|---|---|
| M4-1 | `page.margin.top/bottom/left/right` | 25.4 | 20（四边） | [SC]→[JT]（范文实测 20.32/20.32/19.54/19.97≈2cm，A-1；[SC] 项可被 [JT] 覆盖，原则一） |
| M4-2 | `pagination.header` | title_center | none | [SC]→[JT]（范文 20 页全无页眉，A-3；采信边界为投稿面适配，终排面不保证）。注释保留 title_center 为回滚候选 + L-3 说明 |
| M4-3 | `pagination.header_pt` | 9 | **9（不改值）** | header=none 下闲置（A-3 连带死键），保留待终排回滚复用；注释标注 |
| M4-4 | `author_bio_layout.first_line_indent_chars` | 2 | 0（顶格） | [JT]（范文作者信息全部顶格 x0=57.6，A-4） |
| M4-5 | `author_bio_layout.pt` | 9 | **9（不改值）** | [SC] 字号类按用户裁定保持（A-4 的 pt 部分取消） |
| M4-6 | `tables.border_widths_pt` | 1.0/0.5/1.0 | 1.44/0.72/1.44 | [JT-软件学报]→[JT]本刊范文（A-5；OOXML 1/8pt 粒度实际落地 1.5/0.75，L-5） |
| M4-7 | `tables.header_fill` | 无 | `"#E5EBF0"` | [JT]（范文表头浅灰底 RGB(0.898,0.922,0.941)、黑字，C-1） |
| M4-8 | `figures.caption_bilingual` / `tables.caption_bilingual` | 无 | true | [JT]（范文图题表题中英成对，C-2；双语文本由写作层保证、题注样式不变） |
| M4-9 | `references.hanging_indent_cm` | 0.74 | 0.635 | [GB+JT]→[JT]（范文 18.0pt=2 字符@9pt，360 twips 精确表达，0.635cm 计算见 A-6；原则二情形甲「编辑部接受」） |
| M4-10 | `author_bio_layout.one_paragraph_per_author` | true | false | 原 [S17] 标注系**误标**（polish.md 第 98 行 S17 原文无"一人一段"要求）；[JT] 范文首作者/通信作者各一段、其余作者合并一段（D-5/L-4） |

**字号类保持（按用户裁决，未动）**：`sizes.*` 全部（title_zh 18 / title_en 14 / author 12 / … / page_number 7.5 / header 9 / code 10.5）、`body_pt 10.5`、`author_bio_layout.pt 9`、`figures.caption_pt 9`、`tables.caption_pt 9`。A-2（page_number 7.5→10.5）与 A-4 的 pt 部分均取消。其余未动键：line_spacing 1.5、字体矩阵 fonts.*、paragraph、heading_bold/caption_bold/abstract_label_alignment、heading_numbering、formulas、citation、punctuation、references.order/heading_pt/entry_pt/entry_spacing_pt。

### 3.2 论文侧部署（阶段 2，P1–P7）

- 每篇：首页块序对齐范文体例（中文摘要→中文关键词→基金→英文标题→…→Abstract→Keywords）、题注双语盘点与补齐、通信作者按**三档规则**处理（用户指令 2026-11-12：① 单作者=本人；② 通信作者非首位 → 挪末位保第一作者；③ 通信作者=首位 → 保持不动）、pf patch 级版本递增、按既有构建流程重建 docx+pdf（20mm 边距、A4、header=none 的新 refdoc）、build-record.md 追加构建记录一节；论文侧不 commit（本阶段纪律）。
- **通信作者三档评估结论（2026-11-12 实测 7 篇）**：无单作者篇、无「通信作者=署名首位」篇；各篇通信作者均已处于署名末位 → **全为第②档且已在末位，零挪动 diff**。P3 通信作者以"（通信作者）"文本标记代替 \* 上标，本次未变更（S18 星号格式随正文另立）。
- 论文侧基线（2026-11-12 实测）：7 篇 `paper.yaml.layout_profile` 均为 `stie`；P1/P2/P3 工作树存在他线未提交改动（不裹挟、只改目标文件）；构建产物见各篇 build/<version>/。

## 4. 理由（Rationale）

- 对齐遵循三条采信原则（final-recommendations §1.2）：[JT] 实测可覆盖 [SC] 自选回落；[JT] 覆盖 [GB] 仅限情形甲（编辑部接受，如 A-6）；[S#] 明示项只能核验不能覆盖（本轮无非字号 S 项改动，one_paragraph_per_author 系误标修正而非覆盖 S 项）。
- 工具链改造（M2/M3）为 A-3 前置条件：不改则 refdoc 生成不出、byte-diff 无从执行（P1-a 实测退出码 2）。
- `header_fill`/`caption_bilingual` 走 schema+profile 声明而非生成器硬编码：PF-B11"profile 是唯一真值源"；缺省值=旧行为（无底纹、单语题注），旧 profile 兼容。
- `one_paragraph_per_author` 值改动不推翻任何 S 系列（D-5/L-4 已核对 S17 原文），属 provenance 纠错 + [JT] 实测值，非 `[S#]` 覆盖。
- 字号保持：11.05/12.95/15.95 等范文字号均非标准中文字号档，属原则二情形乙（作者手调痕迹），不构成编辑部认可；用户终局裁定"接近即保留"。

## 5. 备选方案（Alternatives）

| # | 方案 | 结论 |
|---|---|---|
| 1 | 字号数值随范文改为 11.05 等非标值（A-2/A-4 原议） | ❌ 拒：用户终局裁决保持现值；非标字号无编辑部认可依据 |
| 2 | `header_fill` 不进 schema、生成器硬编码 E5EBF0 | ❌ 拒：违反 PF-B3 additionalProperties:false 与 PF-B11 声明唯一真值源 |
| 3 | D 组边距突变保持 1440 字面量 | ❌ 拒：profile 演进后 mutation no-op 误报 FAIL；按 profile 动态计算可随演进免维护（final-recommendations 步骤 6 推荐后者） |
| 4 | verify_layout 加 header 注入式负例（向 none 产物注入 header 引用后断言必须失败） | ⏸ 移出本变更（P1-c-2）：属测试工具能力增强、混入会扩大审查面；按 PF-B12 登记为开放项，stage 2 后补 |

## 6. 风险（Risks）与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | A-3 回滚概率高（页眉为排印项，终排模板可能要求） | 注释保留原值 title_center + header_pt 价值说明；回滚仅需改回 1 键 + 重建；登记开放项 |
| R2 | firstRow `w:shd` 影响 pandoc 往返或 `three_line_table_ok` 判定 | 已验证：shd 为 `tcPr` 内独立元素，`three_line_table_ok` 只数 single 边框，不受影响（C 组 self_check 3/3 通过） |
| R3 | D 组 mutation 在陈旧论文产物上 no-op/正向异常 | 已实证根因 = papers 产物为旧 profile（未重建，阶段 2 处理）；全新产物下 3 项红转绿（§8） |
| R4 | schema pattern 过严拒绝合法色值 | pattern 允许大小写 hex 六位与 none；生成器对无 `#` 输入容忍（strip）；仅 stie 使用该键 |
| R5 | rules_version 判定分歧 | 零规则正文修改，沿 GC-03 先例不 bump；如需评审另裁，另行变更记录 |
| R6 | 论文侧首页块重排破坏构建 | 块级重排不改变 custom-style 语义与段落样式映射；每篇重建后跑产物断言与 verify_layout |

## 7. 恢复方式（Recovery）

- 治理侧（未提交，正常回滚 = 不提交/重置）：`git checkout HEAD -- schemas/layout-profile.schema.json tools/make_refdoc.py tools/verify_layout.py templates/layout/profiles/stie.yaml templates/layout/refdoc/`，并删本记录；再 `python3 -I tools/make_refdoc.py` 重生成全部 refdoc 即可回旧。若已提交，则 `git revert <本变更提交>` 单笔回滚（本变更文件集独立、不与他线交错）。
- 论文侧：重排的 `body/paper.md` 均可按篇 `git diff` 反相还原；重建产物入 build/<version>/（不入库），旧版本产物保留可回切。

## 8. 验证方法（Verification）与结果

**治理侧（阶段 1，本记录范围）实测**：

| # | 方法 | 结果 |
|---|---|---|
| 1 | `make_refdoc.py` 再生成 ×3 | status ok；3 档 self_check 全 True（新 2 项期望值：header=none 无 headerReference、firstRow shd 命中） |
| 2 | refdoc byte-diff | draft/gbt7713 **字节完全一致**（sha256 未变，无回归）；stie 12259→11848B，**4 个部件内容变化**（Content_Types / document.xml / styles.xml / rels）+ **删除 header1.xml** |
| 3 | refdoc 内容 diff（逐项确认） | margin 1440→**1134**（四边）；header part+headerReference 删除、footerReference 保留；三线 sz 8/4/8→**12/6/12**（=1.5/0.75pt，1/8pt 粒度）；firstRow 增 `<w:shd w:fill="E5EBF0"/>`；Bibliography hanging 420→**360**；AuthorBio firstLineChars 200→**0**；Footer sz 仍 15（7.5pt，字号未动） |
| 4 | `make_refdoc.py --check` | 3/3 in_sync=True、self_check.pass=True、退出码 0 |
| 5 | `verify_layout.py` 全量 | **TOTAL 26 PASS 23 FAIL 3**；3 红全在 D 组，根因 = papers 产物为旧 profile（P1 v0.4.0 实测 `w:top="1440"`、含 `<w:headerReference r:id="rId10"/>`）：① none-mode positive（产物仍含 headerReference）② margins_removed mutation no-op（1134 不在 1440 产物中）③ positive（margin 1134 vs 1440）。非工具链缺陷——见 6 |
| 6 | 全新产物实证（/tmp/fresh-check，新 refdoc + pandoc + math-font/关系图修复同真实构建） | 全新产物 pgMar=1134、无 headerReference、firstRow 带 shd；`_assert_layout_landing` **0 failures**；margins_removed 负例命中 1134 正确触发；none-mode positive 通过；另以 gbt7713(title_center) 全新产物验证 header_reference_removed 旧负例仍有效（触发 `header_referenced` 失败）⇒ **3 红项在 stage 2 重建后全部转绿** |

**论文侧（阶段 2，2026-11-12 实测回填）**：P1–P7 全部按五步流程执行完毕，逐篇明细见各篇 `build-record.md` 新增节（P1 R4 / P2 R9 / P3 R8 / P4 R6 / P5 R6 / P6 R10 / P7 R6）。汇总：

| 篇 | 通信作者（三档规则） | 基金位置 | 题注双语 | 版本递增 | 验证 |
|---|---|---|---|---|---|
| P1 | 第②档已在末位，零动作 | 已合规零 diff | 已齐备零 diff（表 1–8、图 1–3） | v0.4.2→**v0.4.3** | check pass；pgMar 1134、无 headerReference、firstRow shd |
| P2 | 第②档已在末位，零动作 | 拆出后移至中文关键词后（块序 +12/−10，含关键词块上移） | 补表 1–9、图 1–4 英文行 | v0.4.4→**v0.4.5** | check pass；版式落地 + 英文题注 + 块序实测 |
| P2（并发线后续） | 不变 | 不变 | 不变 | v0.4.5→**v0.4.6** | 动因=用户终审"内部资料引用清除"线（R10）；release BUILD-v0.4.6-20261112145327，docx `4f2efda2b41c8732`（848 846 B），30 页；refdoc 仍 `96b4ec2638222400`、assertions 0 failed |
| P3 | 第②档已在末位，零动作 | 移至中文关键词后（+4/−4） | 已齐备零 diff（表 1–3、图 1–4） | v0.3.5→**v0.3.6** | check pass；版式自旧 refdoc 1440→1134 首次落入 |
| P4 | 第②档已在末位，零动作 | 拆出后移至中文关键词后 | 补表 1–4、图 1–3 英文行 | v0.3.2→**v0.3.3** | check pass；版式落地 + 英文题注 + 块序实测 |
| P5 | 第②档已在末位，零动作 | 拆出后移至中文关键词后（含关键词块上移） | 补表 1–4、图 1–3 英文行 | v0.4.3→**v0.4.4** | check pass；版式落地 + 英文题注 + 块序实测 |
| P5（并发线后续） | 不变 | 不变 | 不变 | v0.4.4→**v0.4.5** | 动因=用户终审"内部技术方案引用清除"线（R7，与 P2 同源指令）；release BUILD-v0.4.5-20261112144922，docx `35ff3d6b1584a3ae`（389 190 B），17 页；refdoc 仍 `96b4ec2638222400`、assertions 0 failed |
| P6 | 第②档已在末位，零动作 | 拆出后移至中文关键词后（含关键词块上移） | 补表 1–4、图 1–4 英文行 | v0.2.2→**v0.2.3** | check pass；版式落地 + 英文题注 + 块序实测；Consolas 字体替换存量消除 |
| P7 | 第②档已在末位，零动作 | 移至中文关键词后（BodyText 样式保留，−4/+4） | 补表 1–6、图 1–4 英文行 | v0.2.3→**v0.2.4** | check pass；版式落地 + 英文题注 + 块序实测 |

> **版次时效注记（2026-11-12 终审修正时实测）**：本表写就时 P2=v0.4.5、P5=v0.4.4；其后用户终审"内部资料引用清除"并发线将 P2 推进至 **v0.4.6**（R10）、P5 推进至 **v0.4.5**（R7），已补行如上。**本篇写就后各篇仍可能被并发线继续推进，版次一律以各篇 `build-record.md` 最新节与 `build/current.json` 实测为准**，本表不随并发线滚动更新。

- 全部 7 篇经治理仓 `tools/paper.py`（O9 线，已提交 `e1e67ef`；PF-B7 新构建命名"标题（第一作者）.docx"）重建 docx+pdf，`paper.py check` 均 pass；产物版式逐篇实测（pgMar 四边 1134、无 header part/headerReference、footerReference 保留、firstRow `w:shd` E5EBF0）。
- **全量回归闭环：`verify_layout.py` TOTAL 26 PASS 26 FAIL 0**——阶段 1 的 3 红项（D 组 none-mode positive / margins_removed mutation no-op / positive margin 1134 vs 1440）全部转绿。回归输出两档存档于 `temp/VERIFY-GC-2026-1112-05/`：`verify-layout-full-20261112.txt`（首轮，生成于 P2 v0.4.6/P5 v0.4.5 重建之前，已注明被取代）与 `verify-layout-full-20261112-final.txt`（终审修正轮复跑，覆盖并发线推进后的全部当前产物，含 `make_refdoc.py --check` 输出）。
- 存量事项登记（均非本轮引入，留内容线）：P1 conclusion 标题口径（writing-spec"结语" vs 正文"结论与后续"）；P3/P5 作者简介十字段不全（S17/O4）；P6/P7 `abstract.md` 用一级标题 `# 摘要`，与新 paper.py submission 抽取期望的 `## 中文摘要` 不符（P1/P2/P4/P5 均为二级）；P3/P5/P7 PDF 字体替换（Cambria Math/Consolas）；**funding.yaml 与正文定名不一致**（P1/P3 的 `funding.yaml` name="云南省时空大数据重大科技专项" vs 正文渲染行"云南省重大科技专项计划项目（202502AD080005）"；paper.py 不解析该文件、无构建影响，由内容线统一定名）。

## 9. 独立复核与状态

- 本记录草案待写后复核：按 F9，提交前由未参与变更的独立子代理复核实际 diff 与验证结果；本记录 §8 以实施实测为准。
- 已自查事项：py_compile 两工具通过；stie.yaml 过 schema 校验（附加新键在 additionalProperties:false 下合法）；3 篇 refdoc in_sync；git status 仅本变更文件 + 他线 `authors/registry.yaml`（未触碰）。

## 10. 开放项

1. **P1-c-2 注入式负例**（PF-B12 mutation 覆盖补全）：向 header=none 产物注入 header 引用后断言层必须失败。本变更只做条件化 + 正向断言，未补注入能力；旧负例对 title_center profile 仍有效，none 模式暂缺"负例证明断言有效"覆盖。完成条件：该负例在 header=none profile 下可运行并判 FAIL。（对应 final-recommendations L-9）
2. **L-6 registry 无 profile 版本字段**：`registry.yaml` 只有 `schema_version: 1`，无 profile 级语义版本；本变更的版本化落在变更记录文本。是否新增字段待治理评审。
3. **A-3 页眉为高回滚候选**：stie 现 `pagination.header: none`，采信边界为投稿面；终排模板取得后若编辑部要求页眉，回滚为 title_center（并同步回滚 header_pt 闲置标注）。回滚方式见 §7。
4. **英文块结构差异登记**：各篇英文题名/作者/单位块存在形态差异（P1/P4 无独立 EN 作者/单位块、P6 无独立 EN 作者/单位、P7 无独立 EN 题名/作者/单位、P2 无独立 EN 题名）；本轮按"基金挪到中文关键词之后、英文段之前"处理，不补造缺失英文块，形态收敛另立项（涉及论文侧正文与 writing-spec）。
5. **通信作者署名位（用户三档规则 2026-11-12）**：7 篇实测均无单作者篇、无「通信作者=署名首位」篇，且各篇通信作者均在署名末位 → 全为第②档且已在末位、**零动作**；P3 通信作者以"（通信作者）"文本标记代替 \* 上标（S18 星号格式随正文另立）。若未来某篇出现通信作者非末位或=首位的形态，按三档规则处理。
6. **`make_refdoc.py` self_check 死赋值（终审发现，登记不修）**：self_check 中 `footer_page_field` 先以粗粒度 `"PAGE"` 子串匹配计算，随后被 `has_exact_page_field`（精确 `w:instrText` 含 `PAGE` 字段）覆盖，前一次赋值为死赋值（结果未被使用）。不影响任何判定（最终值取精确版），属代码卫生问题；改逻辑需动 O9 在途线邻域（self_check 块），按纪律不在本变更处理，留后续清理轮次。同步事项：该处 AuthorBio 注释文字已在本轮同步至 stie.yaml 现值（见 §3 第 2 项）。

## 11. 后续内容线闭环（2026-11-12 夜）

内容线遗留事项按「GC-2026-1112-05 内容线闭环」清单执行，已提交于各论文仓与本治理仓，未 push。

### 11.1 已关闭项

1. **P6/P7 abstract.md 结构重修（对应各篇 build-record「已发现但未修」的 `## 中文摘要` 口径缺口）**：
   两篇 `abstract.md` 由一级 `# 摘要` 改为合规范例（`# Abstract` / `## 中文摘要` / `## English Abstract`，
   与 P4 样板一致），摘要与关键词正文逐字保留，仅改标题结构与标签格式（`**关键词：**`→`**关键词**：`、
   `**Keywords:**`→`**Keywords**:`）。重建后两篇 manifest `submission_gaps` 均为 `[]`，
   `abstract_zh` / `keywords_zh` / `conclusion` 全部非空，`abstract_zh_missing` / `keywords_zh_missing` /
   `abstract_field_error` / `body_extraction_failed` 全部消失；`tools/verify_layout.py` 全量 26/26 保持。
   P6 → v0.2.4（`body/paper.md` 未动，docx 与 v0.2.3 逐字节一致，纯提交元数据口径修复）；
   P7 → v0.2.5。验证结论见两篇 build-record（P6 R11、P7 R7）。
2. **P7 结论标题对齐 S12（manifest `body_extraction_failed` 根因）**：`# 7 质量评价、实施路径与结论`
   → `# 7 质量评价与实施路径`；原 `## 结语`（二级）升格独立章 `# 8 结语`（一级），内容零改写；
   body/ 章节文件与 README 同步（08-conclusion.md 新建、01-introduction.md 交叉引用同步），
   paper.yaml chapters 增 8 结语。P7 v0.2.5 manifest `conclusion` 实测 = 第 8 章结语全文。
3. **`make_refdoc.py` self_check 死赋值清理（§10 开放项 6 收口：登记不修→已清理）**：删除
   `footer_page_field` 被精确版（`layoutlib.has_exact_page_field`）覆盖前的粗粒度 `"PAGE"` 子串死赋值
   及其唯一下游 `footer_parts` 列表构造（只删死代码，未动任何逻辑）；py_compile 通过，
   `--check` 3/3 in_sync，三个 refdoc（含 stie.docx）再生成后 sha256 逐字节不变
   （stie.docx = `96b4ec2638222400`），证明确认删除未改变任何输出。

### 11.2 缓行项登记（只登记不动手）

1. **P1 结论标题**：`body/07-conclusion.md` 属并发精修线脏文件（该线 28 个之一），结论标题改法归该线统一处理，本线不碰。
2. **P3 作者简介短式**：`authors.txt` 登记在案的设计形态（短式），非内容缺失，暂不追求长式统一。
3. **P5 作者简介**：提取器 best-effort 对 custom-style 块的解析限制，非内容缺失，不在本线结构修复范围。
4. **P1/P3 funding.yaml 定名**：两文件属并发线（P1 精修线脏文件之一），定名决策归该线。

---

## 12. 范本标签接排修正（2026-11-13）

用户 2026-11-13 指示：范本前端写法为「标题：内容」同行接排（范本实例：「摘要：…」「关键词：…」「Abstract: …」「Keywords: …」，标签不加粗、同正文字体字号），非“标签独立成行、内容另起”。本变更消除 7 篇 body/paper.md 前端的 `AbstractTitle` 独立标签行 + `Abstract` 内容块两段式偏差。

### 12.1 修正内容

**四标签合并**：将“AbstractTitle 标签行块 + Abstract 内容块”两段式合并为单块接排——“标签：内容”同一段落（标签与正文同字体字号、不加粗，与范本一致）：

- 中文：「摘要：」「关键词：」（全角冒号，标签直连内容）；
- 英文：「Abstract: 」「Keywords: 」（半角冒号+空格）；
- 英文 Abstract 标签块若位于 `lang=en` 块外（P2/P4/P5/P6），删除该块、标签并入 `lang=en` 内 Abstract 块首；P3 的 Abstract/Key words 块在 `lang=en` 内，原位并排；P7 无 `lang=en`，直连并排。

**文字规范化清单**（仅前端标签文字，正文逐字未改）：

| 篇 | 规范化项 |
|---|---|
| P3 | 「摘  要：」→「摘要：」；「Key words:」→「Keywords:」 |
| P6/P7 | 「关键词： 」「Keywords: 」尾随空格变体 → 并入时统一为「关键词：」「Keywords: 」 |
| P4 | BlockText「资助：云南省时空大数据重大科技专项（202502AD080005）。」→「基金项目：……」（与范本用词及其余六篇统一；P4 writing-spec 无资助用语登记，无冲突） |
| P2/P4/P5/P6/P7 | 前端 BlockText「*通信作者：」→「通信作者*：」（星号移至标签后，与范本一致；仅改星号位置，其余文字不动）。P7 通信作者行位于第二条 Author 块（`\*` 转义），按同规则仅移星号、转义保留；P3 以「（通信作者）」文字标记代替 \* 上标，不涉及 |

铁律：摘要/关键词/英文摘要的正文文字逐字不改；仅动前端标签结构与标签文字；前端块之外不碰。

### 12.2 重建与验证结论

版本 patch 递增（纯版式/形式修正，科学内容零变）：P2 v0.4.6→v0.4.7、P3 v0.3.6→v0.3.7、P4 v0.3.3→v0.3.4、P5 v0.4.5→v0.4.6、P6 v0.2.4→v0.2.5、P7 v0.2.5→v0.2.6。

- 6 篇（P2–P7）经治理仓 `tools/paper.py` 重建 docx+pdf，`check` 均 pass；`layout_assertions=pass`。
- **接排落位验证（docx 解包 word/document.xml，逐篇实测）**：四标签全部以**段落前缀**形式出现（标签与正文同一 `w:p`）——「摘要：」「关键词：」「Abstract: 」「Keywords: 」各 1 段；不再存在独占一行的“摘要 / 关键词 / Abstract / Keywords”标签段（standalone 标签段计数 = 0）。
- `tools/verify_layout.py` 全量回归：**TOTAL 26 PASS 26 FAIL 0**（保持）。输出存档 `temp/VERIFY-GC-2026-1112-05/verify-layout-full-20261113-front-inline.txt`。
- 逐篇产物校验（docx/pdf sha256、大小、页数、manifest）见各篇 build-record.md 新增节（P2 R11 / P3 R9 / P4 R7 / P5 R8 / P6 R12 / P7 R8）。
- **P1 暂缓（并发精修线脏文件）**：本变更动工时 `git diff body/paper.md` 前端区（约 1–60 行）存在脏 hunk（作者块补邮编、通信邮箱变更、基金行挪位、AbstractTitle/关键词/Abstract 块重组），按本线纪律“前端区也有脏 hunk 则停下汇报、不动该篇”执行。**执行期间并发精修线已将 P1 合入**（提交 `802ee42` 精修正文落地、`6f181b7` 基金条目、`072ba47` 版本记录 v0.4.3→v0.4.4 + stage→review，工作树转净），但其 `build/` 仍止于 v0.4.3、build-record 未新增 v0.4.4 重建节，版本号 v0.4.4 与本次规划目标重叠且该线注明“定稿合入后须再重建并追加登记”——P1 处于两线交接未完成态，本线不接管。P1 前端接排修正（四标签合并 + 通信作者星号移位）待与精修线版本/交接对齐后另行执行。

### 12.3 abstract.md 机器锚点说明

- abstract.md 的 `## 中文摘要` 机器锚点结构**保持不变**。manifest 抽取器（`tools/paper.py` submission 抽取）依赖该锚点从 abstract.md 提取中英文摘要与关键词；投稿面渲染已由 paper.md 侧修正为接排。两层格式分工明确：**abstract.md 供机器抽取（结构锚点稳定），paper.md 供投稿渲染（接排呈现）**，互不取代。

---

*GC-2026-1112-05。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B3/PF-B10/PF-B11/PF-B12/PF-B13/PF-B14；写作依据 governance/writing.md PF-W11/PF-W12；版本依据 governance/versions.md PF-V1/PF-V3；规则版本 0.3.0；前置分析 temp/template-analysis-20261112/。*
