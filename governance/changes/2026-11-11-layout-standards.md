# 治理变更记录 GC-2026-1111-02：论文排版规范升级（角色化版式 profile + 目标刊 venue profile + 落地校验）

- 日期：2026-11-11
- 编号：GC-2026-1111-02
- 类型：治理能力修订（版式 profile 由声明变为可执行；新增目标刊 L1 profile；构建期落地校验；写作规格机器可读化）
- 规则依据：AGENTS.md F9（治理变更纪律）、F5（治理任务由主会话或受派子代理执行）、F6（最小改动）；版式语义依据 governance/build.md PF-B3/PF-B10，新增 PF-B11–PF-B14；写作语义新增 PF-W11/PF-W12；审核语义新增 PF-RV7。
- 前置分析：`temp/GC-2026-1111-02/layout-standards-analysis.md`（业内规范基线、现状取证、差距矩阵、F9 变更计划；已由未参与分析的独立子代理复核并按 M1–M10 修订）。
- 流程状态：**已提交**。治理仓提交 `fc09407`（2026-11-11 22:31）一次性提交了 GC-2026-1111-01-S / GC-02 / GC-03 三个变更号；论文侧 P1 提交 `bf4e471`。
- 复核状态：第一轮独立复核（分析阶段）已完成；**两轮独立复核（实施阶段）已完成**——Codex-Team（代码）与 Codex-Plus（文档）各出一份报告，其发现与处置见**第 11 节**；其中若干缺陷已在本轮后续修订中修复（见第 12 节）。

---

## 1. 基线（Baseline）与计划版本

- **rules_version**：0.1.0 → **0.2.0**。同步于 `project.yaml`、`governance/rule-index.yaml` 及 P1–P7 的 `paper.yaml`。理由：新增 PF-B11–PF-B14、PF-W11–PF-W12、PF-RV7 共 7 条规则正文，并修订 PF-B3/PF-B10 语义。
- **git 基线**：治理仓 `a63b477`（GC-2026-1111-01 能力管线修订）；本变更与其后的 GC-01-S / GC-03 一并落在提交 `fc09407` 中（22:31）。
- **提交粒度（事实）**：`fc09407` 是**混号单提交**——其提交说明自陈理由为"三个变更在同一批文件内交错，按文件粒度无法干净拆分，故以单治理提交 + 单 revert 作为恢复方式"。本记录第 7 节原先写的"必须按 hunk 拆分"因此**与实际做法不符，已按事实改写**（第 7 节）。
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

- **实际提交状态**：治理仓为**混号单提交** `fc09407`（GC-01-S + GC-02 + GC-03），因三个变更在同一批文件内交错，按文件粒度无法干净拆分；`fc09407` 的提交说明已自陈此点。论文侧 P1 为 `bf4e471`（提交标题含 `GC-2026-1111-02/03` 混号）。
- **恢复方式（按事实）**：`git revert fc09407` 将**连带回滚 GC-01-S（SemVer 化 / PF-B7 路径）与 GC-03（精修模式 13 条规则）**，不能只回滚 GC-02。若需只回滚 GC-02，须用 `git revert --no-commit fc09407` 后按 hunk 手工挑选逆选。治理仓工作树当前干净。
- 论文侧 P1/P2/P3 的提交标题含 `GC-2026-1111-02/03` 混号（P1 的 GC-02 改动与精修改动同处一次提交），**同样无法单独 revert**；P4–P7 的 GC-02 改动分别落在其各自的正文提交中，同样不可单独回滚。**如实记录**：本变更的恢复粒度实际是"治理仓一次 revert + 论文仓按篇人工处理"。
- 论文工作区不做整体回滚（保留现场，F7）。

---

## 8. 验证方法（Verification）与实际结果

**统一复跑入口**：`python3 -I tools/verify_layout.py`（**21 项检查**，退出码 0 即全通过）。下表为初版（20:2x）实测；**扩充后的 21 项结果见第 12.1 节**。

