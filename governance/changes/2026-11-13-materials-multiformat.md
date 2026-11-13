# 治理变更记录 GC-2026-1113-04：materials 子系统多格式识别修复（防数据摧毁 + 实查放行闸）

- 日期：2026-11-13
- 编号：**GC-2026-1113-04**（编号占用实测核对：01 被另一工作线 PDF 导出确定性变更占用，提交 `37a6037`/`dc3e658`；02 为插图矢量化 `3259220`/`cb783a1`/`75ae414`；03 为 rules_version 0.3.1 升版 `ea6c1c6`；04 空位，本记录启用）
- 类型：工具缺陷修复（`tools/paper.py` materials 子系统；**零规则正文修改**，rules_version 保持 **0.3.1**，理由见 §8）
- 计划版本：无独立计划草案——主会话已实测定位缺陷（`_load_materials` 只认一种格式），本记录为实施 + 自测 + 独立核验收口
- 规则依据：AGENTS.md **F9**（变更纪律：编号/基线与计划版本/精确变更清单/理由/备选/风险/恢复/验证）、**F5/F6**（论文侧工作由受派子代理执行、最小改动）；**PF-B12**（落地校验——凡不可校验即不得静默放行，本缺陷的直接违反项）；**PF-B3**（无静默降级）；版本依据 `governance/versions.md` PF-V3/PF-V5（治理提交不含论文内容）
- 基线（2026-11-13 实施时实测）：治理仓 HEAD `ea6c1c6`（chore(governance): rules_version 0.3.0→0.3.1）；`git status --short` 仅他线 `authors/registry.yaml` 在途未提交——**本提交严禁 stage**；`tools/paper.py` 5 932 行；论文侧九篇 `materials.yaml` 三种形态并存（只读核查，零改动）
- 流程状态：主会话缺陷定位 → **实施 + 自测（本记录收口）→ 独立核验（本记录执行，含对 GC-2026-1113-03 的三项订正，见 §10）**

---

## 1. 缺陷定位（主会话实测 + 本记录复现）

`_load_materials`（修复前 L864–875）只认一种格式——dict 且含 `materials:` 键；其余一律 `except`/类型不符都**静默返回 `{"materials": []}`**。全库九篇 `materials.yaml` 实际三种形态：

| 形态 | 论文 | 结构 | 条目数字段 |
|---|---|---|---|
| ① `materials:` dict | P1/P2/P3（4/4/3 条） | `materials:` 键下 list | `material_id`/`identifier`/`title` |
| ① `materials:` dict | P4/P5（4/15 条） | 同上 | `id`/`title`，**无 identifier** |
| ② keyed dict | P6（10 条） | `primary_source:`/`experiment_data:`/`figures:`/`tables:` 四顶层键，键下 list | 仅 `id`（figures/tables 另带 `sha256_png`/`sha256_svg`） |
| ③ 顶层 list | P7/P8/P9（12/3/1 条） | 文档级 list | 仅 `id`/`path`/`sha256`，**无 identifier/title** |

三条后果链（均有实测证据）：

1. **数据摧毁（主缺陷）**：`cmd_materials_add` 对 P6–P9 先读成空 list，新条目 append 后经 `_save_materials`（只写 dict）**整体覆写文件**——P6 的 10 条、P7 的 12 条等既有登记被静默摧毁，且 `materials add` 退出码为 0，无任何告警。
2. **虚假放行（PF-B12 违反）**：`cmd_materials_check` 对 P6–P9 `total=0` 恒 pass；YAML 解析异常被 `except: return {"materials": []}` 吞掉（坏文件同样"pass"）。
3. **虚假重复（同类误报）**：判重只认 `identifier`。P4/P5 条目无该字段 → 全部命中 `None` 键，修复前实测 P4 fail（4 条报 3 组重复）、P5 fail（15 条报 14 组重复）——纯字段缺失造成的全量误报。P7/P8/P9 若直接放行该逻辑同样会全量误报。
4. `cmd_materials_list`/`cmd_materials_debate` 对 P6–P9 报 0 条。

## 2. 精确变更清单（函数级；`tools/paper.py`，净 +201/−44 行）

