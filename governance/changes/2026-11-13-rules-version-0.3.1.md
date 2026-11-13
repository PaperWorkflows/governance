# 治理变更记录 GC-2026-1113-03：规则版本 0.3.0 → 0.3.1（PF-B12 插图验证条文升版落账）

- 日期：2026-11-13
- 编号：**GC-2026-1113-03**（顺延 GC-2026-1113-02；02 为插图矢量化变更，提交 `3259220`/`cb783a1`/`75ae414`；01 已被 PDF 导出确定性线占用，见 GC-2026-1113-02 记录首部）
- 类型：版本号变更（**PATCH：0.3.0 → 0.3.1**；无新增规则号、无 rule-index 条目增删、无 schema/profile 改动）
- 计划版本：无独立计划草案——本变更为主会话对 **GC-2026-1113-02 §8/§9 开放项**（"rules_version 保持 0.3.0……将升版裁定留开放项"）的**裁定落账**；裁定内容与执行细则见主会话派单（2026-11-13）：按最相近先例做 PATCH 升版、只动 canonical 仓、不传播各篇 paper.yaml
- 规则依据：AGENTS.md **F9**（变更纪律：编号/基线与计划版本/精确变更清单/理由/备选/风险/恢复/验证）、**F3**（版本管理）、**F8**（规则索引）；版本语义 `governance/versions.md` **PF-V1**（规则追溯——论文 paper.yaml 记录的 rules_version 必须能指向包含其适用规则的版本）、**PF-V3**（版本变更记录）、**PF-V5**（提交分区：治理提交不含论文内容）、**PF-V6**（版本 bump 须在 commit body 记理由）；被升版规则正文：`governance/build.md` **PF-B12**（GC-2026-1113-02 增补的插图双层级验证条文，提交 `3259220`）
- 基线（2026-11-13 实施时实测）：治理仓 HEAD `75ae414`（fix(build): 题注定位器几何修正）；工作树仅他线 `authors/registry.yaml` 在途未提交（`git status --short` 实测，本提交**严禁 stage**）；论文侧九篇 `paper.yaml` 均 `rules_version: 0.3.0`（各篇构建时真实记录，manifest 已落账）
- 流程状态：主会话裁定（先例考证）→ **实施 + 自测（本记录收口）→ 独立核验（待主会话派单，F9 要求未经手变更的子代理复核后方可提交）**

---

## 1. 背景与裁定对象

- GC-2026-1113-02（插图矢量化，`3259220`）在 `governance/build.md` PF-B12 **增补了插图双层级验证条文**（docx 层 svgBlip 兜底断言 + PDF 层栅格预算/图位非空/位图引用登记语义），但当时未升 `rules_version`，理由记录于该变更 §9，并将升版裁定留作开放项（§8）；独立审查要求主会话就此裁定。
- 主会话先例考证结论（本记录直接采信，实施时已逐项复核，见 §2）：`ab0bdcc`（2026-11-12 构建修复）将 canonical `governance/rule-index.yaml` 的 rules_version 0.2.0→0.2.1 **且不传播各篇 paper.yaml**；`118b299`（新增 PF-B15/B16）0.2.1→0.3.0；`788d853`（GC-2026-1112-06 断言细化）未升版。
- **裁定**：按最相近先例（构建工具/规则修复 → PATCH 升版、只动 canonical），`rules_version` 0.3.0 → **0.3.1**；各篇 paper.yaml 不动；`tools/paper.py` 新论文 scaffold 缺省同步，使新论文绑定当前规则。

## 2. 先例考证（实施时逐项实测复核）

| 提交 | 日期 | 版本动作 | rules_version 相关文件指纹（实测 `git show --name-only` + diff） | 传播各篇 paper.yaml |
|---|---|---|---|---|
| `a63b477` | 2026-11-11 | 立 0.1.0 | `project.yaml`（+rules_version: 0.1.0）、`templates/paper/paper.yaml`（+null） | 否（当时论文仓未起） |
| `fc09407` | 2026-11-11 | 0.1.0→0.2.0 | `governance/rule-index.yaml` + `project.yaml` 同笔同步 | 否 |
| `ab0bdcc` | 2026-11-12 | 0.2.0→0.2.1 | `governance/rule-index.yaml` + `project.yaml` + `tools/paper.py`（`"rules_version": "0.2.0"`→`"0.2.1"`） | **否**（无任何 paper.yaml） |
| `118b299` | 2026-11-12 | 0.2.1→0.3.0 | `governance/rule-index.yaml` + `project.yaml` + `tools/paper.py`（新增 PF-B15/B16，MINOR） | 否 |
| `788d853` | 2026-11-13 | 未升版（保持 0.3.0） | 无（Compact 缩进断言 + profile/schema 新键，零规则正文修改） | — |
| GC-2026-1112-06（`26cc802` 等） | 2026-11-13 | 未升版（保持 0.3.0） | 无（记录 §1 明载"零治理规则正文修改"） | — |

