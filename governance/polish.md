# Polish Mode Rules（精修模式）

## Scope

This file defines the polish mode execution rules. Polish mode covers: controlled refinement of a completed (or partially completed) body — logic transitions, wording and register, readability, terminology constraints, and venue writing-standard compliance — without adding new facts. Polish never produces a deliverable by itself; delivery still requires the review-mode loop (PF-RV4 pass / PF-RV6 P0-P1 closed).

- 模式定位（GC-2026-1111-03）：第六模式。输入为已写成正文，区别于 writing（从 outline 生成）与 review（只读）。精修期间 `paper.yaml` 的 `stage: revision`、`stage_state: active`（schema 预留槽位）。
- 进入前置条件：paper.yaml 通过 `schemas/paper.schema.json` 校验（含 budget.confirmed 条件分支）；正文流状态明确（`body/paper.md` 为权威源，章文件为派生，PF-B2）；第 0 步判定完成；进入时登记 stage/stage_state/applicable_rules/unresolved 变更。
- 投稿规范单一真值源：本文件的 S 系核对项以各论文 `writing-spec.yaml`（PF-W11 承载）与 `templates/layout/profiles/stie.yaml` 为准，本文件不复制数值。

## Rules

### PF-PL1 准入与隔离

- 单篇触发（`对P{N}进行精修`），一条指令只锁一篇；同一会话已有在修论文时拒绝并行，须先闭环或显式切换。
- 准入四条件：① paper.yaml 通过 schema JSON 校验；② 正文流状态明确（paper.md 权威、章文件派生）；③ 第 0 步判定完成；④ 进入时登记 stage/stage_state/applicable_rules（追加 PF-PL1–PL13）/unresolved 变更。

### PF-PL2 术语前置约束

- **第 0a 步（机器）**：对照该篇 terms.md 扫描 `body/paper.md`，产出 `reviews/polish-r0-extract.md`。候选集：已登记术语 ∪ 正文首现定义式/缩写引入式/重复 ≥3 次的 2–6 字专业 n-gram ∪ `$...$` 内符号与谓词名；按首现行号排序；候选上限 100 项，截断须登记。禁用词候选来自 PF-W9 四类问题模式中文化实例与用户提供的 AI 腔黑名单；grep 命中仅为候选，须经语义确认（对齐 PF-W9 末条）。
- **第 0b 步（人工判定）**：用户裁决，终态三类：`locked`（禁止任何形式改写）/ `anchored`（默认态：可改句式，不得移除定义、不得后移首现位置）/ `banned`（禁用词）。anchored 为默认生效态，用户只显式裁决差异项；每篇人工裁决预算 ≤20 项。判定写回 terms.md"精修约束"独立小节（约束段与主体表 Notes 冲突时约束段优先）。漏登记候选先补登进主体（PF-W8）再打约束标记。二次精修沿用既有判定，只复核变动与新增。
- 未完成 0b 的论文，第 1 步不得启动。

### PF-PL3 全局逻辑诊断

- R-A 视角只读诊断，粒度章×段，强制三产物：①缺陷清单（行号化 `§文件#L行`，标注 PF-RV4 严重度，只计 P0/P1 入轨道判定）；②outline 功能映射表（每个 outline key point → 承载段行号/未承载）；③锚点术语表（anchored 术语 → 定义所在章及行号）。
- 轨道判定：缺陷单元占比 = P0/P1 缺陷段数 / 该章可判定段数；≥50% 判重写轨，<50% 判精修轨；结构性硬伤（未承担 outline 功能、概念硬着陆贯穿全章）直接判重写轨；精修后 Diff 连续两轮不通过升级重写轨。轨道判定经第二诊断者独立盲复核；不一致取更保守级别并记录分歧；仍不收敛升级用户裁定。
- **P0/P1 实质问题升级**：诊断发现真实性/正确性/独立性级问题（如无文献支撑的核心主张），精修无权修复——冻结现场、记入 polish-issues.yaml、升级回 review/research，严禁精修内代写掩盖。

### PF-PL4 精修执行约束

