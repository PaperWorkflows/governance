# 治理变更记录 GC-2026-1112-06：元数据驱动排版自动化（前端/文末生成器 + 范本署名模式入规范 + 七篇迁移）

- 日期：2026-11-13
- 编号：GC-2026-1112-06（顺延 GC-2026-1112-05）
- 类型：治理能力修订 + 论文侧批量迁移（元数据驱动排版：标题/摘要/关键词/作者/单位/简介/基金入元数据，body/paper.md 只写正文；通信作者属性自动排版含文末简介；stie profile authors 域入规范；schema 修订；新生成器 tools/metalayout.py + paper.py 装配接入；七篇迁移）
- 规则依据：AGENTS.md F9（治理变更纪律）、F5（论文侧工作由受派子代理执行）、F6（最小改动）；版式语义 governance/build.md **PF-B2**（单一正文——body/paper.md 为正文单一权威源，front/back matter 元数据化是其「完整构建输入 / 题名与已确认作者来自 config」语义的自然延伸）**PF-B3**（profile 分层与结构身份键版本化）**PF-B10/B11/B12/B14**（三层分层 / refdoc 为版式唯一实现载体 / 落地校验 / provenance 来源等级）**PF-B16**（投稿元数据集合——摘要/关键词/含简介的作者/结论/字数，本轮改由元数据驱动生成，manifest 相应记录 `assembly`）；写作语义 PF-W12（范本实证优先）；版本语义 PF-V1/PF-V3；规则版本 0.3.0
- 前置分析：`temp/template-analysis-20261112/extract-report.md`（通过审稿范文《基于可信数据空间的…》逐行实录 §2 前端 11 块 / §8 文末「作者信息」四段）；P5 试点实测实证（阶段 2b）
- 流程状态：阶段 0+1（契约与 schema）→ 阶段 2a（生成器与构建接入）→ 阶段 2b（P5 试点 + G1/G2 修复）→ 阶段 3（P1/P2/P3/P4/P6/P7 迁移铺开）→ 收尾（city_en，已随 `1ff3cdf` 入库 author.schema.json + metalayout.py）→ **阶段 4（本记录收口，随实施提交一并入库；七篇论文仓已各自提交完毕，见 §5）**

---

## 1. 背景与用户指令

- 用户指令（2026-11-13）：元数据驱动排版自动化——**把原来手写在 body/paper.md 前端的标题、作者行、通信行、摘要、关键词、基金、英文块，与文末「# 作者简介」节的内容，全部 Harvest 进元数据**（authors.yaml 文档级容器 + abstract.md + funding.yaml + paper.yaml）；body/paper.md 只保留正文；构建时由生成器按元数据自动装配前端与文末作者信息；通信作者属性自动排版（署名上标 \* + 文末「通信作者*」段）；每篇一致，对齐范本。
- 治理侧目标：范本署名模式（上标编号式、前端 11 块顺序、文末「作者信息」四段）落入 profile 声明而非逐篇手写；生成器硬闸保证旧格式（裸列表 authors.yaml）不再被误构建；新论文模板与构建工具链同构铺开。
- 论文侧目标：七篇 migration 后科学内容零变更（正文逐字不动，body/paper.md 剥离为**纯删除**，见 §5）。
- 规则版本：**rules_version 保持 0.3.0**（project.yaml / governance/rule-index.yaml / tools/paper.py 常量一致）。理由：**零治理规则正文修改**（build.md、writing.md、rule-index.yaml、project.yaml 均未动）——PF-B2「body/paper.md 为正文单一权威源」语义不变且被加强（正文源继续唯一，front/back matter 移入元数据后正文更纯净），front/back matter 元数据化是 PF-B2「完整构建输入」与「题名/已确认作者来自 config」的自然延伸；沿 **GC-2026-1112-03/04/05 工具链实现先例**（先例均为实现载体变更、rules_version 保持）。

## 2. 范本模式入规范（stie.yaml authors 域键清单 + provenance）

`templates/layout/profiles/stie.yaml` 新增顶层 `authors` 域（GC-2026-1112-06 阶段 0+1），**只承载结构键 + 少量格式参数，不硬编码整句模板**（整句由生成器按元数据拼接）；字号字体类一律沿用现 profile 值，本轮不加字号键。逐键 provenance：

