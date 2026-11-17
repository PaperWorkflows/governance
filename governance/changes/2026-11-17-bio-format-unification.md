# 治理变更记录 GC-2026-1117-09：作者简介三档格式统一（第一作者/通信作者/其他作者同一字段序与渲染式）

- 日期：2026-11-17
- 编号：GC-2026-1117-09
- 类型：生成器渲染统一 + profile/schema 配置废止（`tools/metalayout.py` 删除 `_bio_reduced`、`_bio_corresponding` 两个函数，统一走 `_bio_full`；`stie.yaml` `bio_section` 删除 `other_author_reduced_fields` 与 `corresponding_bio_fields` 两键；`schemas/layout-profile.schema.json` 同步移除两键，含 `required` 中的 `other_author_reduced_fields`；rules_version PATCH 0.4.1→0.4.2 五处同步）
- 计划：无单独计划文件（轻量变更，直接执行）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、F6（最小改动）；版式依据 PF-RV8（刊方明示 > 国标基线 > 本项目回落）、PF-B3（profile 为 L1 结构身份键）；版本依据 PF-V1/PF-V3/PF-V5/PF-V6
- 规则版本：**0.4.1 → 0.4.2（PATCH）**

---

## 1. 基线（Baseline）

- **git 基线（写盘时刻）**：治理仓 HEAD `1874a69`（feat(governance): GC-2026-1117-07 产物命名加版本号后缀 + build-record 历史清理条款）。
- **并行改动**：写盘时刻工作区另有并行会话未提交的引文领域改动，包括 `stie.yaml` `citation.in_text_forms` 的 `zh_paren_*` 三键、schema 同区、`tools/verify_layout.py` 同区，以及未跟踪治理记录 `governance/changes/2026-11-17-citation-zh-parenthetical-forms.md`。
- **改动边界**：本变更只触及 `bio_section` 相关区域，未触碰上述引文领域改动，也不触及任何 `papers/` 下论文仓文件（PF-V5）。
- **rules_version 前后**：0.4.1 → **0.4.2（PATCH）**，同步 `project.yaml`、`governance/rule-index.yaml`、`tools/paper.py` 两处、`templates/paper/paper.yaml`，合计五处。

## 2. 现状取证（问题陈述与证据）

| # | 问题 | 证据 |
|---|---|---|
| E1 | 三类作者简介的格式与描述方式尚未统一 | 用户 2026-11-17 裁定：作者简介的第一作者、第二作者（其他作者位）、通信作者位都保持一致的格式和描述方式 |
| E2 | 通信作者段与首作者段字段序已相同，渲染式仍不同 | GC-2026-1117-02 补全 11 项、GC-2026-1117-03 补渲染分支后，首作者为「通信地址：X；邮政编码：Y」分列且邮编带冒号；通信作者仍为「通信地址：X，邮政编码 Y」合写且邮编无冒号，出自 `_bio_corresponding` 的合写分支 |
| E3 | 其他作者段仅四字段，不满足 S17 对所有作者的字段要求 | 现仅含出生年/性别/单位/从事工作，渲染为「主要从事<研究方向>等工作」，无籍贯/学位/职称、无「研究方向为」标签、无通信地址/邮编/邮箱/电话；与 S17「所有作者均需提供」10 项字段（+单位=11 项）不符。实例：P10 李丽英、P3 赵康、P8 杨礼飞；杨礼飞另有七项字段待补，渲染按缺项跳过，不编造 |
| E4 | 范本简式不能覆盖刊方明示要求 | PF-RV8 优先序为 S17 刊方明示 > [JT] 范本实测；范本虽将其他作者合并为四字段简式段，GC-2026-1117-02/03 已按同一优先序把通信作者补为全字段，本次是同一逻辑的最后一环 |

## 3. 精确变更清单（逐文件）

核心功能与记录文件共四项（3 修改 + 1 新建）：

| # | 文件 | 变更 |
|---|---|---|
| 1 | `tools/metalayout.py` | 删除 `_bio_reduced` 与 `_bio_corresponding` 两个函数；第一作者、通信作者、其他作者统一走 `_bio_full`，使用同一字段序与渲染式 |
| 2 | `templates/layout/profiles/stie.yaml` | 在 `authors.bio_section` 删除 `other_author_reduced_fields` 与 `corresponding_bio_fields` 两键，不再保留三档字段配置特例 |
| 3 | `schemas/layout-profile.schema.json` | 同步移除 `other_author_reduced_fields` 与 `corresponding_bio_fields` 两键，并从 `required` 中移除 `other_author_reduced_fields` |
| 4 | `governance/changes/2026-11-17-bio-format-unification.md` | 本记录（新建） |

版本声明同步四项文件、五处字面量：

| # | 文件 | 变更 |
|---|---|---|
| 5 | `project.yaml` | `rules_version: 0.4.1` → `0.4.2` |
| 6 | `governance/rule-index.yaml` | `rules_version: 0.4.1` → `0.4.2` |
| 7 | `tools/paper.py` | 两处 `rules_version` 字面量由 `0.4.1` 同步为 `0.4.2` |
| 8 | `templates/paper/paper.yaml` | `rules_version: 0.4.1` → `0.4.2` |

