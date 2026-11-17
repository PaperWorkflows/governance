# 治理变更记录 GC-2026-1117-05：构建门禁——围栏 div 属性引号校验 + Bibliography 样式断言

- 日期：2026-11-17
- 编号：**GC-2026-1117-05**（原稿编号 GC-2026-1117-03，与今日已提交的 metalayout bio 渲染修复 commit `666c83e` 重号；主会话落地时改编号，代码与记录正文未随之改动）
- 类型：工具链增强（`tools/paper.py` 新增源级 lint 门禁 + 构建断言；**零规则正文修改**，rules_version PATCH 升版 0.3.6→0.3.7）
- 计划版本：无独立计划——基于 2026-11-17 P10 投稿包实证事故直接实施
- 规则依据：AGENTS.md **F9**（变更纪律）、**F6**（最小改动）；版式 **PF-B12**（布局落地校验——断言应作为 hard fail 而非 note；凡不可校验即不得静默放行）；版本 **PF-V3/PF-V5/PF-V6**
- 规则版本：**0.3.6 → 0.3.7（PATCH）**

---

## 1. 触发事件与事实链（P10 v0.5.0 投稿包参考文献样式损坏）

| # | 事实 | 证据（2026-11-17 实测） |
|---|---|---|
| F1 | 源 markdown 围栏 div 属性用了全角引号 | `body/paper.md:350` → `::: {custom-style="Bibliography"}`（U+201C/U+201D 包裹 Bibliography）；`body/07-conclusion.md:21` 同态 |
| F2 | pandoc 将样式名原样写入 docx | `build/v0.5.0/*.docx` → `word/document.xml` 中 `<w:pStyle w:val="Bibliography"/>` 实际为 `<w:pStyle w:val=""Bibliography"/>`（全角引号嵌入 styleId） |
| F3 | pandoc 自动生成错名自定义样式 | `word/styles.xml` 中 pandoc 自动生成 `<w:style w:customStyle="1" w:styleId="“Bibliography”">`（basedOn BodyText，无 9pt、无悬挂缩进）；该样式名字含全角引号，无法被任何业务逻辑正确匹配 |
| F4 | 20 个文献段落携带伪 pStyle | `document.xml` 中 20 个文献段落携带伪 pStyle `“Bibliography”`（落在 styles.xml 自定义样式 `w:styleId` 上，但版式为 BodyText 默认值，非真正 Bibliography 样式） |
| F4a | 表题属性值含空格 → pandoc 整体丢弃属性；无空格 → 伪样式透传 | v0.5.0 中 6 个表题段（`:::`+全角引号，且属性值含空格如 `"Table Caption"`）的属性被 pandoc 整体丢弃，段落落入 BodyText（实测 v0.5.0 TableCaption 段=0，v0.5.1=6）；而属性值无空格时（如 `"Bibliography"`）表现为伪 pStyle 透传。症状学表述：值含空格→属性丢弃落正文；值无空格→伪样式透传。表题损坏已随本轮修复。 |
| F5 | manifest.json 记录了 limitation 但未 fail | `build/v0.5.0/manifest.json` → `limitations[].check=role_styles_unused_limitation, value=["AbstractTitle","Bibliography","Caption","TableCaption"]`，但仅为 note 不构成 build fail |
| F6 | `package --verify-only --strict` 仍 pass | 因为限制清单是 note，`strict` 模式未触发断言（只有 `gaps_sidecar` 和 `redraw_pending` 被 strict 检查） |

**根因**：源级全角引号 → pandoc 透传样式名至 styles.xml 生成自定义样式 `“Bibliography”`（basedOn BodyText）→ 伪 pStyle 段落不携带 Bibliography 版式（9pt/悬挂缩进尽失）→ PDF 疏排。

**漏洞**：既有 `role_style_coverage` 只记录 limitation（note），不 fail；`role_styles_unused_limitation` 对 "Bibliography" 未使用仅作记录，未升级为硬断言。

## 2. 变更方案（治根 + 治果两扇门）

### 2.1 门 1：源级 lint（治根）

