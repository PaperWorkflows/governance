# Review Mode Rules

## Scope

This file defines the review mode execution rules. Review mode covers: four-perspective independent review, issue grading, dispute resolution, and fix closure.

## Rules

### PF-RV1 生效规则与审核边界

- Main session assigns: paper identity, perspective, fixed input, applicable rule set, evidence scope, and unique report path for each review task.
- Reviewer is read-only. Can only write the assigned report. Cannot modify body, config, code, data, figures, or public rules.
- Each finding cites specific rule ID, location, evidence, and impact. New requirements not in existing rules can only be proposed as governance revisions, not used to silently reject papers.
- Each applicable rule must have a review finding. Each "not applicable" must have a research-type or style basis.
- Checks not actually executed are marked unverified, not passed. Tool missing, source unobtainable = limit noted, impact on conclusion explained.

### PF-RV2 四视角独立初审

- R-A (venue/editor perspective): verifies W1-W4, W9-W10, and applicable P rules for problem value, contribution, related work, logic, independence, and submission fit.
- R-B (technical/reproducibility perspective): verifies W4-W8, W10, and applicable T/P/S rules for proof, algorithm, system, data, experiment, statistics, source support, and reproduction conditions.
- R-C (editor/reader perspective): verifies W1-W3, W6-W10, and applicable T/P rules for bilingual consistency, terminology, citations, authorship, structure, self-sufficiency, and pragmatic wording.
- R-D (layout/output perspective): verifies W2, W8, and applicable T rules for docx, PDF, captions, formulas, figures, tables, and layout.
- Four perspectives conduct independent initial review on the same input, forming judgment before viewing other opinions. One task = one paper × one perspective.
- Same version must not be uniquely accepted by the writer (R3).

### PF-RV3 写审分离

- Executor cannot be the sole acceptor of the same version. Review and fix are dispatched separately.
- Prefer cross-dispatch between general-glm and general-minimax. Record actual executor and degradation reason.
- Subagent unavailability is recorded as gap; main session does not substitute.
- Image issues require second executor or source confirmation before modification.

### PF-RV4 问题分级

- P0 (blocking): invalidates core authenticity, correctness, independence, or delivery safety. Examples: fabricated results, key proof error, snapshot mixing. Unresolved = not a deliverable.
- P1 (important): affects evidence sufficiency, interpretation, reproduction, or style compliance. Must be fixed and re-verified, or proven non-applicable with evidence. Cannot be simply recorded and passed.
- P2 (improvement): expression or presentation improvement that does not affect current requirement satisfaction. May be recorded as not adopted with reason. 正文中残存的“不再重复”、“（定位，非贡献）”等免责甩锅或合规便签字样（违反 PF-W9.1）统一计 P2 缺陷，要求清洗为规范学术界定，严禁 Reviewer 反向逼迫正文通过贴标签自贬来避嫌。
- Report must include: input snapshot and rule version, applicable rule coverage, check method, actual execution record, issue location, rule basis, grade, suggested fix conditions, and limitations.
- Overall status: pass, needs-fix, or incomplete. Warning count does not substitute for complete conclusion.

### PF-RV5 争议与复核

- Main session compiles disputes, both sides' evidence, and pending questions; dispatches independent subagent for arbitration.
- Arbitration checks original text, proof, code, data, or rendering per specific rules. Reports verifiable evidence, support, and counterexamples.
- Majority agreement is only a clue, not a substitute for actual verification.
- Two rounds of集中review still unresolved: record分歧 and evidence gaps, move to补证, claim narrowing, research adjustment, or user report.

### PF-RV6 修复闭环

- Record per issue: pending-fix, fixed-pending-verify, re-verified, rebuttal-valid, not-applicable, or unresolved. Attach evidence.
- Original report preserved. Fix task only modifies authorized scope.
- After body, literature, data, code, figures, authorship, config, toolchain, or layout changes, subagent checks impact and复审 affected items. Cannot reuse expired reports.
- Final report binds to current complete snapshot and re-verification relationships.
- Delivery requires: applicable rules verified, P0/P1 all closed, P2 disposition recorded, and both T-rule artifacts with visual verification complete.

### PF-RV7 目标刊格式合规复核

