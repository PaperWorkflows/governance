# 治理变更记录 GC-2026-1116-07：作者圆括号形式不可达→改连字符形式＋治理仓名勘误

> 本记录为 GC-2026-1116-06 的修订版；计划版本 v1，经独立计划审查批准；落盘后独立复核通过方可提交。

- 编号：GC-2026-1116-07
- 计划版本：v1（经独立计划审查批准）
- 日期：2026-11-16
- 类型：仓库规范修订，修订 GC-2026-1116-06；含治理仓名事实性勘误
- 基线：GC-2026-1116-06（作者圆括号形式）
- 触发：平台实测证明 GitHub 仓名不可含 `()`（`(` 静默替换为 `-`、`)` 静默替换为 `-`）；主会话裁定作者段改连字符形式；用户 2026-11-16 另裁定 P10 暂缓改名；治理仓名文档勘误（instruction → governance）

---

## 新规范全文

```
GitHub 论文仓名 = P{N}-{TITLE_EN}-{FIRST_AUTHOR_EN}
```

- 结构：P{N} 与 TITLE 之间、TITLE 与 AUTHOR 之间用连字符 `-`；TITLE 内部词间连接符一律英文下划线 `_`；FIRST_AUTHOR_EN 前为一个连字符、姓名内部词间以下划线连接；**无圆括号**。
- TITLE_EN：取 `paper.yaml#title_en`；非字母数字一律转 `_`，压缩连续 `_`，去首尾。
- FIRST_AUTHOR_EN：取署名序第一（roles 含 first，经 author_id join `authors.yaml`）的 `name_en`；空格转 `_`，连字符/撇号等非字母数字同样转 `_`；题名与作者名的词字符口径均为 ASCII 字母数字（é 等非 ASCII 拉丁字母按 `_` 处理）。
- 长度硬限：仓名全串（含 P{N}- 前缀与作者后缀）≤100 字符（GitHub 实测 422）；中文不可用——`title_en` 或 `name_en` 缺失/为空/含中文时派生函数必须报错，不得静默产出怪名。
- 超限处置：先剔虚词（and/of/for/the/a/an/in/to/on/with/based，词边界、大小写不敏感）；仍超则按词边界从尾部整词剔除，直至 ≤100。
- 本地工作目录名模式（`papers/P{N}-{AUTHOR_EN}-{YYYYMMDD}`）不随本轮改变。
- 随仓名自动跟随、无需改代码：`tools/pack_submission_zip.py`（从 git remote origin 解析仓名）、`templates/ci` 工作流（用 `github.event.repository.name`）。
- 本规范修订 GC-2026-1116-06（作者圆括号形式改为连字符形式，并修正治理仓名引用）。

---

## 精确变更清单

| 项 | 变更 |
|---|---|
| `governance/changes/2026-11-16-repo-naming-author-hyphen-form.md` | 本记录（新增） |
| `tools/paper.py` | `derive_repo_name` 作者后缀由 `-({name})` 改为 `-{name}`（归一化后判空防护） |
| `SKELETON-PLAN.md` | 三处仓名模式去圆括号（:184 表格、:193 注意段、:257 小节标题） |
| `governance/versions.md` | 治理仓名引用全部从 `instruction` → `governance`（:32 PF-V4 表头、:33 论文仓模式去圆括号、:80 AGENTS 指针、:87 PF-V10 治理仓名） |
| `project.yaml` | `governance_repo: instruction` → `governance`；`paper_repo_name_pattern` 取值去圆括号（:61）；注释更新 |
| `README.md` | 治理仓名引用 `instruction` → `governance`（:3）；示例仓名两处去圆括号（:22 模式块、:29 clone 行）；链接指向 GC-2026-1116-07 |
| `templates/ci/build-submission.yml` | 第 4 行注释与第 35 行 `repository` 回退为 `PaperWorkflows/governance` |
| `governance/changes/2026-11-16-repo-naming-underscore-author-parens.md` (GC-1116-06) | 文首 +1 行指向块（:4）；随轮修正表 2 个单元格追加回退注释（:104-105） |

---

## 理由

1. **平台约束**：GitHub 仓名物理上只允许字母/数字/-/_/.。实测证明 `()` 不可达——含括号 rename 会被静默 mangle 为双连字符尾连字符形式（如 `test-(parentheses)` → `test--parentheses-`），既不符合规范文本，又难看且易误判为笔误。主会话按最接近用户原始意图的形式裁定为连字符分隔。
2. **连字符是结构原生分隔符**：P{N}、TITLE、AUTHOR 三段之间原本就用 `-` 分隔，作者前加 `-` 是最自然的形式，无需括号标记。
3. **治理仓名勘误**：PaperWorkflows 组织下公开治理仓为 `PaperWorkflows/governance`（真实存在，非 private）；`PaperWorkflows/instruction` 不存在。之前的误改把本地目录名 `instruction.git` 与过时文档表述当成了 GitHub 仓名现实。

---

## 备选方案

