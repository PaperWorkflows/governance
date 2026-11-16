# 治理变更记录 GC-2026-1116-08：CI 全链路转绿修复——构建环境依赖缺失（rsvg-convert / poppler-utils）与 Layout verification 跨论文测试缺陷

- 日期：2026-11-16
- 编号：GC-2026-1116-08
- 类型：CI 环境依赖修复 + 诊断加固 + 测试缺陷修复
- 触发：CI（`build-submission.yml`）Build docx 步骤在 `svg_alternatives_preserved` 校验上硬失败——三个图全部产出 SVG-only blip（`primary_rid` 为空），缺少位图回退。本地用相同代码构建却通过。rsvg-convert 修复推送后，Build docx 转绿，失败点前移至 Build pdf 的 pdf-verify 阶段——`pdffonts unavailable`，PDF 本体已由 LibreOffice 成功生成，但无法验证，不得发布。poppler-utils 修复后，docx/pdf/snapshot/package/strict 全部通过，失败点再前移至 Layout verification 的 H 子项——硬编码查找 P4 构建，单篇检出的 CI 中永远无 P4。
- 规则依据：AGENTS.md F9（治理变更纪律）

---

## 1. 问题描述

### 第一层：Build docx 硬失败（rsvg-convert 缺失）

CI 运行 `build docx` 时，`paper.py` 的 `svg_alternatives_preserved` 校验报告失败：

- 三个 SVG 图全部为 `svgBlip` 无 `r:embed` 回退（`primary_rid` 为空）。
- 提示信息为 `../figures/` 路径形式问题，未触及真正原因。
- 本地复现相同代码路径时校验通过。

### 第二层：Build pdf pdf-verify 硬失败（poppler-utils 缺失）

rsvg-convert 依赖修复后，Build docx 步骤通过，CI 失败点前移至 Build pdf 的 `pdf-verify` 阶段：

- PDF 本体已由 LibreOffice 成功生成（`build pdf` 本身通过）。
- `pdf-verify` 阶段调用 `pdffonts` 校验 PDF 字体清单时失败，错误信息 `pdffonts unavailable`。
- 伴随提示：`"the PDF cannot be verified and must not be published"`。
- CI 日志直述根因为 poppler-utils 未安装，无歧义。
- 本地机器因预装 `poppler-utils`，未出现此问题。

### 第三层：Layout verification H 子项失败（跨论文硬编码测试）

poppler-utils 依赖修复后，docx/pdf/snapshot/package/strict 各步骤全部通过，CI 失败点前移至倒数第二关 Layout verification：

- 唯一失败项：`FAIL H. interval [12, 40] not superscripted (P4) | no P4 build found`（26/27 通过）。
- 该子项硬编码在 paper-root 的当前构建中查找 `P4-` 前缀论文，而 CI 的 paper-root 只检出单篇论文（P5），永远找不到 P4 → 记 FAIL → 任何论文仓的 CI 都不可能转绿。
- 本地全量工作区不受影响（P4 有构建 v0.3.18 时该子项走真实断言并通过）。

## 2. 根因分析

**两次失败的共同性质：CI 的 `ubuntu-24.04` runner 缺少本地预装的命令行工具；本地与 CI 的 pandoc/LibreOffice 主版本一致，差异在系统工具链。**

### 第一层：rsvg-convert（librsvg2-bin）

- `pandoc --to docx` 在遇到 `.svg` 输入时，会调用系统上的 `rsvg-convert` 将 SVG 光栅化为 PNG 位图，作为 `<a:blip r:embed="...">` 回退写入 docx 内部。
- CI 的 `ubuntu-24.04` runner 未安装 `librsvg2-bin`，`rsvg-convert` 不可用。
- pandoc 打印警告 `check that rsvg-convert is in path` 后，**跳过位图回退**，只产出 `<asvg:svgBlip>` 无 `r:embed` 的 blip。
- `paper.py` 校验发现 blip 无位图回退 → 失败。
- 本地机器因预装 `librsvg2-bin`，`rsvg-convert` 可用，位图回退正常 → 校验通过。
- **关键点：CI 与本地 pandoc 版本和二进制完全相同，差异仅在 `rsvg-convert` 是否存在。**