- **实测结论一（升版依据）**：历史上每一次 rules_version 变更（`fc09407`/`ab0bdcc`/`118b299`）均将 `project.yaml` 与 `governance/rule-index.yaml` **同笔同步**；`governance/changes/2026-11-11-polish-mode.md` 亦明载"rule-index 与 project.yaml 同步"。派单枚举的三文件未含 `project.yaml`，与先例指纹不符——按派单约束"凡与裁定冲突的实测发现，按证据修正并报告"，本变更将 `project.yaml` 一并升版（§3.3 留痕）。
- **实测结论二（反先例不适用）**：两次未升版先例（`788d853`、GC-2026-1112-06）的共同特征是**零规则正文修改**；GC-2026-1113-02 则实际改动了 `governance/build.md` PF-B12 规则正文（增补插图验证条文），落入 GC-2026-1112-01 的升版触发面（"PF-B11/PF-B12 规则正文扩充 → PATCH 升版"，见 GC-2026-1113-02 §9 引述）。
- **实测结论三（为何当时未升、现在补）**：GC-2026-1113-02 §9 当时不升的直接约束是"任务文件域限定三文件、禁改他篇论文仓，升版传播不可在本变更内完成"；主会话现已裁定传播不必要（`ab0bdcc` 先例：canonical-only bump 是既定模式），约束解除，升版补行。

## 3. 精确变更清单（4 个文件，净 +1 行改动 ×3 + 新记录）

| # | 文件 | 变更 |
|---|---|---|
| 1 | `governance/rule-index.yaml` L2 | `rules_version: 0.3.0` → `rules_version: 0.3.1`（只改这一行） |
| 2 | `tools/paper.py` L290 | `build_paper_yaml(..., rules_version: str = "0.3.0", ...)` → `"0.3.1"`（scaffold 缺省，新论文经此绑定当前规则） |
| 3 | `tools/paper.py` L478 | `build_paper_yaml(..., rules_version="0.3.0", ...)` 调用点实参 → `"0.3.1"`（grep 实测全仓仅此一处额外硬编码；只改 L290 不改 L478 将使 scaffold 仍产 0.3.0，故一并改） |
| 4 | `governance/changes/2026-11-13-rules-version-0.3.1.md` | 本记录（新增） |
| 5 | `project.yaml` L3 | `rules_version: 0.3.0` → `0.3.1`（**证据补入项，偏离派单三文件枚举**，理由见 §2 实测结论一） |

**不改**：九篇论文仓任何文件（P1–P9 `paper.yaml` 保持 0.3.0）；`templates/paper/paper.yaml`（保持 0.3.0，理由见 §9-1）；`governance/rule-index.yaml` 规则条目；`governance/build.md` 等规则正文；`schemas/`；`authors/registry.yaml`（他线在途）；`temp/`（草案不入库）；`tools/paper.py` 其余逻辑。

## 4. 理由

1. **升版的实质触发**：GC-2026-1113-02 增补了 PF-B12 规则正文（插图双层级验证条文），PF-V1 要求论文侧记录的 rules_version 能指向包含其适用规则的版本；规则正文已变而版本号不变，等于版本声明与规则世界脱钩。
2. **PATCH 而非 MINOR**：无新增规则号、无 rule-index 条目增删、无 schema/profile 键变化（`118b299` 式 MINOR 触发面均不满足）；`ab0bdcc` 先例（构建工具/规则修复 → PATCH）是同型最近案。
3. **不传播各篇 paper.yaml**：各篇 0.3.0 是其构建时的真实记录，manifest 已落账；PF-V3 语义下版本记录不替代质量判断，且历史上 `ab0bdcc`/`118b299` 两次 canonical bump 均未传播各篇。下次各篇重建时 manifest 自然携带 0.3.1（build manifest 的 rules_version 取自 paper.yaml 与工具代际，见 `tools/paper.py` L3780 附近注记）。
4. **scaffold 缺省同步（L290 + L478）**：让此后新建论文绑定当前规则世界，避免新论文一出生即落后一个版本。

## 5. 备选与否准

| 备选 | 否准理由 |
|---|---|
| A. 不升版（保持 0.3.0，沿 GC-2026-1113-02 §9 原理由） | §9 原理由的核心约束（文件域内无法完成传播）已因主会话裁定解除；PF-B12 规则正文已实质扩充，落入 GC-2026-1112-01 升版触发面；且 GC-2026-1113-02 §8 已将升版裁定显式留白给主会话，维持不升版需新的实质理由而非路径依赖 |
| B. 升版并传播各篇 paper.yaml（GC-2026-1112-01 式全量联动） | 与最相近先例（`ab0bdcc`：canonical-only，零 paper.yaml）相悖；各篇 0.3.0 是真实构建记录，PF-V5 禁止治理提交混入论文内容，传播须九篇各自提交，超出本变更域；下次重建自然携带 |
| C. 只动 `rule-index.yaml`、不动 `project.yaml` 与 scaffold 缺省（派单字面枚举） | `project.yaml` 分叉将制造历史上从未出现的状态（§2 实测结论一：4/4 同步）；scaffold 缺省不同步则新论文仍绑定 0.3.0，违背升版目的 |
| D. 借机同步 `templates/paper/paper.yaml` | 非 bump 先例指纹成员（§9-1）；功能惰性（scaffold 第 8 步整体覆写 paper.yaml），留开放项由主会话另行裁定 |