- Reviewers verify the paper against the venue constraints recorded in `writing-spec.yaml` (PF-W11), and against the layout profile selected in `paper.yaml.layout_profile` (PF-B11/PF-B12).
- Mechanical checks (title length and punctuation, abstract length and forbidden subject forms, keyword count and separator, presence of the English abstract and keyword blocks, funding note ordering, corresponding-author marking, author biography fields, and reference-entry type codes — every bibliography entry carries a document-type identifier drawn from the registered set: the venue's four templates plus the profile's `citation.fallback_entry_forms` — and conference-entry venue place — every `[C]` conference entry carries the venue place per venue template 15.2③ (`会议录名称. 会议地点：起止页码`); a missing venue place is P1, same caliber as the P5 round-1 RC-02 precedent) are executed and recorded with actual values, not asserted.
- Advisory constraints are reported against their tolerance band; exceeding an advisory constraint is P2 unless the venue's own text makes it binding.
- The layout side is verified against the built artifacts: page geometry, body font and size, heading hierarchy, table rule style, caption placement, page numbering, and the absence of residual default styling. Deviations that the build did not already flag are P1.
- Findings cite the venue clause or the profile key they rest on. Where a value originates from a fallback rather than the venue, the report must say so (PF-B14).

### PF-RV8 目标刊格式规则与精修规则（全局）

- 用户 2026-11-12 提供的目标刊投稿格式要求全文（本文件附录）为**审稿的格式规则与精修规则**，对全部审稿视角（R-A/R-B/R-C/R-D）与精修模式（PF-PL13）全局生效，不因论文而异；与 PF-RV7 的机械核对义务叠加，不替代。
- 条款效力分级：凡刊方以**规定语气**表述（"应/须/要求/以上/不得/必须"，无容差措辞）的条款为硬约束，违反计 P1；仅当出现"一般/为宜/建议/左右"等建议性措辞时按目标值 + 容差执行（同 PF-W11 第 4 条），超容差计 P2，除非刊方文本自身使其成为硬约束。
- **字数带宽（用户 2026-11-17 澄清放宽）**：附录条①"论文字数要求15000字以上"的目标 15000 字可大幅放宽，最新执行带宽为 **8000–16000 字**；带宽内视为满足该条，低于 8000 或高于 16000 计 P1。带宽口径按条①"论文字数"执行；manifest 登记的全文字数与正文字数须随值标注统计口径（PF-B16），审稿引用字数时注明所用口径。
- 审稿必须对附录条款**逐条**给出核对结论（适用/不适用 + 依据）；机械可判项（字数、关键词数与分隔符、缩略词首现全称与中文名、基金排序、著录格式、作者简介字段完备性、署名变更理由）必须给实际值，不得断言（同 PF-RV7）。
- 优先序：刊方明示 > 国标基线（GB/T 7714—2015、GB 3100—3102 等）> 本项目回落；来源等级映射与标注遵循 PF-B14 的八级词表，不得把回落值当成刊方要求。
- **过渡条款**：在 `writing-spec.yaml` / `stie.yaml` 尚未迁移至 2026-11-12 版值之前（GC-2026-1112-02 开放项 O2），**审核与精修以本附录为准**；writing-spec 旧值（如目标 15000、min/max 为 null vs 附录条①经用户澄清的 13000–16000 带宽）与本附录（含字数带宽条款）的分歧记为"待迁移差异"，不判论文违规；写作侧/构建侧机械检查继续按现行 writing-spec 执行，直至迁移完成。
- 附录条款同时作为**精修规则**：精修按其逐条校正（摘要句式与字数带、引言三要素、结语不重复、量与单位与符号统一、公式四类字体、图表先文后图、参考文献著录与排序、作者简介字段、署名规范），不新增事实（PF-PL1–PL13 约束不变）。

## 附录：目标刊投稿格式要求全文（2026-11-12，PF-RV8 附带的刊方原文快照）

> 本附录为刊方原文逐字快照（PF-RV8），更新须另立治理变更，不得就地改写快照正文。
> "图/表制作规范："在刊方原文中即为空条，如实保留（开放项 O3）。

**格式要求**：为保障学术成果的规范传播、提升出版流程效率、确保研究成果符合出版标准与数据库收录规范，现对投稿格式作如下要求。

**投稿**：论文字数要求15000字以上，请在稿件文末附作者详细联系方式，包括通信地址、E-mail、电话等信息，将稿件文件如Word文档、Visio、PDF、SVG等打包成Zip等压缩文件，以电子邮件附件形式发送至编辑部邮箱：stie@mail.sysu.edu.cn。
[注] 用户 2026-11-17 澄清放宽：本条"15000字以上"可大幅放宽，最新执行带宽 8000–16000 字（PF-RV8 字数带宽条款）；快照原文未改动。

**标题**：简明扼要，一般不超过20个汉字（标题一般不包含标点符号）。

**作者姓名和单位**：按"作者姓名（一级单位全称二级单位全称，所在市 邮政编码）"格式。例如：
高校：张三（北京大学信息科学技术学院，北京 100871）
企业：李四（华为技术有限公司云计算事业部，深圳 518129）

