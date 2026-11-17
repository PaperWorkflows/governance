# 治理变更记录 GC-2026-1118-01：参考文献节三条硬断言（存在性 / 渲染落地 / 非空）

- 日期：2026-11-18
- 编号：**GC-2026-1118-01**（1118 系列首个条目）
- 类型：工具链增强（`tools/paper.py` 新增 A6–A8 三条硬断言并接入 `check` / `package` / 构建断言三条路径）+ 规则正文增补（`governance/build.md` PF-B12 一条）；rules_version MINOR 升版 0.4.3 → 0.5.0
- 规则依据：AGENTS.md **F9**（治理变更纪律）、**F6**（最小改动）；版式 **PF-B12**（落地校验：不可校验即不得放行）；版本 **PF-V3/PF-V5/PF-V6**
- 规则版本：**0.4.3 → 0.5.0（MINOR）**。依据：新增三条硬门禁（新增执行能力，非既有条款的措辞修正），先例 GC-2026-1117-06（新增规则正文 0.3.8→0.4.0）。
- 论文侧基线：十篇文献节均已回补（P1 v0.4.24、P2 v0.4.30、P8 v0.1.18、P9 v0.1.14），十仓干净且已推送；本次回归不改任何论文仓文件（PF-V5）。

---

## 1. 触发事件与事实链（2026-11-17 晚改写波次静默删文献）

| # | 事实 | 证据 |
|---|---|---|
| F1 | 11-17 晚 agy 改写波次将 P1/P2/P8/P9 四篇的参考文献整节删除 | 四篇 `body/paper.md` 的 `# 参考文献` 节整体缺失；11-18 独立复核发现并逐一手动回补（P1 v0.4.24、P2 v0.4.30、P8 v0.1.18、P9 v0.1.14） |
| F2 | 四篇全部穿过既有门禁，直达交付件 | 四篇的 `package --verify-only --strict` 在事故态均返回 pass；删除只影响 `references_chars`，`body_chars` 更小、`total` 反而更「达标」 |
| F3 | `bibliography_style_landing` 空真通过 | 该检查以「源文件存在 `custom-style="Bibliography"` 声明」为前置条件；整节删净后声明一并消失，`if _bib_div_declared:` 为假，检查直接跳过 |
| F4 | `role_styles_unused_limitation` 无阻断权 | manifest 只记 note（`Bibliography` 未使用），`strict` 只检查 `gaps_sidecar` 与 `redraw_pending`，不触发 fail |
| F5 | 字数带宽对删节不可见 | 带宽以 `# 参考文献` 切分 body，文献节不在 `body_text` 内；删节点对 `body_chars` 无影响，`total_chars` 仅减少文献字符数 |

**根因（三层盲区）**：① 落地检查以「声明存在」为前提，声明随整节删除而消失，条件为假即空真通过；② 未使用样式只是 note，没有阻断权；③ 结构检查只看「声明有就用」，不看「有引注却无节」。

## 2. 变更方案（三条断言，覆盖三个盲区）

| 断言 | 判据 | 覆盖盲区 | 实现位置 |
|---|---|---|---|
| **A6 存在性** | 正文区（参考文献标题之前，剔除 fenced code）≥ 3 处作者-年引注，且全文无 `^#{0,2}\s*参考文献\s*$` 标题行（裸行 / `#` / `##` 三形态，整行锚定）→ fail | F3/F5 | `_bib_split_references` + `_bib_count_citations` + `_bibliography_gates` |
| **A7 渲染落地** | 源文件存在参考文献标题**或** `custom-style="Bibliography"` 块，但 docx 中 `w:pStyle="Bibliography"` 段落数为 0 → fail | F3 的「声明存在但渲染缺席」分支 | `_bib_count_docx_paragraphs` |
| **A8 非空** | 参考文献节标题存在，但节内非空白字符为 0，或 Bibliography 段落 < 1 → fail | F2/F4 | `_bibliography_gates` |

设计约束（与任务口径一致）：

1. **不比较印出数 = bib 数**。P10 候选池（`references.bib` 49 条、印出 15 条）是合法形态；三条断言只查「有没有 / 落没落 / 空不空」。
2. **不在 `check` / `docx` 不可读时误判 fail**。源文件缺失、docx 解包失败一律记 `status: "error"` 并写明原因，不参与失败判定（`failed` 只收集 `status == "fail"`）。
3. **不改字数口径**。`_package_body` 与 `references_chars` 保持原样，避免既有 release manifest 的 A3 共享字段对账失配（十仓 verify-only 依赖该一致性）。
4. **作者-年引注正则刻意收窄**：半角/全角括号 + 大写开头作者串 + `et al.` / `&` / `and` / `等` + 年份，避免 `(v0.4.24)`、`(2026-11-15)`、`(见表3)` 等误判；扫描前剔除 fenced code。

## 3. 精确变更清单

