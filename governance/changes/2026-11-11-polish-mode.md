# 治理变更记录 GC-2026-1111-03：精修模式（Polish Mode）+ 投稿编写规范纳入精修与审核

- 日期：2026-11-11
- 编号：GC-2026-1111-03（**重编号**：`temp/polish-mode-change-plan-v0.2.0.md` 自编号 GC-2026-1111-02，与排版规范变更编号冲突；消解为排版沿用 02、本变更改 03——依据合并计划 v2.1 §1）
- 类型：新增模式规则（第六模式 polish，PF-PL1–PF-PL13）
- 规则依据：AGENTS.md F2/F9；上游计划 `temp/polish-mode-change-plan-v0.2.0.md`（已经两轮独立复核：glm 规则冲突视角 / minimax 可操作性视角，v0.2.0 为复核修订版）
- 用户指令（2026-11-11）："编写规范可加入精修要求中。待完稿后执行精修即可。"——新增 PF-PL13，并将试跑推迟至首次实际精修
- 流程状态：规则已落盘（未提交）。按 F9，提交前由未参与变更的独立子代理复核实际 diff 与验证结果
- 并发边界：与 GC-2026-1111-02（排版规范落地）同窗口落盘，文件集部分重叠（rule-index.yaml、AGENTS.md、templates/paper/*）；GC-02 记录第 3 节已标注逐文件归属，提交按变更编号分拆

## 1. 基线与版本

- rules_version：0.1.0 → 0.2.0（与 GC-02 同批，单次 bump；rule-index 与 project.yaml 同步）。bump 理由：新增 13 条 PF-PL 规则，PF-V1 追溯语义要求论文 paper.yaml 记录的 rules_version 能指向包含这些规则的版本。
- stage 载体：`schemas/paper.schema.json` 的 `stage` 枚举已有 `revision` 槽位（本变更不改 schema）。

## 2. 精确变更清单

| # | 文件 | 动作 | 内容 |
|---|---|---|---|
| C1 | `governance/polish.md` | 新建 | PF-PL1–PF-PL12 全文（v0.2.0 两轮复核版：准入隔离/术语前置约束/全局逻辑诊断与轨道判定/执行约束/重写轨道/写审分离/语义 Diff/首末衔接/合并回归/产物闭环/失效升级/负载可持续）+ **PF-PL13 投稿规范精修**（S1–S20 核对与修复，以各论文 writing-spec.yaml 为唯一真值源；含题录去重条款） |
| C2 | `governance/rule-index.yaml` | 编辑 | 注册 PF-PL1–PF-PL13（各带 review_roles）；rules_version 0.2.0 |
| C3 | `project.yaml` | 编辑 | modes 增 polish 条目（status: planned，注记"规则已落盘待首次执行"；stage 载体说明）；capabilities 增 `polish: partial`；rules_version 0.2.0 |
| C4 | `templates/paper/terms.md` | 编辑 | 末尾增"精修约束（Polish Constraints）"独立小节（独立表，不动主体表列结构；注明仅启用精修时填写；约束段优先于 Notes；O1 已决方案 A） |
| C5 | `schemas/paper.schema.json` | 不改 | stage 枚举已含 `revision` 槽位（v0.2.0 计划原 C5 沿袭；本轮补登记以消编号空洞） |
| C6 | `AGENTS.md` | 编辑 | F2 模式清单追加第 6 条 Polish mode（一句话定位，细则指向 governance/polish.md） |
| C7 | `templates/paper/reviews/README.md` | 编辑 | 增精修产物命名段（polish-r0/r1/r3/r4/rewrite-plan/issues/version-record/venue-refactor-note 与既有 R-{A..D} 命名空间的关系）+ PF-RV7 一句话 |
| C8 | `governance/changes/2026-11-11-polish-mode.md` | 新建 | 本记录 |

## 3. 对上游计划 v0.2.0 的修订（本轮登记）

- **A1 试跑推迟**：原 §10.2 "在 P4 单篇试跑第 0 步"改为**推迟至首次实际精修执行时进行**（用户 2026-11-11 指令：P4-P7 正在编写、精修待完稿后执行；对未完稿论文试跑术语提取无意义）。
- **A2 增补 PF-PL13**（用户指令"编写规范可加入精修要求中"）：精修第 2 步范围内加入投稿规范合规修复，核对清单 S1–S20（详见 polish.md PF-PL13）；修复属措辞/体例级（PF-PL4 零新增事实约束不变）；结论性改写（如压缩摘要致主张删减）按 PF-PL3 升级路径处理。PL13 清单同时作为 PF-RV7（GC-02）审核输入。
- **A3 真值源指针**：polish.md 引用 `writing-spec.yaml`（PF-W11 承载）与 `templates/layout/profiles/stie.yaml` 为投稿规范单一真值源，不在 polish.md 复制数值（避免两处真值）。
- **A4 D9 表述同步**：v0.2.0 计划中 "applicable_rules 追加 PF-PL1–PL12" 的表述在本轮落盘为 **PL1–PL13**。
- **PF-V1 语义澄清**：paper.yaml 的 rules_version 表示"当前生效规则版本"；最近一次审核实际所用版本以各报告头部记录为准（论文侧 venue-refactor-note 已按此登记）。

## 4. 设计要点（决策记录，全文见 v0.2.0 计划）

模式定位（第六模式，stage 载体 revision）；单论文单会话隔离；术语三态（locked/anchored 默认/banned）+ ≤20 项人工预算；轨道判定（章×段、只计 P0/P1、50% 固定阈值、盲复核仲裁、结构性硬伤直判重写轨）；五角色互斥（甲乙丙丁戊）；执行子代理类型按用户指定 general-purpose（2026-11-11）；朗读指标仅约束改写区域（≤40 字/≤3 层嵌套/公式引导句）；并行按锚点依赖图；重写轨三重防线（事实冻结/用户批准/占位清零闸）；合并回归 5a/5b 字节级口径 + 5c 清单（含 JSON Schema 校验与投稿约束复核）；出口固定流向 review（零实质改动为例外分支）。

## 5. 备选方案（已否决，全文见 v0.2.0 计划 §7）

融入 writing/review 模式、术语编号制、一次性 lock 文件、版本 bump 轨道固定映射、50% 阈值浮动——均否决。本轮新增否决：**推迟到完稿后再落盘精修规则**（用户已明示"编写规范可加入精修要求中"，且 RV7/PL13/writing-spec 需同源，推迟将使在写论文无所遵循）。

## 6. 风险与缓解（全文见 v0.2.0 计划 §8）

重写轨滥用（三重防线）；评审失效（PF-PL11 + 出口 review + 快照重建）；合并方向错误（字节级口径 + 非章区段保护）；人工判定衰减（默认态 + 预算 + 抽检）；并行锚点失效（依赖图 + 交界段整体归属）；占位流入投稿件（清零闸）。本轮新增：**PL13 与 RV7 双向引用的循环风险**——审核（RV7）发现的问题经精修（PL13）修复后仍须重走 review 闭环（出口固定流向），不允许"精修即终局"。

## 7. 恢复方式

回滚 = 删除 C1/C8（新文件）+ 反向应用 C2/C3/C4/C6/C7 的 diff；无数据迁移、无论文工作区改动。方案 A 若证明污染 terms.md，触发条件与迁移路径见 v0.2.0 计划 §9。

## 8. 验证方法与实际结果

1. 计划复核：两轮独立复核（v0.1.0→v0.2.0）已完成；本轮增量（A1–A4 + PL13）随合并计划 v2.1 再经两轮独立复核（处置对照合并计划 §10/§11）。
2. 规则一致性（实测 2026-11-11）：rule-index 共 81 条、无重复 ID；PF-PL1–13 与 governance/polish.md 文内条目一一对应；`governance/polish.md` 引用的 PF-W11/PF-RV7/PF-B14 均已在 rule-index 注册。
3. 模板一致性（实测）：terms.md 精修约束节存在且独立于主体表；reviews/README 命名段含 polish-* 全集；project.yaml modes 含 polish（planned）+ capabilities polish: partial。
4. 试跑：**推迟**至首次实际精修执行（§3 A1）；试跑数据归档要求不变（判定负载/候选准确率/判级一致性 → governance/changes/）。
4b. 准入机器闸（核验 P1-2 处置）：`python3 -I tools/paper.py validate --paper <P>` 提供 PF-PL1 条件① 的全量 jsonschema 校验（含 budget.confirmed 分支）；精修进入前必须 validate=pass。
5. 独立验证（F9 后置）：未参与变更的独立子代理核对 diff 与复跑 2–3。

## 9. 范围排除

- 本变更不含论文正文修改；待精修的内容级缺陷清单见 GC-02 记录开放项 8。
- `tools/paper.py` 合并能力（body split/merge 子命令）：另立治理变更，不阻塞本计划（v0.2.0 O4）。
- PF-B9 渲染过滤器：GC-01 开放项，不属本变更。
