# 治理变更记录 GC-2026-1116-04：表格列宽按内容自动优化（content-proportional column widths）

- 日期：2026-11-16
- 编号：GC-2026-1116-04
- 类型：排版规则修订（profile 新键 + schema 同步 + 构建期列宽重写 + 落地断言）
- 触发：用户指令——表格排版设置列宽自动优化；示例：P3 表 3 第一、二列收窄，为第三列释放列宽空间。
- 规则依据：AGENTS.md F9；PF-B3（profile 为实现载体，无静默降级）、PF-B11（单一真值源）、PF-B12（落地断言）

---

## 1. 基线取证

| 证据 | 内容 |
|---|---|
| markdown 源 | P3 表 3 为等宽管道表（`|---|---|---|`） |
| 成品实测 | pandoc 按分隔线等宽发列：3 列各 2640 twips，网格合计 7920 twips；而 `tblW` 为 `pct 5000`（100%），`tblLayout fixed` |
| 后果 | ① 标签列（"算子大类"）与数列（"数量/个"）和长文本列拿同样宽度；② 网格合计 7920 < 页内容宽 9638 twips，表格整体窄于正文栏 |
| 用户观感 | 短列空荡、长列拥挤换行，正是要优化对象 |

## 2. 规则（profile 新键，schema 已同步）

`tables` 块新增两键（`schemas/layout-profile.schema.json` 的 `tables.additionalProperties: false` 已同步放开登记）：

| 键 | 值 | 含义 |
|---|---|---|
| `column_widths` | `content`（默认）\| `equal` | `content` = 量各列最宽单元格后按比例分配；`equal` = 保持 pandoc 等宽 |
| `min_column_pct` | `5` | 单列宽度下限（占表宽百分比），防止短数列被压塌 |

stie profile 设 `column_widths: content`、`min_column_pct: 5`。9 篇的 `build/layout.yaml` 均未覆写表格键，改动全域生效。

## 3. 实现（paper.py 构建期后处理）

`_optimize_table_columns()`（与 `_harden_tables` 同级，在构建管线中紧随其后调用）：

1. 从 `sectPr` 取页内容宽 = `pgSz.w − pgMar.left − pgMar.right`（P3 实测 9638 twips）。
2. 逐表逐列量**最宽单元格**：CJK 记 2 单位、拉丁记 1 单位（含表头行）。
3. 分配：`列宽% = min_column_pct + (100 − min_column_pct×列数) × 该列量/总列量`——保证每列不低于下限且合计恰为 100%。
4. 写回：`tblW` 改 `dxa` 且等于内容宽（表格与正文栏齐宽）；重建 `tblGrid`；逐单元格写 `tcW`（`tcPr` 首位插入，缺失则新建）。
5. 取整误差吸到最宽列，网格合计与内容宽**严格相等**。
6. 形状异常的表（无行、不足 2 列、行间单元格数不齐）不重写、记入 `skipped`，绝不静默改坏。

## 4. 落地断言（PF-B12）

`_assert_layout_landing` 新增两项，任一不过即构建失败：

- `table_grid_spans_text_block`：每表 `gridCol` 合计 = 页内容宽（容差 2 twips）。
- `table_column_floor_pct`：每表最窄列 ≥ `min_column_pct`（容差 2 twips）。

## 5. 9 篇重建结果

全部 `version-bump patch` → `build docx/pdf` → `snapshot` → `package` → `strict`：

| 论文 | 新版本 | 表数 | 列宽占比（前 3 表示例） | strict |
|---|---|---|---|---|
| P1 | v0.4.21 | 8 | [35,13,52] [30,70] [10,29,30,31] | pass |
| P2 | v0.4.26 | 7 | [55,10,35] [14,24,29,33] [13,42,45] | pass |
| P3 | v0.3.28 | 3 | **[9,14,77] [12,22,66] [13,8,78]** | pass |
| P4 | v0.3.18 | 4 | [7,12,25,56] [23,15,19,43] [9,17,19,19,21,13] | pass |
| P5 | v0.4.21 | 4 | [12,38,50] [16,42,42] [23,39,37] | pass |
| P6 | v0.2.22 | 4 | [17,44,38] [41,23,36] [23,15,11,11,11,15,13] | pass |
| P7 | v0.2.22 | 6 | [12,31,23,34] [15,54,31] [19,45,37] | pass |
| P8 | v0.1.10 | 2 | [11,19,33,37] [15,21,18,18,15,13] | pass |
| P9 | v0.1.11 | 1 | [11,22,67] | pass |

用户点名的 P3 表 3：列 1（算子大类）13.5%、列 2（数量/个）8.3%、列 3（主要功能与代表性算子）78.3%——前两列收窄、空间释放给第三列，符合预期。39 张表网格合计全部等于内容宽，最窄列均高于 5% 下限。`verify_layout.py` 全库 27 PASS / 0 FAIL。

## 6. 精确变更清单

| 文件 | 变更 |
|---|---|
| `schemas/layout-profile.schema.json` | `tables` 新增 `column_widths`（enum content/equal）、`min_column_pct`（number 0–50） |
| `templates/layout/profiles/stie.yaml` | 新增 `column_widths: content`、`min_column_pct: 5` |
| `tools/paper.py` | 新增 `_cell_units()`、`_optimize_table_columns()`；构建管线接入；`_assert_layout_landing` 新增两项断言 |

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 列宽变化改变分页与表格外观 | 9 篇 pdf 已随重建更新；投稿前以新构建为准 |
| R2 | CJK=2/拉丁=1 是近似度量，极端内容（长英文单词、URL）可能仍显挤 | 下限 5% 保证不塌；如需精确可按字体度量后续增强 |
| R3 | 合并单元格（gridSpan）表不适用比例模型 | 实现中按"行间单元格数不齐"判定跳过并记录，不做猜测性重写 |
| R4 | `equal` 回落路径未经实测 | 本次 9 篇均为 `content`；`equal` 分支仅作配置回落，未走构建验证 |
