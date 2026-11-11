# 治理变更记录 GC-2026-1111-02：论文排版规范升级（角色化版式 profile + 目标刊 venue profile + 落地校验）

- 日期：2026-11-11
- 编号：GC-2026-1111-02
- 类型：治理能力修订（版式 profile 由声明变为可执行；新增目标刊 L1 profile；构建期落地校验；写作规格机器可读化）
- 规则依据：AGENTS.md F9（治理变更纪律）、F5（治理任务由主会话或受派子代理执行）、F6（最小改动）；版式语义依据 governance/build.md PF-B3/PF-B10，新增 PF-B11–PF-B14；写作语义新增 PF-W11/PF-W12；审核语义新增 PF-RV7。
- 前置分析：`temp/GC-2026-1111-02/layout-standards-analysis.md`（业内规范基线、现状取证、差距矩阵、F9 变更计划；已由未参与分析的独立子代理复核并按 M1–M10 修订）。
- 流程状态：本记录写入磁盘（**未提交**）。按 F9，提交前须由未参与变更的独立子代理复核实际 diff 与验证结果；第一轮独立复核已完成（意见与处置见第 10 节），**第二轮独立复核尚未完成**（第 10.1 节末）。

---

## 1. 基线（Baseline）与计划版本

- **rules_version**：0.1.0 → **0.2.0**。同步于 `project.yaml`、`governance/rule-index.yaml` 及 P1–P7 的 `paper.yaml`。理由：新增 PF-B11–PF-B14、PF-W11–PF-W12、PF-RV7 共 7 条规则正文，并修订 PF-B3/PF-B10 语义。
- **git 基线**：治理仓已有提交 `a63b477`（GC-2026-1111-01 能力管线修订）。`git status` 中的其余 modified 文件属 GC-2026-1111-01（SemVer 化）与 GC-2026-1111-03（精修模式）的未提交改动，不属本变更。
- **与并发变更的边界**：本变更实施期间，同一工作区有另一条并发治理线在写 **GC-2026-1111-03（精修模式，`governance/polish.md`，PF-PL1–PL13）** 与 **GC-2026-1111-01-S（SemVer 与构建路径补记，`governance/changes/2026-11-11-semver-buildpath-supplement.md`）**。**文件级重叠**：`governance/rule-index.yaml`、`project.yaml`、`governance/build.md`、`schemas/paper.schema.json`、`templates/paper/paper.yaml`、`AGENTS.md`、`templates/paper/terms.md`、`templates/paper/reviews/README.md`。**因此提交必须按 hunk 拆分，不能按文件拆分**（见第 7 节）。
- **论文侧基线**（各篇 git HEAD 实测）：`paper.yaml.layout_profile` 均为 `draft`；`build/layout.yaml` 中 **P2/P4/P5/P6/P7 共 5 篇**不通过 layout schema 校验（用 `layout_profile`/`paper_id`/`paper_version` 而非 `profile`/`kind`）；`writing-spec.yaml` **P1/P2/P3 共 3 篇因散文头与 `##` 标题行而无法被 `yaml.safe_load` 解析**，P4–P7 可解析但 `keywords_separator` 缺全角值。

---

## 2. 问题陈述（本次变更要解决什么）