| # | 键 | 值 | provenance（来源等级 → 依据） |
|---|---|---|---|
| A1 | `affiliation_style` | `numbered_superscript` | [JT] 范本上标编号式（extract-report §2 行 2/3/4、§8）；**S2 偏差登记**（见 §6） |
| A2 | `corresponding_mark` | `"*"` | [S18] 通信作者右上角上标星号 |
| A3 | `corresponding_mark_position` | `after_numbers` | [JT] 范本上标「1,2,*」星号置于单位编号之后 |
| A4 | `name_separator_zh` / `name_separator_en` | `"，"` / `", "` | [JT] 中/英文署名分隔符 |
| A5 | `number_separator` | `","` | [JT] 单位编号间半角逗号 |
| A6 | `affiliation_list_alignment` | `center` | [JT] 中/英单位行均居中（折行仍居中） |
| A7 | `front_order` | 11 个块的数组：title_zh→authors_zh→affiliations_zh→abstract→keywords→**funding**→title_en→authors_en→affiliations_en→abstract_en→keywords_en | [JT] 首页自上而下顺序（extract-report §2 逐行实录；基金插在关键词与英文标题之间） |
| A8 | `front_corresponding_line` | `false` | [JT]+用户裁定：首页无独立通信作者行；通信信息只由署名上标 \* + 文末「通信作者*」段承载 |
| A9 | `funding_positions` | `[front, back]` | [JT] 基金重复登出两处：首页（关键词后）+ 文末作者信息节首段 |
| A10 | `bio_section.heading` | `作者信息` | [JT] 文末节标题（宋体、无编号、顶格） |
| A11 | `bio_section.position` | `after_references` | [JT] 位于参考文献之后（P1 另实测「作者信息生成在附录之后」） |
| A12 | `bio_section.paragraph_labels` | 基金项目 / 作者简介 / `通信作者*` / 其他作者 | [JT] 四段标签（「通信」非「通讯」，C-3 已固化）；标签后全角冒号由生成器拼接 |
| A13 | `bio_section.bio_field_order` | 出生年 性别 籍贯 学位 职称 **单位** 研究方向 通信地址 邮政编码 电子邮箱 电话 | [S17]+[JT] 首作者全字段序内含「单位」（非 bio 对象键，由 affiliation_ids 解析注册表拼得） |
| A14 | `bio_section.other_author_reduced_fields` | 出生年 性别 单位 从事工作 | [JT] 其余作者合并一段，字段精简 |

## 3. schema 变更

### 3.1 author.schema.json（文档级重构，已随 `1ff3cdf` 入库）

`urn:paperfactory:author:3`，从“单作者条目 schema”重构为**整个 authors.yaml 文档的 schema**（type object + required authors；additionalProperties: false）：

- **文档级容器格式**：顶层 `schema_version` / `affiliations`（单位注册表，**全文只声明一份**）/ `authors` 列表；作者经 `affiliation_ids` 引用注册表编号。
- **旧式裸列表作废**：顶层 `- id: ...` 数组不再合法（type object 校验失败）；迁移期七篇统一归一为容器。（控制面裁定 2026-11-13：按条目各持注册表是设计缺陷，文档级注册表为契约。）
- **交叉层级引用不可 schema 表达**：`affiliation_ids` 必须解析到同文档 registration 条目，由构建期硬闸执行（见 §4.3）。
- **name_en 必填**（S5 中英成对）：英文署名/单位编号列表由它生成，缺失即构建失败。
- **bio 必填**：S17 十个字段（birth_year/gender/hometown/degree/title/research_direction/address/postcode/email/phone）全 required（十字段由生成器渲染，均 string 或 integer，phone 亦 string）。
- **收尾新增 `city_en`**（可选 string）：affiliations 注册表项英文单位行的城市名（拼音，如 昆明→Kunming）；缺省时英文行回落中文 city（旧行为保兼容）。

### 3.2 layout-profile.schema.json（authors 域）

新增声明式 authors 域（`additionalProperties: false` 语义保持），本域为**可选**：draft.yaml / gbt7713-2-2022.yaml 无该域仍合法（旧 profile 兼容、构建走既有无 Affiliation 样式路径，refdoc 字节不变，见 §4.4）。键集与 stie.yaml 落地值一一对应（§2 A1–A14）：`affiliation_style`（enum numbered_superscript/inline_parenthesized）、`corresponding_mark(_position)`、`name_separator_zh/en`、`number_separator`、`affiliation_list_alignment`、`front_order`（enum 块清单）、`front_corresponding_line`、`funding_positions`、`bio_section`（heading/position/paragraph_labels/bio_field_order/other_author_reduced_fields）。required 键 9 项保证生成器输入完整。

### 3.3 paper.schema.json（front_notes + authors 域分工）

- **`front_notes`**（新增，可选 array of string）：关键词块与基金块之间的自由说明行，渲染为 BlockText（P3 的「中图分类号：P208　文献标志码：A」经此迁移不丢；终审返工 P3-3 订正：实测 P3 paper.yaml front_notes 值为「中图分类号：P208　文献标志码：A」，非初稿误记的「TP391」）。
- **`authors` 域语义收紧（分工契约）**：paper.yaml.authors 只承载署名顺序/显示名/roles；作者身份、单位编号（affiliation_ids）、bio 全部落到 authors.yaml（author.schema.json 模型）。`affiliations` 由 required 改为 **OPTIONAL**（保留做旧显示路径兼容），`author_id` 改为与 authors.yaml 条目 `id` 联结的 join key（description 同步更正——此前注释误指 authors/registry.yaml）。

## 4. 生成器与构建接入

### 4.1 tools/metalayout.py（新生成器，已随 `1ff3cdf` 入库）

- **定位**：GC-2026-1112-06 阶段 2a 实现载体。读 paper.yaml / authors.yaml / abstract.md / funding.yaml，按阶段 0+1 契约（author.schema.json + 语义硬闸）校验，生成前端与文末「作者信息」的 markdown（pandoc custom-style div，与 §12 落地接排形态同构——中文题名不重复成块，来自 pandoc metadata title 落 Title 样式）。
- **职责**：`load_paper_metadata`（容器形态硬闸 + jsonschema）、`validate_metadata`（语义硬闸，供 check 命令）、`assemble_document`（前端 + body/paper.md + 文末装配成 assembled.md 供 pandoc）。
- **英文署名**：范本 "SURNAME Given" —— name_en 首词大写为姓（P5 试点修正 G2 后的契约，见 §7.1）。
- **依赖面**：与 layoutlib 同（yaml + jsonschema，`python3 -I` 可用）。

