# 治理变更记录 GC-2026-1113-02：插图矢量化（svgBlip 保留 + 栅格兜底硬校验 + PDF 级插图渲染断言）

- 日期：2026-11-13
- 编号：**GC-2026-1113-02**（顺延 GC-2026-1113-01；01 已被另一条工作线的 PDF 导出确定性变更占用，提交 `37a6037`/`dc3e658`。计划草案 `temp/svg-vector-plan.md` 原编号 GC-2026-1113-01，实施时按主会话裁定改号）
- 类型：构建工具链行为修订 + 规则正文增补（`tools/paper.py`；`governance/build.md` PF-B12 增补条文；rules_version 保持 **0.3.0**，理由见 §9）
- 计划版本：v0.1 草案（`temp/svg-vector-plan.md`）+ 独立审查（agent-gpt-plus）裁决"修正后批准"，七项修正全部闭合（①改号 ②重写基线 ③PDF 图位断言重做 ④位图引用行为统一 ⑤F9 写盘后独立核验安排 + PF-B12 规则正文留痕 ⑥数据管线补全 ⑦并发前提）
- 规则依据：AGENTS.md **F9**（变更纪律：编号/基线与计划版本/精确变更清单/理由/备选/风险/恢复/验证）、**F5/F6**（论文侧工作由受派子代理执行、最小改动）；版式语义 **PF-B6**（图表验收——"检查实际 docx/PDF 渲染"）、**PF-B3**（落地校验，无静默降级）、**PF-B12**（落地校验，凡不可校验即不得静默放行）、**PF-B15**（SVG 交付与位图降级语义）、**PF-B7**（manifest 记录）、**PF-B2**（单一正文）
- 探针实测环境：pandoc 3.9 + LibreOffice 25.2.3.2 + poppler-utils 25.03（pdfimages/pdftotext/pdftoppm/pdffonts）+ librsvg2 2.60 + Noto Serif/Sans CJK SC
- 流程状态：计划草案 → 独立审查（七项修正）→ **实施 + 自测（本记录收口）→ 独立核验（agent-gpt-plus）完成：实测复现全部自测结论，另发现并闭合一项 P1 缺陷（poppler 工具缺失闸只兑现 pdfimages 一条），修正与复验见 §11**

---

## 1. 背景与用户指令

- 用户诉求：**PDF 配图文字清晰（矢量）**。旧 P1 v0.4.10 PDF 的 `pdfimages -list` 显示三张图幅级栅格 **605×418 / 605×288 / 605×293 @ 96 ppi**（第 5/10/11 页）——配图文字发虚的直接来源。
- 根因：`_strip_svg_alternatives()`（paper.py L2747–2805，出自 2026-11-12 `ab0bdcc`）把 pandoc 双源产物（栅格 PNG 兜底 + `<asvg:svgBlip>` SVG 备选）中的 **SVG 备选剥离**，PDF 只能内嵌 pandoc 在 96 DPI 下生成的 PNG 兜底。
- 历史缺陷：`ab0bdcc` 当初剥离是为规避"SVG-only blip（无栅格兜底）→ LibreOffice 渲染为空图位"的事故（`../figures/` 路径形式）。该失败模式此前**无任何机器守卫**，一旦复发即静默产出空图位 PDF。
- 本变更要同时解决：矢量诉求（保留 svgBlip）、历史缺陷结构性防回归（缺兜底硬失败）、PDF 级插图渲染无断言（新增图位/栅格断言）。

## 2. 基线（2026-11-13 实施时实测）

