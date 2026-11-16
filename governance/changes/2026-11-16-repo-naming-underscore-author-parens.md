# 治理变更记录 GC-2026-1116-06：论文仓命名规范修正（下划线词间连接＋作者圆括号形式）

> 本记录为 GC-2026-1116-02 的修订版；计划版本 v2，独立计划审查提出的补正项已并入；落盘后独立复核通过方可提交。
> 已被 GC-2026-1116-07 修订：ci 模板两处 governance→instruction 误改由 GC-2026-1116-07 回退为 PaperWorkflows/governance；作者圆括号形式已由 GC-2026-1116-07 修订为连字符形式；历史结论不改写，仅在遗留文案表追加回退注释。

- 编号：GC-2026-1116-06
- 计划版本：v2（经独立审查补正后批准）
- 日期：2026-11-16
- 类型：仓库规范修订，修订 GC-2026-1116-02
- 基线：GC-2026-1116-02 ＋ `rules_version` 0.3.3
- 触发：用户指令——`P{N}-{TITLE}-{AUTHOR}.git` 结构不变，Title/Author 词间连接符用英文下划线 `_`，作者用 `({AUTHOR})` 形式包裹；示例 `P9-Example_Title-(Author_A).git`（用户示例已按 GC-1116-01 映射规则脱敏）
- 规则依据：AGENTS.md F9（治理变更纪律）

---

## 新规范全文

```
GitHub 论文仓名 = P{N}-{TITLE_EN}-({FIRST_AUTHOR_EN})
```

- 结构：P{N} 与 TITLE 之间、TITLE 与 AUTHOR 之间用连字符 `-`（用户示例保留 P9- 形式）；TITLE 与 AUTHOR 内部的词间连接符一律英文下划线 `_`。
- TITLE_EN：取 `paper.yaml#title_en`；非字母数字一律转 `_`，压缩连续 `_`，去首尾。
- FIRST_AUTHOR_EN：取署名序第一（roles 含 first，经 author_id join `authors.yaml`）的 `name_en`；空格转 `_`，连字符/撇号等非字母数字同样转 `_`；整体包裹圆括号。题名与作者名的词字符口径均为 ASCII 字母数字（é 等非 ASCII 拉丁字母按 `_` 处理，实现与规范以此句为准）。
- 长度硬限：仓名全串（含 P{N}- 前缀与作者后缀）≤100 字符（GitHub 实测 422）；中文不可用（GitHub 静默剥除，GC-1116-02 实测）——`title_en` 或 `name_en` 缺失/为空/含中文时派生函数必须报错，不得静默产出怪名。
- 超限处置：先剔虚词（and/of/for/the/a/an/in/to/on/with/based，词边界、大小写不敏感）；仍超则按词边界从尾部整词剔除，直至 ≤100。
- 本地工作目录名模式（`papers/P{N}-{AUTHOR_EN}-{YYYYMMDD}`）不随本轮改变。
- 随仓名自动跟随、无需改代码：`tools/pack_submission_zip.py`（从 git remote origin 解析仓名）、`templates/ci` 工作流（用 `github.event.repository.name`）。
- 本规范修订 GC-2026-1116-02（连字符词间连接、作者无圆括号）。

---

## 精确变更清单

| 项 | 变更 |
|---|---|
| `governance/changes/2026-11-16-repo-naming-underscore-author-parens.md` | 本记录（新增） |
| `project.yaml` | github 节新增 `paper_repo_name_pattern` 字段 |
| `README.md` | Paper Repos 节示例仓名更新为新规范占位形式 |
| `governance/versions.md` (PF-V4) | 仓名模式更新为新规范占位表述 |
| `SKELETON-PLAN.md` | 三处旧仓名模式更新为新规范占位表述 |
| `governance/build.md` (PF-B16) | zip 名描述由"标题（第一作者中文名）.zip"改为 `<repo-name>-<paper_version>.zip` |
| `templates/ci/build-submission.yml` | 第 7 行注释 zip 名描述同步；第 35 行 `repository` 改为 `PaperWorkflows/instruction` |
| `tools/paper.py` | 新增 `derive_repo_name()`；放宽 `parse_paper_id` 正则；proposal `--title-en`/`--author-name-en` 由可选改为必填（不再以 `author_pinyin.title()` 兜底）；scaffold 新增 `--title-en`/`--author-name-en` 可选，成对提供时才走派生 |
| `governance/changes/2026-11-16-repo-naming-and-zip-artifact.md` (GC-1116-02) | 文首 +2 行指向块：`> 已被 GC-2026-1116-06 修订` |

---

## 理由

1. GC-1116-02 采用的连字符词间连接形式（`P9-Example-Title-...-Author_A`）与 GC-1116-02 实测中 5/9 篇超长超限截断的问题同源——连字符在词边界处反复出现导致仓库名冗长。下划线连接词、连字符分隔段落的混排结构可在视觉上将标题与作者区分开，同时减少不必要的分隔符数量。
2. 作者名用 `({AUTHOR})` 圆括号包裹，使仓名三段结构（P{N} / TITLE / (AUTHOR)）一目了然，便于人工识别与解析。
3. `pack_submission_zip.py` 和 CI 工作流从 git remote 或 `github.event.repository.name` 动态取仓名，规范变更后所有现有仓库自动跟随新命名格式，无需额外修改。

---

## 备选方案

| 方案 | 描述 | 结果 |
|---|---|---|
| A | 维持 GC-2026-1116-02 连字符词间连接 | 否，用户已明确修正 |
| B | P{N} 后连接符也改下划线（`P9_TITLE-(AUTHOR)`） | 否，用户示例保留 `P9-` 形式的连字符 |
| C | 标题用驼峰命名（`SupervisionEcologicalConservation...`） | 否，用户明确要求下划线 |