### 4.2 tools/paper.py（装配→pandoc 接入，阶段 4 随本变更提交）

- **cmd_check**：新增 `metadata` 硬校验块——`metalayout.load_paper_metadata` + `validate_metadata`，任一错误以 PF-B16 风格**点名文件与字段**并使 check 失败；metalayout 不可得亦算失败（不静默降级）。
- **_cmd_build_docx_impl**：构建由「pandoc 直读 body_source」改为「pandoc 读 assembled.md」——`assemble_document` 生成 assembled.md 后 pandoc 以其为输入；`--metadata subtitle` 英文题名注入**移除**（pandoc 渲染 subtitle 紧跟题名，会破坏范本前端块序「基金在英文题名之前」；英文题名改为前端生成块落 Subtitle 样式）；作者行不再注入（署名/单位列表由生成器从注册表产出）；插图数量断言、数学公式 OMML 断言改在 assembled.md 上计数（前端/文末不携带插图）。
- **cmd_version_bump**：G1 修复（v 前缀），见 §7.1。
- **_assert_layout_landing**：`role_styles` 映射新增 `affiliation → Affiliation`（单位列表落专用样式而非 BlockText）。
- **_package_authors**：bio 改从 authors.yaml 文档级 bio 块按 author_id 联结（`_BIO_KEYMAP` 蛇形→S17 中文域名）；`author_bio_source` manifest 值改为 `authors.yaml#authors[].bio (GC-2026-1112-06)`。
- **manifest**：新增 `assembly` 记录（method=metadata-driven、front/back_matter_generated、assembled.md 相对路径），保证产物可由源复现。
- **脚手架/rules_version 默认**沿用 0.3.0（未动）。

### 4.3 硬闸清单（过渡期防旧格式误构建）

| # | 硬闸 | 失效动作 |
|---|---|---|
| H1 | authors.yaml 顶层必须是容器（schema_version/affiliations/authors），**旧式裸列表直接拒绝、不回落旧路径**（load 时抛 MIGRATION_MSG） | **load 级**（load 失败 → 构建/check 失败） |
| H2 | authors.yaml 过 author.schema.json（jsonschema） | **load 级** |
| H3 | affiliations 注册表 id 重复 | **语义级**（validate_metadata；check 与 build 均生效，P3-5） |
| H4 | affiliation_ids 悬空（未解析到注册表） | **语义级** |
| H5 | 注册表条目缺 name_en（S5 中英成对）；**署名作者缺 name_en（终审返工 P2-1）** | **语义级** |
| H6 | bio S17 十字段不完整；**署名作者 affiliation_ids 为空（终审返工 P1-1 init 骨架闸）** | **语义级** |
| H7 | paper.yaml.authors.author_id 无匹配 authors.yaml 条目；first 不为 1 个；corresponding 多于 1 个 | **语义级** |
| H8 | abstract.md 缺 `## 中文摘要` / `## English Abstract` 锚点；**关键词解析为空（终审返工 P2-2）** | **语义级** |

**分级说明（终审返工 P3-5 补注）**：H1/H2 为 load 级闸（`load_paper_metadata` 内置，构建/check 必经）；H3–H8 为语义硬闸（`validate_metadata`），终审返工前只在 check 生效、build 不跑——新论文 `init` 骨架（元数据未填）可通过 load 但需在 build 也失败并给可操作提示，故 `_cmd_build_docx_impl` 在装配前调用 `load_paper_metadata + validate_metadata`（终审返工 P3-5 落位，语义闸在 build 亦生效）。

### 4.4 Affiliation 样式（make_refdoc.py，阶段 4 随本变更提交）

- stie refdoc 新增 **Affiliation** 自定义段落样式：字体取 profile `fonts.affiliation`（缺省回落 body）、字号取 `sizes.affiliation`（stie=9，缺省回落 body_pt）、**居中、不加粗**、行距随正文、首行零缩进（范本 §2 行 4/8 单位列表居中）。provenance：[JT]。
- **仅当 profile 声明 authors 域时生成**该样式：draft.yaml / gbt7713-2-2022.yaml 无 authors 域 → 不生成 → 二者 refdoc 保持字节不变（回归验证见 §8，`--check` 3/3）。
- stie.docx 确定性再生成（11848 → 11875 B），draft/gbt7713 refdoc 不动。

## 5. 七篇迁移汇总表

每篇迁移（阶段 3）与收尾（city_en）均已在各篇论文仓独立提交（本次**不碰论文仓**）。版本/提交 hash/产物校验和汇总自各篇 `build-record.md` 迁移节与 city_en 节（sha256 为 16 位前缀，页数 pdfinfo 实测；docx 文件名为 PF-B7「标题（第一作者）.docx」）。

