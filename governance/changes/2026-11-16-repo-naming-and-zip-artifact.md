# 治理变更记录 GC-2026-1116-02：论文仓命名规范与构建产物 zip 命名（repo-name + version）

> 已被 GC-2026-1116-06 修订：命名规范修正（下划线词间连接＋作者圆括号形式）。历史内容未改，指向新记录。

- 日期：2026-11-16
- 编号：GC-2026-1116-02
- 类型：仓库规范修订（命名规则 + 产物命名）
- 触发：用户指令——论文仓名称改为 `P{N}-{FULL TITLE}-{FIRST AUTHOR}.git`（标题为完整英文名称并做 GitHub 规范化转义），构建产物 zip 跟随仓库名 + 版本号。
- 规则依据：AGENTS.md F9（治理变更纪律）；PF-B7（release 文件命名）、PF-B16（投稿包）

---

## 1. 平台硬限制（实测，2026-11-16）

| 限制 | 实测证据 | 处置 |
|---|---|---|
| 仓名上限 **100 字符** | `gh api -X PATCH` 返回 422 `name cannot be more than 100 characters` | 超限篇按 §2 规则压缩 |
| 仓名**不支持中文** | 首轮改名传入 `...-刘馨`，API 返回 200 但实际仓名变为 `...--`（中文被静默剥除） | 第一作者改取其英文名（`authors.yaml#name_en`）的连字符形式，如 `Liu-Xin`、`Yang-Sen` |

## 2. 命名规则（最终采用）

```
仓库名 = P{N}-{TITLE_EN 规范化}-{FIRST_AUTHOR_EN}
```

- `TITLE_EN 规范化`：非字母数字一律转 `-`，压缩连续 `-`，去首尾。
- `FIRST_AUTHOR_EN`：取 `paper.yaml#authors[].name_en`（缺失时回落 `authors.yaml`），空格转 `-`。
- 超限时（9 篇中 5 篇）：先剔除虚词（of/the/for/a/an/and/in/to/on/with/based），仍在 100 内按**词边界截断**，保留前部实词；作者后缀始终保留。
- 旧名中的日期后缀（`-20251110` 等）随本次改名一并去除。

### 9 篇最终仓名

| 本地目录 | GitHub 仓名 | 长度 |
|---|---|---|
| P1-SETDEBATE-20251110 | P1-Set-Relational-Multi-Model-Debate-Quality-Assessment-Contradiction-Detection-Multimodal-Yang-Sen | 99（截断） |
| P2-LAYERGOV-20251110 | P2-Layered-Governance-of-Public-Sector-Knowledge-Assets-Mechanism-and-Evidence-Liu-Xin | 86 |
| P3-SPATIAL-20251110 | P3-Design-Implementation-Spatiotemporal-Big-Data-Governance-Platform-Full-Lifecycle-Li-Liying | 93（截断） |
| P4-CONDITIONAL-COMPLETENESS-20251111 | P4-Conditional-Completeness-Constrained-Retrieval-for-Natural-Resources-Documents-Yang-Sen | 90 |
| P5-AUDIT-EVIDENCE-20251111 | P5-Construction-of-a-Full-Chain-Evidence-Knowledge-Base-for-Audit-Rectification-Liu-Xin | 87 |
| P6-PROVISION-ALIGNMENT-20251111 | P6-Structure-Constrained-Provision-Alignment-Regulatory-Document-Lineage-Natural-Resources-Yang-Sen | 99（截断） |
| P7-GOVERNANCE-TRUSTWORTHY-20251111 | P7-Design-Governance-Framework-Trustworthy-Intelligent-Retrieval-Knowledge-Bases-Yang-Sen | 89（截断） |
| P8-CDC-DELTALAKE-20261113 | P8-Real-Time-Acquisition-and-Version-Tracing-of-Natural-Resource-Spatiotemporal-Data-Liu-Yinghao | 96 |
| P9-SIGNALING-ECRL-20261113 | P9-Supervision-Ecological-Conservation-Redlines-Mobile-Signaling-Data-New-Pathways-Wu-Hongling | 94（截断） |

## 3. 产物 zip 命名（覆盖 PF-B7 传统投稿名）

`tools/pack_submission_zip.py` 的输出名由 `标题（第一作者中文名）.zip` 改为 **`<仓库名>-<版本号>.zip`**（例：`P2-Layered-...-Liu-Xin-v0.4.24.zip`）。

- 仓库名取得优先级：`--name` 显式指定 > 论文仓 `git remote get-url origin` 的仓名 > PF-B7 传统名（无 remote 时兜底）。
- **PF-B7 传统投稿名仍随 JSON 输出的 `submission_name_pf_b7` 字段打印**，编辑部场景如需按 S19 命名可据此改名，不丢信息。
- 确定性不变：条目时间戳仍固定，同输入两次打包字节可比。

## 4. 精确变更清单

| 项 | 变更 |
|---|---|
| `tools/pack_submission_zip.py` | zip 命名改为仓库名+版本号；新增 `--name`；输出增加 `naming`/`repo`/`submission_name_pf_b7` 字段 |
| `templates/ci/build-submission.yml` | 无需改动：工作流以 `${{ github.event.repository.name }}` 取仓名，自动跟随新名 |
| GitHub 组织仓 | 9 个论文仓全部重命名（旧名由 GitHub 自动重定向） |
| 各论文仓本地 git | `origin` URL 已同步为新仓名，`ls-remote` 实测可达 |

## 5. 未随本轮变更的事项（需用户裁定）

1. **本地工作目录名未改**：仍为 `P1-SETDEBATE-20251110` 等旧名，与 GitHub 仓名不一致；`paper.yaml#id` 亦仍是旧值（工具以目录名推导 paper_id，进入 manifest 与 build-record）。改目录名会牵动 build-record / verification.yaml / reviews 等历史文本中的旧标识，需单独一轮。
2. **PF-B7/venue S19 的投稿 zip 名被覆盖**：如编辑部要求 `标题（第一作者中文名）.zip`，按 §3 的 `submission_name_pf_b7` 字段改名即可。

## 6. 验证

| # | 项 | 方法 | 结果 |
|---|---|---|---|
| a | 仓名合规 | `gh api orgs/PaperWorkflows/repos` 列出实际仓名 | 9 篇均为目标名，无残留中文、无超限 |
| b | 本地可达 | 逐仓 `git ls-remote origin HEAD` | 9/9 可达 |
| c | zip 命名 | 本地实跑 `pack_submission_zip.py`（P2） | `P2-Layered-...-Liu-Xin-v0.4.24.zip`，14 条目 |
| d | 兜底 | 复制到无 git remote 的目录实跑 | 回落 PF-B7 名 `公共部门知识资产分层治理：机制与实证（刘馨）.zip` |
| e | 语法 | `py_compile` | 通过 |