| # | 问题 | 取证 |
|---|---|---|
| P1 | **版式 profile 是声明，不是实现** | 已发布 P1/P2/P3 产物的 docx 相对 pandoc 出厂 `reference.docx` 恰有 3 处差异（字面 `eastAsia="新宋体"`、`w:line="360" lineRule="auto"`、显式 A4/1440 边距），与 `draft.yaml` 声明值一一对应 ⇒ 落地曾经可用；但**生成该 reference docx 的实现未随仓留存**，当前 `tools/paper.py` 的 pandoc 调用不带 `--reference-doc`，且 `registry.yaml` 无消费方 |
| P2 | **仓内构建路径是静默降级的回退路径** | 当前 `tools/paper.py` 产出的 P3 `output/REL-*/paper.docx` 为**纯出厂指纹**（无字面字体、无行距、无 `pgSz/pgMar`）——重建会丢掉 A4、边距、1.5 倍行距、中文字体四项 |
| P3 | **schema 无强制点** | `additionalProperties: false` 的设计意图是"未知键构建失败"，但无任何构建步骤读取 schema；P2/P4/P5/P6/P7 共 **5 篇** layout.yaml 实际违规而无人发现 |
| P4 | **schema 表达力与学术排版模型不匹配** | 现有 `typography` 只有"正文一个尺寸 + 一个行距"；题名/作者/单位/摘要/各级标题/图表题/表体/公式/参考文献/脚注/页码**无角色建模**，无法表达任何一个真实刊物的版式 |
| P5 | **目标刊规范从未落进治理** | P1–P7 的 `target_venue` 全部为《数智技术研究与应用》，但该刊的 20 条格式要求（S1–S20）无一进入 profile 或写作规则 |
| P6 | **产物版式全项偏离中文期刊惯例** | 标题层级为蓝色 `#0F4761`、20/16/14pt；主标题 28pt；**无页码**（无 header/footer 部件）；**无首行缩进**；**无表格级边框**（`Table` 样式仅在表头行下画一条单线，非三线表）；段后 10pt 空隙 |
| P7 | **写作规格文件不可解析，目标刊约束整体失效** | `templates/paper/writing-spec.yaml` 与七篇论文的同名文件均以散文头 + `##` 标题行组织，**不是合法 YAML**；`tools/paper.py` 以 `yaml.safe_load` 读取并吞掉异常 ⇒ 七篇论文的目标刊约束（含 350 字摘要、分号分隔、标题 20 字等）**全部被静默丢弃** |
| P8 | **摘要约束量纲错误** | 模板按英文**词数** 200/300 约束中文摘要；目标刊按**汉字数 350**。P1 实测 306 字被模板判为超限 |
| P9 | **产物字体与期刊要求不符** | 旧 PDF 字体为 NSimSun / NotoSerifCJKsc / NotoSansCJKsc / LiberationSerif，**无 Times New Roman、无黑体、无楷体、无仿宋** |

---

## 3. 精确变更清单（逐文件）

### 3.1 治理仓 `instruction.git`

