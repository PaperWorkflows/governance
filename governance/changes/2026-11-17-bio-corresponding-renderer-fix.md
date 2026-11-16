# 治理变更记录 GC-2026-1117-03：_bio_corresponding 补全籍贯/学位/职称渲染分支

- 日期：2026-11-17
- 编号：GC-2026-1117-03
- 类型：生成器渲染缺陷修复（`tools/metalayout.py` `_bio_corresponding` 新增籍贯/学位/职称三个 elif 分支 + rules_version PATCH 升版 0.3.5→0.3.6）
- 计划：无单独计划文件（轻量变更，直接执行）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、F6（最小改动）；版式依据 PF-RV8（刊方明示 > 国标基线 > 本项目回落）、PF-B3（profile 为 L1 结构身份键）；版本依据 PF-V1/PF-V3/PF-V5/PF-V6
- 规则版本：**0.3.5 → 0.3.6（PATCH）**

---

## 1. 基线（Baseline）

- **git 基线（写盘时刻）**：治理仓 HEAD `6cf2718`（fix(governance): GC-2026-1117-02 stie.yaml corresponding_bio_fields 补全籍贯/学位/职称）。
- **rules_version 前后**：0.3.5 → **0.3.6（PATCH）**。同步五处：`project.yaml` L3、`governance/rule-index.yaml` L2、`tools/paper.py` L377 + L581、`templates/paper/paper.yaml` L17。
- **改动范围**：治理仓 metalayout.py 三处新增分支 + 4 个版本声明文件 + 1 个新变更记录，不触及任何 `papers/` 下论文仓文件（PF-V5）。

## 2. 现状取证（问题陈述与证据）

| # | 问题 | 证据 |
|---|---|---|
| E1 | GC-2026-1117-02 已将 stie.yaml 的 `corresponding_bio_fields` 改为全字段（11 项含籍贯/学位/职称），但 `tools/metalayout.py` 的 `_bio_corresponding`（约 L827–887）只处理八个字段分支 | 实测证据：build/v0.1.2 的 docx 中"通信作者*：杨森（1978 年生），男，云南省自然资源厅国土资源信息中心；研究方向为……"无籍贯/学位/职称；而首作者"作者简介：伍红玲（1982 年生），女，四川资阳人，硕士研究生，高级工程师，……"三项齐全 |
| E2 | `_bio_full`（约 L755 起）已有籍贯/学位/职称处理逻辑 | 该函数使用 `bio.get("hometown")` → `f"，{v}人"`、`bio.get("degree")`、`bio.get("title")` 三个 elif 分支，格式与 `_bio_corresponding` 不一致 |
| E3 | authors.yaml 中杨森数据齐全 | `hometown: 云南昆明`、`degree: 硕士研究生`、`title: 高级工程师` 均有值，仅渲染器未处理 |
| E4 | GC-2026-1117-02 登记开放项 1"生成器适配"未闭环 | GC-2026-1117-02 §10 开放项 1 明确列出"生成器适配：tools/paper.py 的 `_bio_corresponding` 渲染逻辑需确认按 `corresponding_bio_fields` 字段序读取 authors.yaml 并输出，新字段能正确渲染"——本次即为此开放项的闭环 |

## 3. 精确变更清单（逐文件；6 个文件 = 4 修改 + 2 新建）

| # | 文件 | 变更 |
|---|---|---|
| 1 | `tools/metalayout.py` L848–854（`_bio_corresponding` 内） | 在"性别"分支与"单位"分支之间新增三个 elif 分支：籍贯（读 `bio.get("hometown")`，格式 `f"，{v}人"`）、学位（读 `bio.get("degree")`，格式 `f"，{v}"`）、职称（读 `bio.get("title")`，格式 `f"，{v}"`），写法与 `_bio_full`（L755–766）完全一致 |
| 2 | `tools/metalayout.py` L827–833（`_bio_corresponding` 函数 docstring） | 更新 docstring：从"简式八字段，无籍贯/学位/职称"改为"全 11 项，GC-2026-1117-03 补全籍贯/学位/职称分支" |
| 3 | `project.yaml` L3 | `rules_version: 0.3.5` → `0.3.6` |
| 4 | `governance/rule-index.yaml` L2 | `rules_version: 0.3.5` → `0.3.6` |
| 5 | `tools/paper.py` L377 + L581 | L377 `rules_version: str = "0.3.5"` → `"0.3.6"`；L581 `rules_version="0.3.5"` → `"0.3.6"` |
| 6 | `templates/paper/paper.yaml` L17 | `rules_version: 0.3.5` → `0.3.6` |
| 7 | `governance/changes/2026-11-17-bio-corresponding-renderer-fix.md` | 本记录（新建） |

**不改**：`schemas/layout-profile.schema.json`、`governance/writing.md`、`governance/review.md`、`tools/verify_layout.py`、`templates/layout/profiles/stie.yaml`（字段列表已在 GC-2026-1117-02 改完，无需再动）、`templates/paper/references.bib`、`papers/` 下任何论文仓文件（PF-V5）。

## 4. 理由（Rationale）