### 第二层：poppler-utils

- `paper.py build pdf` 的 `pdf-verify` 阶段依赖 poppler-utils 提供的命令行工具（`pdffonts`、`pdftoppm`、`pdftotext`、`pdfimages`）。
- `pdffonts`：列出 PDF 内嵌字体清单（字体名、类型、编码、子集化状态），是 `verify_layout.py` 校验 PDF 字体完整性的前置条件。
- `pdftoppm`：PDF 页面光栅化为 PNG，用于版面 bbox 提取与页面尺寸校验。
- `pdftotext`：提取 PDF 文本内容，用于文本密度与段落结构检查。
- `pdfimages`：列出 PDF 内嵌图像清单（分辨率、尺寸、颜色空间），用于图像质量与分辨率校验。
- CI 的 `ubuntu-24.04` runner 未安装 `poppler-utils`，所有上述工具不可用。
- `pdffonts` 调用失败后，`paper.py` 阻止 PDF 发布，标记为不可验证。
- 本地机器因预装 `poppler-utils`，所有工具可用，pdf-verify 通过。
- **关键点：LibreOffice 成功生成了 PDF，问题仅在后续校验环节——校验工具缺失导致 PDF 无法验证、不得发布。**

### 完整的 CI 系统依赖集

经两次失败枚举，CI 所需系统依赖全貌如下：

| 依赖 | 提供工具 | 用途 | 来源 |
|---|---|---|---|
| `libreoffice` | `soffice` | PDF/DOCX 本体构建 | apt |
| `fonts-noto-cjk` | Noto CJK 字体 | CJK 文字渲染 | apt |
| `librsvg2-bin` | `rsvg-convert` | SVG 光栅化为 PNG（docx 位图回退） | apt |
| `poppler-utils` | `pdffonts`/`pdftoppm`/`pdftotext`/`pdfimages` | PDF 构建校验（字体清单/页面光栅/文本提取/图像清单） | apt |
| `pandoc` | `pandoc` | Markdown/DOCX 互转 | `pypandoc-binary` 捆绑 |

## 3. 实验证据链（本地验证）

| 步骤 | 条件 | 结果 |
|---|---|---|
| 1 | 本地有 `rsvg-convert`，构建最小含 SVG 的论文 | PNG 回退写入 blip，`svg_alternatives_preserved` 通过 |
| 2 | PATH 中剔除 `rsvg-convert`，同输入构建 | 复现 CI 完全相同的失败签名：三个图仅 `svgBlip`、无 `r:embed`，blip 无位图回退 |
| 3 | 本地 PATH 剔除 `rsvg-convert` 后 pandoc 原始输出 | 含 `check that rsvg-convert is in path` 警告，产出与 CI 相同签名 |
| 4 | CI 日志中的 pandoc stderr | **不含**该警告（被 `paper.py` 丢弃，仅留误导性路径形式提示——见 §4），故 CI 侧只能靠失败签名比对定位 |
| 5 | CI pdf-verify 阶段日志 | 直述 `pdffonts unavailable`，无歧义（本地未复现——本地已装 poppler-utils） |

## 4. 次要缺陷：诊断提示误诊

`paper.py` 中 `svg_alternatives_preserved` 校验在失败时：

- 将 pandoc stderr 丢弃，只根据 `../figures/` 路径形式给出单一归因。
- 本次 `rsvg-convert` 缺失产生**完全相同**的 SVG-only blip 症状，但根因不同。
- 诊断提示未覆盖此场景，导致排查耗时。

**已修复**：加固校验逻辑——命中 pandoc stderr 中包含 `rsvg-convert` 时，给出准确提示（安装 `librsvg2-bin` 或确保 PATH），并附 stderr 片段。

## 5. 修复内容