| # | 文件 | 类型 | 内容 | 归属 |
|---|---|---|---|---|
| 1 | `schemas/layout-profile.schema.json` | 修改 | 由扁平 typography 扩展为角色化模型：`typography.fonts`（分域分角色）、`typography.sizes`（**24 个角色字号**）、`typography.paragraph`（首行缩进/段前段后/对齐/行距模式）、`typography.heading_numbering`（层级/序号格式/顶格/间距）；新增 `figures`/`tables`/`references`/`pagination`/`punctuation`/`author_bio_layout`；`citation`/`formulas` 扩展子键。**原有 4 个 typography 键与 `page` 的 `size`/`margin` 全部保留**，新键全部可选。`page` **未**扩展 columns/text_block（未实现） | GC-02 |
| 2 | `templates/layout/profiles/draft.yaml` | 修改 | L0 草案档：保留原有 4 个 typography 键与 page 值，追加角色表、段落几何、标题编号、图表/公式/引用/页码/标点分域，逐项标注来源等级 | GC-02 |
| 3 | `templates/layout/profiles/gbt7713-2-2022.yaml` | **新建** | L1 国标基线档（GB/T 7713.2-2022 附录 B 表 B.1 角色表 + CY/T 170-2019 三线表 + GB/T 3179-2009 页码页眉） | GC-02 |
| 4 | `templates/layout/profiles/stie.yaml` | **新建** | L1 目标刊档：《数智技术研究与应用》专刊。**版式相关 9 条落 profile**（S8 标题序号、S9 公式可编辑、S10 四类字体、S11 先文字后图表、S13/S14/S16 引用制式、S15 文后排序、S17 作者简介）；**写作级 11 条落 `writing-spec.yaml`**（S1–S7、S12、S18–S20）。每值带来源等级标记 `[S#]`/`[GB]`/`[CY]`/`[JT]`/`[TD]` | GC-02 |
| 5 | `templates/layout/registry.yaml` | 修改 | 登记 `draft`(L0)/`gbt7713-2-2022`(L1)/`stie`(L1)，每条带 `refdoc` 路径；写明"refdoc 缺失即构建失败，禁止静默回退 pandoc 默认" | GC-02 |
| 6 | `templates/layout/refdoc/{draft,gbt7713-2-2022,stie}.docx` | **新建** | 由 `tools/make_refdoc.py` 生成的 reference docx（单一真值源，禁止手改）。**注**：`gbt7713-2-2022.docx` 与 `stie.docx` 目前字节相同——两 profile 的差异在 `heading_numbering` 与 `references.order`，不影响 refdoc 可渲染部分（见第 9 节开放项 11） | GC-02 |
| 7 | `tools/layoutlib.py` | **新建** | profile 解析与合并库：registry 解析、L0→L1→L2 键级合并与覆写日志、逐层 schema 校验、L2 边界检查（仅 `profile`/`kind`/`typography`）、refdoc 路径解析（缺失即报错）、角色视图扁平化（含 PF-B10 回落） | GC-02 |
| 8 | `tools/make_refdoc.py` | **新建** | profile → reference docx 生成器。**纯标准库实现**（直接改写 OOXML），因 `python-docx`/`lxml` 位于用户 site-packages、`python3 -I` 下不可用（见第 5 节备选 4） | GC-02 |
| 9 | `tools/paper.py` | 修改 | `cmd_build_docx` 接入 profile 解析 + `--reference-doc` + 覆写日志 + 构建期落地断言；新增 `_assert_layout_landing`（含行距/拉丁字体/页眉页脚 XML 良构/角色覆盖检查）、`_inject_paper_title_header`（**XML 转义**）、`_expected_pdf_fonts`/`_font_present`（PDF 字体核对）；`_load_paper_yaml` 解析失败改为报错；`cmd_build_pdf` 修复双 JSON 输出与 `pdf_fonts` 未定义 | GC-02 |
| 10 | `tools/verify_layout.py` | **新建** | 可复跑验证脚本（16 项）：schema 正/反向校验、refdoc 幂等、**断言负例**（改坏产物必须失败）、标题 XML 转义、L2 边界、writing-spec 解析 | GC-02 |
| 11 | `governance/build.md` | 修改 | 新增 **PF-B11 版式实现载体**、**PF-B12 版式落地校验**、**PF-B13 L2 覆盖边界**、**PF-B14 版式数值来源等级**；修订 **PF-B3**（结构身份键清单改为 `page`/`citation`/`formulas`/`target_venue`，`profile`/`kind` 归为选择键）与 **PF-B10**（补 L2 合并边界一句） | GC-02 |
| 12 | `governance/writing.md` | 修改 | 新增 **PF-W11 目标刊格式约束**、**PF-W12 目标刊优先** | GC-02 |
| 13 | `governance/review.md` | 修改 | 新增 **PF-RV7 目标刊格式合规复核** | GC-02 |
| 14 | `governance/rule-index.yaml` | 修改 | 登记 PF-B11–PF-B14、PF-W11–PF-W12、PF-RV7；`rules_version` → 0.2.0。（同文件另含 GC-03 的 PF-PL1–PL13 条目） | GC-02 + GC-03 |
| 15 | `project.yaml` | 修改 | `rules_version` → 0.2.0 | GC-02 |
| 16 | `templates/paper/paper.yaml` | 修改 | `layout_profile: draft` → `stie`；第 7 章标题 `Conclusion` → `结语`（目标刊 S12） | GC-02 |
| 17 | `templates/paper/build/layout.yaml` | 修改 | L2 只保留选择键 `profile`/`kind`；**移除**原先重复声明的结构身份键 `page`（与 PF-B3 冲突）；`profile` → `stie` | GC-02 |
| 18 | `templates/paper/writing-spec.yaml` | 重写 | 改为**合法 YAML**；删除量纲错误的 `abstract_max_words`/`abstract_min_words`，改为 `abstract_target_chars` + `abstract_tolerance_pct`；新增目标刊约束键；散文说明移入 `notes:` 块标量 | GC-02 |
| 19 | `schemas/paper.schema.json` | 修改 | 新增 `title_en`（双语论文必需，GC-2026-1111-01 开放项 3）。**同文件另含 GC-01-S 的两项语义变更**（`paper_type` 枚举增 `design_science`、`papers[].number` minimum 1→0），归 GC-01-S | GC-02 + GC-01-S |
| 20 | `governance/changes/2026-11-11-layout-standards.md` | **新建** | 本记录 | GC-02 |

### 3.2 论文工作区 `papers/`（各篇独立仓）