| # | 方法 | 实际结果 |
|---|---|---|
| A | **schema 正向校验**：3 个 profile + 模板 `build/layout.yaml` + 七篇论文 `build/layout.yaml` 对新 schema | **11 targets, 0 failed** |
| B | **schema 反向校验**：新增 profile 对改前基线 schema 应 FAIL | `stie.yaml` 1 errors、`gbt7713-2-2022.yaml` 1 errors —— **符合预期**（新键真实生效） |
| C | **refdoc 生成器幂等 + 自检** | 3 profile `in_sync=True`、`self_check=True`（题名 18pt / 一级标题 12pt / 首行缩进 2.0 / A4 / 边距 25.4×4 / 无蓝字 / 三线表 / 页码域 / 页眉占位全 true） |
| D | **断言负例**（改坏产物必须失败） | 初版 4 例（行距/幅面/边距/中文字体）；**第二轮后扩至 9 例**，新增缩进、网格表、`NUMPAGES`、页眉引用、小写蓝字 —— 见第 12.1 节 |
| E | **标题 XML 转义**（`A & B <研究> "x" \z`） | 页眉部件 **well-formed** |
| F | **L2 边界** | `page`/`citation` 拒绝；`tables`/`pagination` 拒绝（PF-B13）；`profile`/`kind`/`typography` 放行 |
| G | **writing-spec 解析与目标刊约束** | **7 papers, 0 problems** |
| 1 | **端到端构建**：`paper.py build docx --paper P1` | `status: ok`，`layout_profile: stie`，**`layout_assertions: pass`**，覆写日志 **16 条**，产物 `build/v0.4.0/*.docx` |
| 2 | **产物 OOXML 逐项核对**（P1 新产物） | docDefaults：Times New Roman + 宋体、`sz 21`(10.5pt)、`line=360`(1.5×)、段前后 0；Normal：`firstLineChars=200` + `firstLine=420`、两端对齐；Title：黑体 `sz 36`(18pt) 居中 黑色；Author：楷体 `sz 24`(12pt) 居中；Heading1：黑体 `sz 24`(12pt) 左对齐；Heading2：黑体 `sz 21`(10.5pt)；Abstract：仿宋 `sz 18`(9pt)；Bibliography：宋体 `sz 18`(9pt) + 悬挂缩进 420；Caption：黑体 `sz 18`(9pt) 居中；sectPr：A4 11906×16838 + 四边 1440 twips + header/footer 引用；**蓝字残留 0**。**注意**：`Abstract`/`Bibliography`/`Caption`/`TableCaption` 四个样式虽定义正确，但在产物中**使用次数为 0**（实测 `ImageCaption` 3 次，其余段落走 `FirstParagraph`×33 / `BodyText`×38）→ 见第 9 节开放项 10 |
| 3 | **PDF 落位字体** | **SimSun / SimHei / KaiTi / FangSong / TimesNewRomanPSMT / BoldMT / ItalicMT** 均已嵌入；manifest `pdf_fonts_expected` 7 项、`pdf_fonts_missing` **[]**（对照旧 v0.3.1 产物：无 Times New Roman、无黑体、无楷体、无仿宋） |
| 4 | **PDF 页面装饰** | 23 页，`pdftotext` 逐页末行 = 1..23，页脚居中页码 |
| 5 | **视觉验收**（PF-B6） | 首页：页眉题名居中、题名黑体 18pt、作者楷体 12pt、单位宋体 9pt、摘要黑体标签、正文首行缩进 2 字符、1.5 倍行距、页码居中、无蓝字；第 8 页：**三线表**（顶线 1.0pt / 表头线 0.5pt / 底线 1.0pt、无竖线）、编号标题「4.3 三个检测器」黑体顶格。**表题未居中**——产物中表题为 `BodyText`（左对齐、继承首行缩进），非 `TableCaption` 样式 → 见第 9 节开放项 10 |
| 6 | **回归**：`paper.py check --paper <P1..P7>` | 论文侧基线（各篇 GC-02 前 commit）为 **7/7 fail**（该基线失败由 GC-01-S 的 `^v` 版本号模式造成，非 GC-02 专属）；**现态 7/7 pass** ⇒ 不新增失败项成立 |
| 7 | **独立验证** | 已由未参与变更的独立子代理复核两轮（分析阶段一轮；实施阶段两轮：Codex-Team 代码、Codex-Plus 文档）。意见与处置见第 10–12 节 |

---

## 9. 开放项（Open Items）

> 本节在两轮独立复核后重写：删除已不成立的条目（PDF 字体、P6 materials.yaml、英文摘要缺失、回归 6/7），补入复核新发现的缺口，并按实际状态更正数值。

1. **编辑部官方 Word 模板未取得**（作者中心需登录）。取得后以实测值替换 profile 中"本刊未规定项"（字号、页边距、页码、三线表线宽），profile 结构不变。
2. **摘要/英文摘要标签的样式载体 —— 已澄清（复核更正）**：pandoc 3.9 **支持** `custom-style` 围栏 Div（`::: {custom-style="AbstractTitle"}`）并生成同名段落样式，**不是工具链限制**（本记录上一稿据此误判）。正文侧约定见"附二"。因此：`# 摘要` 的写法使该标签走 `Heading1`（黑体 12pt），而按约定标注时才得到"小五黑体标签"。作者与单位的"同段内联、单位小五宋体"仍**无对应样式**——`affiliation` 宏数据在 docx 中不被输出，`Subtitle` 承载的是**英文题名**，单位行只能落在 `BlockText`（正文 10.5pt 宋体）。
3. **profile → 产物的键级落地缺口**（复核新发现，须分两类处理）：
   - **(a) 生成器未实现**（真缺口，无断言覆盖）：`typography.paragraph.alignment`（生成器硬编码 `both`）、`paragraph.spacing_before/after_pt`（正文实际走 `BodyText`/`Compact`，自带段后 9pt/1.8pt，非 profile 的 0）、`sizes.table_body` / `tables.body_pt`（表内文字继承正文 10.5pt）、`sizes.affiliation` / `keywords` / `funding` / `author_bio` / `table_note` / `reference_heading`（无对应样式）、`formulas.symbol_styles`（OMML 内无对应样式）、`tables.caption_pt` / `figures.caption_pt` / `references.heading_pt`（被 `sizes.*` 取代）。**须在补齐生成器或收窄 profile 声明之间择一**，避免"声明了但没落地"。
   - **(b) 正文未标注**（非工具链问题）：版式角色靠正文侧 `custom-style` 标注进入产物。实测采用该约定的论文已全部落位——**P5**：`AbstractTitle`4 / `Abstract`4 / `TableCaption`4 / `Bibliography`19 / `Author`1；**P7**：`Bibliography`36 / `Author`2 / `TableCaption`6；而**P1/P2/P3/P4/P6 未采用**，对应角色数为 0。**这是论文侧源结构工作，须逐篇补齐**（F5：受派子代理执行）。
