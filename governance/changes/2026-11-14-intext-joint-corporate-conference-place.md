# 治理变更记录 GC-2026-1114-02：联合团体著者文内引注分隔登记（citation.in_text_forms.joint_corporate_separator）+ 会议论文条目"会议地点"机械核对项（PF-RV7）

- 日期：2026-11-14
- 编号：GC-2026-1114-02
- 类型：治理能力修订（venue profile 新增 citation.in_text_forms.joint_corporate_separator 可选子键 + schema 同步 + PF-RV7 机械核对清单增一项 + verify_layout 基线剥离补行 + rules_version PATCH 升版 + 论文侧铺开三档处置政策待派单）
- 计划：`temp/GC-2026-1114-02/plan.md`（**计划版本 v0.2.0**；v0.1.0 为初稿，round 1 独立复核 FAIL（P1×1/P2×1/P3×5，F1–F7）整改升 v0.2.0，round 2 独立复核 PASS-with-notes（唯一 P3：N1——P9 自然人次双著者顿号 5 处实为 7 处，随本执行批订正 plan §2.1 E6 与 §10 开放项 6），两轮复核记录存 `temp/GC-2026-1114-02/`）；本记录按 plan v0.2.0 §3 精确变更清单由原计划起草人写盘（2026-11-14）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、F5、F6（最小改动）；版式 PF-B3/PF-B11/PF-B12/PF-B13；著录基线 PF-W11；真实性 PF-W1；核验入口 PF-RV7/PF-RV8；版本规则 PF-V1/PF-V3/PF-V5/PF-V6
- 规则版本：**0.3.2 → 0.3.3（PATCH，主会话裁定）**

---

## 1. 基线（Baseline）

- **git 基线（写盘时刻）**：治理仓 HEAD `61d04bf`（docs(governance): GC-2026-1112-06 §9 第14项；其 parent 为 `2b7b06f` = GC-2026-1114-01 提交；工作树除本变更 8 个已跟踪文件外干净）。**基线偏移说明**：派单阶段测量基线为 `2b7b06f`，其后并发治理线提交 `61d04bf` 仅改 `governance/changes/2026-11-13-metadata-driven-layout.md`（+8 行纯记录追加，`git show 61d04bf --stat` 实测），与本变更 9 文件零交集。
- **rules_version 前后**：0.3.2 → **0.3.3（PATCH）**。同步五处（四文件）：`project.yaml` L3、`governance/rule-index.yaml` L2、`tools/paper.py` L290（scaffold 缺省）+ L478（scaffold 调用点，一对必须同改——GC-2026-1113-03 §3 先例）、`templates/paper/paper.yaml` L17。PATCH 判据 = 既有条款扩充 + 解释登记、无新增规则号（PF-RV7 原句扩充、profile/schema 为既有块增可选子键，rule-index 无条目增删，PF-RV7 条目 L249–250 已登记）；先例：GC-2026-1112-01 0.2.0→0.2.1、GC-2026-1114-01 0.3.1→0.3.2。
- **论文侧基线（2026-11-14 实测）**：九篇 `paper.yaml` `rules_version` 均 **0.3.2**（GC-2026-1114-01 铺开已完成）；papers 侧在途改动仅 P7（3 个 untracked review 文件：`reviews/polish-issues.yaml`、`reviews/polish-r1-blind-review.md`、`reviews/polish-r1-logic.md`）。论文侧铺开按 plan v0.2.0 §9 三档处置政策由主会话另行派单，**本变更治理提交不含任何论文仓内容**（PF-V4/PF-V5）。

## 2. 现状取证（问题陈述与证据，2026-11-14 实测）

### 2.1 口径①：联合团体著者文内引注用顿号，S14 无规定