- **治理仓 HEAD**：`dc3e658`（docs(governance): GC-2026-1112-06 §9 第 11 项）。`tools/paper.py` 5 277 行。
- **并发前提（审查项⑦）**：他线对 `tools/paper.py` 的在途改动（PDF 导出确定性归一化，+246/−10，触及 `cmd_build_pdf` 与 `manifest["layout"]`，与本变更插入位重叠）**已于 2026-11-13 提交**（`37a6037` feat(manifest) + `dc3e658` docs）。实施前重申并实测：`git -C instruction.git diff --stat tools/paper.py` **为空**；`git status --short` 仅 `authors/registry.yaml`（他线未提交改动）——**本提交严禁 stage 它**。（订正计划草案 §1"在途改动为 +61/−10 `_extract_abstract` 英文摘要"之描述：该改动已在他线提交内，基线以实测空 diff 为准。）
- **论文侧事实（只读核查，papers/ 零改动；八篇）**：P1/P3/P4/P5/P6/P7 正文引 `.svg`，P2 仍引 `.png`（4 图均有同 stem `.svg` 伴生），**P8 有 `figures/`（3 组 png+svg 双源）但正文暂无插图引用**。订正计划草案 §1 表格：P4/P5/P7 已由 `.png` 迁移为 `.svg`；P5 fig2 现有 `.svg` 伴生（草案"仅 .png"已过时）。
- **探针关键结论（复现计划 §4）**：pandoc 对 `figures/x.svg` 引用恒产双源——`<a:blip r:embed="rIdN.png">` + `<asvg:svgBlip r:embed="rIdM.svg">`；P1 三图 extent 453.0×312.8 / 453.0×216.0 / 453.0×219.0 pt。当前工具链下 **SVG-only blip 亦渲染为矢量、非空**（neg1 实测 ink 37.66%/14.88%/8.78%，与正常构建逐位一致）——即 `ab0bdcc` 空图事故在当前环境**不复现**，差异来自宿主状态，代码无法锁死环境，只能靠断言守门（PF-B12）。
- **题注形态**：P1/P3/P6 为中英双语题注（中文「图 N」+ 英文「Fig. N」，P1 两者相隔约 6pt）；P3 正文额外重复中文题注段（pandoc 隐式题注在后文之前）；P6 正文存在「图4绘制三种方法…」类**干扰行**（以图号开头但非题注）。docx 图段样式 `CaptionedFigure`（含 keepNext），题注段样式 `ImageCaption`。

## 3. 精确变更清单（函数级；`tools/paper.py`，净 +586/−55 行）

| # | 位置 | 内容 |
|---|---|---|
| 1 | L2744–2805 `_strip_svg_alternatives`（59 行）→ **删除** | 不再改动 docx：保留全部 svgBlip，PDF 图位即矢量 |
| 2 | 新增 `_docx_relationship_targets` / `_validate_svg_alternatives`（L2744 起） | 枚举 docx 全部 `<a:blip>`；对每条含 `<asvg:svgBlip>` 的 blip 断言：① 开标签有栅格 `r:embed`（扩展名 ∈ `.png/.jpg/.jpeg/.bmp/.gif/.emf/.wmf/.tif/.tiff`）、② 其 relationship target 部件在包内、③ svgBlip 自身 `r:embed` 部件在包内。任缺 → 记 `{blip 序, primary/svg rid, defects}`；返回 `{check: svg_alternatives_preserved, svg_blips, raster_fallbacks, blips_missing_raster, missing}` |
| 3 | 调用点（原 L3054–3055） | `svg_stripped = _strip_svg_alternatives(...)` → `svg_verified = _validate_svg_alternatives(...)`；`layout_notes` 的 `svg_alternatives_stripped` 改为 `svg_alternatives_preserved`；`blips_missing_raster > 0` → append 进 `failures` **硬失败**（退出码 1；错误信息点名 blip/svg rid + 修复指引：`figures/x.svg` 形式 vs `../figures/` 形式） |
| 4 | 新增 drawing 计数硬闸（pandoc 后、后处理前） | `_docx_figure_geometry` 数 drawing 段；`drawings < refs` → 硬失败（媒体部件在包但正文丢了 drawing 的空槽场景，媒体计数查不出——pandoc 每图嵌 PNG+SVG 双部件） |
| 5 | 新增 `_docx_figure_geometry` / `_pdf_text_lines` / `_pgm_ink_ratio` / `_figure_source_candidates` / `_classify_figure_refs` / `_figure_text_intrusion_applicable` / `_locate_caption_line` / `_region_ink_ratio` / `_verify_pdf_figures` + 常量组（`RASTER_EXTENSIONS`、`FIGURE_RASTER_MIN_PX=64`、`FIGURE_REGION_GAP_PT=4.0`、`FIGURE_REGION_MIN_INK=0.01`、`FIGURE_INK_THRESHOLD=250`、`FIGURE_RENDER_DPI=150`、`CAPTION_MATCH_CHARS=12`） | PDF 级插图验证（详见 §4）；PGM 直解析（Pillow 非声明依赖且 `-I` 下不可见） |
| 6 | `_cmd_build_docx_impl` manifest | `layout.figures` 新块：`refs`、`docx_media`、`docx_figures`、`svg_blips_preserved`、`raster_fallbacks`、`blips_missing_raster`、`raster_only_figures`、`raster_ref_with_svg`；PDF 步回填 `pdf` 子块（经既有 `_atomic_write_json`） |
| 7 | `_cmd_build_docx_impl` 成功载荷（审查项⑥） | 新增 `figure_refs`（原仅局部变量）与 `figures_dir`，供 PDF 步取数 |
| 8 | `cmd_build_pdf`（LibreOffice 转换后、pdffonts 块之后） | 调 `_verify_pdf_figures(pdf, docx, figure_refs, figures_dir)`；结果写 `manifest["layout"]["figures"]["pdf"]`；**失败路径**：manifest 记 `pdf_figure_verification_failed` limitation + `_atomic_write_json` 回写 + 退出码 1（同 pdffonts 不可得先例）；成功载荷增 `figure_assertions` |
| 9 | `governance/build.md` PF-B12（审查项⑤） | 增补插图双层级验证条文（docx 层 svgBlip 兜底 + PDF 层栅格预算/图位非空/位图引用登记语义），见 §7 |

