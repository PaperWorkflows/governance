# 治理变更记录 GC-2026-1116-03：表格字号落地修复与 8pt 新规（table body/header 8pt）

- 日期：2026-11-16
- 编号：GC-2026-1116-03
- 类型：排版规则修订（profile + refdoc 生成器 + 落地断言）
- 触发：用户指令——9 篇论文的表格（table）中表头与内容行字体均使用 8pt（比正文略小）。
- 规则依据：AGENTS.md F9；PF-B3（profile 为实现载体，无静默降级）、PF-B11（refdoc 由 profile 生成）、PF-B12（落地断言）

---

## 1. 基线取证：表格字号此前**从未落地**

用户要求“表头与内容行 8pt”，但核查发现既有配置本身是失效的：

| 证据 | 内容 |
|---|---|
| profile 声明 | `stie.yaml` 同时写有 `typography.sizes.table_body: 9` 与 `tables.body_pt: 9` |
| 生成器消费 | `make_refdoc.py` 只把 `tables.cell_first_line_indent_chars` 打到 `Compact` 样式的缩进上，**两处字号均无任何消费点**（grep 零命中） |
| 成品实测 | P2 v0.4.24 docx：表格单元格无显式 `w:sz`，`Compact` 样式无 `w:rPr` → 单元格继承 `Compact → BodyText → Normal`，即正文 10.5pt |
| 结论 | 表格实际渲染 10.5pt，比 profile 声明的 9pt 大 1.5pt；这是“声明未落地”的静默降级，正是 PF-B3 要防的形态 |

## 2. 根因与修法

pandoc 把**所有**表格单元格（含表头行）渲染为 `Compact` 段落样式。因此表格字号必须落在 `Compact` 上：

1. `make_refdoc.py`：给 `Compact` 补 `rPr`（表格字体 + 字号）。取值优先级 `tables.body_pt` → `typography.sizes.table_body`，与既有双声明兼容，不新增第三种来源。
2. `stie.yaml`：`tables.body_pt` 与 `typography.sizes.table_body` 一并设为 **8**（用户裁定）。
3. `paper.py`：`_assert_layout_landing` 新增 `compact_sz_halfpt` 断言——从成品 docx 的 `Compact` 样式读 `w:sz`，与 profile 期望值比对，不等即构建失败。此类“声明未落地”缺陷今后会在构建期暴露，不会再把错误字号送出。
4. 重生成 refdoc（PF-B11 同步校验通过）。

表头行与内容行由同一 `Compact` 样式承载，故一次落地即同时覆盖用户要求的“表头 + 内容行”；三线表的表头底边框与填充色由 `tblStylePr firstRow` 承担，不受影响。

## 3. 未动的项

- `typography.sizes.table_note: 9`（表注）——用户只指定表头与内容行，表注维持 9pt。
- `tables.caption_pt: 9`（表题）——同上，未在指令范围内。
- 正文 `body_pt: 10.5`、参考文献条目 9pt 等均未动。

## 4. 精确变更清单

| 文件 | 变更 |
|---|---|
| `templates/layout/profiles/stie.yaml` | `tables.body_pt: 9 → 8`；`typography.sizes.table_body: 9 → 8` |
| `tools/make_refdoc.py` | `Compact` 样式补 `rPr`（表格字体 + 字号），取值 `tables.body_pt` → `sizes.table_body` |
| `tools/paper.py` | `_assert_layout_landing` 增 `compact_sz_halfpt` 断言 |
| `templates/layout/refdoc/stie.docx` | 重新生成（`Compact` 现含 `<w:sz w:val="16"/>`，即 8pt）；`make_refdoc.py --check` 三档 in_sync |

## 5. 9 篇重建结果

全部 `version-bump patch` → `build docx` → `build pdf` → `build snapshot` → `package` → `package --verify-only --strict`：

| 论文 | 新版本 | docx/pdf | strict |
|---|---|---|---|
| P1 | v0.4.20 | ok | pass |
| P2 | v0.4.25 | ok | pass |
| P3 | v0.3.26 | ok | pass |
| P4 | v0.3.17 | ok | pass |
| P5 | v0.4.20 | ok | pass |
| P6 | v0.2.21 | ok | pass |
| P7 | v0.2.21 | ok | pass |
| P8 | v0.1.9 | ok | pass |
| P9 | v0.1.10 | ok | pass |

成品复核：9 篇 docx 的 `Compact` 样式 `w:sz` 均为 **16 半磅 = 8.0pt**。`verify_layout.py` 全库 27 PASS / 0 FAIL。

## 6. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 表格字号由 10.5pt 降到 8pt，版面更紧凑，可能改变分页 | 9 篇 pdf 页数已随重建更新；投稿前如需核对页码以新构建为准 |
| R2 | `Compact` 同时服务于紧凑列表（tight list） | 本次改动使紧凑列表也变 8pt；9 篇构建的 landing 断言与版面校验均通过，未见异常；如个别篇目紧凑列表需保持正文号，另立专项 |
| R3 | 既有 L2 覆盖 | 已逐篇核查 `build/layout.yaml`，9 篇均未覆写表格相关键，改动全域生效 |