- 零新增事实（PF-W1）；保留全部学术限定词；locked 零改写；anchored 不移除定义、不后移首现。
- 去 AI 腔按 PF-W9 引用执行，精修增量：禁等长排比、消名物化堆叠（改具体动作与物理过程）。
- 朗读指标仅约束改写区域：改写后单句建议 ≤55 字（超出须登记理由），以保证复合从句的语义自足与定语自然流畅，严禁为凑字数而将完整句式切碎为缺乏主语的 API 电报体；连续从句嵌套 ≤3 层；编号公式/算法步骤前后有不回头的自然语言引导（不新增事实）。严格遵守 PF-W9.1 学术修辞铁律（杜绝免责甩锅词、杜绝合规便签进正文）。
- 分章并行/串行按**锚点依赖图**：定义所在章与其下游引用章串行；纯叙述章可并行；交界段整体归属一章，禁止跨章改同一段。
- 精修不新增主张，不触发 PF-W3 查新义务；拟引入新主张即越出精修边界，退出并按 W3 执行。

### PF-PL5 重写轨道

- 触发判据同 PF-PL3。重写方案（新骨架 + 材料映射表 + 术语锚点检查）先行，经用户书面批准后执行。
- 事实冻结：仅重组本文已有材料；缺机理处插 `【作者待补：…】` 占位，严禁代写桥接句。**占位标记清零闸**：第 5 步回归 grep `【作者待补`，命中即阻塞退出；占位须登记责任人。
- 重写稿照常过第 3、4 步（衔接与 Diff）。

### PF-PL6 写审分离与并行控制

- 五角色互斥分派不同实例：诊断（甲）/精修重写（乙）/衔接（丁）/Diff 核验（丙）/合并回归（戊）；执行者不得自验。
- 执行子代理类型由用户指定（2026-11-11 登记为 general-purpose，五角色仍互斥分派不同实例）。
- 流程：0a 机器提取 → 0b 人工判定【准入闸】→ 1 诊断（含盲复核）→ 2 分章精修/重写 → 3 首末衔接（丁）→ 4 语义 Diff（丙，覆盖含丁改动稿；不通过回 2，修正由乙执行、丙复验）→ 5 合并回归（戊；不一致回 2，两轮不可收敛升级用户）。

### PF-PL7 语义 Diff 核验

- 覆盖最终稿（含衔接改动）；查事实/界限漂移、概念衔接、残留 AI 腔。
- 结论只有两种："核验通过"或"具体句 + 最小改动修正"；修正回传乙执行、丙复验，状态记 fixed-pending-verify → re-verified（PF-RV6 六态）。

### PF-PL8 首末衔接

- 仅评估相邻段/章首末句。改写白名单：a) 增删连接词/介词短语；b) 同指代替换；c) 段首句内修饰成分移动。"前半句"= 第一个中文逗号/分号/冒号切出的首个分句。
- 禁止：更换主语、引入新命题、调整主干句序、跨句合并。

### PF-PL9 合并回归

- **5a 合并**：以 `# N` 一级章标题为字节段边界替换 `body/paper.md` 对应段；frontmatter、摘要/关键词、数据与代码可用性、参考文献、附录区段原样保留（章文件不覆盖此区段）。
- **5b 派生再生成**：按"章标题至下一章标题前字节段"重新生成 body/ 章文件，与 paper.md 逐字节比对，全数 PASS。
- **5c 回归检查清单**：locked 逐字符比对；banned 存在性检查+人工抽检；anchored 首现/定义行号前后对比（位移 >0 即违规）；占位标记 grep 清零；`tools/paper.py check`（骨架/结构检查）；JSON Schema 校验（`python3 -I`，schemas/paper.schema.json）；**投稿约束复核**（正文无空白字符数 vs writing-spec 的 target/min_chars 偏离登记；中英摘要字数区间与术语一致性 PF-W2）；术语首现位置重算登记回 terms.md。

### PF-PL10 产物与闭环

- 产物：`reviews/polish-r0-extract.md`、`polish-r1-logic.md`、`polish-r3-diff.md`（衔接评估并入 r3 前段，`r4-transition.md` 记录衔接 diff）、`polish-rewrite-plan.md`、`polish-issues.yaml`（字段：ID/位置/规则依据/级别/状态/证据/处置人）、`polish-version-record.md`；术语判定在 terms.md 约束段。
- 中间稿放论文仓库 `temp/P{N}-<DATE>-polish/TASK-<NNNN>/`（PF-V7）。问题状态流转沿用 PF-RV6 六态。
- 退出闸：受影响历史评审项已复核或书面声明失效（附证据）；polish-issues.yaml 中 P0/P1 全闭合或已升级；占位标记清零；合并回归通过。