| # | 位置（修复后行号） | 内容 |
|---|---|---|
| 1 | L864 `MaterialsFormatError`（新增异常类） | 解析失败/不可读/结构不可识别时抛出，错误信息点名文件与底层异常；替代旧 `except: return {"materials": []}` 静默路径 |
| 2 | L871 `_DEDUP_KEY_FIELDS` + L874 `_entry_dedup_key()`（新增） | 判重键回退链 `identifier → id → title → sha256`；四字段全缺（None/空）或条目非 dict 返回 None——**跳过该条判重**，杜绝"都缺字段"误报成全量重复 |
| 3 | L888 `_entry_label()`（新增） | 条目单行可读描述（debate 上下文用），容忍非 dict 条目与缺失字段 |
| 4 | L897 `_load_materials()`（重写） | 三形态识别并归一：dict+`materials:` → `"materials"`；dict+其他顶层键 → `"keyed"`（键下 list/dict 逐块收集）；顶层 list → `"list"`；空文件/纯注释 → `"empty"`；文件缺失 → `"missing"`。返回 `{"format", "raw", "entries", "blocks"}`——`raw` 保留原始数据供写回，`blocks` 仅 keyed 形态非空（跨块不合并）。解析失败/`materials` 键非 list/顶层标量 → 抛 `MaterialsFormatError` |
| 5 | L957 `cmd_materials_add()` | 防摧毁闸：`keyed`/`list` 形态与解析失败一律拒绝（exit 2，错误信息说明仅支持 `materials:` dict 形态、提示手工登记或先转换格式），**绝不写盘**；`materials` 形态行为不变（identifier 判重、`MAT-` 编号、退出码语义不变），写回时用 `dict(raw)` 保留原始其他顶层键，内部标记不泄进 YAML；`missing`/`empty` 允许新建 |
| 6 | L1020 `cmd_materials_list()` | 三形态诚实计数：`list` 直接给条目；`keyed` 按键分组 `blocks`（含 primary_source 等分块条目）+ 聚合 `count`；`--type` 过滤对扁平列表与分块同步生效；输出新增 `format` 字段 |
| 7 | L1057 `cmd_materials_check()` | 三形态实查：`list` 查该 list；`keyed` 对每个顶层键下的 list **逐块独立判重**（figures/tables 与 primary_source 语义不同，跨块不合并）；判重键走回退链；title 近重比较容忍 None；输出报告 `format`、真实 `total` 与 keyed 分块计数；解析失败 → `status=fail` + error（exit 2），不再空过 |
| 8 | L1132 `cmd_materials_debate()` | 三形态都可构建上下文（keyed 按块分组列出）；无条目时报错行为不变（exit 2，同一消息）；解析失败 → error exit 2 |

**附带治理收尾**（同提交）：`governance/changes/2026-11-13-rules-version-0.3.1.md` 据独立核验结论订正（§8c"九篇全 pass"、§3 表头计数、§2 `fc09407` 行补 `tools/paper.py` 指纹、§9-1 标记模板已追齐，详见该记录首部订正块与 §10）；`templates/paper/paper.yaml` `rules_version: 0.3.0 → 0.3.1`（GC-2026-1113-03 §9-1 开放项关闭）。

**不改**：九篇论文仓任何文件（只读核查，`materials.yaml` md5 前后一致）；条目 schema；materials 命令集（不加新命令）；`_save_materials`；`governance/` 规则正文；`authors/registry.yaml`（他线在途）。另注：`cmd_review_debate` 函数体内 L1957–2101 存在一段 `return` 之后的死代码（旧 CLI parser 副本，含 materials 旧子命令注册）——不可达、不影响行为，**不在本变更范围**（改动最小化），留档备忘。

## 3. 理由

1. **数据摧毁不可接受**：`materials add` 以退出码 0 静默销毁 P6–P9 的既有登记，违反最小惊讶与 PF-B3（无静默降级）；修 check 不修 add 则主缺陷仍在（见 §5 备选 A）。
2. **不可校验不得静默放行（PF-B12）**：解析失败与结构不可识别必须变成 exit≠0 的显式失败；六/七/八/九篇从 `total=0` 假 pass 转为实查，是诚实的代价而非回归。
3. **判重键稳健化是实查的前提**：不回退键名，P7/P8/P9（仅 `id`）与 P4/P5（仅 `id`+`title`）一实查就全量误报，闸门会因狼来了而失效；字段全缺的条目跳过判重而非计入重复。
4. **保留原始数据（`raw`）**：add 只被允许在 `materials:` dict 形态追加，其他形态拒绝执行——这保证了"拒绝"策略永远不需要写盘，也就不需要格式转换器；`raw` 仅用于 materials 形态写回时保留其他顶层键。

## 4. 设计要点