| 方案 | 描述 | 结果 |
|---|---|---|
| A | 作者段 = 连字符＋姓名内下划线（`-Author_A`） | **采用**，最接近用户原始意图 |
| B | 全下划线无作者标记（无 AUTHOR 段） | 否，丢失作者信息 |
| C | 维持 mangle 双连字符尾连字符形式（`-parentheses-`） | 否，难看且易误判为笔误 |

---

## 风险

| # | 风险 | 处置 |
|---|---|---|
| 1 | P1–P9 共 9 个既有论文仓需第三次 `gh rename`；GitHub 自动重定向、本地 `origin` 同步——GC-1116-02 与 GC-1116-06 已验证此流程可安全执行 | 逐仓执行 `gh repo rename` + `git remote set-url origin` |
| 2 | zip 产物名随仓名变，已交付包不受影响 | 仅影响新交付 |
| 3 | P10 暂缓改名不动（用户 2026-11-16 裁定） | 本轮不涉及 P10 |
| 4 | 本地工作目录名不改（仍为 `papers/P{N}-{AUTHOR_EN}-{YYYYMMDD}` 形式） | 不变 |

---

## 恢复方式

- 仓名可再 `gh repo rename` 回退至 GC-2026-1116-06 形式或其他规范形式。
- 工具代码改动可通过单次 `git revert` 恢复。
- 文档性变更直接回改即可。

---

## 验证方法

| # | 项 | 方法 |
|---|---|---|
| a | `derive_repo_name` 正确性 | 对 9 篇（P1–P9）现场跑 `derive_repo_name` 并核验字符数 ≤100 |
| b | 工具无回归 | `py_compile` + P9/P10 工作区 `check` / `validate` 无回归 |
| c | 独立方核 diff | 独立方核对 diff 与变更清单一致 |
| d | rename 实测 | 逐仓 `gh repo view` + `git ls-remote origin` 确认可达 |

---

## 随本轮一并修正的遗留文案与缺陷

| 文件 | 原文 | 修正后 |
|---|---|---|
| `project.yaml:57` (github.governance_repo) | `instruction` | `governance`（真实 GH 仓名） |
| `project.yaml:60` (paper_repo_name_pattern 注释) | `作者圆括号` | `作者连字符形式` |
| `README.md:3` (治理仓名引用) | `PaperWorkflows/instruction` | `PaperWorkflows/governance` |
| `governance/versions.md:32` (PF-V4) | `PaperWorkflows/instruction` | `PaperWorkflows/governance` |
| `templates/ci/build-submission.yml:4` | `公共治理仓 PaperWorkflows/instruction` | `公共治理仓 PaperWorkflows/governance`（回退 GC-1116-06 的误改） |
| `templates/ci/build-submission.yml:35` | `PaperWorkflows/instruction` | `PaperWorkflows/governance`（回退 GC-1116-06 的误改） |

---

## 治理仓名勘误说明（事实性修正）

以下修正源于将本地目录名 `instruction.git` 与过时文档表述误认为 GitHub 仓名现实：

| 文件 | 勘误前 | 勘误后 | 原因 |
|---|---|---|---|
| `project.yaml:57` | `governance_repo: instruction` | `governance_repo: governance` | GH 上公开治理仓名为 `PaperWorkflows/governance` |
| `README.md:3` | `This is the public PaperWorkflows/instruction repo` | `This is the public PaperWorkflows/governance repo` | 同上 |
| `governance/versions.md:32` | `` `PaperWorkflows/instruction`, public`` | `` `PaperWorkflows/governance`, public`` | 同上 |
| `templates/ci/build-submission.yml:4` | `公共治理仓 PaperWorkflows/instruction` | `公共治理仓 PaperWorkflows/governance` | 同上 |
| `templates/ci/build-submission.yml:35` | `repository: PaperWorkflows/instruction` | `repository: PaperWorkflows/governance` | 同上 |

---

## 隐私处置声明

本治理仓不落真实作者英文名与真实仓名映射；示例一律采用占位形式（如 `P1-Example_Paper_Title-Author_A`）。`derive_repo_name` 的派生逻辑由各论文仓本地 `paper.yaml` / `authors.yaml` 现场执行，映射不留存于治理仓。

---

## 已登记的已知项（与 GC-2026-1116-06 记录合并）

以下项已合并记录于 GC-2026-1116-06 的"未随本轮变更的事项"与"已登记的已知项"，此处不复述。

## 已登记的遗留项（本轮未改动）

| # | 项 | 说明 |
|---|---|---|
| ⑤ | 模板与代码中残留 8 处 `PaperWorkflows/instruction` 引用 | `templates/paper/AGENTS.md:4/16/17`、`templates/paper/README.md:14/86`、`tools/paper.py:627`（proposal 写入 AGENTS.md）、`tools/paper.py:922`（check 验证 expected_ref）、`SKELETON-PLAN.md:77`。迁移需连带存量 10 篇论文工作区的 AGENTS.md 更新，建议后续轮次一并提供迁移方案后处理。 |