1. **配置已改、渲染器未跟**：GC-2026-1117-02 修改了 `stie.yaml` 的 `corresponding_bio_fields` 配置为全 11 项，但 `_bio_corresponding` 生成器逻辑仍只处理八个字段分支。配置先行、渲染器滞后导致改配无效。
2. **最小改动原则**：仅在 `_bio_corresponding` 的字段分支中补上三个 elif，行为与 `_bio_full` 保持一致，不重构、不改其它函数。
3. **authors.yaml 数据已就绪**：P10 杨森的 `hometown/degree/title` 均有值，补分支后即刻生效，无需论文侧数据变更。
4. **版本 PATCH**：与 GC-2026-1117-01、GC-2026-1117-02 同型——"渲染器缺陷修复 + profile 配置闭环，无新增规则号"。
5. **闭环 GC-2026-1117-02 开放项 1**：该变更 §10 开放项 1 登记"生成器适配未落地"，本次即为此项的完成。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 回退 stie.yaml `corresponding_bio_fields` 到简式八字段 | 违反 PF-RV8 刊方明示优先序；S17 明文含籍贯/学位/职称，简式八字段缺项计 P1 问题 |
| 由作者在 Word 中手工补全籍贯/学位/职称 | 违背自动化构建理念；人工补录不可复现、不可追溯，且易被下次构建覆盖 |
| 重写 `_bio_corresponding` 为通用渲染循环 | 过度工程化，当前改动仅需三个 elif 分支；违背 F6 最小改动原则 |

**拟取方案**：在 `_bio_corresponding` 中补籍贯/学位/职称三个分支，与 `_bio_full` 对齐。

## 6. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 下次构建产物通信作者段多出籍贯/学位/职称三字段 | 确认预期行为（刊方 S17 要求），非风险 |
| R2 | authors.yaml 中部分作者缺籍贯/学位/职称数据 | 生成器 `bio.get()` 空值判断：缺值不输出，不影响非对应作者段 |
| R3 | 已构建 docx/pdf 与新版本不一致 | 已构建工件不回溯变更；下次构建按新版本重出 |
| R4 | 治理仓并发线在途改动被裹挟 | 提交前 `git status --short` + 显式 add，禁 `-A` |

## 7. 恢复方式（Recovery）

**治理仓**：本变更为单笔纯治理提交，整体恢复用 `git revert <commit>`；若需部分回退：

| # | 文件 | 恢复命令路径 |
|---|---|---|
| 1 | `project.yaml`（L3） | `git checkout HEAD^ -- project.yaml` |
| 2 | `governance/rule-index.yaml`（L2） | `git checkout HEAD^ -- governance/rule-index.yaml` |
| 3 | `tools/paper.py`（L377 + L581） | `git checkout HEAD^ -- tools/paper.py` |
| 4 | `templates/paper/paper.yaml`（L17） | `git checkout HEAD^ -- templates/paper/paper.yaml` |
| 5 | `tools/metalayout.py`（`_bio_corresponding` 三分支 + docstring） | `git checkout HEAD^ -- tools/metalayout.py` |
| 6 | `governance/changes/2026-11-17-bio-corresponding-renderer-fix.md`（本记录） | `git rm governance/changes/2026-11-17-bio-corresponding-renderer-fix.md` |

- 禁止 `--hard` 与任何历史改写（AGENTS.md F7 保留现场）。
- **论文侧**：本变更不涉及 `papers/` 下任何文件，无需论文侧回退。

## 8. 影响面

- **全部论文构建产物**：所有使用 stie profile 的论文（P1–P10 及后续可能添加的 stie 论文）在下一次构建时，通信作者段将包含籍贯、学位、职称三个新增字段。
- **已构建的 docx/pdf 不回溯变更**：已有构建工件保持原貌，需下次构建时再生成新产物。
- **authors.yaml 数据完整性依赖**：生成器按 `authors.yaml` 中字段实际值渲染，缺值字段不输出。

## 9. 验证方法与结果（2026-11-17 落盘后实测）

| # | 验证项 | 方法 | 实测结果 |
|---|---|---|---|
| a | metalayout.py 语法完整 | `python3 -I -m py_compile tools/metalayout.py` | **通过** |
| b | paper.py 语法完整 | `python3 -I -m py_compile tools/paper.py` | **通过** |
| c | 版本对账 | `grep -n '0\.3\.6'` + `grep -n '0\.3\.5'` 残留 = 0 | **五处已同步** |
| d | _bio_corresponding 分支覆盖 | `grep -c 'elif field ==' tools/metalayout.py` | 11 个 elif 分支（出生年/性别/籍贯/学位/职称/单位/研究方向/电子邮箱/电话/通信地址/邮政编码），与 `_bio_full` 的籍贯/学位/职称处理一致 |
| e | P10 validate | `python3 -I tools/paper.py validate --paper <P10>` | **pass** |
| f | verify_layout | `python3 -I tools/verify_layout.py --paper-root <papers>` | **TOTAL 27 PASS 27 FAIL 0** |

## 10. 复核（F9）

- 本变更由执行代理起草并写盘，需待未参与变更的子代理复核实际 diff（逐文件逐键）与 §9 检查结果复跑一致、提交域合规（六文件、零论文仓触碰）；复核后方可 commit/push，主会话不得自批。

## 11. 开放项

1. **P1–P7 重构建**：下次构建时通信作者段将多出三项籍贯/学位/职称，需在各自论文 build-record 中登记，由主会话另行派单。
2. **P10 重构建**：本任务一并执行（见任务三），P10 是首个受益于本修复的论文。

---

*GC-2026-1117-03。规则依据：AGENTS.md F9/F6；版式依据 governance/build.md PF-B3；著录基线 PF-RV8（刊方明示优先）；版本依据 governance/versions.md PF-V1/PF-V3/PF-V5/PF-V6；变更类型：rules_version PATCH 0.3.5→0.3.6。*