4. **公式粗斜体/粗正体（S10）保真度**：pandoc 的 MathML→OMML 不区分语义类别，需在公式源码中显式 `\mathbf`/`\boldsymbol`；当前构建记录 OMML 计数与 limitation，未逐类校验。数学**字体**已解决（docx 声明 `m:mathFont`，构建断言 `math_font_declared`）。
5. **标题编号由正文承担**：pandoc 不自动编号；目标刊的 `1、1.1、1.1.1、（1）、①` 序列现由 `body/paper.md` 的标题文本自带（P1 实测 `# 1 引言` / `## 2.1 …`），profile 记录该约定但不强制生成。
6. **`citation.style` / `formulas.renderer` 仍无可执行实现**：标引引擎与公式渲染器未落地，著者出版年制的正文引用改写属论文侧工作。
7. **第 7 章标题**：论文侧现为三种写法（"结论与后续" / "结论" / "结语"，P5、P7 无 conclusion 章）；模板已改为"结语"，论文侧统一属论文侧复核项（PF-RV7）。
8. **题名与摘要不合规项**（题名 3/7 超 20 字、P2 含标点、4/7 摘要用"本文"主语、P1 摘要偏短）属论文侧内容修复，本变更不代改。英文摘要与关键词行经本变更修复后已 7/7 齐备。
9. **LaTeX 链路**（备选 2）未评估。
10. **`writing-spec.yaml` 模板与论文侧键集合双向不齐**：模板缺 `promotion`/`quality_requirements`/`review_service`（P1–P3 有）；**P4/P5/P7** 缺 `manuscript_types`/`special_requirements`（模板有；P6 已齐）。需按 PF-W11 收敛为单一真值源。
11. **profile 角色在产物中的实际生效情况**：构建记录 `role_style_coverage`。**P1 产物实测 5 个角色样式零使用**（`Abstract`、`AbstractTitle`、`Bibliography`、`Caption`、`TableCaption`）——摘要正文以宋体 10.5pt 排出（非仿宋 9pt）、表题为 `BodyText` 左对齐（非居中）。**成因是 P1 正文未采用 `custom-style` 角色标注**（见第 3 条 (b)），非工具链限制；采用该约定的 P5/P7 已全部落位。在论文侧补齐前，该差距由 manifest 显式记录（不沉默）。
12. **两个 L1 profile 的 refdoc 字节相同**：`gbt7713-2-2022.docx` 与 `stie.docx` 当前完全一致，因为两者差异（`heading_numbering` 层级与 `references.order`）不体现在 refdoc 可渲染部分。语义上仍是有区别的 profile，但版式上无区分度。
13. **PF-W11 / PF-RV7 当前无机械执行点**：`writing-spec.yaml` 的目标刊约束键（题名字数、摘要字数、关键词分隔符等）**28 个键中 26 个零消费点**，PF-RV7 为纯文本规则。构建期只校验版式类项。**这是本记录最要紧的一条开放项**：规则读起来像已落地，实际只有 `venue` 与 `target_chars` 被读取。
14. **`gbt7713-2-2022` 是否保留**：其角色表已被 `draft` 承载、`stie` 覆盖版式项，是否降级为"L0 角色表 + L1 delta"待定。
15. **GB/T 7714 版次待编辑部确认**：本刊征稿启事引 **GB/T 7714—2015**；现行版为 **GB/T 7714—2025**（2026-07-01 实施，2015 版同日废止）。经核 2025 版 §9.3 著者-出版年制的出版年**同样前置**于著者之后，与本刊 S16 模板**一致**，故本刊合规；仅"标准版本号"字段过时。著录按本刊 S16 模板执行，版次以编辑部确认为准。
16. **结构化 provenance 未实现**：profile 的来源等级以注释 + 8 级缩写词表落地（`[S#]`/`[S#-adv]`/`[GB]`/`[CY]`/`[JT]`/`[TD]`/`[SC]`），未落为 schema 的键级结构化登记。
17. **`writing-spec.yaml` 的静默吞异常**：`tools/paper.py` 读 `writing-spec.yaml` 处仍是 `except: pass`（不在 build 路径上，但 PF-W11 要求该文件机器可读，故应一并修正）。
18. **断言覆盖率**：stie profile 约 107 个叶键，构建期断言覆盖其中 15 个；其余维度要么未落地（见第 3 条），要么以 `skipped` 记入 manifest。覆盖率提升依赖第 3 条的取舍。

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