- **形态即契约**：`_format` 标记让调用方对"能不能 add、怎么 check"有一处裁决；add 的支持面刻意保持为"新建 + `materials:` dict"，与派单一致，不引入转换逻辑。
- **跨块不合并**：P6 的 `figures`/`tables` 与 `primary_source` 语义不同（id 命名空间不同），合并判重会产生跨命名空间假重复；分块计数同时让登记结构可见。
- **空文件/缺失文件不算失败**：空登记是合法状态（`check` 报 `total=0` pass，与修复前一致）；论文级 `check` 的 required_paths 已独立把关 `materials.yaml` 存在性。

## 5. 备选与否准

| 备选 | 否准理由 |
|---|---|
| A. 只修 check/list，不动 add（把 add 的格式限制留给用户自觉） | **否准**：add 的数据摧毁是主缺陷（§1.1），且它以退出码 0 运行——不修等于保留一条静默毁数据路径；只修 check 连"destroyed 后无人知晓"都发现不了 |
| B. add 对 keyed/list 形态做自动格式转换后追加 | 否准：转换等于替用户决定登记 schema（P6 四键语义、P7 条目字段均与 `materials:` 不同），转换本身可能引入新错误；拒绝执行 + 明确错误信息是更小且可审计的动作 |
| C. 解析失败仍返回空、仅在 check 里提示 | 否准：PF-B12 要求不可校验不得静默放行；list/debate/add 同样需要失败信号，统一在 loader 层抛异常、各调用方转 exit≠0 是单一裁决点 |
| D. 判重只按 identifier，缺失即跳过全部条目 | 否准：P7/P8/P9 将无任何判重覆盖；回退链 + 全缺跳过以最小代价获得真实覆盖且不误报 |

## 6. 风险与边界

| 风险/边界 | 现状与缓解 |
|---|---|
| P6–P9 从"空过"转为实查，可能暴露存量登记问题 | **处理原则：如实报告，不改论文文件**。本次实查结论：P6（10 条）/P7（12 条）/P8（3 条）/P9（1 条）**均无重复**（pass）；若未来实查发现真实重复/缺失，按同一原则报告，由主会话裁向论文线处理 |
| P4/P5 判重结论从 fail 翻转为 pass | 非放水：旧 fail 是 `identifier` 全缺导致的全量误报（4 条报 3 组、15 条报 14 组）；新结论按 `id` 判重（P4 `mat-001..004`、P5 `source_doc` 等 15 个 id 均唯一），title 近重比较亦无命中 |
| add 支持面收窄（P6–P9 不能再 `materials add`） | 有意为之：这些文件的登记由各论文线手工维护（P6/P7/P8/P9 的条目带 sha256/status 等字段，本就超出 add 的 schema）；错误信息指明替代路径（手工登记或先转换格式），且不写盘 |
| `_load_materials` 返回结构变化（`format`/`raw`/`entries`/`blocks` 取代裸 dict） | 私有函数，全仓调用方仅本子系统四个 cmd_（已同笔更新）；无外部消费者（grep 实测 `duplicate_identifiers` 等输出键无仓外消费） |
| 他线在途 `authors/registry.yaml` 被误 stage | 提交只显式 add 4 个目标文件，禁 `git add -A`/`commit -a`；提交前 `git status --short` + `git diff --cached --name-only` 双重复核（§9 验证 e） |

## 7. 恢复方法（Recovery）

- **revert 优先**：本变更为单笔提交，`git revert <commit>` 即恢复旧 loader 行为（PF-B12 违反与数据摧毁路径随复原，属预期回退成本）；**禁止** `--hard` 与历史改写（F7）。
- 论文侧无回滚动作：九篇零改动（md5 实测一致）。
- 治理收尾两笔可独立回退：`templates/paper/paper.yaml` 单行改回 0.3.0；GC-2026-1113-03 记录的订正块可整段删除（原始文本在 git 历史中）。
- /tmp 下的验证副本（`/tmp/matsim/`、`/tmp/headcheck/`）为一次性测试产物，随 `/tmp` 清理，不入库。

## 8. rules_version 不升版的理由

本笔为工具缺陷修复，**零规则正文修改**（`governance/` 下规则文件未动一字）。按 GC-2026-1112-06 先例（`788d853`：零规则正文修改不升版）与 GC-2026-1113-03 §2 实测结论二（未升版先例的共同特征即零规则正文修改），rules_version 保持 **0.3.1**。PF-B12 是本笔援引的既有规则（GC-2026-1113-02 落成、GC-2026-1113-03 升版承载），本笔是其执行面修复，不产生新的规则声明。

## 9. 验证矩阵（2026-11-13 实测，`python3 -I`）

