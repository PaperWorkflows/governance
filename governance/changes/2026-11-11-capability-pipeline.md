# 治理变更记录 GC-2026-1111-01：P1/P2/P3 全流水线执行沉淀的治理能力修订

- 日期：2026-11-11
- 编号：GC-2026-1111-01
- 类型：治理能力修订（project.yaml 模式状态、版式实现载体、schema 增量扩展、模板缺陷修复、骨架状态表刷新）
- 规则依据：AGENTS.md F9（治理变更纪律，本记录按其九要素编制）、F5（治理任务由主会话或受派子代理执行）、F6（最小改动）；layout 语义依据 governance/build.md PF-B3/PF-B10。
- 流程状态：本记录写入磁盘（未提交）。按 F9，提交前由未参与变更的独立子代理复核实际 diff 与验证结果。

## 1. 基线（Baseline）与计划版本

- rules_version：0.1.0（project.yaml 与 governance/rule-index.yaml 一致），本变更后保持 0.1.0——本变更不修改任何规则正文与 rule-index.yaml 条目，仅补实现载体与执行状态；若独立验证判定需 bump，须另行变更记录。
- git 基线：instruction.git（master）截至本记录起草时**尚无任何提交**，全部治理文件为未跟踪工作树文件，故无更早 HEAD hash 可引；本变更以该工作树状态为基线，本记录所列文件将随首个治理提交入库。
- 论文侧基线：P1-SETDEBATE-20251110、P2-LAYERGOV-20251110、P3-SPATIAL-20251110 均 paper_version 0.3.1，各自完成 REL-0001（P3 另有 REL-0002）docx+pdf 构建，产物在各论文 output/REL-*（含 current.json）。

## 2. 精确变更清单（逐文件）

| # | 文件 | 类型 | 内容 |
|---|---|---|---|
| 1 | `project.yaml` | 修改 | `modes.research.status` 与 `modes.writing.status` 由 `planned` 改为 `implemented`，并在两者 description 行尾加注释 `# verified via P1/P2/P3 pipeline 2026-11-11`；`capabilities` 各项（均已 implemented）与其余字段不动 |
| 2 | `templates/layout/registry.yaml` | 新建 | PF-B10 三层版式实现注册表：结构说明注释 + `schema_version` + `profiles.draft`（`file: profiles/draft.yaml`、`kind: draft`、`layer: L0`、`description: L0 project draft profile`）；注释载明 L1 venue profile 扩展约定与 `layout_profile` 指向校验口径 |
| 3 | `templates/layout/profiles/draft.yaml` | 新建 | L0 draft profile：`profile: draft`、`kind: draft`、`page`（A4、25.4mm 四边边距）、`typography`（`body_pt: 12`、`line_spacing: 1.5`、`east_asia_font: "Noto Serif SC"`；`latin_font` 缺省并以注释说明回退口径） |
| 3a | `schemas/layout-profile.schema.json` | 修改 | 增加可选对象键 `typography`（子键 `body_pt`/`line_spacing`/`east_asia_font`/`latin_font`，全部 optional、带 description、子级 `additionalProperties: false`）；顶层 `required`/`additionalProperties` 不动；纯增量扩展 |
| 4 | `templates/paper/build/layout.yaml` | 修改 | 修复散文缺陷：原第 3–4 行散文未加 `#`，整文件解析为字符串标量；重写为合法 YAML 对象（`profile: draft`、`kind: paper`、`page` A4 + 25.4mm×4），与三篇论文修复版一致；原散文转注释并登记缺陷说明 |
| 5 | `SKELETON-PLAN.md` | 修改 | 仅第 9 节状态表"构建管道（docx/PDF）"与"审核派发"两行由"🔴 未实现"改为"✅ 已实现"并注明证据（P1/P2/P3 构建与审核闭环、GC 编号）；其余行（含 MCP/Skill、.gitignore 模板、references/ 子目录）不动 |
| 6 | `governance/changes/2026-11-11-capability-pipeline.md` | 新建 | 本记录 |