### 10.1 第二轮复核（修订后）—— 已被第 11、12 节取代

本小节记录的是**首轮复核意见的修订**（标题 XML 转义、行距与拉丁字体断言、PF-B12 字体清单、L2 边界、PF-B3/PF-B10 条款、`cmd_build_pdf` 双 JSON、`paper.yaml` 畸形处理等）。随后**又接受了实施阶段的两次独立复核**（Codex-Team 代码 / Codex-Plus 文档），其发现与全部修订**以第 11、12 节为准**。

---

## 11. 实施阶段的独立复核（两轮，两名未参与者）

按 F9，本变更在提交前后各接受了独立复核。实施阶段的复核由两名**未参与任何实施**的子代理分别承担：一个查代码，一个查文档与治理一致性。两份报告均以实跑为据，未发现伪造结果。

### 11.1 Codex-Team（代码复核，85 次工具调用）

**结论**：架构方向正确，但"防静默降级"这一核心承诺在断言层与字体核对层被实现缺陷击穿——**6 个已实测的假阴性**（产物已坏但构建报 PASS）与 **1 个假阳性**（正常产物被误判失败）。

**P0（3 项）**

| # | 问题 | 机理 |
|---|---|---|
| M1 | schema 允许的 `pagination.header: "none"` 会生成**打不开的 docx** | `_apply_section` 无条件写 `headerReference`/`footerReference`，而对应部件与关系只在非 `none` 时创建 → 关系闭包不成立（LibreOffice 报 "source file could not be loaded"） |
| M2 | 关系 Id 冲突**静默跳过** → sectPr 指向别的部件 | `_add_relationship` 遇到已占用的 Id 直接 `return rels` |
| M3 | 构建**不校验 refdoc ↔ profile 同步** | 构建只算 sha256 记 manifest，手改/陈旧的 refdoc 可直接进产物 |

**P1（11 项）**：断言假阴性 6 处（`PAGE` 子串匹配被 `NUMPAGES` 满足；三线表只数 `single` ≥2，网格表照样通过；蓝色检测大小写敏感、不解析 `themeColor`、只扫 styles.xml；sectPr 删掉页眉引用不报；整包删除页眉部件零 failure 零 note）；缺页眉部件完全无断言；`Cambria Math` 缺失被 `OpenSymbol` 顶替；PF-B13 自带示例 `body_pt` 覆写导致构建必失败（生成器写 `sizes.body`、断言比较 `body_pt`）；L2 可覆写 `typography` 子树中的 venue 决策；`pagination` 三个 schema 合法取值被静默替换；`pdffonts` 不可用时构建仍报 ok；`paper.yaml` 双解析（正则 vs YAML）结果不一致。

**P2/P3（20 项）**：断言覆盖率仅 15%（stie profile 107 个叶键）、`role` 参数是死参数（断言另有一套展平逻辑）、`self_check` 页边距硬编码 25.4mm、`table_three_line` 算了却不参与判定、`limitations` 两种结构并存、docx 字节不可复现、regex 解析器脆弱等。

### 11.2 Codex-Plus（文档与治理复核，75 次工具调用）

**结论**：实施质量总体好（`verify_layout.py` 16/16，§8 的数字逐条可复现），但存在 **2 项 P0**。

| # | 问题 |
|---|---|
| P0-1 | **变更记录描述的状态不存在**——记录通篇写"未提交""必须按 hunk 拆分""提交前仍需独立复核"，而变更已于 22:31 以混号单提交 `fc09407` 落地 |
| P0-2 | PF-B12"table rule style"断言是假阴性——把产物改成全网格表后断言仍 0 failures（**与 Codex-Team M4/A-N2 独立同源命中**） |

**P1（5 项）**：`writing-spec.yaml` 的静默吞异常未修；`min_chars: 15000` 把"15000 字**左右**"的建议性写成硬下限；PF-B14 的来源等级在 profile 落地失真（`venue_advisory` 与 `self_chosen` 零实例，自选回落值被标成 `[TD]`/`[GB]`）；`stie.yaml` 的版次注记自相矛盾且指向不存在的开放项；`affiliation` 角色映射到 `Subtitle`（实际 `Subtitle` 装的是英文题名），`role_style_coverage` 因此给出假"已覆盖"信号。

**其他**：目标刊 S1–S20 转录逐条核对**无遗漏、无杜撰**；GB/T 7714-2025 §9.3 出版年位置**经原文核实确在著者之后**，即本刊与现行版一致；§3 归属标注 4 处不准确；§9 开放项有 3 条已过时、3 条遗漏。

