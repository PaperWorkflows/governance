# 治理变更记录 GC-2026-1117-02：corresponding_bio_fields 补全籍贯/学位/职称

- 日期：2026-11-17
- 编号：GC-2026-1117-02
- 类型：治理能力修订（`stie.yaml` `authors.bio_section.corresponding_bio_fields` 由简式八字段→全字段十一字段 + rules_version PATCH 升版 0.3.4→0.3.5）
- 计划：无单独计划文件（轻量变更，直接执行）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、F6（最小改动）；版式依据 PF-RV8（刊方明示 > 国标基线 > 本项目回落）、PF-B3（profile 为 L1 结构身份键）；版本依据 PF-V1/PF-V3/PF-V5/PF-V6
- 规则版本：**0.3.4 → 0.3.5（PATCH）**

---

## 1. 基线（Baseline）

- **git 基线**：治理仓 HEAD `3126c6b`（fix(governance): GC-2026-1117-01 stie.yaml citation.fallback_entry_forms 新增 thesis 键）。
- **rules_version 前后**：0.3.4 → **0.3.5（PATCH）**。同步五处：`project.yaml` L3、`governance/rule-index.yaml` L2、`tools/paper.py` L377 + L581、`templates/paper/paper.yaml` L17。
- **改动范围**：本变更只修改治理仓模板与版本声明文件，不触及任何 `papers/` 下论文仓文件（PF-V5）。

## 2. 现状取证（问题陈述与证据）

| # | 问题 | 证据 |
|---|---|---|
| E1 | 刊方 S17 明文要求作者提供 10 项基本信息（+ 单位名称 = 11 项） | 用户提供的刊方投稿格式要求全文 S17："所有作者均需提供姓名（出生年）、性别、籍贯、学位、职称、研究方向、通信地址、邮政编码、电子邮箱、电话"——10 项字段 + 生成器附加的「单位」 = 11 项 |
| E2 | stie.yaml `corresponding_bio_fields` 仅 8 项 | 当前值来自 [JT] 范本实测（首作者/通信作者各一段、其余作者合并一段），不含籍贯/学位/职称，与 S17 明文不符 |
| E3 | `bio_field_order`（首作者字段序）已含全 11 项 | L239–250 登记 S17 全文 11 字段（含「单位」）；通信作者字段序与首作者不一致 |
| E4 | PF-RV8 优先序 | "刊方明示 > 国标基线 > 本项目回落"——S17 刊方明示优于 [JT] 范本实测 |

## 3. 精确变更清单（逐文件；7 个文件 = 6 修改 + 1 新建）

| # | 文件 | 变更 |
|---|---|---|
| 1 | `templates/layout/profiles/stie.yaml` | `authors.bio_section.corresponding_bio_fields` 由 8 项扩展为与 `bio_field_order` 一致的 11 项全字段序（出生年、性别、籍贯、学位、职称、单位、研究方向、通信地址、邮政编码、电子邮箱、电话）；注释由 `[JT]` 范本实测改为 `[S17]` 刊方明示，记录 PF-RV8 优先序抉择（GC-2026-1117-02） |
| 2 | `project.yaml` L3 | `rules_version: 0.3.4` → `0.3.5` |
| 3 | `governance/rule-index.yaml` L2 | `rules_version: 0.3.4` → `0.3.5` |
| 4 | `tools/paper.py` L377 + L581 | L377 `rules_version: str = "0.3.4"` → `"0.3.5"`；L581 `rules_version="0.3.4"` → `"0.3.5"` |
| 5 | `templates/paper/paper.yaml` L17 | `rules_version: 0.3.4` → `0.3.5` |
| 6 | `governance/changes/2026-11-17-bio-corresponding-full-fields.md` | 本记录（新建） |

**不改**：`schemas/layout-profile.schema.json`（corresponding_bio_fields 不在 schema 结构校验范围）、`governance/writing.md`、`governance/review.md`、`tools/verify_layout.py`、`tools/paper.py` 逻辑代码（仅版本号字面量）、`templates/paper/references.bib`、`papers/` 下任何论文仓文件（PF-V5）。

## 4. 理由（Rationale）