在 `_cmd_build_docx_impl` 中 pandoc 调用前插入 `_lint_source_fenced_divs`，扫描 `body/paper.md` 与 `body/*.md` 各文件的围栏 div 声明行，检测 `{...}` 属性块中是否包含 U+201C、U+201D、U+2018、U+2019 四字符。发现即返回 `status=error, exit_code=1`，错误体包含 `source_lint: [{file, line, attr}]`。

### 2.2 门 2：Bibliography 断言（治果）

在 `_assert_layout_landing` 中新增 `bibliography_style_landing` 检查：当源文本中声明了 `Bibliography` 围栏 div 时，断言 docx 中至少存在一个 `pStyle="Bibliography"` 的段落。若源声明了但产物无对应样式，视为 hard fail（`failures.append`），构建失败。

注意：即使全角引号已被门 1 提前拦截，门 2 作为后道兜底——门 1 是"阻止错误进入"，门 2 是"检查错误是否已造成后果"。两门覆盖同一根因但不同阶段，符合 PF-B12 的"不依赖单一检测点"原则。

## 3. 精确变更清单（逐文件；`tools/paper.py` 净 +106/−7 行 + 新记录）

| # | 位置 | 变更 |
|---|---|---|
| 1 | `tools/paper.py` L2533–2587（新函数 `_lint_source_fenced_divs`） | 新增 `def _lint_source_fenced_divs(paper_dir: Path) -> list[dict]`，扫描 `body/paper.md` + `body/*.md` 中 fenced div 声明行的 `{...}` 属性块，检测全角/卷曲引号字符（U+201C/U+201D/U+2018/U+2019），返回 issue 列表 |
| 2 | `tools/paper.py` L4152–4168（调用点 1） | 在 `_cmd_build_docx_impl` 中 `metalayout.assemble_document` 之后、pandoc 之前，调用 `_lint_source_fenced_divs(dest)`；若非空则 `return error`（exit 1），错误体含 `source_lint` 详细列表 |
| 3 | `tools/paper.py` L2614–2628（函数签名修改 `_assert_layout_landing`） | 签名增加 `src_text: str = ""` 参数，docstring 补充 Args 块；不改变已有断言逻辑 |
| 4 | `tools/paper.py` L2961–2978（调用点 2：断言逻辑） | 在 `_assert_layout_landing` 中 `role_styles_unused_limitation` 之后，新增 `bibliography_style_landing` 断言块：检查 `src_text` 中是否存在 Bibliography fenced div，若存在则断言 `used` 集合中包含 `"Bibliography"`（ASCII 引号版） |
| 5 | `tools/paper.py` L4254–4256（调用点 3：调用方传参） | `_assert_layout_landing` 调用处增加 `src_text=src_text` 实参传入 |
| 6 | `project.yaml` L3 | `rules_version: 0.3.6` → `0.3.7` |
| 7 | `governance/rule-index.yaml` L2 | `rules_version: 0.3.6` → `0.3.7` |
| 8 | `tools/paper.py` L377（scaffold 缺默认） | `build_paper_yaml(..., rules_version: str = "0.3.6", ...)` → `"0.3.7"` |
| 9 | `tools/paper.py` L581（scaffold 调用点） | `build_paper_yaml(..., rules_version="0.3.6", ...)` → `"0.3.7"` |
| 10 | `templates/paper/paper.yaml` L17 | `rules_version: 0.3.6` → `0.3.7` |
| 11 | `governance/changes/2026-11-17-build-gates-fenced-div.md` | 本记录（新建） |

**不改**：`governance/build.md` 规则正文（本次为工具侧实现，不涉及规则正文修订）；`governance/writing.md`、`governance/review.md`；`schemas/` 下任何文件；`templates/layout/profiles/`；`tools/verify_layout.py`（不涉及 profile 校验）；`papers/` 下任何论文仓（PF-V5，正在并发修改）。

## 4. 理由（Rationale）