---

## 12. 第二轮之后的修订（本节所列均已落地并复跑）

| 类别 | 修订 | 对应复核意见 |
|---|---|---|
| **P0** | `make_refdoc._apply_section` 改为**按实际创建的部件**生成引用；新增 `_assert_relationship_closure`（每个引用必须解析到类型正确、目标存在的部件） | Codex-Team M1 |
| **P0** | 关系 Id 改为**动态分配**（`_next_rid`），已占用即报错而非静默跳过 | Codex-Team M2 |
| **P0** | 构建前**重生成 refdoc 并逐字节比对**，不同步即构建失败 | Codex-Team M3 |
| **P0** | 变更记录 §1/§7/§8 按**已提交**的事实改写；恢复方式如实写明 `git revert fc09407` 会连带回滚 GC-01-S/GC-03 | Codex-Plus P0-1 |
| **P1** | 断言重写：页码域**精确匹配 PAGE 令牌**（排除 NUMPAGES）；三线表**逐边校验**（left/right/insideH/insideV 须 none、firstRow 只允许 bottom single）；蓝色检测**大小写不敏感 + 解析 themeColor + 覆盖 styles/document/header/footer**；**校验 sectPr 的页眉页脚引用可解析**且部件存在；**遍历全部 sectPr**；profile 未声明的维度记为 `skipped` 而非静默 | Codex-Team M4 / Codex-Plus P0-2 |
| **P1** | **发现并修复一条既有产物缺陷**：pandoc 复制页眉页脚**部件**却不复制**关系**，交付的 docx 关系图不闭合（LibreOffice 容忍，Word 未必）。新增 `_repair_header_footer_relationships` 在构建后闭合关系图 | Codex-Team A-N6/A-N7 的成因 |
| **P1** | 数学字体控制点移到**文档声明**：refdoc 与产物 docx 均写入 `m:mathFont`（pandoc 会丢弃 reference 的 `m:mathPr`，故构建后重写），并断言 `math_font_declared`；PDF 阶段的数学替代记为**宿主替代**而非 profile 失败 | Codex-Team M5 |
| **P1** | 断言与生成器**同源**：正文大小一律取 `typography.sizes.body`（回落 `body_pt`），PF-B13 示例 `body_pt` 覆写不再使构建失败 | Codex-Team M6 |
| **P1** | L2 边界收紧到 `typography` 的 `body_pt`/`line_spacing`/`first_line_indent_chars` 三个键；venue 角色表（fonts/sizes/heading_numbering）不可被论文覆写；PF-B13 文本同步 | Codex-Team M7 |
| **P1** | `pagination` 的 `footer_right`/`header_right`/`journal` 三个 schema 合法取值**已实现**（页码位置/对齐、页眉内容源） | Codex-Team M8 |
| **P1** | `pdffonts` 不可用 → **构建失败**，不再让不可核验的 PDF 通过 | Codex-Team M9 |
| **P1** | `paper.yaml` 改为**单一 YAML 解析**（`_get_paper_info` 不再用正则），消除标题/文件名的两套读法 | Codex-Team M10 |
| **P1** | `min_chars` 由 15000 改为 `null`（本刊"15000 字**左右**"属建议性，不得作硬下限）；模板与七篇论文同步 | Codex-Plus P1-4 |
| **P1** | profile 来源等级扩到 PF-B14 的 8 级：新增 `[S#-adv]`（本刊建议性）与 `[SC]`（**自选回落**），并把边距/行距/西文字体/页码字号/页码位置/页眉/作者简介字号/脚注字号改标 `[SC]` | Codex-Plus P1-5 |
| **P1** | `stie.yaml` 版次注记改为与 `entry_order` 一致（按本刊 S16 模板 = 2025 版形态），并指向**新增的开放项 15** | Codex-Plus P1-6 |
| **P1** | `role_style_coverage` 修正 `affiliation` 误映射（`Subtitle` 实为英文题名），并单列 `title_zh`/`title_en` | Codex-Plus P1-7 |
| **P2** | `self_check`：页边距期望值改为取自 profile；`table_three_line` **纳入判定**；新增字体与页眉引用检查 | Codex-Team M11 |
| **P2** | `make_refdoc` 补齐 `TitleChar`/`SubtitleChar` 联动字符样式（原先仍带 pandoc 主题字体与 28pt） | Codex-Team 建议项 |
| **P2** | docx 构建**字节可复现**：所有部件固定 zip 时间戳 + 固定 `docProps/core.xml` 日期（连跑三次 sha256 一致） | Codex-Team C.6 |
| **P2** | `verify_layout.py`：负例由 4 个扩到 **9 个**（新增缩进、网格表、NUMPAGES、页眉引用、小写蓝字），全部要求命中目标检查项；临时目录改用 `tempfile` | Codex-Team F 组 |

### 12.1 修订后的验证结果（可复跑）

