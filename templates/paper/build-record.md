# 构建记录（build-record）

本文件按 PF-B5/PF-B6 载明每次构建的可复现步骤、产物校验与版式决策。

**产物本体在 `build/<version>/`，不入版本库**（`.gitignore` 已排除 `build/`、`temp/`、`output/`）。
入库的凭据是**本记录 + `build/<version>/manifest.json`**：manifest 记录本次构建的输入快照
（逐文件 sha256）、所用 layout profile 与 reference docx 的 sha256、规则版本、工具链版本、
产物 sha256 与页数；本记录以人可读的方式登记**为什么这么排、哪些缺陷改了、哪些没改**。

> 二者缺一不可：manifest 说明"是什么"，本记录说明"为什么"。
> 两者都不入库则发布记录不可复核；两者都入库则产物本体污染仓库。

---

## R<N> · <paper_version> <本次构建的触发原因>（<日期>）

- 触发：<例如：视觉验收判定 X/Y pass、N 项 must_fix / 版式 profile 变更 / 引文体例修正>
- 修复前 HEAD：`<sha>`（版式/内容状态）
- 修复提交：`<sha> <简述>`、`<sha> <简述>`
- 工具链：pandoc <版本>（docx）、LibreOffice `soffice --headless --convert-to pdf`（PDF）
- CLI：`instruction.git/tools/paper.py`（`python3 -I`，`--paper` 绝对路径）

### 可复现构建步骤（按序）

```bash
cd <governance repo>
python3 -I tools/make_refdoc.py            # 由 profile 生成 reference docx（确定性）
python3 -I tools/paper.py build docx --paper <paper 绝对路径>
python3 -I tools/paper.py build pdf  --paper <paper 绝对路径>
```

### 产物校验

| 项 | 值 |
|---|---|
| docx sha256 | `<16 位前缀>` |
| pdf sha256 | `<16 位前缀>` |
| 总页数 | `<N>` |
| pdf 嵌入字体 | `<字体清单>` |
| layout profile / reference docx sha256 | `<profile>` / `<16 位前缀>` |
| manifest 快照校验 | `<逐文件 sha256，见 manifest>` |

### 决策与取舍登记

<逐条写明：改了什么、依据哪条规则、为什么这么改、放弃了哪个替代方案、
哪些问题**没有**改以及原因。>

### 相关文件

<列出本次涉及的正文/配置/图表文件路径。>

---

## 维护约定

- 每次构建**追加**一节，不改写既有节（PF-B7：已发布版本不得就地修改）。
- 产物本体不入库；`build/` 已在 `.gitignore` 中。
- 引用目标刊要求时写条款号或来源 URL，不写"按要求"（PF-W6/F9）。
- 版式缺陷按 PF-B6 逐页目视记录，页码写明。