| 篇 | 迁移版本 | 迁移提交 | 迁移 docx sha16 | 迁移 pdf sha16 | 收尾版本 | 收尾提交 | 收尾 docx sha16 | 收尾 pdf sha16 | 页 |
|---|---|---|---|---|---|---|---|---|---|
| P1 | v0.4.5 | `092c72c` | `e59d1adf09e05408` | `93b27bc4de73bf05` | v0.4.6 | `10e6947` | `f4cbc8ea791a2c2f` | `1e521acc4d02770b` | 21 |
| P2 | v0.4.9 | `eae931b` | `fe5d09cdf4e88efe` | `bb62061503f7523b` | v0.4.10 | `e235ed7` | `797fb7dcd2d02d14` | `367c2c14065e8740` | 31 |
| P3 | v0.3.9 | `76187c7` | `889ae6d0356b99fc` | `51b51cc5c1130945` | v0.3.10 | `cc58bdf` | `100e722cd6bd7ea1` | `00df5c5cdf24e62d` | 14 |
| P4 | v0.3.6 | `d38c981` | `acd82003203dc9c0` | `a5546cf298d66e4e` | v0.3.7 | `8fd5ed2` | `896db4d354d67a0b` | `ece310356ca2ba19` | 19 |
| P5（试点） | v0.4.8 | `038ccce` | `4b03e9cddba154f2` | `c45cbe3c2a560ed3` | v0.4.9 | `61ead81` | `642f98ae3977f329` | `ef93cc38c1cf2ea4` | 16 |
| P6 | v0.2.7 | `e36b74c` | `9f32acf4eab3fe44` | `2c7b8d369c20c6df` | v0.2.8 | `f5dcfbf` | `22433195b87d4f8c` | `f04c8169c30c51c6` | 17 |
| P7 | v0.2.8 | `7e9ec4f` | `c15505396cd0395e` | `eed229579ca3bb85` | v0.2.9 | `585c8dc` | `aaf5415d4b3aa7b3` | `cc8a493d58b3e8d3` | 20 |

- 共同迁移动作（P5 试点后同模式铺开）：authors.yaml 归一为容器（affiliations 注册表 + affiliation_ids + 条目级 bio 十字段）；body/paper.md 前端与文末「作者简介」节剥除（P1 48 / P2 49 / P3 43 / P4 49 / P5 56 / P6 50 / P7 44 行，均为**纯删除、零新增零修改**，中文正文逐字未动）；paper_version patch 递增；manifest `assembly.method = metadata-driven (GC-2026-1112-06)`、front/back_matter_generated=true。
- 基金名渲染迁移（终审返工 P3-4 补记）：P1/P3 渲染基金名由手写稿前端「云南省重大科技专项计划项目」迁移为 funding.yaml 登记名「云南省时空大数据重大科技专项」（以元数据为准；同 code 202502AD080005，P1/P3 build-record 已在案）。
- **零编造铁律**：bio 全字段与唯一信息源 authors.txt 逐字段交叉核对，两源不一致项 0；英文单位名只取各篇稿件英文单位行原文（P2 自稿 *Finance Section, Yunnan Mapping Institute*、P3 自稿等），稿件无英文单位行的篇（P1/P4/P6/P7）**沿用 P5 已登记同单位译名**并在各篇 paper.yaml.unresolved 在案「待用户复核」。
- **harvest 计数口径**：manifest body_chars/total_chars 锚定结构标题区间，不含前端/文末——迁移后与迁移前**逐字节一致**（P5 实测 16,308 = 16,308），前端移除对计数无影响（既定行为，非回归）。
- 收尾 city_en：英文单位行城市由中文 city 修正为拼音（昆明→Kunming），`(1. <name_en>, <city_en> <postcode>, China)` 整行无中文字符；中文单位行省份保持中文；新旧版本逐段 diff 唯一文本差异为英文行城市（n=0）；旧版 build/\<version\>/ 保留（PF-B7）。

## 6. S2 偏差登记（PF-W12 范本实证优先）

- **writing-spec S2 原文**：`author_affiliation_inline` 现登记「作者姓名（一级单位全称 二级单位全称，所在市 邮编）」行内括号式。
- **范本实证**：extract-report §2 行 2/3/4、§8 为**上标编号式**——姓名后上标单位编号、单位列表置于独立居中单位行。
- **裁定**：按 **PF-W12「以范式实证优先」**（范文为该刊通过审稿投稿稿，已过审），stie authors 域落地 `affiliation_style: numbered_superscript`；**writing-spec S2 原文保留不删**（作为期刊明示原文登记，供编辑部核实时引用）。schema 的 `affiliation_style` 同时保留 `inline_parenthesized` 枚举供需要时切换。

## 7. 试点与修复记录

### 7.1 G1 / G2（P5 试点发现，均落本批次治理侧提交）

- **G1 — `paper.py version-bump` 不识别 SemVer `v` 前缀**：`v0.4.7.split('.') → ['v0','4','7'] → int('v0') 抛 ValueError` 阻断升版（PF-V2 下七篇版本均带 `v`，会拦迁移升版）。修复：`cmd_version_bump` 数值解析前剥前缀、输出与 replace 用原始记号（三处小改）。P5 升版用修复后 CLI 实测通过。
- **G2 — 英文署名契约错序（渲染反序）**：阶段 2a 原契约「name_en 末词大写为姓」（Given Surname 西语序）把中文姓前名后的英文名末词当姓，渲染成 `San ZHANG` 反序错误（范本要求 `ZHANG San`，唯一信息源 authors.txt 为姓前名后）。修复：`_surname_given` 改**首词大写为姓**（`Author B`→`ZHANG San`）；templates/paper/authors.yaml 契约注释与示例同步（`San Zhang`→`Zhang San`）；verify_layout 无测试锁定旧契约（已查证）。重建后英文署名实测 `ZHANG San1, AUTHOR A2,*` 与范本一致。P5 build-record R10 登记。

### 7.2 P2 构建事故