**不改**：`papers/` 下任何论文仓文件（PF-V5）；citation 领域任何文件及其未提交改动；其他 profile（`draft`、`gbt7713-2-2022` 无 `bio_section`，不涉及）；`tools/verify_layout.py` 的 `author_bio_layout` 断言（该组只辖字号、缩进等排版属性，不含字段格式，无需改）。

## 4. 理由（Rationale）

1. **用户裁定即最高指令**：三档作者简介必须保持一致的格式和描述方式，本变更直接落实该裁定。
2. **S17 是面向所有作者的硬约束**：其他作者简式四字段缺少刊方要求项，与 GC-2026-1117-02/03 处理通信作者缺项属于同型问题。
3. **消除同义不同式的维护负担**：`_bio_full`、`_bio_corresponding`、`_bio_reduced` 三套函数分别维护，已造成字段相同而渲染式不同；取消特例后由 `_bio_full` 提供单一真值源。
4. **数据侧已就绪**：审计结论为除 P8 杨礼飞七项待补外，各篇 `authors.yaml` 的 bio 十一项齐全，渲染层统一无需论文侧数据变更。
5. **版本按 PATCH 定级**：本次统一既有渲染行为并废止特例配置，无新增规则号，与 GC-2026-1117-01、GC-2026-1117-02、GC-2026-1117-03 同型。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 维持三套格式 | 直接违反用户裁定；其他作者四字段简式仍违反 S17 |
| 仅统一通信作者邮编写法，保留其他作者简式 | 只解决局部表象，三档字段与描述方式仍不一致，S17 缺项问题依然存在 |
| 在论文侧 `writing-spec` 覆盖 | 违反 PF-B3：L2 论文层不可覆写 profile 的 L1 结构身份键 |

**拟取方案**：删除两个特例渲染函数及对应 profile/schema 配置键，三档作者统一由 `_bio_full` 渲染。

## 6. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 其他作者段由简式变为全字段，篇幅增加 | 范本合并段结构不变，字数增量有限，接受 |
| R2 | 已发布产物的作者信息节与新版不一致 | 属论文侧重建 rollout 事项；PF-V5 下本变更不含 `papers/`，各篇重建后生效，登记为开放项 |
| R3 | P8 杨礼飞字段缺失导致输出不完整 | 渲染按缺项跳过、不编造；其 S17 闸门本就拦截重建，无新增风险 |
| R4 | schema 删键后旧 profile 校验失败 | `additionalProperties: false` 下，仍含两键的旧 profile 将被拒；现存仅 `stie.yaml` 含有且本轮同步删除，无在役影响 |

## 7. 验证

以下实测结果占位由实现方回填，**执行结果见实现轮汇报**。

| # | 验证项 | 通过标准 | 实测结果 |
|---|---|---|---|
| V1 | profile/schema 校验 | 改后 `stie.yaml` 对改后 schema 校验通过 | 执行结果见实现轮汇报 |
| V2 | 十篇渲染前后对比 | 十篇运行 `render_bios.py` 对比变更前后输出，核对三档作者统一及缺项跳过行为 | 执行结果见实现轮汇报 |
| V3 | P1/P3 检查 | P1、P3 check 均 pass | 执行结果见实现轮汇报 |
| V4 | 生成器语法结构 | `tools/metalayout.py` AST 解析通过 | 执行结果见实现轮汇报 |

## 8. 影响面

- **论文范围**：所有使用 stie profile 的论文（P1–P10）在下次重建后，文末作者信息节发生变化。
- **通信作者段**：邮编由与通信地址合写改为分列，与第一作者段渲染式一致。
- **其他作者段**：由四字段简式补全为统一字段序；缺值字段跳过，不编造。
- **构建产物**：既有 docx/pdf/zip/.eml 不回溯变更，需重建方同步更新。

## 9. 结论

本变更以用户裁定和 S17 为直接依据，按 PF-RV8 处理刊方明示与范本简式的冲突；三档作者统一使用 `_bio_full`，废止两套特例函数及对应配置键，rules_version 按 PATCH 升至 0.4.2。变更不触碰论文仓和并行引文改动。

## 10. 开放项

1. **论文侧重建 rollout 待派单**：九篇可建；P8 待杨礼飞七项字段补齐后再重建，各篇重建后同步更新 docx/pdf/zip/.eml。
2. **GC 编号占用提示**：今日 GC-2026-1117-04 被两个文件同时占用（构建产物命名重构与中文括号式文内引注形态），本记录取 -09；-08 据 P8 build-record R21 记载为参考文献类别准入改造（并行会话），编号去重由治理负责人裁定。

---

*GC-2026-1117-09。规则依据：AGENTS.md F9/F6；版式依据 PF-B3；著录基线 PF-RV8（刊方明示优先）；版本依据 PF-V1/PF-V3/PF-V5/PF-V6；变更类型：rules_version PATCH 0.4.1→0.4.2。*