| # | 证据 | 位置 |
|---|---|---|
| E1 | 刊方 S14 = 附录 15.1 只规定四种形态（①单/双著者"和"/"&"②多著者"等"/"et al"③同年同著者 a/b/c④重复引用角标页码），**无团体著者间分隔规定** | `governance/review.md` L122–L129（刊方原文快照，PF-RV8 管辖） |
| E2 | P2×5：L23 同括号两条（国家市场监督管理总局、国家标准化管理委员会，2024b/2024a）、L69、L91、L132（中共中央、国务院，2018） | `papers/P2-LAYERGOV-20251110/body/paper.md` |
| E3 | P3×2：`（中共中央、国务院，2023）`、`（中共中央、国务院，2022）`（build-record L3008"6 处中文机构引用"系含单机构引注的类计数，不混入本 census） | `papers/P3-SPATIAL-20251110/body/paper.md` L2 |
| E4 | P8×1：`（中共中央、国务院，2022；2023）` | `papers/P8-CDC-DELTALAKE-20261113/body/paper.md` L3 |
| E5 | P9×3：L3（生态环境部办公厅、自然资源部办公厅，2019）、L15 两处 | `papers/P9-SIGNALING-ECRL-20261113/body/paper.md` |
| E6 | **census 合计 11 处**（P2×5、P3×2、P8×1、P9×3），四篇实践一致用顿号；口径 = 著者位多机构联合署名且机构间用顿号；P9 自然人次双著者顿号 7 处（L5/L17×2/L21/L41/L47/L101）不属本口径，归 S14①/`zh_double` 管辖 | 全量 grep + 逐条人工分类（round 2 起草人复测） |

### 2.2 口径②：会议论文条目缺"会议地点"

| # | 证据 | 位置 |
|---|---|---|
| E8 | 刊方模板③明示：`著者，出版年. 篇名[C]∥会议录名称. 会议地点：起止页码. 网址.` | `governance/review.md` L136–L137 |
| E9 | P8 6 条 [C] 全部无"会议地点："形态（5 条无地点词元，L407 KREPS 有裸地点 `Athens.`） | `papers/P8-CDC-DELTALAKE-20261113/body/paper.md` L397–L417 |
| E10 | P7 4 条 [C] 中 2 条无地点词元（L364/L384），2 条"出版地：出版者"形态（L372 DE MARTIM、L390 PALLAVI） | `papers/P7-GOVERNANCE-TRUSTWORTHY-20251111/body/paper.md` |
| E11 | 先例：P5 首轮 RC-02 按 **P1** 记，修复轮补齐会议条目出版地（Piscataway: IEEE、New York: ACM） | `papers/P5-AUDIT-EVIDENCE-20251111/reviews/20261111-round1/RC.md` L85–L86/L133/L299；`fix-dispositions.md` L59 |

**九篇 [C] 条目普查（两口径，body/paper.md 文后参考文献表）**：33 条总数；①无任何地点词元 **22 条**（P1 4、P2 3、P4 7、P5 1、P7 2、P8 5）；②有地点词元、非③形态 **11 条**（P2 2、P3 1、P5 2、P6 3、P7 2、P8 1）；③形态合规 **0 条**。逐条行号见 plan v0.2.0 §2.2 普查表。

### 2.3 工具侧现状（安全性实测）

- `grep -rln "in_text_forms" tools/` = 零命中：无构建/校验代码消费该块，新键不需工具侧配合改动。
- `grep -c "citation" tools/make_refdoc.py` = 0：refdoc 不消费 citation.* 键，C 组 in_sync 不受影响。
- schema `in_text_forms` 整体 `additionalProperties: false`：stie 加键必须同步 schema，否则 A 组校验失败。

## 3. 精确变更清单（逐文件；8 modified + 1 新记录）

| # | 文件 | 变更 |
|---|---|---|
| 1 | `templates/layout/profiles/stie.yaml` | `citation.in_text_forms` 八键后（L153 后）新增第九键 `joint_corporate_separator: "、"`，provenance 注释含 [SC] 回落依据、自然人规则不冲突声明、条目级/文内级分治句（条目级联合著者仍按 GB/T 7714 逗号分隔，P8 L385–389、P9 L232/L276 条目实证） |
| 2 | `governance/review.md` | PF-RV7 机械核对清单句（L59 单行句）扩一项：conference-entry venue place——每条 `[C]` 条目须含 ③"会议地点"，缺失计 P1（P5 首轮 RC-02 同口径先例）；措辞对齐 PF-RV7 既有英文句式，单行不断行 |
| 3 | `schemas/layout-profile.schema.json` | `citation.properties.in_text_forms.properties` 增可选属性 `joint_corporate_separator`（type: string；L309 加逗号 + 新行）；`in_text_forms` 整体 `additionalProperties: false` 不变；不入 required；draft/gbt7713 缺省不声明仍合法 |
| 4 | `tools/verify_layout.py` | section_b baseline 剥离清单补一行嵌套 pop：`baseline["properties"]["citation"]["properties"]["in_text_forms"]["properties"].pop("joint_corporate_separator", None)  # GC-2026-1114-02`（紧跟 L96 fallback_entry_forms pop 后）。**机理口径（GC-2026-1114-01 §3.1-11 同型，主会话终局裁决）**：该行不影响 B 组 PASS/FAIL——B 组对 stie 的拒绝由顶层键 pop 承载；保留理由 = 基线保真（baseline 语义上等价上一代 schema，防"新键 load-bearing"测试对本键静默退化）。其余 section A/C–H 零改动 |
| 5 | `project.yaml` / `governance/rule-index.yaml` / `tools/paper.py`（L290 + L478）/ `templates/paper/paper.yaml` | rules_version 0.3.2 → **0.3.3**（五处、四文件；paper.py 一对同改） |
| 6 | `governance/changes/2026-11-14-intext-joint-corporate-conference-place.md` | 本记录（新建，11 节） |