- **现象**（P2 阶段 3 迁移，2026-11-13 实测）：P2 首次 metadata-driven 构建（temp `TASK-20261112191343`，docx 849 149 B）在 body/paper.md **尚未剥除旧前端时**执行——`assemble_document` 把旧手写前端（YAML frontmatter / 旧作者行 / 旧「通信作者*」BlockText / 旧摘要关键词基金 / 旧英文块）整体嵌入生成器已产出的新前端之后，assembled.md 97 589 B，产物**前端块重复**（新生成块 + 旧手写残留，双作者行/双摘要/双英文标题头）。
- **处置**：剥除 body/paper.md 旧前端后重建（`TASK-20261112191441`，assembled.md 92 724 B、docx 848 713 B = 入库 v0.4.9 校验值）；旧错误装配留 temp 任务目录（PF-B5「Failed build artifacts stay in temp」），未进入任何 release。正常序列为「先剥正文再构建」，P2 一次构建即暴露并纠正，后续六篇均按正确顺序执行，无复发。
- **启示登记**：生成器硬闸（H1）只防旧 authors.yaml 格式，不防 body/paper.md 残留旧前端——迁移操作顺序（Harvest → 剥正文 → 构建）由构建记录与派单纪律约束；已在 §10 回滚说明中明确「剥除为纯删除、git 可逆」。

### 7.3 P3 Key words 标签（生成器英文关键词锚点）

- **现象**（P3 阶段 3）：generator `_parse_abstract` 英文关键词行正则 `Keywords`（大小写敏感），P3 abstract.md 原「**Key words**」不命中 → **首建缺失英文 Keywords 块**（前端结构异常）。七篇中仅 P3 用此非规范标签。
- **处置**：按「不编造」只改标签词（`Key words`→`Keywords`）、关键词内容逐字未动，重建后英文 Keywords 块落位（前端 11 段验证）。P3 build-record R11 登记。

### 7.4 city_en（收尾修正）

- **现象**：生成器英文单位行固定 `(n. <name_en>, <城市> <邮编>, China)`，城市误用中文 `city`（实测 `(1. …, 昆明 650034, China)`），与范本英文城市（`Haikou 570208, China`）不符。
- **修正**（随 `1ff3cdf` 入库）：author.schema.json affiliations 注册表增可选 `city_en`；metalayout `_build_registry` 带出 `city_en`，英文行城市 `city_en or city`（中文行仍中文 city，省份不改）。七篇注册表每条补 `city_en: Kunming`（标准拼音转写，非编造）。重建后英文 Affiliation 行整行无中文字符、逐段 diff 唯一差异为 `昆明→Kunming`。schema 新增为 optional，不含 city_en 的既有 authors.yaml 仍合法（以修正前某篇对修正后 schema 实测 VALID）。

## 8. 验证结论

| # | 方法 | 结果（2026-11-13 实测） |
|---|---|---|
| 1 | `tools/verify_layout.py` 全量（跨七篇产物） | **TOTAL 26 PASS 26 FAIL 0** |
| 2 | `tools/make_refdoc.py --check` | **3/3 in_sync=True、self_check.pass=True**（draft/gbt7713 字节不变，仅 stie 增 Affiliation 样式） |
| 3 | 七篇 `paper.py check` 逐篇 | 均 pass（含 metadata 硬闸：authors.yaml 容器 + jsonschema + validate_metadata 全过；P2 另 submission_gaps=[]） |
| 4 | docx 前端块序实测（逐篇解包 word/document.xml） | 11 块 = 范本 §2：Title→Author（上标 run）→Affiliation（居中）→Abstract→Keywords→基金→Subtitle（英文标题，在基金后）→Author(en)→Affiliation(en)（含 `Kunming … , China`）→Abstract(en)→Keywords(en)；前端无独立通信作者行（front_corresponding_line: false）；星号位于单位编号之后（corresponding_mark_position=after_numbers——P2/P5 上标实测 `2,*`、P1 `1,*`） |
| 5 | 文末「作者信息」节实测 | 范本 §8 四段：Heading1 作者信息 → 基金项目 → 作者简介（10 字段全）→ 通信作者*（10 字段全）→ 其他作者（others 空则不出段，P1/P2/P5 两作者篇符合预期）；P1位于附录之后（position=after_references） |
| 6 | manifest 核对 | `assembly.method=metadata-driven (GC-2026-1112-06)`、front/back_matter_generated=true；bio 均来自 authors.yaml 且非空、`bio_gaps: []`；`body_chars/total_chars` 与迁移前逐字节一致 |
| 7 | 阶段 4 冒烟（本收口批次） | `py_compile` tools/paper.py、tools/make_refdoc.py、tools/metalayout.py 通过；`python3 -I tools/paper.py --help` 正常；templates/paper/authors.yaml 对 author.schema.json **0 error**；stie.yaml 对 layout-profile.schema.json **0 error**；`verify_layout` 26/26 复跑保持 |

## 9. 开放项 / 遗留