### PF-PL11 失效与升级

- 正文/术语/摘要/config 变更即按 PF-RV6 宣告受影响评审报告与 build 快照失效。
- P0/P1 实质问题禁止精修内修复，冻结升级 review/research；核心结论推翻级改动退出精修。
- 版本 bump 按 PF-V2 内容判据：重写/重组后 qualified conclusion 新增或改变（对照材料映射表）→ MINOR；纯措辞与结构重排且结论逐项不变 → PATCH；核心结论推翻不得在精修内完成。版本记录产物 `polish-version-record.md`（对齐 PF-V3），bump 后由未参与改写者复验。

### PF-PL12 负载与可持续

- 0b 判定预算 ≤20 项/篇；判定质量抽检（每篇抽 10% 复核一致率）；候选上限 100 项并登记截断。
- 朗读指标与禁用词命中均为候选线索，最终判定须经语义确认。

### PF-PL13 投稿规范精修（venue compliance）

- 完稿后按该篇 `writing-spec.yaml`（PF-W11 真值源）逐项核对并修复投稿格式合规，核对清单：
  - **S1 标题**：≤20 汉字且一般不含标点；
  - **S2 作者与单位**：作者行内联"作者姓名（一级单位全称二级单位全称，所在市 邮政编码）"格式；
  - **S3 摘要**：350 字左右（容差以 writing-spec 为准）第三人称（禁"本文/我们/作者"主语），不引文献、不用公式与特殊符号；
  - **S4 关键词**：3–8 个，全角分号相隔；
  - **S5 中英一致**：标题、作者姓名、单位名称、邮编、摘要、关键词中英成对且内容一致；
  - **S6 缩略词**：首现给英文全称与中文名称，其后可用缩写；
  - **S7 基金**：项目类型+全称，圆括号内编号，多项目按国家级→省部级→市级→校级排序；
  - **S8 正文内标题**：层次不过多，阿拉伯数字分层编号顶格，层次序号 `1、1.1、1.1.1、（1）、①`；
  - **S11 图表**：先文字后图表；图/表有编号与题名且在正文引用处提及；
  - **S12 结语**：章名用"结语"，内容为主要结果论点提炼，不与摘要、引言重复；
  - **S13/S14 引用**：著者出版年制（GB/T 7714，版次以 writing-spec 登记为准）；正文引用形式——中文单著者 `张三（2020）`、双著者 `张三和李四（2020）`、多著者 `张等（2020）`；英文 `(Smith, 2020)`、`(Smith & Chick, 2020)`、`(Smith et al., 2020)`；同名同年加 a/b/c；重复引用在出版年后以角标著录页码；
  - **S15/S16 文后参考文献**：先中文后英文，各按著者拼音排序；著录以"著者，出版年."开头，末尾". 网址."（专著/期刊/会议/预印本四模板见 writing-spec）；
  - **S17 作者简介**：全员提供姓名（出生年）、性别、籍贯、学位、职称、研究方向、通信地址、邮编、邮箱、电话；
  - **S18 通信作者**：指定一位，姓名右上角上标 \*；
  - **S20 字数**：对齐 writing-spec 的 min_chars/target_chars。
- 修复属措辞/体例级，受 PF-PL4 零新增事实约束；涉及结论性改写（如压缩摘要致主张删减）按 PF-PL3 升级路径处理。
- PL13 核对结论同时作为 PF-RV7 审核输入；不合规项按 PF-RV4 分级（机械可判的硬约束 ≥P1）。
- 题录去重：paper.md 题录段（标题/作者行）与构建期 metadata（PF-B2 题名来自 config）重复时，以 config 为准精简正文题录段，正文保留作者行/基金/收稿等 front matter 信息。

---

*PF-PL1–PF-PL12 落盘依据：temp/polish-mode-change-plan-v0.2.0.md（两轮独立复核版）；PF-PL13 依据用户 2026-11-11 指令"编写规范可加入精修要求中"（GC-2026-1111-03 修订 A2）。*