**不改**：draft.yaml / gbt7713-2-2022.yaml（可选键缺省合法）；`tools/make_refdoc.py`（citation 零消费实测）；`governance/writing.md`（PF-W6/PF-W11 本变更不涉）；`governance/polish.md`（S13/S14 汇总句不改，真值源在 profile，PF-B11）；`tools/paper.py` 其余逻辑（L6040 `--version` 帮助文本 `v0.3.2` 为 paper_version 示例，豁免）；papers/ 下任何论文仓（PF-V4/PF-V5）。

**PF-B3 结构身份键合规**：`citation` 为 PF-B3 结构身份键，L2 仍不可覆写（PF-B13，构建失败）；本次为治理层 F9 流程对 `citation.in_text_forms` 增可选子键，属 profile 版本化动作，未赋予论文级覆写能力。

## 4. 理由（Rationale）

1. 解决"实践一致但无登记依据"（E2–E6）：四篇 11 处顿号实践落为 profile 键值（PF-B11 单一真值源），PF-RV7/精修从"靠记忆"变为"可引用键值"。
2. 补齐机械判据（E8–E11）：刊方③明示要素固化为 PF-RV7 机械核对项，给实际值不得断言；P5 首轮 RC-02 已实证该缺陷漏网计 P1，不固化可复发。
3. 三层同构（profile → schema → PF-RV7），与 GC-2026-1114-01 确立结构同型。
4. 版本 PATCH：无新增规则号、rule-index 无条目增删，两条先例同型。
5. verify_layout 补行：基线保真（§3-4）。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 不登记联合团体著者例外，维持评审临时判断 | 四篇 11 处实践已存在且一致，不登记则每轮重复裁定、口径漂移；GC-2026-1114-01 已确立 [SC]/[GB] 回落登记路径 |
| 维持自然人规则外一律不做处理（含会议地点不固化） | P5 首轮 RC-02 实证缺出版地漏网计 P1；不固化则修复轮缺机械判据 |
| 只在 PF-RV7 写文字规定、不动 profile/schema | 无真值源；schema additionalProperties:false 下 profile 自行加键即 A 组校验失败 |
| 强制团体著者改用"和" | 违反官方文件联合署名惯例；回改 P3/P8/P9 现产文本触发 PF-B7 冻结与重建，成本收益不成比例 |
| verify_layout 不加 pop 行 | baseline 不再等价上一代 schema，新键 load-bearing 证明静默退化；GC-2026-1114-01 round 2 终局裁决 baseline 保真口径同型复用 |

## 6. 两个口径决策（主会话裁定，照登）