| # | 验证项 | 方法 | 结果 |
|---|---|---|---|
| a | 语法完整 | `python3 -I -m py_compile tools/paper.py` | 通过 |
| b | 九篇 list 诚实计数 | `materials list --paper` ×9 | P1 materials/4、P2 materials/4、P3 materials/3、P4 materials/4、P5 materials/15、P6 keyed/10（primary_source 1 + experiment_data 1 + figures 4 + tables 4）、P7 list/12、P8 list/3、P9 list/1 |
| c | 九篇 check 实查 | `materials check --paper` ×9 | P1–P5 pass（P4/P5 由修复前 fail 翻转，理由见 §6）；P6–P9 pass 且 total 为 10/12/3/1（修复前恒 0 假 pass）；均无真实重复 |
| d | add 防摧毁（P6–P9 副本） | 副本置于 `/tmp/matsim/<paper>/`（仅 materials.yaml），跑 `materials add` | P6 keyed、P7/P8/P9 list 全部 exit=2 拒绝，错误信息点名形态与替代路径；四副本 md5 逐一比对**字节不变** |
| e | add 既有行为不破（P1 副本） | 同上对 P1 副本 add | exit=0，`MAT-0005` 追加成功，4→5 条，原 4 条原样保留；重复 identifier 再 add → exit=1 duplicate |
| f | 解析失败不空过 | `/tmp/matsim/broken/` 造语法错误 materials.yaml，跑 list/check | list exit=2 error（点名文件 + ParserError 行列）；check exit=2 `status=fail` + error |
| g | 判重键稳健化（合成用例） | `/tmp/matsim/duplist`（list 内 `id=X-1` 两条）、`/tmp/matsim/dupkeyed`（figures 内 `fig-a` 两条 + tables 内同名一条） | duplist fail 且仅报 `id=X-1`；dupkeyed fail 且仅报 figures 块内 `fig-a`——**跨块同名不合并**，验证分块判重 |
| h | 边界形态 | 缺失文件 / 空文件（纯注释）/ `materials:` 键非 list / debate 无条目 | missing 与 empty：list count=0、check pass（与修复前一致）；add 可新建；debate 无条目 exit=2 消息不变；解析失败 debate exit=2 |
| i | 论文级回归 | `check --paper` 跑 P1 与 P8 | 均 pass（该命令只验 materials.yaml 存在性，L763 required_paths，零写入） |
| j | 论文侧零改动 | 九篇 `materials.yaml` md5 修复前后比对 | 全部一致 |
| k | 提交域 | 提交前 `git status --short` + `git diff --cached --name-only` | 仅 4 个目标文件入暂存区；`authors/registry.yaml` 未 stage |

## 10. 独立核验注记（对 GC-2026-1113-03 的订正，同笔落账）

本记录执行时按派单对 GC-2026-1113-03（`governance/changes/2026-11-13-rules-version-0.3.1.md`）做了三项订正 + 一项开放项关闭，证据：

1. **§8c**：`git archive HEAD` 干净快照直跑 `check --paper` 九篇——P1–P8 pass；**P9 fail 为存量问题**（`body_chapters`：`body/` 下缺 01-introduction…06-conclusion 全部 6 个骨架成员；`metadata`：`authors.yaml#authors.'author_e'` bio 缺 address 项，venue S17）。HEAD 原码同样 fail，与 0.3.1 升版（只动 rule-index/project/paper.py×2/记录）无关。（注：`cmd_check` fail 时退出码为 0 是 HEAD 既有行为，与本笔无关，不在本变更范围。）
2. **§3 表头**："4 个文件，净 +1 行改动 ×3"与表 5 行不符；`project.yaml` 并入主表后订正为"4 个文件、表 5 行；净 +1 行改动 ×4 + 新记录"。
3. **§2 先例表**：`git show fc09407 --stat` 实测该提交同笔改 `tools/paper.py`（+467/−43，含 scaffold 缺省 `"rules_version": "0.2.0"`），补入该行指纹列。
4. **§9-1**：`templates/paper/paper.yaml` 由本笔追齐至 `0.3.1`，开放项标记"已追齐"（关闭）。

---

*GC-2026-1113-04。规则依据：AGENTS.md F9/F5/F6；PF-B12（落地校验，凡不可校验即不得静默放行）/PF-B3；版本依据 governance/versions.md PF-V3/PF-V5；基线 ea6c1c6；先例 GC-2026-1112-06（零规则正文修改不升版）；materials 子系统多格式修复（净 +201/−44 行，tools/paper.py），rules_version 保持 0.3.1。*