未改动：AGENTS.md、CLAUDE.md、governance/*.md 规则正文、governance/rule-index.yaml、schemas/author.schema.json、schemas/paper.schema.json、templates/paper/ 其余文件、tools/、authors/。

## 3. 理由（Rationale）：流水线执行证据

本次 P1/P2/P3 全流水线（实验→配图→写作→四视角审核→修复闭环→构建 docx+pdf）实际执行暴露并沉淀以下治理缺口，各论文 reviews/20261111-round2/closure.md 第三节（P2 为处置表 transferred-to-governance 行）已登记为移交治理缺陷：

- **证据（论文仓库 commit 与 reviews 路径）**：
  - P1-SETDEBATE-20251110：`9ca1eea`（round2 修复闭环 0.3.0→0.3.1）、`c62a8e3`（REL-0001 构建 v0.3.1）、`70e3db1`（公式渲染修复）；`reviews/20261111-round2/{RA,RB,RC,RD,closure}.md`。
  - P2-LAYERGOV-20251110：`8dfa6ab`（round2 修复闭环 v0.3.1）、`baf244b`（REL-0001 构建 v0.3.1）；`reviews/20261111-round2/`。
  - P3-SPATIAL-20251110：`aab53b6`（round2 修复闭环）、`c910564`（REL-0001 构建）、`22ac7bf`（REL-0002 视觉修复重建）；`reviews/20261111-round2/`。
- **变更 1（modes 状态）**：research 模式（实验复跑落证、数据处理）与 writing 模式（图文集成、正文生成与润色）已在三篇论文实际执行并推进 stage，`planned` 与事实不符；build/review 两模式此前已 implemented，capabilities 全部已 implemented，均不动。
- **变更 2/3（registry + L0 profile）**：P1 closure 第三节 RD-02、P2 closure RD-F2、P3 closure RD-03 均登记 `templates/layout/registry.yaml` 与 L0 draft profile 缺失（`paper.yaml.layout_profile: draft` 指向不存在的注册项），属 PF-B10 实现载体缺口，论文层无权亦无落点代建。
- **变更 3a（schema typography）**：P1 closure 第三节 RD-02 关联项登记 schema 无 12pt/1.5 倍行距键位（`additionalProperties: false`），草案默认值只能以注释登记；PF-B3 明示"12pt body, 1.5x line spacing (overridable)"，故 typography 增量为**非结构身份键**（可被上层覆盖），page/citation/formulas 等结构身份键语义不变。
- **变更 4（模板 layout.yaml）**：三篇论文原 build/layout.yaml 为同型散文 stub（解析为字符串标量、不满足 schema），已逐 paper 修复（P3 closure RD-03 记 fixed；P2 closure RD-F1）；治理仓库模板 stub 未同步，属同型缺陷，本变更使其与论文修复版一致。

## 4. 备选方案（Alternatives，未采纳）

1. **paper.py 新增 build 子命令**（一键构建 docx/pdf，内建 PF-B4 快照、PF-B5 暂存、PF-B7 manifest）：工作量大（快照校验和、原子发布、发布锁均需实现与测试），且 PF-B9 渲染过滤器未落地，先落子命令会把已知输入缺陷固化进工具链；当前三篇论文以受派子代理 + 固定 pandoc 管线完成构建并留有 REL 产物与 manifest 佐证。列入开放项第 4/5 条。
2. **paper.py 渲染指令过滤器（PF-B9）**：过滤语义（render-note 剥离、render-spec 单 JSON 校验、散文句/未闭合容器=失败、V1–V6 自检报告）需独立设计与测试，不宜与本批数据文件混改；论文层输入已合规化（P2 closure RD-F6 记录）。列入开放项。
3. **顺带修订 author.schema.json / paper.schema.json**（postal_code/roles、title_en）：超出本变更授权清单（F6 最小改动），且涉及作者信息确认流程，列为开放项第 2/3 条。

## 5. 风险（Risks）与处置

1. **schema 扩展不兼容**：`typography` 为可选键、纯增量，已实际验证向后兼容（三篇论文 layout.yaml 不含新键，对扩展后 schema 校验全部通过；改前基线亦通过，见 §7）。
2. **registry 语义漂移**：registry 仅登记 name→file 映射，语义以 governance/build.md PF-B3/PF-B10 为准；registry 当前无工具消费（tools/paper.py 不读取），工具链落地前三层合并靠流程执行，该局限在 §8 如实登记。
3. **模式状态提前风险**：research/writing 状态以实际执行证据（§3 commit 与 reviews 路径）为据，非预期性声明。

## 6. 恢复方式（Recovery）

本变更随单一治理提交入库（PF-V5 纯治理分区）；恢复方式为对该提交执行 `git revert`（单提交、不改写历史，符合 F7）。新建文件（registry.yaml、draft.yaml、本记录）随 revert 一并移除；三篇论文工作区不回滚（F7 保留现场）。

## 7. 验证方法（Verification）与实际结果

执行环境：`python3 -I`，jsonschema 4.19.2（Draft-07）。验证脚本为只读校验，未改动论文工作区。

1. **基线（schema 修改前）**：三篇论文 build/layout.yaml 对改前 schema 校验 → 全部 PASS（解析为 dict，键 profile/kind/page）。
2. **schema 修改后 jsonschema 校验** → 全部 PASS：
   - `templates/layout/profiles/draft.yaml`（含 typography 键）→ PASS；
   - `templates/paper/build/layout.yaml` → PASS（修复后为对象；修复前解析为 `str` 标量，缺陷已留痕于 §3）；
   - 三篇论文 `papers/{P1-SETDEBATE-20251110,P2-LAYERGOV-20251110,P3-SPATIAL-20251110}/build/layout.yaml`（不含 typography 键）→ PASS，证明扩展向后兼容；
3. **YAML 解析**：`templates/layout/registry.yaml` → dict，`profiles` 含 `draft` 条目 → PASS。
4. **现有 check 工具回归**：`python3 -I tools/paper.py check --paper <P1/P2/P3>` → 三篇 overall `pass`，无失败子项。
5. **独立验证**：独立子代理复核实际 `git status`/`git diff` 并复跑上述 1–4 后方可提交（F9）。

## 8. 开放项（Open Items，如实登记）

1. **experiments/runs/runs/ 嵌套副本清理**（P1 closure 第三节第 6 条，RB-6）：待授权清理；清理时须在 record.yaml notes 登记。
2. **author.schema.json 与模板/tools 生成格式冲突**（P1 closure 第三节第 3 条）：schema（additionalProperties: false）缺 `postal_code`/`roles`，而 `templates/paper/authors.yaml` 与 `tools/paper.py` 生成格式含该二字段（P1 authors.yaml 实际含 `postal_code: null`）；需治理层对齐，届时可按用户确认恢复邮编登记。
3. **paper.schema.json 缺 `title_en`**（P1 closure 第三节第 4 条）：双语论文（bilingual_abstract: true）所需英文题名无法按 schema 登记。
4. **paper.py 渲染指令过滤器与 cmd_build_docx 输入缺陷**（P2 closure RD-F5/RD-F6，PF-B9 治理级过滤器未落地）：过滤器与 V1–V6 自检未实现；`cmd_build_docx` 输入含 paper.md+README 重复且未设 `--resource-path=<论文根>`。构建前置条件已登记于 P1/P2 build/layout.yaml 注释。
5. **paper.py profile 读取/合并/覆写日志**（P2 closure RD-F2 工具侧剩余，PF-B10）：本变更补齐数据载体（registry + L0 profile），工具侧三层合并、键级覆写日志（old/new/source-layer）与 registry 消费仍开放。
6. **SKELETON-PLAN 第 9 节剩余行**：本变更已将"构建管道（docx/PDF）""审核派发"两行刷新为已实现（见 §2 #5）；"MCP/Skill 配置""论文仓库 .gitignore 模板""冗余 references/ 子目录"仍为未实现/待决策，不在本变更范围。