1. **P1 结论标题口径**（内容线，非本变更引入）：body 结论章为「# 7 结论与后续」，writing-spec `conclusion_heading='结语'` 未命中 → manifest `submission.conclusion` 仍空、`body_extraction_failed` 计入 gaps（v0.4.4 代即存在，逐字节核对确认）；正文逐字不动，留内容线统一。
2. **P1/P4/P6/P7 英文单位名沿用 P5 登记译名待用户复核**：四篇稿件无英文单位行，注册表 name_en 沿用 P5 已登记同单位译名 *Land and Resources Information Center, Department of Natural Resources of Yunnan Province*；各篇 paper.yaml.unresolved 在案（owner：用户；如另给规范译名可一行回退）。P2/P3 用各自稿件英文单位行原文（P2 译名与 P5 不同，按指令勿抄）。
3. **P2 基金名本地值**：P2 `funding.yaml` name=`云南省重大科技专项计划项目`，其余六篇为 `云南省时空大数据重大科技专项`（同 code 202502AD080005）；现渲染以各篇 funding.yaml 为准，统一命名留内容线。
4. **四人 ORCID 待补**：七篇作者池（作者A/作者C/作者B/作者D）authors.yaml 均无 orcid 条目（模板默认 `orcid: null`），待作者自行补充。
5. **P3 funding.yaml 属内容线存量**：P3 前端「中图分类号：P208　文献标志码：A」已入 front_notes 未丢（终审返工 P3-3 订正：实测 P3 paper.yaml front_notes 值为「中图分类号：P208　文献标志码：A」，非初稿误记的「TP391」）；P3 funding.yaml 定名与正文渲染一致性问题非本变更范围，留内容线。
6. **英文块结构差异（GC-2026-1112-05 开放项延续）**：各篇英文题名/作者/单位块形态差异（P1 等）已由生成器统一起源自元数据，形态收敛不再依赖正文手写；存量的英文译名规范性与编辑部复核（开放项 2）继续挂账。
7. **authors 域声明键登记（终审返工 P2-3，同义登记）**：`affiliation_style` / `affiliation_list_alignment` / `front_corresponding_line` / `bio_section.position` 为**声明键**——不做第二形态实现（避免无人使用的死形态），当前生成器实现范本形态（numbered_superscript / center / 无前端通信行 / after_references），切换需生成器开发。layout-profile.schema.json 的 authors 域 description 与 stie.yaml 各键注释已标同义声明（P2-3 落位）。
8. **【闭合】开放项 1（P1 结论标题）已闭合**：P1 第 7 章标题「结论与后续」→「结语」（S12 合规；章内四段正文逐字不动，派生章文件 body/07-conclusion.md 同步），v0.4.7→**v0.4.8**（提交 `d01d7f5`）。manifest `submission.conclusion` 落位（1131 非空白字符=第 7 章全文）、`submission_gaps: []`；新旧 docx 526 段逐段 diff 唯一差异即该标题行；verify_layout 26/26、check pass。开放项 2/3/4 仍挂账（owner：用户）。
9. **【闭合】开放项 2/3/4（用户 2026-11-13 三项裁决）已闭合**：
   - **开放项 2（英文单位名待用户复核）已闭合**：P1/P4/P6/P7 注册表 name_en *Land and Resources Information Center, Department of Natural Resources of Yunnan Province* 经用户 2026-11-13 确认定稿，不再挂账；各篇 paper.yaml.unresolved 同步关闭（P1 条目标题改「（2026-11-13 用户确认定稿）」；P4/P6/P7 对应条目内英文单位名子句的「待用户复核」改为「2026-11-13 用户确认定稿」，随各篇提交一并入库）。P5 自稿「<单位已脱敏> Yunnan Institute of Surveying and Mapping」不属本次裁决范围，继续挂账。
   - **开放项 3（基金名统一）已闭合**：用户 2026-11-13 裁定基金官方名为「云南省重大科技专项计划项目」（code `202502AD080005`），渲染以各篇 funding.yaml 为准；P2 本即此名（不动），其余六篇 funding.yaml 已统一 `name` 并重建：P1 v0.4.8→**v0.4.9**（`08f2444`）、P3 v0.3.11→**v0.3.12**（`45beae8`）、P4 v0.3.8→**v0.3.9**（`76a16d0`）、P5 v0.4.10→**v0.4.11**（`efb2ed5`）、P6 v0.2.9→**v0.2.10**（`853a205`）、P7 v0.2.10→**v0.2.11**（`f4fed8a`）。各篇验证：docx 前端（关键词后）与文末（作者信息节首段）两处基金行均为「基金项目：云南省重大科技专项计划项目（202502AD080005）」（实测文本见各篇 build-record 新节）；除基金行外逐段 diff 与旧版零差异；manifest `submission_gaps: []`；`paper.py check` pass；verify_layout 26/26。（同步订正 §5 迁移注记中「P1/P3 渲染基金名…迁移为 funding.yaml 登记名『云南省时空大数据重大科技专项』」所指向的旧登记名——该名已按用户裁决替换为官方名，见各篇 build-record 新节。）
   - **开放项 4（ORCID 待补）已闭合**：用户 2026-11-13 裁定 ORCID **不需要提供**，不再挂账；七篇 authors.yaml `orcid: null` 保持（模板默认亦如此），各篇 unresolved 无 orcid 挂账。