```
$ python3 -I tools/verify_layout.py
TOTAL 21  PASS 21  FAIL 0
```

| 组 | 内容 | 结果 |
|---|---|---|
| A | schema 正向（3 profile + 模板 L2 + 七篇论文 L2） | 11 targets, 0 failed |
| B | schema 反向（新 profile 对改前基线） | stie 1 errors / gbt7713 1 errors（符合预期） |
| C | refdoc 幂等 + 自检（含三线表逐边、字体、页眉引用闭包） | 3 profile `in_sync=True`、`self_check=True` |
| D | **9 个负例** + 正例 | 全部命中目标检查项并失败；未改动产物 0 failures |
| E | 标题 XML 转义（`A & B <研究> "x" \z`） | 页眉部件 well-formed |
| F | L2 边界（含 `typography` 子树越权） | 越权全部拒绝，合法形式放行 |
| G | writing-spec 解析与目标刊约束 | 7 papers, 0 problems |

端到端：`build docx` → ok / `layout_assertions: pass` / 覆写日志 16 条；`build pdf` → ok / 23 页 / `pdf_fonts_missing: []`；七篇 `paper.py check` **7/7 pass**；docx 连跑三次 sha256 一致。


---

## 13. 第三轮：版式角色落位（论文侧）与两项治理缺陷修复

### 13.1 版式角色落位——为什么"声明了"不等于"落进了"

治理侧把 `Abstract`（仿宋 9pt）、`TableCaption`（表题居中黑体 9pt）、`Bibliography`（宋体 9pt + 悬挂缩进）定义进了 reference docx，但**pandoc 只会把正文里显式标注的 `::: {custom-style="X"}` 转成对应段落样式**；不标注，这些样式在产物里的使用次数就是 0，角色等于没落地。这是"声明 vs 实现"在正文侧的同一个毛病。

**做法**：由论文侧子代理（F5）逐篇给 `body/paper.md` 加标注，**只加标记结构、不改任何文字**；以 P5 的既有实现为参考。六篇（P1/P2/P3/P4/P6/P7）各一个独立提交，**每个提交只含 `body/paper.md` 一个文件**。P1 的执行代理发现其工作区含并发精修线的未提交正文改写，遂**拆分暂存**（只提交 HEAD 文字 + 自己的标注），把精修线的改动原样留在工作区——已复核：该提交与其父提交归一化后**正文逐行一致**（212 行全等）。

**结果**（产物 `w:pStyle` 使用次数，独立复核）：

| 论文 | Author | BlockText | AbstractTitle | Abstract | TableCaption | Bibliography | ImageCaption |
|---|---|---|---|---|---|---|---|
| P1 | 1 | 2 | 4 | 4 | 8 | 10 | 3 |
| P2 | 1 | 2 | 4 | 4 | 9 | 55 | 4 |
| P3 | 2 | 1 | 4 | 4 | 6 | 11 | 4 |
| P4 | 1 | 2 | 4 | 4 | 4 | 14 | 3 |
| P5（参考实现） | 1 | 2 | 4 | 4 | 4 | 19 | 3 |
| P6 | 1 | 2 | 4 | 4 | 4 | 6 | 4 |
| P7 | 2 | 0 | 4 | 4 | 6 | 36 | 4 |

**两条实现事实**（子代理实测、非推测）：
1. pandoc 的 custom-style **不向紧凑列表条目传播**；参考文献若写成紧凑有序列表，条目会落 `Compact` 而 `Bibliography` 计数为 0。须把参考文献写成**松散列表**（条目间空行），样式才落地，编号（numPr）保留。P1/P2/P3/P7 因此各有一处纯结构改动。
2. pandoc 的 `:::` 围栏**不能紧贴段落行**（会被吸成字面文本），须留空行。

### 13.2 治理缺陷一：`keepLines` 把长摘要整体推到下一页

P2 视觉验收发现：英文摘要整段落到了**第 2 页**，首页下方留白约 1/3。根因是 `Abstract` 样式继承了 pandoc 基础 reference.docx 的 `<w:keepLines/>`（整段不跨页）。

**修法**：`make_refdoc._apply_ppr` 增加 `keep_lines` 开关；`Abstract` 与 `AbstractTitle` 显式写 `<w:keepLines w:val="0"/>` 取消继承。实测 P2 由 33 页减为 32 页、英文摘要回到首页、版式无副作用；七篇共享的三个 refdoc 确定性再生成。

### 13.3 治理缺陷二：重建会就地改写已发布版本（PF-B7 违反）

构建直接写 `build/<version>/<title>.docx` 与 `manifest.json`，**无覆盖保护**。同一 `paper_version` 下重建会**就地覆盖已发布版本的产物与发布记录**，而 PF-B7 明文要求"已发布版本不得就地修改，旧版本保留"。（实测证据：P7 的 `build/v0.2.2/manifest.json` 被构建改写，且其记录的 `paper.yaml` 快照哈希与当前树已不一致。）