**不改**：pandoc 命令行参数、reference docx、`metalayout.py`、`project.yaml`、`schemas/`、`templates/`、`tools/` 其它文件、八篇论文仓 tracked 文件（P1 仅 build-record.md）。

## 4. PDF 图位断言设计（审查项③的重做）

原方案"题注上方矩形取像素非白"有实测缺陷：题注上方区间混入正文（空图位区域仍约 36% 非白，漏放）；且按"第二个匹配"取双语题注会误杀正常构建。新方案三段：

- **A. 图幅级栅格预算**：`pdfimages -list` 全页扫描，image 对象（除 smask/mask/stencil）宽或高 >64px 者计 `figure_level_rasters`；≤64px 者计 `pattern_tiles`（SVG `<pattern>` 斜线填充被 LibreOffice 栅格化为贴片，探针实测 28–49px；2026-11-13 P1/P6 实构建测得 **0 贴片**——其 pattern 以矢量渲染，64px 地板留作一般性防御）。**`figure_level_rasters − 位图引用图数` 必须为 0**——引 `.svg` 的图与引 `.png` 的图都不得出现图幅级栅格（驱动 .png→.svg 迁移的闸门）。
- **B. drawing 计数**：docx drawing 数不得少于正文插图引用数（见 §3-4）。
- **C. 图位非空**：从 docx 取每图 `wp:extent` 高（EMU→pt）与题注段文本（`ImageCaption` 样式，pandoc 隐式题注）；在 PDF 文本层按**归一化题注前缀（前 12 字符）取读序首个匹配**定位题注行（正文「如图1所示」类干扰行不携题注原文；P3 式正文重复题注在后）；推算图幅区间 `[题注块上沿 − 图高 − 4pt, 题注块上沿]`，`pdftoppm -gray` 150 DPI 裁剪渲染，**非白比例 ≥ 1.0%**（校准：真实图位 8.78%–37.66%，空白区 0.019%）；另加**文字侵入断言**（该区间内不得有正文文字行）——捕获图槽塌缩、正文上溢的场景。
- **文字侵入的适用范围**：LibreOffice 把 SVG 内部 `<text>` 渲染为**可提取的 PDF 文字**（2026-11-13 实测 P4/P6 图），含 `<text>` 的 SVG（P2/P4/P5/P6/P7/P8）其标签行天然位于图位内，一律计入即误杀——实测 P6 四图位内分别含 23/29/23/43 行 SVG 标签文字（「文献D」「来源登记与结构解析」等），若无范围裁剪，P6 健康构建必被误杀。故侵入断言仅对**纯路径 SVG（P1/P3）与位图引用**施加，含 `<text>` 的 SVG 只受 ink 断言保护（空白槽仍可捕获）。边界记入 §8 开放项。
- **题注定位失败的降级**：docx 有题注但 PDF 文本层找不到 → 记 `caption_unlocated` 备注并跳过该图区域断言（不硬失败，防文本提取差异误杀）；无题注段 → `caption_absent` 跳过；无 `wp:extent` → `extent_missing` 跳过。栅格预算与 drawing 计数对全部图恒生效。
- **工具不可得**：`pdfimages`/`pdftotext`/`pdftoppm` 缺失或失败 → `status=unavailable` → 构建失败（PF-B12：不可校验不得静默放行；同 pdffonts 先例）。