10. **【新增修正】表格单元格首行缩进归零（用户 2026-11-13 发现，GC-2026-1112-06 后续修正）**：根因——docx 表格单元格段用 pandoc `Compact` 样式（basedOn BodyText→Normal），自身无 `w:ind`，继承 Normal 的 `firstLineChars=200`（正文 2 字缩进，正确），导致表内文字首行缩进 2 字符（不合范本：表内顶格）。修复三处：① 规范——stie.yaml `tables` 域新增 `cell_first_line_indent_chars: 0`（[JT] 范本实测）+ layout-profile.schema.json 同名键（integer，缺省 0）；② 代码——make_refdoc.py 给 Compact 打显式 `<w:ind w:firstLine="0" w:firstLineChars="0"/>`（读 profile 键，缺省 0）+ self_check 增 `compact_first_line_chars` 比对；三档 refdoc 全部重生成（draft/gbt7713 的 Compact 同款继承漏洞一并修复，字节变化属修复应有之义）；③ 断言——paper.py `_assert_layout_landing` 增 Compact 缩进断言（旧产物记 note 不阻断，篡改硬失败）+ verify_layout 增负例 `compact_indent_restored`（回归 27/27）。论文侧五篇重建（body 干净仓）：P1 v0.4.9→**v0.4.10**（`01b439e`）、P3 v0.3.12→**v0.3.13**（`38a9872`）、P4 v0.3.9→**v0.3.10**（`ec2269b`，页数 19→18 属缩进归零后自然紧凑化）、P6 v0.2.10→**v0.2.11**（`1dc5dee`）、P7 v0.2.11→**v0.2.12**（`af54b60`，main 分支）；逐篇实测表格单元格段有效 firstLineChars=0、正文段仍 200 未误伤、strict pass、包重装。**P2/P5 缓行**：两篇有并发内容线在途编辑（P2 多段精修中、P5 round 2 评审中），此刻重建会把半成品内容固化为 release；其线的下次重建自动继承本修复（refdoc 已修）。冒烟证据：表格段/紧凑列表 0、正文 FirstParagraph/BodyText 200 保持。提交：`788d853`。

11. **【新增修正】manifest 英文字段 + P3 标题空行 + PDF 确定性（用户 2026-11-13 发现两项，GC-2026-1112-06 后续修正）**：
    - **manifest 四要素**：用户指出 submission manifest 只有中文摘要，需中英摘要+中英关键字齐。修复——`_extract_abstract` 扩展抽取英文摘要全文+英文关键字（复用 metalayout 英文块同源解析，manifest 与成稿一致）；`_build_submission_block` 增 `abstract_en`/`keywords_en`（缺失记 gap 不炸构建，DD-2 边界）；`_package_plan` 包 manifest 同步增列；`_compare_submission_block`（A3）将两字段纳入共享比对集（只加一侧即 A3 fail）。落地方式：四篇同版本重build（本改只动 manifest、docx 字节不变——逐篇 sha 实证），P1 `a4d8342`（另 `f6cf3de` 收口挂起 PKG 记录）、P4 `d4035b0`、P6 `959ac87`、P7 `3e71df8`；四要素实测 438/1380/6/6（P1）、383/1612/5/5（P4）、389/1770/6/6（P6）、383/1684/7/7（P7），strict 全过。P2/P5 树脏缓行（其线重建自动继承）。
    - **P3 PDF 导航错乱**：根因——pandoc 要求 ATX 标题前必须有空行，否则标题行被吞为段落惰续行（字面 `#` 都渲染进正文）；P3 正文 31 个标题中 28 个前无空行（旧装配脚本产物），docx 仅 4 个 Heading 段、PDF 书签仅 4 节点。修复——body/paper.md 纯插入 28 空行（169→197 行，内容零改动）升 v0.3.14（`95ea515`）：docx Heading H1=8/H2=24、字面 `#` 零出现、PDF 书签 4→**32 节点**（树形实测 0 引言→1 平台总体设计→1.1…→2 关键技术…；参考文献按 Bibliography 样式排版本非标题、无书签节点属既有版式）。**卫生闸防复发**：metalayout.validate_metadata 增 ATX 标题空行硬闸（违排列出行号+标题文本，围栏代码块内豁免），七篇 check 全过。
    - **PDF 导出确定性**：重build 时发现 LibreOffice 每次导出盖 `CreationDate`（墙钟）+`Trailer/ID`（随机）+`/DocChecksum`，PDF 字节必非确定而 docx 完全确定（渲染级零差异实证）。修复——build pdf 后做同长度字节规范化（三处元数据替固定值，不破坏 xref）+ 金丝雀校验（pypdf 解析/页数/pdftotext）+ 失败兜底（还原原文件+manifest 记 limitation）。实证：同 docx 连续两次 build pdf sha256 完全一致（`e8412647…`），与旧版渲染级一致（pdftotext 字节一致+全页栅格化 0 差异）。提交：`37a6037`；回归 27/27。

12. **【新增修正】引文体例转著者-出版年制 + 测试时效（GC-2026-1113-03，用户发送前检查发现）**：
    - **发现**：投稿前全要素检查（机检+视觉门亲验）发现 P1/P3 正文用顺序编码制（P1 16+ 处 `[N]` 含多引、P3 13 处）而刊物 S13/S14/S15/S16 明示著者-出版年制（范文实证此制过审）——P3 早已登记为内容级开放项，P1 从未登记（GC-2026-1112-01 只修了上标排版）。P2/P4/P5/P6/P7 本就合规。
    - **转换**（两篇各一提交，均为内容级变更+逐条核验）：P1 v0.4.13（`3844d59`+回填 `da01d04`；文内 27 处标记 1:1 转全角作者-年形式、10 条英文条目按 S16 重排（姓氏全大写/年份紧跟作者/按字母序/DOI 收尾）、前导语编号指代改非数字措辞）；P3 v0.3.16（`b46980d`；13 处 1:1、11 条重排——中文 7 条（GB/T 标准号作著者置首+政府文件按范文不保留"北京：出版者"）+英文 4 条按姓氏序）。验证：残留 `[N]`=0、引用-条目双向对应无孤儿、标记数守恒、条目数不变、check/strict 全过；转换后参考文献页经视觉复验（P1 p16/P3 p15）。
    - **并发线协调**：执行期间并发内容线连续发布新版本（P1 v0.4.12 研究方向扩充、P3 v0.3.17 作者信息同步），均正确处理——在途改动原样落盘（`cb716d0`/`77388de`，使 HEAD 与已在盘 release 一致消除审计缺口），转换避让至下一 patch（P1 v0.4.13/P3 v0.3.16 后由 P3 线再推 v0.3.17 含转换）。
    - **测试时效**：`citation_superscript_removed` 负例的 mutation 前提（产物存在数值引用 run）随转换消失，报 no-op FAIL。修为条件化可见 skip（对齐 E 组范式），负例有效性经 /tmp 注入探针证明（有数值引用时仍执行且正确失败）。提交 `983d113`；回归 27/27。
    - **形式差异待确认**：profile 登记的英文文内形式为半角 `(Smith, 2020)`，范文实证为全角 `（Gorelick et al.，2017）`——按“已过审实证优先”执行全角，差异已登记各篇 build-record，**待编辑部确认**。
    - **终态**：七篇 current 版本全部 strict pass、四要素齐、表格缩进归零、PDF 确定性；投稿 zip 七篇齐（P1 v0.4.13/P2 v0.4.12/P3 v0.3.17/P4 v0.3.12/P5 v0.4.12/P6 v0.2.13/P7 v0.2.14），发送待用户指令（F7）。