**4. 摘要**：300-400字左右为宜，超过350字可尽量压缩，除非无法压缩，允许放宽到400字。应具独创性，着重创新、发现。用第三人称写法（避免使用"本文""我们""作者"等主语），建议采用"对……进行研究""分析……现状""开展……调查"等句式阐述文章的研究性质和核心主题。避免引用文献、公式或特殊符号，以确保数据库收录检索的便利性。

**关键词**：3～8个为宜，中间用分号相隔。

**英文**：标题、作者姓名、单位名称、邮政编码、摘要和关键词与中文内容一致。

**7. 英文首字母缩略词**：文中第一次出现英文缩写，应给出英文全称和中文名称，其后再出现可以用首字母缩略词。

**基金项目**：获得基金项目资助的稿件应注明项目类型、全称，并在圆括号内注明项目编号。若有多个基金项目资助，请按国家级→省部级→市级→校级的顺序排序。例如：
基金项目：国家自然科学基金项目（11590771）;贵州省大学生创新创业训练计划项目（201510976011）

**引言**：开门见山、客观阐述、重点突出。介绍现状，分析问题，阐述目的。

**正文**：结构严谨、表达简明、语义确切、论点鲜明、论据充分、引用规范、数据准确。

**正文内标题**：要简洁、明确、层次不宜过多，采用阿拉伯数字分层编号，章、节的编号顶格排列；层次序号为：1、1.1、1.1.1、（1）、①。

**量与单位**：参照GB 3100—3102《量和单位》及国际通用学术写作标准制定，请严格遵照执行。同一符号在全文（包括正文、公式及图表）中应保持统一，避免使用不同符号表示同一物理量（特别注意符号的大小写和上下标的一致性）。在公式中，符号的意义和计量单位在首次出现时应明确注明其代表的含义。公式须使用公式编辑器生成（Word自带公式编辑器或等），勿以图片形式插入。公式中的变量、函数等应遵循以下格式要求：
①斜体：如变量、物理量符号等；
②正体：如单位、常量、函数名等；
③粗斜体：如矩阵、向量、张量等；
④粗正体：如实数集R、整数集Z、自然数集N等。

**13.图/表**：正文中图/表简洁明晰，遵循"先文字后图表"的原则，避免内容重复。正文中的图/表必须有图号/表号、图题/表题，并在正文引用处提及；图中涉及的术语、数值、符号、计量单位等应符合相应的国家标准，且与正文及其他插图保持一致。

**图/表制作规范**：（刊方原文此条为空）
[注] 原文"图/表制作规范："后无内容，如实保留空条；模板取得后回填（开放项 O3）。

**结语**：结论是主要结果、论点的提炼、概括。不可与摘要、引言重复，应准确、简明、完整、有条理。

**参考文献**：著录格式应符合国家相关标准《信息与文献 参考文献著录规则》（GB/T7714—2015）。本刊采用著者出版年制。建议优先引用5年内公开发表、具有权威性的学术研究成果。

**15.1 正文引用形式**：
①引用单著者、两个著者文献著者需要全部标注。
单著者：(Smith，2020)；张三（2020）
双著者：(Smith & Chick，2020)；张三和李四（2020)
②引用多著者文献时需要用"等"或"et al"。
多著者：(Smith et al.,2020)；张等（2020)
③当不同文献标注相同（即作者名与出版年份均一致）时，应在年份后加"a""b""c"等，以示区分。
④多次引用同一著者的同一文献，在出版年后以角标形式著录引文页码。

**15.2 文后参考文献**：先中文，后英文，中英文均按照著者汉语拼音字顺排列。以下是三种基本著录形式（英文文献同）：
①  专著
著者，出版年. 书名[M]. 出版地：出版者：起止页码（任选）.网址.
②  期刊
著者，出版年. 篇名[J]. 刊名，卷号（期号）：起止页码. 网址.
③  会议论文
著者，出版年. 篇名[C]∥会议录名称. 会议地点：起止页码. 网址.
④  预印本
著者，年份. 题名［EB/OL］.（更新日期）［引用日期］. 网址.

**作者简介**：应指定一位通信作者，并在其姓名右上角用*星号标注。通信作者可以是第一作者，也可以是其他作者，但必须是论文负责者，对稿件的科学性和结果、结论的可信性负主要责任，同时也是本刊和读者所联系的对象，原则上通信作者为研究生导师或科研课题的负责人。所有作者均需提供姓名（出生年）、性别、籍贯（省、市或县）、学位、职称、研究方向、通信地址、邮政编码、电子邮箱、电话。
例如：黄小丹（1988年生），女，江苏苏州人，硕士研究生，讲师；研究方向为ARM嵌入式，E-mail：huangxd@163.com

**署名**：凡合著的稿件，投稿前应仔细斟酌，考虑周全，并征得所有合著者的同意。投稿后，第一作者原则上不得变更，其他作者及署名顺序原则上不作调整，如确需修改，须提供充分理由并经编辑部审核。