## 5. 位图引用行为统一（审查项④）

- **裁定：记 manifest 警告 + layout_notes，不硬失败**。理由：P2 的 paper.md 仍引 `.png` 且另一条工作线在其上有在途润色，硬失败会阻断对方构建；`.png` 引用是迁移状态而非构建缺陷——其 PDF 内嵌**原始高分辨率位图**（实测 P1 位图场景内嵌 1890×1305 @299 ppi 原图，而非 96 DPI 兜底）。
- **硬失败只保留历史缺陷类**：① 含 svgBlip 的 `<a:blip>` 缺栅格 `r:embed` 兜底（`ab0bdcc` 空图事故的结构性防回归）；② drawing 缺失；③ 图幅级栅格超预算；④ 图位空白/被正文侵入。
- `raster_only_figures`（位图引用且无同 stem `.svg`，PF-B15 降级语义）与 `raster_ref_with_svg`（有位图伴生但正文仍引位图，迁移中）分别登记，均不阻断。

## 6. 自测与验证结论（2026-11-13 实测）

自测载体 P1-SETDEBATE-20251110（3 图引 .svg，旧 PDF 3 张 605px@96ppi，最干净 A/B 对照）；沙盒全量重建 + 本仓同版本重build（v0.4.10，review_status=pending，PF-B7 允许）。

| # | 验证项 | 方法 | 结果 |
|---|---|---|---|
| a | 新 PDF 栅格清零 | 新旧 PDF 各 `pdfimages -list` | 旧：3 张 605×418/288/293 @96ppi（页 5/10/11）；新：**0 张**（image 对象全无，pattern 贴片 0） |
| b | 300 DPI 文字清晰度 | `pdftoppm -r 300` 裁图位 vs `rsvg-convert` 同图 SVG 目视 | 新 PDF 图位矢量文字锐利（与 rsvg 渲染一致）；旧版 96 DPI 同图发虚 |
| c | 断言与回归 | build 输出 + `check` + `verify_layout.py` | `layout_assertions: pass`；`figure_assertions: pass`；`paper.py check` pass；`verify_layout` **27 PASS / 0 FAIL** |
| d | manifest | 读 `build/v0.4.10/manifest.json` | `layout.figures` 全块落盘（refs 3 / docx_media 6 / docx_figures 3 / svg_blips_preserved 3 / raster_fallbacks 3 / blips_missing_raster 0 / pdf.figure_level_rasters 0 / pattern_tiles 0 / unexpected_rasters 0 / pages_checked [5,10,11] / blank_figure_regions []）；旧字段无损（assertions/pdf_fonts_*/pdf_determinism/submission 四要素/artifacts/limitations） |
| e | 负例① SVG-only 拦截 | 沙盒论文正文改 `../figures/` 形式重建 | **构建失败，退出码 1**；`svg_alternatives_preserved` 失败项点名 3 个 SVG-only blip（svg rid rId21/rId33/rId37，"no raster r:embed on the blip"）+ 修复指引 |
| f | 负例② 空图位捕获 | 探针 docx 主图换 1×1 白 PNG 且去 svgBlip（extent 保留，模拟"渲染为空"）转 PDF | 三图位 ink=**0.0000** < 0.01，全部判 `blank_or_intruded`，构建失败 |
| g | 负例③ 图丢失捕获 | 探针 docx 剥离 `<w:drawing>` 转 PDF | drawing 计数 0 vs refs 3 → `figure_drawing_count_mismatch` 硬失败（docx 步快速失败 + PDF 步自洽兜底） |
| h | 双语题注不误杀 | P1 现构建（图 N + Fig. N 相隔约 6pt） | 题注按文本匹配定位中文题注行（568.8/282.7/494.7pt），三图位 pass，零误杀 |
| i | 位图引用场景（P2 式） | 沙盒论文改引 `.png`（同 stem 有 .svg） | 构建 **pass**；`raster_ref_with_svg` 记 3 项警告（manifest + layout_notes）；`unexpected_rasters = 3−3 = 0` |
| j | raster-only 豁免 | 沙盒删 fig2 的 .svg 后引 .png | 构建 **pass**；`raster_only_figures = [figures/fig2-main-results.png]` 登记 |
| k | PDF 确定性不回退 | 同 docx 两次 build pdf | sha256 均 `b157ed381ee4d82eae7a…`，字节一致（GC-2026-1113-01 机制不受影响） |
| l | 跨篇回归（沙盒副本，不动他仓） | P2（4 图引 .png）/ P6（4 图引 .svg、SVG 含 `<text>` 与 `<pattern>`）各 `build pdf` | 均 **pass**。P2：图幅栅格 4 = 位图引用 4（unexpected 0）、`raster_ref_with_svg` 记 4 项警告、四图位 ink 0.15–0.35 全 pass；P6：图幅栅格 0、pattern 贴片 0、四图位 pass（侵入断言按范围裁剪跳过，见 §4） |