## 6. 风险与边界

| 风险/边界 | 现状与缓解 |
|---|---|
| 新论文绑定 0.3.1 而现役九篇 manifest 仍记 0.3.0 | 预期行为（PF-V1 追溯的是各篇构建时规则）；工具代纪差异既有先例（GC-2026-1112-01 整改批次 §18：manifest 0.3.0 vs paper.yaml 0.2.1 并存且全部经现行断言验证） |
| `project.yaml` 偏离派单枚举 | 单行改动、可独立回退（§7）；已在本记录 §2/§3.5 显式留痕并进交付报告，主会话可否决 |
| `templates/paper/paper.yaml` 保持 0.3.0 与新世界不一致 | 功能惰性（§9-1 论证）；不阻止 scaffold 正确绑定；留开放项 |
| 版本声明与规则正文脱钩复发（本次即该模式） | 开放项建议：后续任何改动 `governance/` 规则正文的变更，收口时核对 rules_version（本变更自身即按此闭环） |
| 他线在途 `authors/registry.yaml` 被误 stage | 提交只显式 add 上述 4 文件（§3-1/2/3/4 + `project.yaml`），禁 `git add -A`/`commit -a`；提交前 `git status --short` 复核 |

## 7. 恢复方法（Recovery）

- **revert 优先**：本变更为单笔治理提交，`git revert <commit>` 整体恢复 0.3.0 世界（规则正文 PF-B12 条文不受影响——它在 `3259220`，属 GC-2026-1113-02），**禁止** `--hard` 与历史改写（F7）。
- 若仅否决 `project.yaml` 一项：`git revert` 后对该文件单行改回 0.3.0 重提，或直接 `git checkout ab0bdcc..HEAD -- project.yaml` 式取旧值前先确认无他线改动（当前 `project.yaml` 工作树干净，`git status` 实测）。
- 论文侧无回滚动作：九篇零改动。
- 工作区不回滚；无 temp 草案入库。

## 8. 验证方法与结果（2026-11-13 实施时实测）

| # | 验证项 | 方法 | 结果 |
|---|---|---|---|
| a | 语法完整 | `python3 -I -m py_compile tools/paper.py` | 通过 |
| b | scaffold 缺省生效 | `python3 -I` 导入 `tools/paper.py` 直跑 `build_paper_yaml(...)` 检视 `rules_version` 行 | 输出 `rules_version: 0.3.1`（缺省路径与 L478 实参路径一致） |
| c | 论文侧不破 | `python3 -I tools/paper.py check --paper` 对 P1（并扩测九篇） | P1 pass（退出码 0）；九篇全 pass（只读校验，零写入） |
| d | 全仓对账 | `grep -rn rules_version` 覆盖 instruction.git 与九篇论文仓 | canonical/project/paper.py×2 为 0.3.1；九篇 paper.yaml 均 0.3.0；`templates/paper/paper.yaml` 0.3.0（§9-1 预期）；`governance/changes/` 历史记录含 0.3.0 字样不属声明位 |
| e | 提交域 | 提交前 `git status --short` + `git diff --cached --name-only` | 仅 4 个目标文件入暂存区；`authors/registry.yaml` 未 stage |

## 9. 开放项 / 注记

1. **`templates/paper/paper.yaml`（rules_version: 0.3.0）不随本变更升版**：① 两次版本 bump 先例（`ab0bdcc`、`118b299`）的文件指纹均不含该文件——其现值 0.3.0 系 `0c0bc19`（GC-2026-1112-01 整改批次）事后追齐，非 bump 指纹成员；② 功能惰性——scaffold 第 7 步复制模板后，第 8 步以 `build_paper_yaml` 生成内容整体覆写 `paper.yaml`（`tools/paper.py` L472–482），模板该行永不进入新论文；③ 如主会话要求模板与世界完全对齐，单行改动可随时补做（风险为零，收益为声明整洁）。
2. **独立核验（F9）待主会话派单**：本记录收口时未经手子代理复核；提交与核验顺序按主会话编排执行。
3. **版本声明脱钩模式**：本次即"规则正文先落、版本号后补"模式；建议后续规则正文变更在其变更记录中显式判定 rules_version 去留（GC-2026-1113-02 §9 做了理由留白但未裁定，本变更补裁）。

---

*GC-2026-1113-03。规则依据：AGENTS.md F9/F3/F8；版本依据 governance/versions.md PF-V1/PF-V3/PF-V5/PF-V6；被升版规则正文 governance/build.md PF-B12（GC-2026-1113-02，提交 3259220）；先例考证 ab0bdcc/118b299/fc09407/788d853（git 实测）；开放项来源 GC-2026-1113-02 §8/§9；规则版本 0.3.0 → 0.3.1（PATCH）。*