| 项 | 变更 |
|---|---|
| `templates/ci/build-submission.yml` | Install system dependencies 步骤并入 `poppler-utils`：`apt-get install -y --no-install-recommends libreoffice fonts-noto-cjk librsvg2-bin poppler-utils`，后回显 `rsvg-convert --version` 与 `pdffonts -v` 确认安装成功 |
| `papers/P5-AUDIT-EVIDENCE-20251111/.github/workflows/build-submission.yml` | 同步模板变更（librsvg2-bin + poppler-utils 两项） |
| 各论文仓 `.github/workflows/build-submission.yml` | 其余论文仓待同步 librsvg2-bin 与 poppler-utils 两项 |
| `tools/paper.py` | `svg_alternatives_preserved` 校验诊断加固：检测 pandoc stderr 中 `rsvg-convert`，给出对应提示（见 §4） |
| `tools/verify_layout.py` | `section_h` 子项 (1)（P4 专属回归守卫）在 paper-root 无 `P4-*` 论文（单篇 CI 检出）或 P4 无当前构建时，由记 FAIL 改为记跳过（`skipped: ...`），不再阻塞单篇仓 CI；P4 有构建时的真实断言逻辑不变 |

## 6. 影响面

- 本次为 **CI 环境依赖缺失**，非论文内容问题。
- 治理仓 `templates/ci/build-submission.yml` 与 `tools/paper.py` 的改动不影响构建成功路径，仅修正 CI 环境（新增依赖）和改善错误提示文案。
- 各论文仓同步后，CI 构建可正常产出带位图回退的 docx 并通过 PDF 验证。

## 7. 待办事项

1. **其余论文仓 `.github/workflows/build-submission.yml` 同步**：P5 已修改，其余论文仓需跟进同步 librsvg2-bin 与 poppler-utils 两项安装。
2. CI 全链路（docx → pdf → snapshot → package → strict → layout → zip）转绿后关闭本轮修复。

## 8. 验证

| # | 项 | 方法 | 结果 |
|---|---|---|---|
| a | 本地复现 CI 失败签名 | PATH 剔除 `rsvg-convert` 后以 pandoc 最小用例构建 | 复现成功：仅 `svgBlip`、无 `r:embed`，blip 无位图回退 |
| b | 端到端复现（经 paper.py 全链路） | PATH 剔除 `rsvg-convert` 后对 P5 执行 `paper.py build docx` | 通过（见端到端复现结果） |
| c | 诊断提示 | 端到端复现中观察失败提示文案 | 通过（见端到端复现结果） |
| d | 语法 | `py_compile tools/paper.py` | 通过 |
| e | 第二层 CI 日志证据 | 查看 pdf-verify 阶段 `pdffonts unavailable` 日志 | CI 日志直证（pdf-verify 阶段 pdffonts unavailable）；本地未复现（本地已装 poppler-utils），待下次 CI 运行验证 |
| f | 第三层本地复现（单篇根） | 构造只含一篇论文的临时 paper-root 跑 `verify_layout.py` | H 子项 (1) 输出 `PASS ... | skipped: no P4-* paper in paper-root (single-paper CI checkout)`，TOTAL 27 PASS 27 FAIL 0 |
| g | 第三层本地回归（全量根） | 对真实工作区跑 `verify_layout.py` | P4 有构建（v0.3.18），H 子项走真实断言并通过（`1 plain interval run(s), 0 wrongly raised`），修复不改变有构建时的行为 |

### 端到端复现结果（PATH 剔除 rsvg-convert，本地实跑 `paper.py build docx`）

| 项 | 结果 |
|---|---|
| 退出码 | 1（status: error） |
| 失败校验 | `svg_alternatives_preserved`：三个 blip（rId24 / rId37 / rId48）全部 `primary_rid` 为空、SVG-only blip——与 CI 失败日志逐字一致（连 rId 都相同） |
| hint 首句 | `pandoc could not rasterize the SVG bitmap fallback: rsvg-convert is unavailable (install librsvg2-bin or ensure rsvg-convert is in PATH) (GC-2026-1116-08)` |
| stderr 片段 | 成功提取到冒烟警告原文，形如 `[WARNING] Could not convert image figures/fig1-evidence-chain-architecture.svg: "check that rsvg-convert is in path.\nrsvg-convert: createProcess: posix_spawnp: does not exist (No such file or directory)"`（三个图各一条） |
| 结论 | 根因在全链路复现；诊断加固按设计输出准确提示与证据片段 |