论文侧：P1 同版本重build 提交 `b39837a`（仅 build-record.md；build/ 产物不入库）；`body/paper.md`、`authors.yaml`、`figures/` 零改动。

## 7. 规则正文变更（`governance/build.md` PF-B12 增补条文）

PF-B12 新增一条（GC-2026-1113-02）：插图在 **docx 与 PDF 两级**验证——构建**保留** pandoc 的 SVG 备选（`<asvg:svgBlip>`）使 PDF 图位为矢量，并断言每条含 svgBlip 的 `<a:blip>` 同时带栅格 `r:embed` 兜底（缺兜底即 2026-11-12 空图槽回归，**构建失败**）；PDF 转换后断言：(a) 栅格预算——宽或高 >64px 的 image 对象（除 smask）不得超过正文位图引用图数（≤64px 为 SVG `<pattern>` 贴片，计数不失败）；(b) 每个引用图在 docx 中有对应 drawing；(c) 每个图位非空——题注块上沿与图高（docx `wp:extent`）之间的区域须有墨迹且无正文文字侵入。正文引位图而同 stem 存在 `.svg` 记迁移警告（manifest + layout notes）不阻断；无 `.svg` 伴生的位图引用记 `raster_only_figures`（PF-B15 降级语义）。图幅库存不可得（`pdfimages`/`pdftotext`/`pdftoppm` 缺失）**构建失败**——不可校验的插图不得出厂。

## 8. 风险、边界与开放项