| # | 范围 | 变更 | 归属 |
|---|---|---|---|
| 21 | P1–P7 `paper.yaml` | `layout_profile: draft` → `stie`；`rules_version` → 0.2.0 | GC-02 |
| 22 | P1–P7 `build/layout.yaml` | 统一为 `profile: stie` + `kind: paper`（移除结构身份键 `page`），**修复 P2/P4/P5/P6/P7 不通过 schema 的缺陷** | GC-02 |
| 23 | P1–P7 `writing-spec.yaml` | 补齐目标刊约束键；**修复不可解析**（散文头与 `##` 标题行改注释、散文归入 `notes:` 块标量）；**修正并发中间稿引入的重复键 `min_chars`**（保留首现的 15000）与 **`keywords_separator` 转义值**（`\"；\"` → `；`） | GC-02 |

### 3.3 未改动（属其他变更）

`AGENTS.md`、`SKELETON-PLAN.md`、`governance/versions.md`、`governance/changes/2026-11-11-capability-pipeline.md`、`governance/changes/2026-11-11-semver-buildpath-supplement.md`、`governance/changes/2026-11-11-polish-mode.md`、`governance/polish.md`、`templates/paper/terms.md`、`templates/paper/reviews/README.md`、`templates/paper/.gitignore` —— 分别属 GC-2026-1111-01 / GC-01-S / GC-03，本变更未触碰其语义。

---

## 4. 理由（Rationale）

- 第 2 节的九项问题全部由实测取证得出；取证过程与逐项数据见 `temp/GC-2026-1111-02/layout-standards-analysis.md` §2、§5.6。
- 目标刊规范来源：该刊征稿启事格式要求全文（2026-11-11 用户提供，S1–S20）。该刊**未规定任何字号、字体、页边距、行距、页码、图题字号、三线表线宽**，这些一律回落到 GB/T 7713.2-2022 附录 B 表 B.1、CY/T 170-2019、GB/T 3179-2009 与期刊模板实测值，并在 profile 中以来源等级标注，**不得表述为"期刊要求"**。
- 独立复核的 M1 修正了首版分析的因果误判：profile 落地**曾经可用**（产物证据），问题不是"从未实现"，而是"实现未入库 + 当前路径会静默降级"。据此，载体设计改为**重建并入库该链路**，并新增针对降级的断言与负例测试。

---

## 5. 备选方案（Alternatives）

| # | 方案 | 结论 |
|---|---|---|
| 1 | 仅扩 schema，不改工具与模板 | ❌ 拒绝：profile 仍无消费点，等于把注释写得更精细 |
| 2 | 仅交付 LaTeX 链路（XeLaTeX + ctex） | ⚠️ 保留：版式保真度最高，但本机 `xelatex`/`latexmk` **均未安装**，且投稿交付形态仍需 docx → 列为开放项 |
| 3 | 只改 `typography` 扁平键（`title_pt`/`heading1_pt`…） | ❌ 拒绝：无法表达"字体-字号配对"，键数量膨胀 |
| 4 | 引入 python-docx 直接生成 docx | ❌ 拒绝：**`python-docx` 位于用户 site-packages，`python3 -I` 下不可用**；项目工具链约定全程 `-I`（隔离模式），第三方依赖会使工具链不可复现。改为**标准库直接改写 OOXML** |
| 5 | 一次性覆盖全部国际 venue profile | ❌ 拒绝：目标刊已确定为《数智技术研究与应用》，先立该刊 profile + 留扩展位 |
| 6 | 直接套用期刊官方 Word 模板 | ⚠️ **优先级最高但当前不可得**：作者中心"下载中心"需登录会话，本轮未取得任何官方模板。取得后，profile 的"本刊未规定项"以实测值覆盖，**profile 结构不变、只换数值来源** |
| 7 | 手工维护 reference docx | ❌ 拒绝：profile 与 refdoc 两处真值必然漂移。生成器为必选项 |

---

## 6. 风险（Risks）与处置