- **决策①（联合团体著者顿号回落）**：`joint_corporate_separator: "、"` 为 [SC] 本项目自选回落（刊方 S14 未规定团体著者形态；官方文件联合署名惯例用顿号；P2/P3/P8/P9 现状实践）；自然人双著者仍按 S14① 用"和"，本键不改变自然人规则；条目级联合著者仍按 GB/T 7714 逗号分隔，本键仅辖文内引注形态。
- **决策②（会议地点硬约束 + 三档处置）**：会议地点属刊方③明示硬约束（规定语气、无容差，按 PF-RV8 条款效力分级一贯生效，**非本次新规**），各篇修复轮内一并修复：**①本届修复轮必修**——P2/P4/P5/P6/P7/P8/P9 七篇的 [C] 条目地点缺口（普查①②两列共 28 条 = ①列 18 + ②列 10）随各篇修复轮同轮修复，地点信息须实际核验（PF-W1 禁编造），核不掉的不补、转③档；**②轻量修复轮**——P1（4 条①列）与 P3（1 条②列）原无修复轮，为本项各开一轮轻量修复（仅会议地点 + 必要形式），与其 rules_version 同步合并提交；**③开放项挂篇**——核验不了的条目逐条挂该篇 paper.yaml unresolved（GC-2026-1114-01 决策 B 同机制）。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 治理仓并发线在途改动被裹挟（起草期 HEAD 已从 2b7b06f 前移 61d04bf，并发线活跃） | 每文件写前 `git status --porcelain` 检查；提交前 `git diff --cached --name-only` 对账 §3 九文件；禁 `-A`/`-a` |
| R2 | 改 stie 漏改 schema（A 组即 FAIL） | §3-1/§3-3 同笔；A 组 13 targets 兜底 |
| R3 | §3-4 pop 行漏执行 → B 组输出不变，属静默缺陷 | 该行不影响 B 组 PASS/FAIL（§3-4 照登结论），diff 核对是唯一捕获点——写盘后独立验证必查 |
| R4 | 行号漂移（并发提交触及目标文件） | Edit 文本匹配不依赖行号；失配即停手重测基线 |
| R5 | 论文侧铺开裹挟 P7 在途 review 文件 | 铺开提交域限 paper.yaml + build-record 登记节（+修复轮授权范围）；执行时刻逐篇实测 git status |
| R6 | 版本残留 | 五处同笔 + grep 对账（paper.py L6040 帮助文本豁免） |
| R7 | 新键被误读为覆盖自然人"和"规则 | provenance 注释句内显式否认；写盘后文档复核逐字比对 |
| R8 | 记录节次缺项 | 11 节结构逐项验收（本记录 §3-6 对齐 GC-2026-1114-01） |

## 8. 恢复方式（Recovery）

**提交前回退（当前状态，文件未暂存）**：8 个已跟踪文件逐个 `git checkout HEAD -- <path>` 还原；本记录为 untracked，直接删除。禁 `--hard` 与任何历史改写（F7）。

**提交后整体恢复**：`git revert <commit>`（单笔纯治理提交）。部分回退逐文件 `git checkout HEAD^ -- <path>`：`templates/layout/profiles/stie.yaml`、`schemas/layout-profile.schema.json`、`governance/review.md`、`tools/verify_layout.py`、`tools/paper.py`、`project.yaml`、`governance/rule-index.yaml`、`templates/paper/paper.yaml`；本记录 `git rm`（revert 连带移除）。

**论文侧**：本变更治理提交不含论文仓内容（PF-V5），papers/ 零改动、无回滚对象；铺开若已执行后需撤，按篇 `git revert <paper sync commit>`（仅撤该篇 paper.yaml 版本行与 build-record 登记节），不回退既有正文/PKG。计划、复核与整改记录留存 `temp/GC-2026-1114-02/`（gitignored）。

## 9. 验证方法与结果（2026-11-14 落盘后实测）

**改动前基线（同命令，2026-11-14 @ `61d04bf`）**：`TOTAL 27 PASS 27 FAIL 0`（exit 0）；A 组 `13 targets, 0 failed`；B 组 `PASS | stie.yaml: 2 errors; gbt7713-2-2022.yaml: 1 errors`；C 组三 profile `in_sync=True self_check=True`；G 组 `9 papers, 0 problems`。

| # | 验证项 | 方法（全部只读，`python3 -I` + 绝对路径） | 实测结果 |
|---|---|---|---|
| a | verify_layout 全量 | `python3 -I tools/verify_layout.py --paper-root <papers>` | **TOTAL 27 PASS 27 FAIL 0（exit 0）**；A 组 `13 targets, 0 failed`；**B 组 `PASS`，细目 `stie.yaml: 3 errors; gbt7713-2-2022.yaml: 1 errors`**（较基线 2 errors 多一条，与 plan v0.2.0 §7-b 期望一致）；C 组 `draft/gbt7713-2-2022/stie: in_sync=True self_check=True`；D–H 全 PASS（G 组 `9 papers, 0 problems`）。只读模拟实证三条错误细目：①顶层键集合 additionalProperties 错误、②`'fallback_entry_forms' was unexpected`、③**`'joint_corporate_separator' was unexpected`**（新键拒绝独立成条，机理同 GC-2026-1114-01 记录 §9-b） |
| b | YAML/JSON 解析与版本对账 | `python3 -I -c` 解析五个文件 | stie.yaml OK（in_text_forms **恰九键**，第九键 `joint_corporate_separator` 值 `"、"`，八键无扰动）；schema OK（in_text_forms.additionalProperties=False、joint_corporate_separator present=True、JSON 合法）；project.yaml / rule-index.yaml / templates/paper/paper.yaml OK（**rules_version=0.3.3**）；残留对账：四个声明文件 `0\.3\.2` 零命中（tools/paper.py L6040 `--version` 帮助文本 `v0.3.2` 为 paper_version 示例，豁免不改） |
| c | 语法完整 | `python3 -I -m py_compile tools/paper.py tools/verify_layout.py` | 均通过 |
| d | 提交域 | `git status --short` + `git diff --stat`（写盘后、未暂存） | **8 modified + 1 新记录 = 9 文件**，`8 files changed, 10 insertions(+), 7 deletions(-)`——与 plan v0.2.0 §3/§7-e 预期（+10/−7）逐文件对账一致：stie +1/−0、schema +2/−1、review +1/−1、verify_layout +1/−0、paper.py +2/−2、project/rule-index/paper.yaml 各 +1/−1；无第 10 个文件、无 papers/ 条目 |