| 风险/边界 | 现状与缓解 |
|---|---|
| SVG 内部 `<text>` 与正文文字在 PDF 文本层不可区分（无字体级分析） | 侵入断言仅对纯路径 SVG/位图引用施加；含 `<text>` 的 SVG（P2/P4/P5/P6/P7/P8）只受 ink 断言保护——空白槽（ab0bdcc 模式）仍可捕获，塌缩槽不可 |
| 题注定位依赖文本匹配 | 提取差异导致找不到题注 → `caption_unlocated` 备注跳过（不硬失败）；docx 有题注而 PDF 完全没有属异常，由 drawing/栅格断言与人工版式检查（PF-B6）兜底 |
| ink 阈值 ε=1.0% 对极端稀疏图可能误杀 | 现役八篇图位 8.78%–37.66%，余量约 8.8 倍；空白区 0.019%（约 50 倍于阈值下） |
| 脚注内插图不支持计数配对 | 八篇正文零脚注（2026-11-13 实测）；如未来使用需扩展 `_docx_figure_geometry` 扫描域 |
| poppler 工具缺失 | 构建失败（PF-B12），与 pdffonts 先例一致 |
| **待独立核验** | ~~F9 写盘后独立核验由主会话派独立 subagent 执行（本记录交稿时状态：待核验）~~ **已完成**：agent-gpt-plus 独立核验，§6 各项实测复现，另发现 P1 缺陷一项（poppler 工具缺失闸只兑现 pdfimages 一条），修正与复验矩阵见 §11（2026-11-13 闭合） |
| 论文侧 .png→.svg 迁移 | P2/P8 待迁（P4/P5/P7 已完成）；P2 线上有在途润色，迁移时机归其内容线 |
| SVG `<pattern>` 展开 | P6 fig01/02/04 有 pattern；工具侧 64px 豁免 + `pattern_tiles` 记录，展开归论文侧（P1 fig2 已由 `092093d` 完成） |
| rules_version | 保持 0.3.0（理由见 §9）；若主会话裁定 PF-B12 条文扩充须升版（GC-2026-1112-01 先例：0.2.0→0.2.1 因 PF-B11/PF-B12 正文扩充），需另起一笔同步 `project.yaml`/`rule-index.yaml`/paper.py 常量/`templates/paper/paper.yaml` 与八篇 `paper.yaml`——超出本变更三文件域 |

## 9. rules_version 保持 0.3.0 的理由

本变更在 PF-B12 **既有语义**（"落地校验……任何失败断言即使文件能打开也失败；不可校验不得静默放行"）内扩充**插图断言清单**，未新增规则号、未改结构身份键、未动 schema/profile——与 GC-2026-1112-06 §10 第 10 项（新增 Compact 缩进构建断言 + profile/schema 新键，未升版）同属"实现载体/断言清单"扩展；而 GC-2026-1112-01 升版（0.2.0→0.2.1）的直接触发是 PF-B11/PF-B12 **规则正文扩充 + schema/profile 新键 + 八篇 paper.yaml 联动**，本变更无 schema/profile 改动且任务文件域限定三文件（禁改他篇论文仓），升版传播不可在本变更内完成。故保持 0.3.0 并将升版裁定留开放项（§8）。

## 10. 恢复方法（Recovery）

- **revert 优先**：本变更为单笔治理提交（`tools/paper.py` + 本记录 + `governance/build.md`），`git revert <commit>` 整体恢复"剥离 svgBlip"旧行为、保留历史（沿 GC-2026-1112-02/03 先例），**禁止** `--hard` 与历史改写（F7）。
- 若需就地重做：`git reset --soft HEAD^` 重分组后重提。
- 论文侧无回滚动作：P1 为同版本重build（v0.4.10，pending），`git revert b39837a` 仅撤账章节，产物留工作区（PF-B7 旧版本产物不删）；若新断言误伤某篇，该篇记 limitation + 论文侧修 SVG，不回退工具主路径。
- 工作区不回滚；计划草案与沙盒留痕存 `temp/svg-vector-plan.md`、`/tmp/svgprobe/`（沙盒非入库）。

## 11. P1 缺陷修正与审计注记（2026-11-13，独立核验后订正）

独立核验（agent-gpt-plus）对提交 `3259220` 实测发现一项 **P1 缺陷**：§4 末条与 §8 承诺的"poppler 工具缺失即构建失败"只有 `pdfimages` 一条兑现——`_pdf_text_lines` 把 FileNotFoundError/超时/非零返回与"PDF 无文本层"混同（PATH 剔除 pdftotext 后，含空图位的探针 PDF 判 `status=pass`，notes 记 "no text layer; figure-slot region check skipped"）；`_region_ink_ratio` 对 `None` 只记 note 不入 failures（剔除 pdftoppm 后 `ink_unavailable` 仍 pass）。即 §4 设计的 C 段断言在两条路径上可被整体静默跳过，违背 PF-B12。修正（instruction.git 后续提交，`tools/paper.py` 净 +89/−22 行）：