| # | 风险 | 处置 |
|---|---|---|
| R-a | **重建回归**：用当前 `tools/paper.py` 重建会丢掉已落地的 A4、边距、1.5 倍行距、中文字体 | 构建期断言逐项检查；`tools/verify_layout.py` 的 D 组**负例**证明：删掉行距→`docdefault_line_240`/`normal_line_240` 失败、删掉幅面→`page_*_twips` 失败、改边距→`margin_top_twips` 失败、换中文字体→`normal_east_asia_font` 失败 |
| R-b | 构建输入通配：`body/*.md` 会把 `paper.md`/`README.md` 与分章文件一并纳入 | 构建改为只取 PF-B2 权威源 `body/paper.md`；断言产物中不出现 README 标记文本 |
| R-c | PDF 转换的字体替换 | manifest 记录 `pdf_fonts_embedded`、**`pdf_fonts_expected`**、**`pdf_fonts_missing`**；缺失即写入 `limitations`。本机实测 **missing = []**（宋体/黑体/楷体/仿宋/Times New Roman 全部真实落位） |
| R-d | `writing-spec.yaml` 修复可能改变论文侧既有语义 | 转换器只做语法修复（注释散文、去重复键、去转义），不改任何 venue 字段取值；逐篇比对转换前后字段值并复跑解析 |
| R-e | rules_version bump 使论文侧绑定悬空 | 七篇 `paper.yaml.rules_version` 同步至 0.2.0 |
| R-f | 本刊"未规定项"的取值与编辑部最终模板不一致 | 全部以 `source_level` 标注；取得官方模板后以实测值覆盖（备选 6） |
| R-g | 公式粗斜体/粗正体（S10）在 docx 落地保真度不足 | 构建断言记录 OMML 计数；无法保真时在 manifest 显式声明 limitation，**不得静默** |
| R-h | 与并发变更 GC-03 / GC-01-S 文件重叠 | 按**hunk** 而非按文件分拆提交（第 7 节） |
| R-i | 题名含 `&`/`<`/`>` 时页眉 XML 畸形 | `_xml_escape_text` 转义 + 页眉部件 XML 良构性断言（verify_layout.py E 组实测） |
| R-j | **profile 角色定义了但产物中未被使用**（如摘要正文实际走 `FirstParagraph`→`BodyText`→`Normal`，未用 `Abstract` 样式） | 构建记录 `role_style_coverage` 与 `role_styles_unused_limitation`，使该缺口**可见、可复核**，而不是沉默（见第 9 节开放项 10） |

---

## 7. 恢复方式（Recovery）

- 前置条件：**先单独提交 GC-2026-1111-01（含 GC-01-S）与 GC-2026-1111-03，再以独立提交落 GC-2026-1111-02**。
- **提交拆分粒度**：`governance/rule-index.yaml`、`project.yaml`、`governance/build.md`、`schemas/paper.schema.json`、`templates/paper/paper.yaml` 五个文件内含两组变更编号的 hunk，**必须按 hunk 拆分**；按文件拆分会把两组变更混进同一提交，破坏第 1 节声明的边界。
- 恢复方式：对 GC-2026-1111-02 的独立提交执行 `git revert`（单提交、不改写历史，符合 F7）。新增文件（3 个 profile、3 个 refdoc、`tools/layoutlib.py`、`tools/make_refdoc.py`、`tools/verify_layout.py`、本记录）随 revert 移除。
- 论文工作区不回滚（保留现场，F7）；论文侧修复（layout.yaml、writing-spec.yaml、paper.yaml）为独立仓的独立提交，可单独 revert。

---

## 8. 验证方法（Verification）与实际结果

**统一复跑入口**：`python3 -I tools/verify_layout.py`（16 项检查，退出码 0 即全通过）。以下为 2026-11-11 20:2x 实测输出。