## 10. 复核（F9）

- **计划阶段复核（两轮，均未通过原起草人）**：round 1 独立复核 FAIL（P1×1：F1 处置政策；P2×1：F2 census 口径；P3×5：F3–F7）→ v0.2.0 整改；round 2 独立复核 **PASS-with-notes**（唯一 P3：N1——P9 自然人次双著者顿号 5 处实为 7 处，补 L47/L101）→ 主会话裁决按 PASS-with-notes 放行，N1 随本执行批订正 plan §2.1 E6 与 §10 开放项 6。改动技术文本经两轮复核逐字实读与实跑零漂移。
- **写盘后独立验证（待主会话派单，最终门禁）**：由未参与计划与写盘的子代理核验实际 diff（逐文件逐键，含 §3-4 pop 行在位——该行不影响 B 组输出，diff 核对是唯一捕获点）、§9 检查结果复跑一致、提交域合规（8 modified + 1 新记录、零论文仓触碰）；复核后方可 commit/push，主会话不得自批。

## 11. 开放项

1. **[R/OL] 报告类在线文献**等类型未入 `citation.fallback_entry_forms` 登记集合（现四键 law/regulation/standard/standard_online）——出现即另立 GC 候选。
2. 原派单指令"六篇修复派单"与七篇枚举的计数出入——已由 §6 决策②三档处置实际覆盖（7 篇随既有修复轮 + P1/P3 新开轻量轮），仅留档备查。
3. **[C] ②列 11 条全谱登记**（有地点词元、非③形态）：P2×2（L414/L442 `New York: ACM`）、P3×1（L188 `San Jose: USENIX`）、P5×2（L295 `Piscataway: IEEE`、L297 `New York: ACM`）、P6×3（L300 `Online:`、L302 `Hong Kong`、L306 `San Diego`）、P7×2（L372 `Amsterdam`、L390 `Piscataway`）、P8×1（L407 `Athens.`）——逐条按 §6 决策②三档处置，由所在轮次审稿判定改写为③形态或核验不了挂篇 unresolved，本变更不预裁。
4. 英文联合团体著者（多机构英文署名）间分隔形态未登记（现键值为中文顿号场景；勿径用 "&"——& 为自然人 en_double 专用）。
5. 纯在线会议（无物理地点，如 P8 L401 CIDR）的"会议地点"著录口径待编辑部确认，核验不了按③档挂篇级 unresolved。
6. P9 文内自然人次双著者顿号 7 处（L5/L17×2/L21/L41/L47/L101，以修复轮全量复 grep 为准）与 S14①/`zh_double` "和"规则的符合性——不属本变更登记范围，留待 P9 修复轮按 PF-RV7 既有规则核对。
7. **论文侧铺开**：九篇 paper.yaml 0.3.2→0.3.3 + 会议地点三档处置 + build-record 登记（含执行时刻 git status 快照），按 plan v0.2.0 §9 由主会话另行派单（PF-V5 每篇独立提交）。

---

*GC-2026-1114-02。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B3/PF-B11/PF-B12/PF-B13；著录基线 governance/writing.md PF-W1/PF-W11、governance/review.md PF-RV7/PF-RV8；版本依据 governance/versions.md PF-V1/PF-V3/PF-V5/PF-V6；计划 temp/GC-2026-1114-02/plan.md（v0.2.0，两轮独立复核：round 1 FAIL 整改 + round 2 PASS-with-notes/N1 随批订正）；规则版本 0.3.2 → 0.3.3（PATCH）。*