| 函数 | 修正前 | 修正后 |
|---|---|---|
| `_pdf_text_lines` | 工具缺失/超时/非零 → `[]`，与"PDF 无文本层"混同 | 抛 `FigureToolUnavailable`（点名 pdftotext 与被跳过的"题注定位→图位断言"）；仅 PDF 确实无文本层时返回 `[]`（合法阴性） |
| `_region_ink_ratio` | 一切失败 → `None`，与"区域无墨色"混同 | 工具缺失/超时/非零/PGM 输出不可测 → 抛 `FigureToolUnavailable`（点名 pdftoppm 与影响）；仅区域退化为零像素（文档几何阴性）时返回 `None` |
| `_verify_pdf_figures` | 仅 pdfimages 三处闸内联返回 unavailable | 四闸统一走新增 `_pdf_figures_unavailable()`：`status=unavailable` + failures 记 `figure_tool_unavailable` + error 点名工具与影响 → 调用方记 `pdf_figure_verification_failed` limitation + 退出码 1（pdfimages 既有先例的形状，failures 列表补齐） |

- **复验矩阵**（探针 `/tmp/svgverify/neg2w.pdf`——第 5 页含真实空图位；对 `_verify_pdf_figures` 直跑，PATH 分别剔除单工具）：

  | 场景 | 修正前 | 修正后 |
  |---|---|---|
  | 探针 + 完整 PATH | fail（空图位 ink 0.0000 被捕获） | fail（负例本体不破） |
  | 探针 + 剔除 pdftotext | **pass（缺陷）** | **unavailable**（`pdftotext could not be run …; figure captions cannot be located …`） |
  | 探针 + 剔除 pdftoppm | **pass（缺陷）** | **unavailable**（`pdftoppm could not be run …; the figure-slot region cannot be rendered …`） |
  | 探针 + 剔除 pdfimages | unavailable（既有先例） | unavailable（回归不破） |
  | P1 现行产物 `build/v0.4.10/*.pdf` + 完整 PATH | pass | **pass**：三图位 ink 0.3766/0.1488/0.0878、pages [5,10,11]、blank []，与 manifest `layout.figures.pdf` 逐项一致，零误杀 |

  回归：`python3 -I tools/paper.py check --paper ../papers/P1-SETDEBATE-20251110` pass（退出码 0）；`python3 -I tools/verify_layout.py` 27 PASS / 0 FAIL。本任务不跑 soffice。
- **行数订正**：§3 头部原记"净 +553/−55 行"系 `3259220` 实测误记；`git diff dc3e658 3259220 -- tools/paper.py` 实测为 **+586/−55**（本节订正；§3 表内函数级清单内容不变）。
- **审计注记（论文侧 build-record.md 带入他线未提交节）**：P1 仓库提交 `b39837a`（2026-11-13 14:47:37 +0800）的 build-record.md 除本变更的 GC-2026-1113-02 节外，还带入了另一条工作线**当时未提交**的「PKG-v0.4.10 · 投稿交付包组装（2026-11-13 14:31:27 +0800）」节。经核对：两节内容**均完整、无丢失**（GC 节自 build-record.md L1912 起、PKG 节自 L1862 起，各节数字与 manifest/产物一致），该 PKG 节非本变更产出但已随 `b39837a` 入库。提交信息无法追改，特此在治理记录补痕；论文侧后续整理不得删除该节。

---

*GC-2026-1113-02。规则依据：AGENTS.md F9/F5/F6；版式依据 governance/build.md PF-B2/PF-B3/PF-B6/PF-B7/PF-B12/PF-B15；规则版本 0.3.0；计划 temp/svg-vector-plan.md（v0.1，改号前为 GC-2026-1113-01）+ agent-gpt-plus 独立审查七项修正闭合；论文侧明细见 P1 build-record.md（GC-2026-1113-02 节，提交 b39837a）；独立核验后 P1 缺陷修正（poppler 工具缺失闸）与审计注记见 §11。*