| # | 位置 | 变更 |
|---|---|---|
| 1 | `tools/paper.py` L6063–6262（新函数区） | 新增 `_BIB_HEADING_RE` / `_AUTHOR_YEAR_CITE_RE` / `_BIB_DIV_RE`、`_bib_strip_fenced_code`、`_bib_split_references`、`_bib_count_citations`、`_bib_count_docx_paragraphs`、`_bibliography_gates`；中文失败信息含回补指引 |
| 2 | `tools/paper.py` L6387–6425（`_package_assertions` 尾部） | A5 之后追加 A6–A8；docx 取打包件优先、回退 release docx；`body/paper.md` 不可读时三条均记 `error` |
| 3 | `tools/paper.py` L3003–3016（`_assert_layout_landing`） | 原 `bibliography_style_landing`（以 div 声明为前提）替换为无条件的三断言门禁，构建失败项命名 `bibliography_gate_a6/a7/a8` |
| 4 | `tools/paper.py` L953–987（`cmd_check`） | 新增 `results["bibliography_gates"]`：源侧读 `body/paper.md`，docx 侧读 `build/current.json` 指向版本的首个 `.docx`；fail 置 overall=fail（exit 2），error 不阻断 |
| 5 | `tools/paper.py` L5892（`_package_plan` 返回体） | 增加 `paper_dir`，供断言定位源文件 |
| 6 | `governance/build.md` PF-B12 | 增补文献节三条硬断言条款（英文正文，标注 GC-2026-1118-01） |
| 7 | `project.yaml` L3 / `governance/rule-index.yaml` L2 / `tools/paper.py` L383 / L587 / `templates/paper/paper.yaml` L17 | `rules_version: 0.4.3` → `0.5.0`（五处、四文件） |
| 8 | `governance/changes/2026-11-18-bibliography-hard-gates.md` | 本记录（新建） |

**不改**：`papers/` 下任何论文仓（PF-V5）；`_package_body` 与字数口径；`reference_entry` / `role_style_coverage` 既有 note（保留为 FYI，不升格）。

## 4. 回归验证（十仓，`package --verify-only --strict`）

命令：`python3 -I tools/paper.py package --paper <仓绝对路径> --verify-only --strict`。
运行后各仓 `build-record.md` 的 PKG 追加为回归噪音，已逐仓 `git checkout -- build-record.md` 还原，未提交任何论文仓改动。

| 论文 | 版本 | 结果 | A6/A7/A8 |
|---|---|---|---|
| P1-SETDEBATE | v0.4.24 | ok / exit 0 / strict pass | pass / pass / pass |
| P2-LAYERGOV | v0.4.30 | ok / exit 0 / strict pass | pass / pass / pass |
| P3-SPATIAL | v0.3.28 | ok / exit 0 / strict pass | pass / pass / pass |
| P4-CONDITIONAL-COMPLETENESS | v0.3.18 | ok / exit 0 / strict pass | pass / pass / pass |
| P5-AUDIT-EVIDENCE | v0.4.23 | ok / exit 0 / strict pass | pass / pass / pass |
| P6-PROVISION-ALIGNMENT | v0.2.22 | ok / exit 0 / strict pass | pass / pass / pass |
| P7-GOVERNANCE-TRUSTWORTHY | v0.2.22 | ok / exit 0 / strict pass | pass / pass / pass |
| P8-CDC-DELTALAKE | v0.1.18 | ok / exit 0 / strict pass | pass / pass / pass |
| P9-SIGNALING-ECRL | v0.1.14 | ok / exit 0 / strict pass | pass / pass / pass |
| P10-ONEMAP | v0.5.3 | ok / exit 0 / strict pass | pass / pass / pass |

十仓 A1–A8 全 pass，工作区在还原后干净（`git status --porcelain` 空）。

### 4.1 反向验证（临时副本，未触碰任何论文仓）

| 场景 | 构造 | 结果 |
|---|---|---|
| 整节删除（P9 副本，截断于 `# 参考文献`） | 源侧无标题，正文 16 处引注 | `status: fail`、exit 1、`failed_assertions: ["A6"]`；A7 因旧 docx 仍在而 pass，A8 `not_applicable` |
| 渲染缺席（P9 docx 副本，`Bibliography` → `BlockText`） | 源侧声明完整，docx 段落数 0 | A7 fail（声明存在但渲染缺席）、A8 fail（节内非空但 Bibliography 段落 0） |
| 空节（仅保留 `# 参考文献` 标题） | 源侧标题在、节内无内容 | A8 fail（节内非空白字符 0） |
| docx 路径不存在 | 传给 `_bibliography_gates` 不存在路径 | A7/A8 均 `status: "error"`，未计 fail |
| 无标题且无引注 | `# 1 引言` + 普通正文 | A6 pass、A7 pass、A8 `not_applicable` |

## 5. 已知边界与开放项

1. **A6 只认作者-年引注**：纯数字上标 `[12]` 体系（GB/T 7714 顺序编码制）不在本断言覆盖内。当前十篇均为作者-年制；如后续出现顺序编码制论文，需另立判据（引注数阈值改为 `[N]` 计数）。
2. **A7 依赖 `pStyle` 精确等于 `Bibliography`**：全角引号导致的伪样式（`“Bibliography”`）同样会被判 fail；这正是 GC-2026-1117-05 源级 lint 的兜底，失败信息已提示引号问题。
3. **`check` 的 docx 选取**：取 `build/current.json` 指向版本的第一个 `.docx`。若同版本目录存在多份 docx（非规范状态），可能选中非交付件；`package` 路径不受影响（按 manifest 记录的 basename 解析）。
4. **未做的**：断言未写入 manifest 的 `limitations` 字段（保持既有 schema 不变）；`role_styles_unused_limitation` 仍为 note，硬约束由 A7 承担。

## 6. 复现与核对命令

```bash
# 三断言全绿
python3 -I tools/paper.py package --paper <repo> --verify-only --strict
# check 侧
python3 -I tools/paper.py check --paper <repo> | python3 -c 'import json,sys;print(json.load(sys.stdin)["results"]["bibliography_gates"])'
# rules_version 无旧值残留
grep -rn '"0\.4\.3"\|rules_version: 0\.4\.3' project.yaml governance/rule-index.yaml templates/paper/paper.yaml tools/paper.py
```