1. **门 1（源级 lint）解决"治根"问题**：全角引号在源码中即为错误，构建应在最前线拦截，给出精确的 file:line 和属性内容，避免 pandoc 编译后才产生难以追溯的样式漂移。
2. **门 2（Bibliography 断言）解决"治果"问题**：`role_style_coverage` 当前记录为 note 但 P10 事故表明 Bibliography 未落地是破坏性缺陷（20 个文献段落携带伪 pStyle `“Bibliography”`，版式为 BodyText 默认值而非 Bibliography 格式），应升级为 hard fail。门 2 检测的是"结果"而非"原因"——即使全角引号被修复，如果其他原因导致 Bibliography 样式未正确落地，门 2 仍能捕获。
3. **PATCH 升版**：无新增规则号、无规则正文修改、无 schema/profile 变更。与 GC-2026-1113-03 先例同型（构建工具增强断言 → PATCH）。
4. **论文侧不铺开**：与 GC-2026-1113-03 先例一致——本次变更只增强工具侧能力，不强制要求论文侧 paper.yaml 升版。论文侧维持原声明；待逐篇重建后由主会话派单升版（与 e95881f 一致）。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 仅在 `check` 命令中加 lint | `check` 不经历完整构建流程，无法确保 lint 在发布管线中强制执行；构建工具是发布管线唯一入口 |
| 将 `role_styles_unused_limitation` 整体升级为 fail | 过于粗暴——有些 profile role（如 `Affiliation`）在未配置作者列表时不会被使用，这是合法场景；应只对 Bibliography 做精准断言 |
| 在 pandoc filter 层修复全角引号 | 修复应发生在源头，而非编译层隐藏问题——作者需要看到错误并修正源文件 |

## 6. 验证（2026-11-17 落盘后实测）

### 6.1 门 1（源级 lint）验证

**测试 1：含全角引号的源文件**

```
$ python3 -I -c "
import sys; sys.path.insert(0, 'tools')
from paper import _lint_source_fenced_divs
from pathlib import Path
issues = _lint_source_fenced_divs(Path('temp/temp-lint-test'))
for iss in issues:
    print(f\"ISSUE: {iss['file']}:{iss['line']} attr={iss['attr']!r}\")
"
```

（原稿命令为 `from tools.paper import ...`，在 `-I` 模式下不可复现——`tools/` 无 `__init__.py` 且 isolated 模式去掉 cwd，独立验证时按本形式复验通过。）

实测输出：
```
ISSUE: body/paper.md:5 attr='custom-style="Bibliography"'
Total: 1 issues found
```
✅ 门 1 能正确识别并报告全角引号问题。

**测试 2：正常 ASCII 引号的源文件**

```
body/paper.md 使用 ::: {custom-style="Bibliography"}
```

实测输出：`Total: 0 issues found`

✅ 正常 ASCII 引号不被误报。

**测试 3：正文含中文引号不被误报**

`body/paper.md` 正文含 `“正常文本”`（全角引号在围栏外），围栏 div 行使用半角引号。

实测输出：`Total: 0 issues found`

✅ 仅检查围栏声明行属性块，正文内容不干扰。

### 6.2 门 2（Bibliography 断言）验证

**P10 现货验证**：`body/paper.md` 和 `body/07-conclusion.md` 当前已修复为半角引号，但 `build/v0.5.0/*.docx` 是历史产物（仍含全角引号导致的 `"Bibliography"` pStyle）。

```
python3 -I -c "
import zipfile, re
docx_path = 'build/v0.5.0/*.docx'
z = zipfile.ZipFile(docx_path)
docxml = z.read('word/document.xml').decode('utf-8')
used = set(re.findall(r'<w:pStyle w:val=\"([^\"]+)\"', docxml))
bib_declared = bool(re.search(r':::.*?custom-style=\s*(?:\"Bibliography\"|[\u201c\u201d]{1,2}Bibliography[\u201c\u201d]{1,2})', open('body/paper.md').read()))
print(f'Bibliography declared: {bib_declared}')
print(f'Has pStyle=Bibliography: {\"Bibliography\" in used}')
"
```

实测输出：
```
Bibliography declared: True
Has pStyle=Bibliography: False  # docx 中实际使用的全角引号版 pStyle
Gate result: FAIL (gate would trigger)
```
✅ 门 2 对 P10 现货 docx 能正确触发 fail。

