# 治理变更记录 GC-2026-1111-01-S：SemVer 与产物路径孤儿批次补充记录

- 日期：2026-11-11
- 编号：GC-2026-1111-01-S（Supplement；对 GC-2026-1111-01 提交 `a63b477` 之后工作树中已存在、但无变更记录的一批修改做 F9 追溯补记）
- 类型：规则正文与 schema 修订的追溯登记（内容为先行落盘，本记录不改动该批文件）
- 规则依据：AGENTS.md F9（治理变更纪律）；复核来源：GC-2026-1111-02/03 合并计划 v2.1 第一轮独立复核 P1-1
- 流程状态：随 GC-2026-1111-02 + GC-2026-1111-03 同一治理提交入库；其规则正文修改一并计入 rules_version 0.2.0

## 1. 基线

`a63b477`（即 GC-2026-1111-01 提交）之后、GC-02/03 落盘之前，工作树中存在以下未提交且无记录的修改。来源为本项目治理执行会话（非本记录起草会话）；本记录按 F9 对其逐文件登记，使"变更清单与记录对应"恢复成立。

## 2. 逐文件清单（内容不改，仅登记）

| # | 文件 | 改动内容 | 理由 |
|---|---|---|---|
| 1 | `AGENTS.md` | F3 版本管理改为 SemVer 2.0.0 `vMAJOR.MINOR.PATCH` 表述（初稿 `v0.1.0`、首发 `v1.0.0`，MAJOR/MINOR/PATCH 加粗分级） | 与 versions.md PF-V2 同步统一 |
| 2 | `governance/versions.md` | PF-V2 同步 SemVer v 前缀表述；删除"0.x 研究期用 minor"特则 | 同上 |
| 3 | `governance/build.md` | PF-B7 版本发布：产物路径 `output/REL-0001/` → `build/<version>/`；新增中文全题名 POSIX 安全文件名规则；`current.json` 切换位置同步 | 论文侧 P1-P3 已按 `build/<version>/` 实操（三篇完成 v1.1.1 样式版本号制度重构），规则与实操对齐 |
| 4 | `schemas/paper.schema.json` | `paper_version` pattern 加 `^v` 前缀 | 与 F3/PF-V2 SemVer 表述一致 |
| 5 | `templates/layout/profiles/draft.yaml` | 字体值 `Noto Serif SC` → `新宋体` + `latin_font: Times New Roman` + 跨平台说明 | 中文期刊惯例基线 |
| 6 | `templates/paper/.gitignore` | 增加 `build/` | 构建产物不入库（论文侧提交策略） |
| 7 | `templates/paper/build/layout.yaml` | GC-01 修复版的注释措辞更新 | 与 draft.yaml 字体值联动 |
| 8 | `templates/paper/paper.yaml` | `paper_version: v0.1.0`（v 前缀） | 同 #4 |
| 9 | `SKELETON-PLAN.md` | §6 版本表改 SemVer 三段表；§9 构建管道行更新（REL 记录在 output/、新制度产物在 build/） | 同 #1/#3 |
| 10 | `governance/changes/2026-11-11-capability-pipeline.md` | GC-01 记录自身的基线描述同步（论文侧基线 v 前缀、产物双轨制表述） | 记录与事实对齐 |

## 3. 连带冲突与处置（GC-02/03 承接）

- schema `^v` pattern 与 7 篇论文 `paper_version` 无 v 前缀冲突 → 论文侧 config 重构（合并计划 v2.1 C2）统一加 v 前缀归一。
- PF-B7 新路径与 `tools/paper.py` 旧 `output/REL-*` 行为不一致 → GC-2026-1111-02 的 paper.py 构建重构已改为 `build/<version>/` + 中文题名文件。

## 4. 恢复方式

本批次随 GC-02/03 单一治理提交入库；恢复 = revert 该提交。

## 5. 验证

- `python3 -I` jsonschema 校验：模板与 7 篇论文 paper.yaml 对修订后 schema 的校验结果见 GC-2026-1111-02 记录 §验证（v 前缀归一后除已登记 budget 已知项外全 PASS）。
- YAML 解析：draft.yaml / paper.yaml 模板 safe_load 通过。