1. **刊方 S17 明文是硬约束**：S17 规定"所有作者均需提供"的字段包含籍贯、学位、职称，这是刊方投稿格式要求，属于最高优先级的 `[S#]` 来源等级。
2. **PF-RV8 优先序裁决**：`[S#]` 刊方明示 > `[JT]` 范本实测。范本实测得出"通信作者简式八字段"，但刊方明文要求全 11 项，冲突时取刊方明文。
3. **与 bio_field_order 对齐**：首作者字段序（`bio_field_order`）已是 11 项全字段，通信作者字段序对齐后可消除两段落不一致的维护负担。
4. **authors.yaml 数据已齐全**：各论文 `authors.yaml` 中籍贯、学位、职称字段均有数据支撑，仅渲染层缺口（生成器按 `corresponding_bio_fields` 列表截断），补全后无需论文侧数据变更。
5. **版本 PATCH**："既有规则正文扩充（字段列表），无新增规则号"，与 GC-2026-1114-01、GC-2026-1117-01 同型。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 维持简式八字段（现状） | 违反 PF-RV8 刊方明示优先序；S17 明文缺项计 P1 问题（PF-RV8 规定语气 = 硬约束） |
| 仅更新注释不改字段 | 注释与实值不一致造成后续维护混淆，违反 PF-W1 真实性 |
| 在写作层 writing-spec.yaml 覆盖 | writing-spec 是 L2 论文层，profile 是 L1 全局基准；PF-B3 规定 L2 不可覆写 profile 结构身份键 |

**拟取方案**：`corresponding_bio_fields` 对齐 `bio_field_order` 全字段序。

## 6. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 下次构建产物（docx/pdf）通信作者段多出籍贯/学位/职称三字段 | 确认预期行为（刊方 S17 要求），非风险 |
| R2 | 部分论文 authors.yaml 缺籍贯/学位/职称数据 | 生成器应按字段在 authors.yaml 中存在时才输出，空值不显示；不影响非对应作者段 |
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
| 5 | `templates/layout/profiles/stie.yaml`（corresponding_bio_fields 块） | `git checkout HEAD^ -- templates/layout/profiles/stie.yaml` |
| 6 | `governance/changes/2026-11-17-bio-corresponding-full-fields.md`（本记录） | `git rm governance/changes/2026-11-17-bio-corresponding-full-fields.md` |

- 禁止 `--hard` 与任何历史改写（AGENTS.md F7 保留现场）。
- **论文侧**：本变更不涉及 `papers/` 下任何文件，无需论文侧回退。

## 8. 影响面

- **全部论文构建产物**：所有使用 stie profile 的论文（P1–P7 及后续可能添加的 stie 论文）在下一次构建时，通信作者段将包含籍贯、学位、职称三个新增字段。
- **已构建的 docx/pdf 不回溯变更**：已有构建工件保持原貌，需下次构建时再生成新产物。
- **authors.yaml 数据完整性依赖**：生成器需按 authors.yaml 中字段实际值渲染，缺值字段不输出（或输出占位符视生成器实现而定）。
- **模板数据层（templates/layout/profiles/stie.yaml）是唯一变更源**，不影响论文侧 `authors.yaml` 结构。

## 9. 验证方法与结果

| # | 验证项 | 方法 | 预期结果 |
|---|---|---|---|
| a | YAML 可解析 | `python3 -I -c` 解析 stie.yaml | 解析通过，corresponding_bio_fields 含 11 项 |
| b | schema JSON 可解析 | `python3 -I -c` 解析 schema | 解析通过 |
| c | 版本对账 | `grep -n '0\.3\.5'` + `grep -n '0\.3\.4'` 残留 = 0 | 五处已同步 |
| d | paper.py 语法完整 | `python3 -I -m py_compile tools/paper.py` | 通过 |
| e | P10 validate | `python3 -I tools/paper.py validate --paper <P10>` | pass |
| f | verify_layout | `python3 -I tools/verify_layout.py --paper-root <papers>` | TOTAL 27 PASS 27 FAIL 0 |

## 10. 开放项

1. **生成器适配**：`tools/paper.py` 的 `_bio_corresponding` 渲染逻辑需确认按 `corresponding_bio_fields` 字段序读取 authors.yaml 并输出，新字段（籍贯、学位、职称）在 authors.yaml 中有值时能正确渲染。
2. **P1–P7 重构建**：下次构建时通信作者段将多出三项，需确认是否符合刊方期望（刊方 S17 明文要求，预期符合）。
3. **已构建工件标注**：建议在 build-record 中登记本轮变更导致通信作者段字段数变化，方便追溯。

---

*GC-2026-1117-02。规则依据：AGENTS.md F9/F6；版式依据 governance/build.md PF-B3；著录基线 PF-RV8（刊方明示优先）；版本依据 governance/versions.md PF-V1/PF-V3/PF-V5/PF-V6；变更类型：rules_version PATCH 0.3.4→0.3.5。*