**修法**：构建前比对已存在产物——内容**相同**则允许（docx 已字节可复现）；内容**不同**时，若该版本的 manifest 的 `review_status` 不是 `pending`（即**已发布**），**拒绝构建**并要求按 PF-V3 升版本号；`pending` 草稿仍可就地重建（草稿不是已发布版本）。

### 13.4 本轮验证

`python3 -I tools/verify_layout.py` → **21/21 PASS**；七篇 `build docx` + `build pdf` 全 ok、`layout_assertions: pass`、`paper.py check` 全 pass；页数 P1 23 / P2 32 / P3 13 / P4 20 / P5 18 / P6 18 / P7 21。

### 13.5 本轮新增的开放项

19. **作者简介（S17）所需字段全员缺失**：`authors.yaml` 只有 name/name_en/affiliations/email/orcid/postal_code/roles，**出生年、性别、籍贯、学位、职称、研究方向、通信地址、邮编、电话**均无；作者A邮箱为 null。**须由用户按 F4 提供**，不得从 Git 身份或拼音推导。七篇一律未撰写简介段。
20. **P3 正文标题解析失败（既有缺陷，非本轮引入）**：`body/paper.md` 多数 `#`/`##` 标题行前无空行，pandoc 全文只解析出 3 个标题，其余标题连同字面 `#` 并入正文段落（PDF 可见 "# 2 关键技术 …"）。基线 v0.3.1 同样存在，且当时已标 "round3 视觉判定 pass"。修复需在全部标题前补空行（正文结构调整），应单独立项。
21. **P3 首页题名重复**：构建从 `--metadata` 生成 Title/Subtitle 段，而正文 L1 中文标题与 L9 英文标题仍在 → 首页两遍中文题名。P5 靠正文不写题名规避；P3 消除重复需删正文题名行（文字删除，超出授权）。
22. **P2 引文体例与 profile 冲突**：stie profile 规定著者-出版年制（S13/S16），而 P2 正文与参考文献为**顺序编码制 [1]–[55]**。本轮只做版式标注未改引文体例；按目标刊投稿需一次文字级大改，须单独授权与评审。
23. **build 产物被 git 跟踪**：七篇论文仓各跟踪 1–5 个 `build/` 文件，每次构建都会弄脏工作树，且已提交 manifest 的快照哈希会与当前树脱节。建议 `build/` 产物不入版本库（发布记录另存），或每次构建后随源码一同提交 manifest。
24. **发布记录目录结构待改**：现为 `build/<version>/` 平铺，建议改为 `build/<version>/REL-<时间戳>/` + `current.json` 指向最新发布，与 PF-B7"原子切换 build/current.json"的表述一致。
25. **S5 中英成对**：P4/P6 正文缺英文作者名与英文单位行（S5 要求与中文成对），P1/P2/P3 待核。补它属加文字，须授权。
26. **S2 作者行邮编**：P1/P2/P3/P4 的作者行缺"所在市 邮政编码"中的邮编部分。

---


---

## 14. 第四轮：插图在产物中缺失（投稿件硬伤）与图路径规范化

### 14.1 缺陷

七篇论文的 `body/paper.md` 共引用 24 张插图，但**产物里的插图数一度为 0**。实测三层根因：

1. **路径形式决定 pandoc 是否生成栅格备选**。实测（受控探测件）：
   - `![x](figures/t.svg)` → pandoc 产出 **SVG + PNG 备选**（6 个 media / 3 图）；
   - `![x](../figures/t.svg)` → pandoc 只产出 **SVG**（4 个 media / 4 图），**无栅格备选**。
   带 `..` 的路径使 pandoc 走"外部资源"分支，不生成 PNG 兜底。
   P2/P3 的正文用的正是 `../figures/`（其余五篇用 `figures/`）。
2. **pandoc 的 docx 写入把 SVG 作为 `<asvg:svgBlip>` 备选嵌入**（主图是 PNG 兜底）。**LibreOffice 优先取 SVG 备选且渲染不出** → docx 转 PDF 后图位全空。
3. **构建链对此完全沉默**：pandoc 对未取到的资源只发 `WARNING`，`paper.py` 只看退出码 → **构建成功、产物缺图**。P2 的 `build-record.md` 曾把"产物 0 图"如实记为已知问题，但没有任何机制阻止它再次发布。

### 14.2 修复（治理侧）