| # | 方法 | 实际结果 |
|---|---|---|
| A | **schema 正向校验**：3 个 profile + 模板 `build/layout.yaml` + 七篇论文 `build/layout.yaml` 对新 schema | **11 targets, 0 failed** |
| B | **schema 反向校验**：新增 profile 对改前基线 schema 应 FAIL | `stie.yaml` 1 errors、`gbt7713-2-2022.yaml` 1 errors —— **符合预期**（新键真实生效） |
| C | **refdoc 生成器幂等 + 自检** | 3 profile `in_sync=True`、`self_check=True`（题名 18pt / 一级标题 12pt / 首行缩进 2.0 / A4 / 边距 25.4×4 / 无蓝字 / 三线表 / 页码域 / 页眉占位全 true） |
| D | **断言负例**（改坏产物必须失败） | 删行距→`docdefault_line_240`+`normal_line_240`；删幅面→`page_width_twips`+`page_height_twips`；改边距→`margin_top_twips`；换中文字体→`normal_east_asia_font`；**未改动产物 → 0 failures** |
| E | **标题 XML 转义**（`A & B <研究> "x" \z`） | 页眉部件 **well-formed** |
| F | **L2 边界** | `page`/`citation` 拒绝；`tables`/`pagination` 拒绝（PF-B13）；`profile`/`kind`/`typography` 放行 |
| G | **writing-spec 解析与目标刊约束** | **7 papers, 0 problems** |
| 1 | **端到端构建**：`paper.py build docx --paper P1` | `status: ok`，`layout_profile: stie`，**`layout_assertions: pass`**，覆写日志 **16 条**，产物 `build/v0.4.0/*.docx` |
| 2 | **产物 OOXML 逐项核对**（P1 新产物） | docDefaults：Times New Roman + 宋体、`sz 21`(10.5pt)、`line=360`(1.5×)、段前后 0；Normal：`firstLineChars=200` + `firstLine=420`、两端对齐；Title：黑体 `sz 36`(18pt) 居中 黑色；Author：楷体 `sz 24`(12pt) 居中；Heading1：黑体 `sz 24`(12pt) 左对齐；Heading2：黑体 `sz 21`(10.5pt)；Abstract：仿宋 `sz 18`(9pt)；Bibliography：宋体 `sz 18`(9pt) + 悬挂缩进 420；Caption：黑体 `sz 18`(9pt) 居中；sectPr：A4 11906×16838 + 四边 1440 twips + header/footer 引用；**蓝字残留 0**。**注意**：`Abstract`/`Bibliography`/`Caption`/`TableCaption` 四个样式虽定义正确，但在产物中**使用次数为 0**（实测 `ImageCaption` 3 次，其余段落走 `FirstParagraph`×33 / `BodyText`×38）→ 见第 9 节开放项 10 |
| 3 | **PDF 落位字体** | **SimSun / SimHei / KaiTi / FangSong / TimesNewRomanPSMT / BoldMT / ItalicMT** 均已嵌入；manifest `pdf_fonts_expected` 7 项、`pdf_fonts_missing` **[]**（对照旧 v0.3.1 产物：无 Times New Roman、无黑体、无楷体、无仿宋） |
| 4 | **PDF 页面装饰** | 23 页，`pdftotext` 逐页末行 = 1..23，页脚居中页码 |
| 5 | **视觉验收**（PF-B6） | 首页：页眉题名居中、题名黑体 18pt、作者楷体 12pt、单位宋体 9pt、摘要黑体标签、正文首行缩进 2 字符、1.5 倍行距、页码居中、无蓝字；第 8 页：**三线表**（顶线 1.0pt / 表头线 0.5pt / 底线 1.0pt、无竖线）、编号标题「4.3 三个检测器」黑体顶格。**表题未居中**——产物中表题为 `BodyText`（左对齐、继承首行缩进），非 `TableCaption` 样式 → 见第 9 节开放项 10 |
| 6 | **回归**：`paper.py check --paper <P1..P7>` | 论文侧基线（各篇 GC-02 前 commit）为 **7/7 fail**；现态 **6/7 pass，仅 P6 body_chapters fail** ⇒ **不新增失败项**成立 |
| 7 | **独立验证** | 已由未参与变更的独立子代理复核一轮；意见与处置见第 10 节 |

---

## 9. 开放项（Open Items）