13. **【新增修正】S1–S20 全项审计 + 英文引用形态批次对齐（GC-2026-1113-03 续，用户“继续”驱动）**：
    - **S 审计**（七篇×15 项机检+内容级抽检）：无 P0/P1。P2 级两项发前必修——P3 摘要 456 字超硬限 400（v0.3.18 压至 391）、P1 摘要 410 字+两处“本文”主语违 S3（v0.4.14 压至 384 并改无人称，13 项数字逐一核对无丢失）；另修 P3 图题注重复渲染（根因：pandoc alt 题注+裸文本题注双源，v0.3.18 去重）及其样式归位（v0.3.19：题注收回 alt 承载，落 ImageCaption 小五黑体，与其余六篇 canonical form 一致）。P3 摘要/题注修复期间并发线三波在途改动均按协议原样落盘。
    - **英文引用形态批次对齐（PF-B14 provenance 修正）**：第 12 项按“范文个案”执行的全角形式，经全批次权威扫描发现三种形态并存（P1/P2/P3 全角、P4/P5/P7 半角、P6 全角括号+半角逗号混排）。按 PF-B14 层级**刊物明示的 S14 登记形式（半角 `(Smith, 2020)`）优先于范文作者个案**，且批次既成多数本为半角——P1（27 处：11 括号式+16 叙事式，含“Hu 等（2025）”→ `Hu et al. (2025)`）、P2（27 处，多为混排形态）、P3（5 处）、P5（2 处）、P6（6 处）全部对齐半角；中文引用全角零误伤；中英混排组（P2 L58 一处）按登记规则保留全角外括号；GB/T 标准码（P3）经判定不属英文著者引用豁免。终态权威复扫：七篇纯英文引用全角残留=0。
    - **留待用户/编辑部的未决项**（均已登记，不阻断发送）：P2 标题含全角冒号（S1 title_forbid_punctuation，主流主副题体例，建议与编辑部确认）；P1 标题 30 字（S1 软限 20，范文 28 字过审先例）；S20 字数六篇超带宽上限（P2 27676/P7 20800 超幅最大，均已登记 INFO，裁定权 PF-RV8，建议投稿前与编辑部确认口径）；跨篇英文单位译名不统一（P2/P3 用各自稿件译名，建议批次统一为注册表定稿译名）。
    - **终态**：七篇 strict pass、zip 齐（P1 v0.4.15/P2 v0.4.13/P3 v0.3.20/P4 v0.3.12/P5 v0.4.13/P6 v0.2.14/P7 v0.2.14）、verify_layout 27/27、引用形态全批一致；发送待用户指令（F7）。

## 10. 回滚说明

- **论文侧**：各篇「body/paper.md 剥纯正文」为**纯删除**（剥离行数见 §5，零新增零修改），按篇 `git revert <迁移提交>` 即可无损还原旧前端与文末简介；authors.yaml 容器化与 paper.yaml 变更随同提交一并回退。旧版产物仍留各篇 build/\<version\>/（PF-B7）。
- **治理侧**：本变更文件集独立、不与他线交错（工作树基线仅他线 `authors/registry.yaml`，未触碰）；终审返工 P3-9 订正——本变更为**三笔提交**（`1ff3cdf` → `75be595` → `26cc802`），回滚须**按逆序** `git revert`（26cc802 → 75be595 → 1ff3cdf），**非单笔**；随后重建即得旧行为。
- **防旧格式误构建**：生成器硬闸（H1）对旧式裸列表 authors.yaml 直接拒绝、不回落旧路径——即使回滚遗漏迁移，旧格式也不会被当前工具链静默排错。

---

*GC-2026-1112-06。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B2/PF-B3/PF-B10/PF-B11/PF-B12/PF-B14/PF-B16；写作依据 governance/writing.md PF-W12；版本依据 governance/versions.md PF-V1/PF-V3；规则版本 0.3.0；前置分析 temp/template-analysis-20261112/extract-report.md；论文侧明细见各篇 build-record.md（P1 R6/R7、P2 R13/R14、P3 R11/R12、P4 R9/R10、P5 R10/R11、P6 R14/R15、P7 R10/R11）。*