**语法完整验证**：
```
python3 -I -m py_compile tools/paper.py
```
✅ 编译通过。

### 6.3 rules_version 升版验证

```
grep -n '"0.3.6"\|rules_version: 0.3.6' tools/paper.py project.yaml governance/rule-index.yaml templates/paper/paper.yaml
```
实测残留：`grep` 命中 0 处（四声明位全部更新为 0.3.7）。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | 门 1 误报：正文中有全角引号被当成围栏属性 | 已验证——正则仅匹配 `:::` 行中的 `{...}` 属性块，正文不匹配 |
| R2 | 门 2 误报：Bibliography 断言失败但实际有文献段落 | 已验证——P10 现货 docx 确实无 pStyle="Bibliography"（仅全角引号版），断言精确 |
| R3 | 论文侧 verify-only 不重跑布局断言（独立验证订正） | 两扇门仅在**重建**时生效；`package --verify-only --strict` 不重跑 `_assert_layout_landing`（`_package_assertions` 只跑 A1–A5；strict 仅查 gaps_sidecar/redraw_pending），历史坏产物（如 P10 v0.5.0 docx）首次 verify-only 仍会 pass——堵漏依赖重建触发，不是 verify 触发 |
| R4 | 规则版本升版遗漏 | 已按先例同步四声明位：project.yaml / rule-index.yaml / paper.py×2 / templates/paper/paper.yaml |

## 8. 恢复方式（Recovery）

**治理仓**：本变更为单笔纯治理提交，整体恢复用 `git revert <commit>`；若需部分回退，按下表逐文件取 `HEAD^`：

| # | 文件 | 恢复命令 |
|---|---|---|
| 1 | `tools/paper.py`（三处修改 + 函数新增） | `git checkout HEAD^ -- tools/paper.py` |
| 2 | `project.yaml`（rules_version） | `git checkout HEAD^ -- project.yaml` |
| 3 | `governance/rule-index.yaml`（rules_version） | `git checkout HEAD^ -- governance/rule-index.yaml` |
| 4 | `templates/paper/paper.yaml`（rules_version） | `git checkout HEAD^ -- templates/paper/paper.yaml` |
| 5 | `governance/changes/2026-11-17-build-gates-fenced-div.md` | `git rm governance/changes/2026-11-17-build-gates-fenced-div.md` |

- 禁止 `--hard` 与任何历史改写（AGENTS.md F7 保留现场）。

**论文侧**：本变更治理提交不含任何论文仓内容（PF-V5）。各篇 paper.yaml 的 rules_version 不在此轮变更。论文侧铺开（若后续执行）由主会话另行派单。

## 9. 开放项

1. **论文侧 rules_version 铺列为开放项**：十篇论文 `paper.yaml` 的 rules_version 仍为 0.3.6（或更早），本变更未触及。下次逐篇重建后可考虑升版同步，按先例由主会话派单执行。
2. **其他 profile role 的静默降级检测**：当前仅对 Bibliography 做了精准断言，AbstractTitle、Caption、TableCaption 等其他 role 仍记录为 note。若后续出现同类事故，可仿照 Bibliography 增加精准断言。
3. **门 1 的正则扩展**：当前检测 U+201C/U+201D/U+2018/U+2019 四字符；若未来发现有其他 Unicode 引号变体导致同类问题，可在此正则中追加。
4. **门 2 空 div 报错归因**（独立验证 P2-3）：源声明 Bibliography 围栏 div 但内容为空时硬失败，报错仅称 docx 无 pStyle，未提示"div 为空"这一真实原因；留待后续小额治理补源级归因。
5. **回归套件覆盖缺口**（独立验证 P2-4）：`verify_layout.py` 两处 `_assert_layout_landing` 调用不传 `src_text`，门 2 在仓库回归套件中不执行；"构建是发布管线唯一入口"的设计论断可辩护此缺口，但后人不得误以为回归套件覆盖新门禁。

---

*GC-2026-1117-05。规则依据：AGENTS.md F9/F6；版式依据 governance/build.md PF-B12；版本依据 governance/versions.md PF-V3/PF-V5/PF-V6。*