1. **编辑部官方 Word 模板未取得**（作者中心需登录）。取得后以实测值替换 profile 中"本刊未规定项"（字号、页边距、页码、三线表线宽），profile 结构不变。
2. **摘要/英文摘要标签的样式载体**：pandoc 的 docx writer 不输出 `AbstractTitle`（`abstract` 元数据只产出 `Abstract` 样式），也不支持 `custom-style` run 级格式。因此正文用 `# 摘要` 时该标签走 `Heading1`（黑体 12pt），与"小五黑体标签"有差；且 `affiliation` 元数据在 docx 中不被输出，作者与单位只能分两段（作者行 `Author` 12pt 楷体 / 单位行 `Subtitle` 9pt 宋体），与目标刊"同段内联"形态不同。**记为工具链限制**，非 profile 缺陷。
3. **公式粗斜体/粗正体（S10）保真度**：pandoc 的 MathML→OMML 不区分语义类别，需在公式源码中显式 `\mathbf`/`\boldsymbol`；当前构建记录 OMML 计数与 limitation，未逐类校验。
4. **标题编号由正文承担**：pandoc 不自动编号；目标刊的 `1、1.1、1.1.1、（1）、①` 序列现由 `body/paper.md` 的标题文本自带（P1 实测 `# 1 引言` / `## 2.1 …`），profile 记录该约定但不强制生成。
5. **`citation.style` / `formulas.renderer` 仍无可执行实现**：标引引擎与公式渲染器未落地，著者出版年制的正文引用改写属论文侧工作。
6. **第 7 章标题**：论文侧仍为三种写法（"结论与后续工作"/"结论与后续"/"结语"）；模板已改为"结语"，论文侧统一属论文侧复核项（PF-RV7）。
7. **题名与摘要不合规项**（题名 3/7 超 20 字、P2 含标点、4/7 摘要用"本文"主语、P1 摘要偏短）属论文侧内容修复，本变更不代改。英文摘要与关键词行经本变更修复后已 7/7 齐备。
8. **LaTeX 链路**（备选 2）未评估。
9. **`writing-spec.yaml` 模板与论文侧键集合双向不齐**：模板缺 `promotion`/`quality_requirements`/`review_service`（P1–P3 有）；P4–P7 缺 `manuscript_types`/`special_requirements`（模板有）。需按 PF-W11 收敛为单一真值源。
10. **profile 角色在产物中的实际生效情况**：构建现记录 `role_style_coverage`，实测 `Abstract`/`Bibliography`/`Caption`/`TableCaption` **零使用**——即摘要正文实际以宋体 10.5pt 排出（非仿宋 9pt）、表题为 `BodyText` 左对齐（非居中）。根治需论文侧改用 pandoc 的 `abstract:` 元数据与表格题注语法；在此之前该差距由 manifest 显式记录（不沉默）。
11. **两个 L1 profile 的 refdoc 字节相同**：`gbt7713-2-2022.docx` 与 `stie.docx` 当前完全一致，因为两者差异（`heading_numbering` 层级与 `references.order`）不体现在 refdoc 可渲染部分。语义上仍是有区别的 profile，但版式上无区分度。
12. **PF-W11 / PF-RV7 当前无机械执行点**：`writing-spec.yaml` 的目标刊约束键（题名字数、摘要字数、关键词分隔符等）尚无自动校验实现，PF-RV7 为纯文本规则。构建期只校验版式类项。
13. **`gbt7713-2-2022` 是否保留**：其角色表已被 `draft` 承载、`stie` 覆盖版式项，是否降级为"L0 角色表 + L1 delta"待定。
14. **结构化 provenance 未实现**：profile 的来源等级目前以注释 + 等级缩写词表落地（`[S#]`/`[GB]`/`[CY]`/`[JT]`/`[TD]`），未落为 schema 的键级结构化登记。

---

## 10. 复核与修订记录（Round 1）

按 F9，本变更在写入治理文件前由一名**未参与实施**的独立子代理做了对抗性复核（166 次工具调用）。其提出的阻塞项与本记录的处置：

| 复核意见 | 核实 | 处置 |
|---|---|---|
| 变更记录 §3.1 项 1 描述含未实现的 `provenance`/`source_level` 与 `page` 扩展，`sizes` 键数写成 16 | ✅ 成立 | §3.1 项 1 已改为 24 键并删除未实现项；结构化 provenance 列入开放项 14 |
| §3.1 项 4 称"S1–S20 逐条落为 profile 键" | ✅ 成立 | 已改为"版式 9 条落 profile、写作级 11 条落 writing-spec.yaml" |
| §8 覆写日志写作 17 条 | ✅ 成立 | 实为 **16 条**，已更正 |
| §8 #10 "修复前 4 篇解析失败、3 篇重复键、7 篇分隔符含转义" | ⚠️ 方向颠倒 | 基线（各篇 git HEAD）实为 **3 篇解析失败（P1/P2/P3）、0 篇重复键**；重复键与转义是并发中间稿引入、本变更就地修正的。§3.2 项 23 与 §8 已按真实序列改写 |
| `_inject_paper_title_header` 未做 XML 转义 | ✅ 成立 | 已修（`_xml_escape_text`）+ 页眉部件 XML 良构性断言 + verify_layout.py E 组 |
| 断言不覆盖行距丢失（假阴性） | ✅ 成立 | 已补 `docdefault_line_240`/`normal_line_240` 断言 + D 组负例 |
| 断言不检查拉丁字体族 | ✅ 成立 | 已补 `normal_latin_font`/`normal_latin_font_hAnsi` |
| PF-B12 字体替换条款只记录不比对 | ✅ 成立 | 已实现 `pdf_fonts_expected`/`pdf_fonts_missing` 并写入 limitations；PF-B12 条款同步改写为与实现一致 |
| `check_l2_overrides` 比 PF-B13 宽（venue 域可被 L2 覆写） | ✅ 成立 | 已收紧为仅 `profile`/`kind`/`typography`；PF-B13 与实现一致 |
| PF-B3 结构身份键清单与实现冲突 | ✅ 成立 | PF-B3 已改；PF-B10 补 L2 边界一句 |
| §8 #6/#9 称 Abstract/Bibliography/Caption 生效、表题居中 | ✅ 成立（样式定义对但未使用） | §8 已注明"使用次数 0"，并列入开放项 10；构建新增 `role_style_coverage` 记录 |
| §8 #2 反向校验计数 | ⚠️ 口径不一 | 统一以 `verify_layout.py` 的基线定义（当前 schema 去掉新键）为准：stie/gbt 各 1 errors |
| §8 #11 回归基线未固化 | ✅ 成立 | §8 #6 已写入真实基线（7/7 fail → 现 6/7 pass）；并由 verify_layout.py 固化 |
| §9 项 6/7/8 与现状不符 | ✅ 成立 | 已更正（三种章名；英文摘要关键词行已齐备；删除"materials.yaml 解析失败"） |
| 并发变更边界声明文件集不全、分拆不可执行 | ✅ 成立 | §1 已补全重叠文件清单；§7 已明确**按 hunk 拆分** |
| `cmd_build_pdf` 双 JSON 输出、`pdf_fonts` NameError | ✅ 成立 | 已修 |
| `_load_paper_yaml` 解析失败静默回落 draft | ✅ 成立 | 已改为报错 |
| `schemas/paper.schema.json` 的 `paper_type`/`number` 语义变更未登记 | ✅ 成立 | §3.1 项 19 已标注归属 GC-01-S |