---

## 风险

| # | 风险 | 处置 |
|---|---|---|
| 1 | P1–P9 共 9 个既有论文仓需再次 `gh rename`；GitHub 自动重定向、本地 `origin` 同步——GC-1116-02 已验证此流程可安全执行。P10 暂缓改名（用户 2026-11-16 裁定：待其论文任务完成后按当时规范改名），本轮不动其本地 origin（现为 `P10-ONEMAP-20261116.git`） | 逐仓（P1–P9）执行 `gh repo rename` + `git remote set-url origin` |
| 2 | 超限篇数量：P1/P3/P6/P9/P10 共五篇（GC-1116-02 实际记录 9 篇中 5 篇截断），下划线替换连字符后词更长，超限风险可能增加 | 派生函数内置虚词剔除与尾部整词截断 |
| 3 | zip 产物名随仓名变，已交付包不受影响 | 仅影响新交付 |
| 4 | 工具改动（`derive_repo_name`、`parse_paper_id`、proposal/scaffold）需回归测试 | 见验证方法 |
| 5 | 隐私：GC-1116-02 记录中已含真实作者英文名及真实仓名映射，属既成暴露；本记录按 GC-1116-01 映射规则使用占位符，不写入真实作者英文名与真实仓名 | 重新公开前需处置 GC-1116-02 遗留 PII，属 GC-1116-01 待裁事项 |

---

## 恢复方式

- 仓名可再 `gh repo rename` 回退至 GC-1116-02 形式或其他规范形式。
- 工具代码改动可通过单次 `git revert` 恢复至 GC-1116-02 实现。
- 文档性变更（README、versions、build.md 等）直接回改即可。

---

## 验证方法

| # | 项 | 方法 |
|---|---|---|
| a | `derive_repo_name` 正确性 | 对 10 篇现场跑 `derive_repo_name` 并核验字符数 ≤100 |
| b | 工具无回归 | `py_compile` + P9/P10 工作区 `check` / `validate` 无回归 |
| c | 独立方核 diff | 独立方核对 diff 与变更清单一致 |
| d | rename 实测 | 逐仓（P1–P9）`gh repo view` + `git ls-remote origin` 确认可达 |

---

## 随本轮一并修正的遗留文案与缺陷

| 文件 | 原文 | 修正后 |
|---|---|---|
| `governance/build.md:140` (PF-B16) | `标题（第一作者中文名）.zip`（venue S19） | `<repo-name>-<paper_version>.zip`；PF-B7 传统名保留为 `pack` 工具输出的 `submission_name_pf_b7` 兜底字段 |
| `templates/ci/build-submission.yml:7` | `标题（第一作者中文名）.zip（PF-B7 / venue S19）` | `仓库名 + 版本号`（`<repo-name>-<paper_version>.zip`） |
| `templates/ci/build-submission.yml:35` | `repository: PaperWorkflows/governance`（治理仓旧名遗留） | `repository: PaperWorkflows/instruction`（现治理仓名，GC-2026-1116-07 回退为 `governance`） |
| `templates/ci/build-submission.yml:4` | `公共治理仓 PaperWorkflows/governance` | `公共治理仓 PaperWorkflows/instruction`（GC-2026-1116-07 回退为 `governance`） |
| `tools/paper.py:build_paper_yaml` | `paper_version: 0.1.0`（缺 `v` 前缀，proposal 新建工作区过不了 validate） | 新增 `paper_version` 参数，proposal 传 `args.version`（缺省 `v0.1.0`），scaffold 同理 |

---

## 隐私处置声明

本治理仓不落真实作者英文名与真实仓名映射；示例一律采用占位形式（如 `P1-Example_Paper_Title-(Author_A)`）。`derive_repo_name` 的派生逻辑由各论文仓本地 `paper.yaml` / `authors.yaml` 现场执行，映射不留存于治理仓。

追认 GC-1116-02 记录中已含真实作者英文名与真实仓名映射为既成暴露事实；治理仓重新公开前需按 GC-1116-01 处置，属 GC-1116-01 待裁事项。

---

## 未随本轮变更的事项

1. **本地工作目录名不改**：仍为 `papers/P{N}-{AUTHOR_EN}-{YYYYMMDD}` 形式。
2. **GC-1116-01 重新公开裁定不动**：治理仓当前 private，是否重新公开由用户另行裁定。
3. **P10 仓名暂缓**：用户 2026-11-16 裁定待 P10 论文任务完成后再改名；本轮的 `gh rename` 与本地 `origin` 设置均不含 P10（其 origin 保持 `P10-ONEMAP-20261116.git`）。`derive_repo_name` 的 10 篇派生测试包含 P10 仅为工具验证，不构成改名动作。

## 已登记的已知项（后续轮次处理）

| # | 项 | 说明 |
|---|---|---|
| ① | `derive_repo_name` 短虚词题 early-return | 如 `The And Of` 全为虚词时走 stop-word 过滤后的 early-return（长度≤100），代码注释"不得静默产出怪名"宽于实际触发条件（仅虚词标题不报错）。不影响 GC-1116-02 实测的 9 篇实题。 |
| ② | SKELETON-PLAN.md:194 措辞 | "题名变更不影响仓库名"在新规范下易误导（仓名含 `title_en`）。建议改为"仓名立项时一次性派生，题名变更不触发仓名变更"。 |
| ③ | scaffold `git remote add origin` 健壮性 | 以 `check=True` 在 try 之外，异常可能未捕获。 |
| ④ | 字符口径 | 作者/题名规范化仅处理 ASCII 字母数字（é 等非 ASCII 拉丁字母按分隔符 `_` 处理）。将此类口径补入记录"新规范"正文的作者规范化条目，消除规范文本与实现的歧义。 |