| # | 位置 | 内容 |
|---|---|---|
| 1 | `tools/paper.py` 构建命令 | `--resource-path` 追加 `<paper>/body`，使 `../figures/` 与 `figures/` 两种形式都能解析到文件 |
| 2 | `tools/paper.py` 构建后处理 | 新增 `_strip_svg_alternatives`：仅当同一 `<a:blip>` 存在**栅格兜底**时，才剥离 `asvg:svgBlip` 的 SVG 备选；SVG 是唯一图像时**保留**（否则会删掉图本身）。产物 docx 只留 PNG，LibreOffice 与 Word 均可渲染；SVG 源文件仍在论文仓 `figures/`，供目标刊 S19 的 SVG 附件 |
| 3 | `tools/paper.py` 构建断言 | **图数断言**：正文引用的图数必须 ≤ 产物 `word/media/` 数，否则**构建失败**（不再允许缺图发布） |
| 4 | `tools/paper.py` 构建断言 | PDF 级核对：产物 PDF 必须含图（`pdfimages` 计数），纳入 manifest 记录 |
| 5 | 宿主环境 | 安装 `librsvg2-bin`（pandoc 的 SVG 光栅化依赖），使 pandoc 能生成 PNG 兜底 |

### 14.3 论文侧（两个独立提交，每个只含 `body/paper.md`）

P3 `2c51a46`、P2 `588673f`：图片引用路径前缀 `../figures/` → `figures/`，**4 处/篇，正文文字逐字未变**。P3 改后 docx media 由 4（纯 SVG）变为 4（纯 PNG），**PDF 插图数由 0 变为 8**（4 图 + 4 透明蒙版）。

### 14.4 终检（七篇）

| 论文 | 引用 | docx media | PDF 插图 | 页数 | check |
|---|---|---|---|---|---|
| P1 | 3 | 3 | 6 | 23 | pass |
| P2 | 4 | 4 | 4 | 34 | pass |
| P3 | 4 | 4 | 8 | 15 | pass |
| P4 | 3 | 3 | 3 | 20 | pass |
| P5 | 3 | 3 | 5 | 18 | pass |
| P6 | 4 | 4 | 8 | 18 | pass |
| P7 | 4 | 4 | 8 | 21 | pass |

`python3 -I tools/verify_layout.py` → **26/26 PASS**（含并发会话新增的 H 组：区间 `[12,40]` 不上标、引用计数 docx==源）。

### 14.5 本轮新增开放项

27. **章文件（草稿）仍残留 `../figures/` 形式**：P2 的 4 个章文件、P3 的 2 个章文件。构建只读 `body/paper.md`（PF-B2），当前无碍，但**下次重新组装正文会把该形式带回来**。须在组装环节统一路径形式，或把约定写进章文件模板。
28. **manifest 缺页数字段**：PF-B7 明列 manifest 应含页数，当前只能靠账本补记；属治理仓 `tools/paper.py` 待补项。
29. **PDF 的 sha256 不可作幂等判据**（LibreOffice 在 PDF 内写入时间戳）：幂等锚点应取 docx 的 sha256。

---


---

*GC-2026-1111-02。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B3/PF-B10/PF-B11–PF-B14；验证入口 tools/verify_layout.py。*

---

## 附二：构建后视觉验收回归修订（2026-11-11，P5 首走新链路三轮视觉验收沉淀）

P5 v0.4.0 构建经 PF-B6 三轮视觉验收（R1 13 页 fail → R2 5 页 fail → R3 18/18 pass）暴露并修复以下工具/样式级缺陷：

| # | 文件 | 修订 | 依据 |
|---|---|---|---|
| 1 | `tools/paper.py` | 移除 pandoc metadata author 注入（与 paper.md 权威作者行重复且丢失 S18 通信作者 * 标记） | R1 page-01 |
| 2 | `tools/paper.py` | 新增 `_harden_tables` 构建后处理：全部表格行 cantSplit + 首行 tblHeader 跨页重复（承接旧手工管线 P2 REL-0002 实践），行数入 manifest 断言注记 | R1 表 3/4 拦腰截断 |
| 3 | `tools/make_refdoc.py` | Abstract 样式显式 keepNext=false（pandoc 基础样式继承的 keepNext 造成"摘要体→关键词→引言"整链跳页、首页 1/3 空白） | R2 page-01 |
| 4 | `tools/make_refdoc.py` | sectPr 移除 docGrid（网格吸附使 CJK advance 虚增 ~7%，破坏字号核验与视觉判读） | R2 实测 页眉 9.0pt 标定 vs 文献 9.67pt 假象 |
| 5 | refdoc ×3 重新生成 | 随 3/4 确定性再生成（diff 即上述样式变化） | — |

**写作侧配套约定**（由 P5 落位、后续论文沿用，精修 PL13 核对项）：摘要/关键词区用 `custom-style` Div（AbstractTitle/Abstract）、表题 TableCaption、图题 ImageCaption、参考文献条目 Bibliography、作者行 Author——pandoc custom-style 是版式角色进入产物的正文侧载体（与 refdoc 样式定义互补）。

**防漂移执行实例**：P5 writing-spec min_chars 曾被并发会话放宽为 null（违反 PF-RV7），已回退并登记（P5 95ada39）。

**验收方法教训（登记）**：CJK 字号像素判读须用纯中文行墨迹高度对同页基准（页眉 9pt），混排行"行宽÷字数"系统性高估 5–8%（ASCII 窄字符摊宽）；docx 层样式+run 覆盖核验为决定性证据。