复核结论：实现层经独立复跑全部复现，未发现伪造结果；阻塞项集中在变更记录与实际 diff 的对应关系与两处实现缺陷，均已处置。**再次独立复核后方可提交。**

### 10.1 第二轮复核（修订后）

第一轮意见的修订完成后，逐条复跑与复查的结果：

| 复核项 | 结果 |
|---|---|
| 变更记录 §8/§9/§10 的数字与描述 | 已按实测改写（16 条覆写日志；3 篇基线解析失败；角色样式零使用；表题未居中；章名三种；英文摘要关键词行已齐备） |
| 标题 XML 转义 | 已修；实测注入 `A & B <研究> "x" \z` 后页眉部件 XML 良构 |
| 行距断言 | 已补 `docdefault_line_240` / `normal_line_240`；**并修正一处潜在假阳性**：若 `Normal` 样式自身不带 `w:spacing`（继承 docDefaults），断言改为回落到 docDefaults 取值，仅当两者皆无时报失败 |
| 拉丁字体断言 | 已补 `normal_latin_font` / `normal_latin_font_hAnsi` |
| PF-B12 字体替换条款 | 已实现：`pdf_fonts_expected` 7 项、`pdf_fonts_missing` **[]**；实测 7 个 profile 字体全部判为存在，4 个对照字体（Arial / Helvetica / SimKai / Courier New）全部判为不存在 |
| L2 边界收紧 | 已收紧为仅 `profile`/`kind`/`typography`；`page`/`citation`/`tables`/`pagination` 均被拒，合法形式放行 |
| PF-B3 / PF-B10 条款 | 已修订（结构身份键清单与实现一致；PF-B10 补 L2 边界一句） |
| `cmd_build_pdf` 双 JSON 与 `pdf_fonts` 未定义 | 已修 |
| `paper.yaml` 畸形时的静默回落 | 已改为报错；实测畸形 `paper.yaml` 返回干净 JSON 错误（`stage: pre-build`），不再回落到 draft 档、不再抛栈 |
| 回归基线固化 | `tools/verify_layout.py` 固化 16 项检查；D 组负例证明断言对"丢行距/丢幅面/改边距/换中文字体"均会失败 |
| 新增静默降级路径 | 未发现。registry 缺项、refdoc 缺失、L2 越界、L2 与 `paper.yaml.layout_profile` 不一致、profile 解析失败、paper.yaml 畸形——均为显式失败 |

**尚缺**：F9 要求的**第二次独立复核**尚未完成——派出的第二轮独立子代理因用量上限中止，第二轮复查由本会话执行（上述表格）。**提交前仍需一次未参与者的独立复核**。

---

*GC-2026-1111-02。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B3/PF-B10/PF-B11–PF-B14；验证入口 tools/verify_layout.py。*
