# 治理变更记录 GC-2026-1112-03：PF-B15/B16 构建工具链落地（`package` 子命令）

- 日期：2026-11-12
- 编号：GC-2026-1112-03（承接 GC-2026-1112-02 开放项 **O1**；独立成号沿 02 记录 §9 O1 明示建议"建议 GC-2026-1112-03"）
- 类型：治理工具链实现（规则正文已由 GC-2026-1112-02 立；rules_version 保持 **0.3.0**，本变更无新规则 id）
- 计划版本：**v1.1**（`temp/GC-2026-1112-03/plan.md`；v1.0 经 agent-gpt-team 与 agent-glm 并行交叉复核后修订，两份报告在 `temp/GC-2026-1112-03/`）
- 规则依据：AGENTS.md F9/F5/F6、F7（外部传输须用户明示）；PF-B5/B6/B7/PF-B15/PF-B16（语义源）；PF-RV8（字数带宽提示）；S12（结语标题）、S17（作者简介十字段）
- 实施编排：agent-gpt-team + agent-glm 并行复核（已完成）→ **agent-minimax 实施** → agent-glm 写后 diff 复核与沙盒实跑验证 → 主会话按复核结论提交 → agent-gpt-team 一次内容一致性检查
- **流程状态**：**已提交**。治理仓提交 **`9552e7d`**（2026-11-12，恰 3 文件：tools/paper.py +1075、build.md PF-B16 过渡与执行点条款、本记录）；agent-glm 写后 diff 复核 **PASS**（verify-glm.md，沙盒独立重跑 3 项负例全部复现）；内容一致性检查 **consistent**（consistency-check-gpt-team.md）：其 C-1（本头部状态滞后）与 C-2（结语锚点实测失败集更正为 P1/P2/P7 共 3/7）由本次收口处置；C-3（02 记录 O1/O4 回填指针）已同步处理

---

## 1. 基线（实施时实测）

- **git 基线**：治理仓 HEAD = `db52de1`（"feat(template): 论文侧排版约束与投稿方向登记键（GC-2026-1112-02-A2）"）。工作树在途改动仅 `authors/registry.yaml`（他线，不在本变更域，未触碰）。**实施第一步前置检查**：`git status --short` = 仅 ` M authors/registry.yaml`；`git diff --stat tools/paper.py` = **空**（`tools/paper.py` 相对 HEAD 干净，无他线在途改动）→ 满足开工条件。
- **`tools/paper.py` 现状**：3255 行；`cmd_check` / `cmd_writing_status` / `_count_chinese_chars`（L1191）/ `_posix_safe_title`（L1945）/ `_norm_version`（L1950）/ `_load_paper_yaml`（L1955）/ 构建 manifest 写入处（L2888–2923）已实读，实施沿用其风格、`yaml.safe_load` 加载方式与 `emit()` 单一 JSON 输出形态。
- **论文侧基线（P4 仓 `P4-CONDITIONAL-COMPLETENESS-20251111`）**：`build/current.json` → **v0.3.2**，`build/v0.3.2/` 内 **docx 与 pdf 双全**（426 237 B / 1 122 932 B），`manifest.json` 存在（`paper_title` 与 `paper.yaml` 的 title 一致）；工作树干净（`git status --short` 空）；`figures/index.yaml` **3 条登记且 3 条均带 `filename_svg`**（fig1/fig2/fig3 全 SVG）；`body/paper.md` **4 个管道表**（表 1–表 4）；`abstract.md` 有 `## 中文摘要` + `**关键词**：`（5 词全角分号）；`writing-spec.yaml` 有 `conclusion_heading: 结语`、`min_chars: 13000` / `max_chars: 16000`、`cfp_directions`、`submission_direction`；`body/paper.md` 尾部 `# 作者简介` 节含两位作者**完整十字段**。
- **基线漂移声明（复核意见 G9/T10 处置）**：计划 v1.0 所记的"P4 两图"作废（实为 3 图）；本记录所载全部数值以本次实施实测为准，每步以当次实测复核。
- **两口径实测（P4 正文，第 1 章标题行 → 结语节末，1-based 55–480 行）**：真非空白字符 **18722**；`_count_chinese_chars`（CJK 字符数 + 非 CJK 空白分词词数）**13846**。同一段文本两口径相差 26%，结论方向相反（18722 越上带 16000，13846 在带内），两值不可混用（详见 §5.1）。

---

## 2. 问题陈述（本次变更要解决什么）

| # | 问题 | 取证 |
|---|---|---|
| P1 | **PF-B15/PF-B16 的交付义务没有机器载体**：投稿包骨架（标题（第一作者中文名）.docx/pdf、figures/fig{N}.svg\|png、tables/tab{N}.csv、manifest.json）、投稿面 manifest 八字段、CSV 导出、图表交付状态全部靠人工手工完成；PF-B16 明写"包骨架齐备性是构建检查：逐文件存在 + manifest 字段完整性，缺失 = 构建失败，禁旧包补齐"，但工具不执行 | `governance/build.md` PF-B15 L119–127、PF-B16 L129–145；02 记录 §9 O1；`tools/paper.py` 无任何 package 逻辑（3255 行实读） |
| P2 | **PF-B7 的共享字段一致性无处核对**：PF-B7 要求发布 manifest 另记 PF-B16 投稿元数据集 + 包 manifest 的 sha256，共享字段不一致即构建失败；PF-B16 要求"共享字段必须在两个 manifest 中一致并在构建时交叉核对，不一致即构建失败" | `governance/build.md` PF-B7 L58、PF-B16 L140 |
| P3 | **缺口无处登记**：作者简介十字段（P4 正文已含、authors.yaml 未结构化）、投稿方向待作者确认等缺口既不能硬失败（内容线未完成），也不该出现在对外投稿面的 manifest 里（PF-B16 明禁内部限制清单入投稿面），此前只能散落在 build-record 的人工记述中 | PF-B16 L140/L141；复核意见 G2/G7 |
| P4 | **字数口径不统一会翻转合规判定**：PF-RV8 带宽 13000–16000；P5 既有裁定为 `len(re.sub(r'\s','',s))`，而工具既有 `_count_chinese_chars` 是"CJK 字符数 + 非 CJK 空白分词词数"，两者数值不同，若按不同口径出报告，会出现"同一标签下两个相反结论" | 复核意见 G5/T1；实测 18722 vs 13846 |

---

## 3. 精确变更清单（逐文件）

| # | 文件 | 类型 | 内容 |
|---|---|---|---|
| 1 | `tools/paper.py` | 修改 | 新增 `package` 子命令与配套函数块（`# ── package (PF-B15/PF-B16 submission package, GC-2026-1112-03) ──`，位于 `cmd_build_debate` 之后、`main()` 之前，**纯追加 +1075 行 −0 行，未改动任何既有函数体**）：`cmd_package` + 30 个辅助函数/常量/异常类（清单见 §10.1）；CLI `package --paper <目录名或路径> [--version vX.Y.Z \| --current] [--verify-only] [--strict]`，缺省 `--current`（读 `build/current.json`）；骨架组装（§4.1）、投稿面 manifest（§4.2）、断言 A1–A5（§4.3）、build-record 追加（§4.4） |
| 2 | `governance/build.md` | 修改 | **PF-B16 末条（"Sending the package…"条）之后追加一条**过渡与执行点条款，**逐字**采用计划 §5 全文（+1 行 −0 行，1 个 hunk，纯追加；PF-B15/PF-B16 正文一字未动） |
| 3 | `governance/changes/2026-11-12-build-package-toolchain.md` | 新建 | 本记录 |

**不改**：`governance/rule-index.yaml`（无新规则 id，rules_version 保持 0.3.0）、`project.yaml`、`governance/review.md`、`governance/writing.md`、`governance/polish.md`、`schemas/`、`templates/`、七篇论文仓 tracked 文件、`authors/registry.yaml`（他线在途）。

**沙盒**：`temp/VERIFY-GC-2026-1112-03/`（.gitignore 内，不入库）——P4 副本、位图 fixture 三份、负例副本、夹具生成脚本与验证日志。

---

## 4. 理由（Rationale）

- **P1**：目标刊 S19 要求投稿以 Zip 打包 Word/PDF/SVG 等。规则已立（PF-B15/PF-B16）但无执行载体，投稿包仍靠手工组装、包骨架齐备性靠人眼核对。`package` 子命令把"组装 + 校验 + 登记"三件事落到构建流上，PF-B15/PF-B16 从"人工过渡执行"转为"构建流生成 + 断言"——这正是 02 记录 O1 承诺的实现载体，独立成号执行（沿 02 §9 O1"建议 GC-2026-1112-03"）。
- **P2**：PF-B7/PF-B16 的"共享字段一致、不一致即构建失败"是硬条文，此前无任何代码路径能触发。`package` 在组装期读取发布 manifest `build/<version>/manifest.json` 并对 `paper_title` / `paper_version` 作双向核对（A3），是该条款在构建流中的执行点。
- **P3**：缺口既要留痕、又不属于对外投稿面。解决方式是**包外 sidecar**：缺口清单写 `build/<version>/package-gaps.json`（包目录之外，永不进投稿 zip），投稿面 manifest 只保留投稿所需的字段与摄影类降级摘要。PF-B16 对投稿方向已有"可 null + 缺口登记"先例，bio 沿用同一机制并由 build.md 过渡条款显式授权（§5.3）。
- **P4**：字数口径按 P5 既有裁定统一为**真非空白字符**，工具侧新增独立计数函数，旧口径 `_count_chinese_chars` 不进 manifest、只作 sidecar 参考值双记，避免"同一方法学标签下两个数"。
- **最小改动**：不并入 `build` 路径（§6 备选 2），不改既有函数体（`git diff` 对 `tools/paper.py` 为纯追加），`check` / `writing status` / `build` 等既有子命令行为零变化（§8 回归实测）。

---

## 5. 关键设计裁定

1. **字数双口径**：manifest 的 `total_chars` / `body_chars` 使用**新增的真非空白计数函数**（`len(re.sub(r'\s','',text))`），方法学字符串如实登记为"非空白字符（含标点/数字/字母），与 P5 既有裁定口径一致"；`_count_chinese_chars`（CJK 字符数 + 非 CJK 空白分词词数）**不用于 manifest**，其值在 sidecar 的 `char_count_reference` 中双记，作为 writing-status 旧指标的参照。计数范围：body = `body/paper.md` 自首个带章号的一级标题起至结语节末；total = 中文摘要段（`abstract.md` `## 中文摘要`）+ 正文 + 参考文献节（三元分解随值登记）。
2. **gaps 走包外 sidecar**：投稿面 manifest **不含** gaps、source_manifest 等内部字段；缺口、降级明细、redraw_pending 明细、字数带宽提示、source_manifest 指针、旧口径参考值全部写入 `build/<version>/package-gaps.json`（包目录之外，永不入投稿 zip）。投稿面只保留 PF-B16 明文要求的"摄影类降级摘要"（图号、交付名、降级类别、降级原因）。
3. **表格以 body/paper.md 单源为准**：管道表按文档序枚举，题注取最近前置的"表 N"（`::: {custom-style="Table Caption"}` 围栏内的题注优先；句内引用如"表 3 报告了…"因含句号或超长不视为题注），无题注按序补配；逐表导出 `tab{N}.csv`（UTF-8、首行表头、CSV 标准转义，仅剥离 Markdown 粗体包裹标记 `**`——标记非数据）。`tables/index.yaml` 各篇 schema 不齐（P2/P7 嵌套 `tables:` 键、P5 无 `body_table_no`、P6 `status: done`、P7 `status: extracted`），故**只作 best-effort 元数据补充，不作断言基准**；A4 改为 paper.md 表集合与包内 CSV 集合的**双向**核对。
4. **结语锚点取自 writing-spec**：锚点 = `writing-spec.yaml` 的 `conclusion_heading`，在 `body/paper.md` 的 `#` 级标题行中作**子串匹配**（允许"# 7 结语""# 结语""# 6  结语"等章号变体），范围自锚点行起至下一个 `#` 级标题行前；**找不到锚点即失败**并报 `writing-spec.conclusion_heading` 与正文一级标题清单（S12 内容级由审稿线裁定，工具不静默取空、不取整章）。
5. **降级资格收窄至摄影类**：`figures/index.yaml` 只押 `filename_svg` 字段判定状态——登记且文件存在 → `svg_source_registered`（同源免对比）；无 SVG 且 `type` ∈ {photo, photograph, photography, 照片, 摄影, 写真} → `downgraded_bitmap`（复制为 png，记降级原因）；无 SVG 且非摄影类或 type 不可判 → `redraw_pending`（**不复制**，入 sidecar 缺口，保守默认交人工裁决，PF-B15 的重绘硬义务不被降级通道架空）。`filename_svg` 登记但文件缺失 → 直接失败。
6. **`--verify-only` / `--strict` 双模式**：`--verify-only` 不重建包，只对既有 `package/` 重跑 A1–A5 + manifest 字段核（负例载体，也是投稿前终检的载体）；`--strict` 在缺口非空或存在 `redraw_pending` 时失败。断言失败退出码 1，用法/环境错误退出码 2（与 `build docx` 的退出码约定一致）。
7. **发送门槛**：`build.md` 新增条款写死"No submission zip may be sent unless `package --verify-only --strict` passes"，发送本身仍受 AGENTS.md F7 用户明示指令约束（工具不实现 zip 打包与邮件发送）。

---

## 6. 备选方案（Alternatives）

1. **新建独立 `tools/package.py` 脚本**——否：`tools/paper.py` 是全仓唯一的 CLI 载体（既有子命令 30 余个、退出码与 `emit()` 输出形态已定型），另起脚本会造成第二套 CLI 入口与第二套约定，且 PF-B16 的断言要与 `build` 侧共享 `paper.py` 内的既有函数（`_posix_safe_title` / `_norm_version` / `_load_paper_yaml` / `_count_chinese_chars`），拆文件反而增加耦合。
2. **并入 `build` 路径（build 成功后自动组装包）**——否：PF-B7"已发布版本不得就地修改"与"每次构建追加 build-record"使 build 成为有状态发布动作；把组装塞进 build 会让每次重新构建都重写包内容、且负例无法单独复验（包损坏时重跑 build 反而自愈）。独立 `package` 子命令使组装与校验解耦，--verify-only 才能真正验证既有包。
3. **投稿面 manifest 增 JSON Schema 强制（O5）**——否：属超本轮最小域的新增能力，登记 O5；本轮只做字段完整性断言。
4. **工具化 SVG 重绘与差异对比**——否：重绘脚本选型仍未定（O6）；本轮只预留 `redraw_pending` 状态机。
5. **实现 zip 打包与邮件发送**——否：F7 禁未经授权外部传输；打包属投递步骤，由用户指令触发。
6. **引入第三方依赖（python-docx / lxml 等）**——否：PF-B11 记载 `python3 -I` 下二者不可用；本轮只做 stdlib + `yaml` 的文件级操作。

---

## 7. 风险与恢复（Risks & Recovery）

### 7.1 风险与缓解

| 风险 | 缓解 | 恢复 |
|---|---|---|
| 题注与表块错配（正文引用"表 N"被当题注） | 题注优先取 `Table Caption` 围栏内的行；句内引用按"含句号或长度 > 60"排除；配不上的表按序补配；解析失败（列数不一致）即失败并给行号 | 修正解析后重跑；沙盒留痕 |
| 结语锚点在部分论文取不到（初估 P1/P2/P5/P7/P3；**实测修正：失败集为 P1/P2/P7 共 3 篇**，P3/P5 章号变体子串命中，见 §10.3） | 锚点取 `conclusion_heading` 子串匹配，允许章号与空格变体；**取不到即失败并报 writing-spec 键**，不静默降级 | 论文侧标题对齐（S12/PF-RV8 要求），另立论文侧小任务 |
| 误把待重绘位图当摄影类放行（G1） | 降级资格收窄到 `type` 命中摄影类词表；不可判一律 `redraw_pending` 并入缺口，`--strict` 拦截 | 收紧 PHOTO_TYPES 或在 index 补 `type` |
| 缺口随投稿 zip 外泄（G2） | 缺口一律写包外 sidecar；投稿面 manifest 无 gaps/source_manifest 字段；发送前须 `--verify-only --strict` | 删除包内残留并重跑 package |
| 他线并发改 `tools/paper.py` | 实施前 `git diff --stat tools/paper.py` 非空即停（本次实测为空） | 主会话裁决顺序 |
| 字数口径混用致带宽误判 | manifest 固定非空白口径，sidecar 双记旧口径，方法学字符串如实登记 | 口径修正另立补充 |
| 包内文件被手工增删后误发送 | A1/A4/A5 双向集合核对 + `--verify-only --strict` 发送门槛 | 重跑 package 组装 |
| 误提交他线文件 | 提交前 `git status --short` 域核对（恰 3 路径 + 他线 `authors/registry.yaml`） | `git restore --staged` |

### 7.2 恢复方式（Recovery）—— **revert 优先**

- 本变更为**单笔治理提交**（3 个路径），可 `git revert <commit>` 整体恢复，保留历史（沿 GC-2026-1112-02 §6.2 先例）。**禁止** `--hard` 与历史改写（F7）。
- 若需就地重做：`git reset --soft HEAD^` 重分组后重新提交。
- 工作区不做整体回滚（F7 保留现场）；计划、两份复核报告、实施报告与沙盒留痕留存 `temp/GC-2026-1112-03/`、`temp/VERIFY-GC-2026-1112-03/`。
- **论文仓无回滚动作**：本轮全部实跑在沙盒副本执行，真实论文仓零改动（实测 P4 `git status --short` 空）。

---

## 8. 验证方法与实测结果（Verification）

沙盒根：`temp/VERIFY-GC-2026-1112-03/`（gitignore 内）。完整日志：`temp/VERIFY-GC-2026-1112-03/verify-log.txt`（1 483 行，14 步逐项留痕）。

| # | 验证项 | 方法 | 实测结果 |
|---|---|---|---|
| 1 | **正例组装（P4 沙盒副本）** | `python3 -I tools/paper.py package --paper temp/VERIFY-GC-2026-1112-03/P4-sandbox --current` | **退出码 0**；A1–A5 **全部 pass**；`failed_assertions: []`；包根 `build/v0.3.2/package/` 重建为 10 个文件：`面向自然资源文献的条件完整性约束检索方法（作者A）.docx`（426 237 B）/`.pdf`（1 122 932 B）、`figures/fig1.svg`（6 230 B）/fig2.svg（4 418 B）/fig3.svg（3 851 B）、`tables/tab1.csv`（946 B）/tab2.csv（759 B）/tab3.csv（601 B）/tab4.csv（163 B）、`manifest.json`（8 385 B） |
| 2 | **三图全 SVG（计划 §6.1 期望）** | 读 manifest `figures.items` | **3 图全 `svg_source_registered`**（fig1/fig2/fig3 → `figures/figN.svg`）；与 `figures/index.yaml` 三条 `filename_svg` 登记一一对应 |
| 3 | **表数 = paper.md 实际管道表数** | A4 双向集合核对 + 独立解析 | **4 表**（表 1–表 4），与 `body/paper.md` 的 4 个管道表块一致；题注配对命中 4/4（`表 1 六类条件定义与实例` 等），正文引用句"表 3 报告了…"未被误取 |
| 4 | **manifest 八字段实值** | 读 `package/manifest.json` | title `面向自然资源文献的条件完整性约束检索方法`；title_en `Conditional Completeness Constrained Retrieval…`；abstract_zh 369 字（非空白）；abstract_en_present `true`；keywords_zh 5 词；authors 2（作者C corresponding=true，两位 bio 十字段全解析）；conclusion 1 354 字；total_chars **21108**；body_chars **18722**；submission_direction `专刊主题：多模态时空大数据处理关键技术及应用研究（方向条目（一）–（四）待作者确认后细化）` |
| 5 | **sidecar 生成** | 读 `build/v0.3.2/package-gaps.json` | 生成且**在包目录之外**；`gaps: []`（P4 两位作者 bio 均从 paper.md 解析成功）、`downgrades: []`、`redraw_pending: []`、`notes` 1 条（投稿方向带注记）、`char_count_bandwidth` = {min 13000, max 16000, body 18722, status **above_max**, level INFO}、`char_count_reference`（旧口径 body 13846 / total 14643）、`source_manifest`（`build/v0.3.2/manifest.json` + release_id `BUILD-v0.3.2-20261112060025`）、`author_bio_source`、`tables_source`（4 条正文行号） |
| 6 | **build-record 追加节** | 读沙盒 `build-record.md` 尾部 | 追加 `## PKG-v0.3.2 · 投稿交付包组装（2026-11-12 16:28:30 +0800）` 一节：运行命令/模式/版本、骨架清单（图逐项状态、表逐项交付名与题注）、字数三元与旧口径参考、带宽行、缺口摘要、A1–A5 逐项结论、退出码；**失败运行同样留痕**（见第 9 项） |
| 7 | **位图 fixture 两路径** | 沙盒构造最小论文夹（figures/index.yaml：fig1 `type: photo` 无 SVG、fig2 `type: schematic` 无 SVG） | fig1 → **`downgraded_bitmap`**（复制 `figures/fig1.png`，记 `reason_category: photograph_like` 与 sha256）；fig2 → **`redraw_pending`**（**不复制**，入 gaps + `redraw_pending` 明细，附 declared_type `schematic`）；A1–A5 全 pass，退出码 0 |
| 8 | **strict 拦截** | fixture `--verify-only --strict` | **退出码 1**，`strict_status: fail`，原因 2 条：`2 gap(s) recorded in package-gaps.json`、`1 figure(s) pending SVG redraw` |
| 9 | **负例① 删包内 csv → A4 失败** | P4 副本删 `tables/tab2.csv` 后 `--verify-only` | **退出码 1**，`failed_assertions: ["A4"]`；A4 明细 `expected [tab1..tab4] / packaged [tab1,tab3,tab4] / missing ["tab2.csv"]` |
| 10 | **负例② 篡改包 manifest title → A3 失败** | 篡改包内 manifest.json 的 title 后 `--verify-only` | **退出码 1**，`failed_assertions: ["A3","A4"]`（A4 为承前一步删 csv 的残留）；A3 明细 `differences: [{field: title, release_manifest: 面向自然资源文献的条件完整性约束检索方法, package_manifest: 篡改后的标题（用于 A3 负例）}]` |
| 11 | **负例③ 置空关键词 → A2 失败** | fixture 变体"关键词："行置空 | **退出码 1**，`failed_assertions: ["A2"]`；A2 明细 `empty_fields: ["keywords_zh"]`、`field_errors: ["keywords_zh: the keyword line parsed to an empty list"]` |
| 12 | **负例④ 删结语锚点 → 报 conclusion_heading** | fixture 变体把"# 2 结语"改为"# 2 结束语" | **退出码 1**，`status: error`；`error: conclusion heading not found in body/paper.md: writing-spec.conclusion_heading='结语' (S12 …)`，附 `h1_titles: ["1 引言","2 结束语","参考文献","作者简介"]` |
| 12b | **用法错误退出码** | `package --paper /nonexistent/paper/path` | **退出码 2**（用法/环境错误与断言失败分流），`error: Paper directory not found: /nonexistent/paper/path` |
| 13 | **静态与回归** | `python3 -I -m py_compile tools/paper.py`；`check --paper <真实 P4>`；`writing status --paper <真实 P4>`；`build list --paper <沙盒>` | py_compile **退出码 0**；`check` → **status pass**（paper.yaml / required_paths / agents_pointer / body_chapters / git_repo 五项全 pass，退出码 0）；`writing status` → **status ok，total_words 14302**（旧口径，writing-status 指标未动）、progress 95%、7 章全 complete，退出码 0；`build list` → status ok（build 子命令分派未被本变更影响），退出码 0 |
| 14 | **口径双值核验** | 独立脚本 `fixtures/count_check.py` 重算正文（1-based 55–480 行） | 非空白 **18722**、旧口径 **13846**，与 sidecar / manifest 记录**逐值一致**（断言通过）；正文按非空白口径**越上带 16000**（above_max，INFO 级，裁定权在 PF-RV8 审稿线，见 §10.3） |
| 15 | **变更域核对** | `git status --short` / `git diff --stat` | 治理仓：本变更触及 **3 个路径**（`tools/paper.py` +1075 −0、`governance/build.md` +1 −0、本记录新建未跟踪）；他线 `authors/registry.yaml` 仍为在途改动，**未触碰、未纳入**；论文仓 **零 tracked 改动**（P4 `git status --short` 空，HEAD `997882a` 未变） |
| 16 | **不越界自检** | 全程命令审计 | 未执行任何 `git add` / `git commit` / `git stash` / `git checkout`；未改 `rule-index.yaml`、`project.yaml`、`review.md`、`writing.md`、`polish.md`、`schemas/`、`templates/`；未触碰七篇论文仓 tracked 文件；沙盒与 `temp/` 写入均在 .gitignore 内 |

---

## 9. 开放项（Open Items，登记不实施）

- **O4（归一：吸收计划原拟 O8，与 02-O4 同义）**：计划 v1.0 曾另立 "O8 = authors.yaml 结构化十字段简介回填"，与 02 记录 §9 **O4**（作者简介十字段的数据源扩展 + `writing-spec.yaml` 增"征稿方向清单"键）**同义**，故本轮不再另立编号，**归入 02-O4** 一并跟踪。事实校正（G7/T8）：十字段数据**已在 `body/paper.md` 作者简介节内**（P4 两作者全字段齐备，6/7 篇论文有该节），缺的是 `authors.yaml` 的结构化存储与用户确认；因此 bio 走"paper.md 解析优先"路径，解析失败/缺失才落 sidecar 缺口（过渡条款，§5.3）。
- **O9（新，PF-B7 残留载体）**：build 侧集成尚缺——新构建产物按"标题（第一作者中文名）"命名（PF-B7 命名条）、发布 manifest 增记 PF-B16 投稿元数据集与包 `manifest.json` 的 sha256。**本轮由 `package` 命令作交叉核对执行点**（A3 双向核对共享字段），但 build 侧回写与命名本身未实现；O9 收口前"已发布版本不就地改写"的语义不受影响。
- **O6（维持）**：SVG 重绘自动化工具链选型（重绘/对比脚本）。本轮预留 `redraw_pending` 状态机；**重绘差异对比与色系调整登记仍属人工（PF-B15 过渡执行）**——工具只登记"该图待重绘"这一事实，不产出对比结论，也不替代色系调整的逐图登记义务。
- **O5（维持）**：投稿面 manifest 的 JSON Schema 强制（`schemas/` 增 manifest schema 与构建断言）——本轮只做字段完整性断言，未增 schema。
- O2 余量 / O3 / O7 维持 02 登记（本轮不涉及）。

---

## 10. 实施记录（T：agent-minimax）

### 10.1 实施范围与文件改动

| # | 文件 | 类型 | 实测内容 |
|---|---|---|---|
| 1 | `tools/paper.py` | 修改（纯追加） | **+1075 −0 行**（3255 → 4330 行），3 个 hunk（**全为新增，无删除行**）：`@@ -3069,0 +3070,1067 @@`（package 函数块）、`@@ -3206,0 +4274,7 @@`（argparse 注册）、`@@ -3249,0 +4324 @@`（cmds 派发表新增 `"package": cmd_package`）。**既有函数体零改动**（`git diff` 无删除行）。新增符号：`class PackageFailure`；常量 `PHOTO_TYPES` / `FIG_STATUS_SVG` / `FIG_STATUS_DOWNGRADE` / `FIG_STATUS_REDRAW` / `CHAR_COUNT_METHOD`；函数 `_load_yaml_file`、`_load_yaml_mapping`、`_resolve_paper_dir`、`_resolve_package_version`、`_count_nonwhitespace_chars`、`_markdown_sections`、`_strip_pandoc_fences`、`_split_md_row`、`_is_md_separator`、`_strip_markdown_bold`、`_package_figures`、`_package_tables`、`_package_body`、`_extract_abstract`、`_label_value`、`_parse_bio_paragraph`、`_parse_author_bios`、`_package_authors`、`_package_direction`、`_find_release_artifact`、`_package_plan`、`_materialize_package`、`_package_assertions`、`_append_build_record`、`cmd_package` |
| 2 | `governance/build.md` | 修改（纯追加） | **+1 −0 行**（1 个 hunk），PF-B16 末条"Sending the package…"之后追加过渡与执行点条款，**逐字**采用计划 §5；逐字校验脚本已通过（`lines[hits[0]] == expected`）。 |
| 3 | `governance/changes/2026-11-12-build-package-toolchain.md` | 新建 | 本记录 |

### 10.2 实现要点与规格对应

- **CLI 形参**：`--paper` 接受路径、仓目录名或论文号（`P4` → 唯一匹配 `P4-*`）；`--version vX.Y.Z` 与 `--current` 互斥，缺省走 `--current`（读 `build/current.json`）；退出码 0 成功 / 1 断言或组装失败 / 2 用法与环境错误（与 `build docx` 约定一致）。
- **骨架**：`build/<version>/package/` 每次**清空重建**（清空前校验路径必须是 `build/<version>/package`，否则拒绝执行）；docx/pdf 自 `build/<version>/` 取既有产物（优先匹配"标题（第一作者中文名）"命名，多个候选则报歧义）；文件名 = `_posix_safe_title(f"{title}（{第一作者中文名}）")`，复用仓内 PF-B7 转义函数（空格与 `/ \ : * ? " < > |` → `_`，中文与全角括号保留）。
- **figures**：只押 `filename_svg`；三态判定与降级资格见 §5.5；`figures/index.yaml` 兼容平铺列表与 `figures:` 嵌套两种形态（P2/P7）。
- **tables**：paper.md 单源，题注配对与补配规则见 §5.3；CSV 用 `csv` 模块写出（UTF-8、`\n` 行尾、标准引号转义），单元格仅剥离 `**` 粗体标记。
- **manifest**：八字段 + 合法扩展（`title_en` / `abstract_en_present` / `char_count_methodology` / `char_count_components` / `figures` / `tables` / `downgrades` / `package_version` / `generated_at`），**无 gaps、无 source_manifest、无内部凭据**。
- **bio 解析**：从 `body/paper.md` `# 作者简介` 节按段切分，逐段解析"姓名，出生年—，性别，籍贯人，学位，职称"前缀 + "研究方向：/通信地址：/邮编：/电子邮箱：/电话："标注字段，输出十字段；解析不到或字段缺失 → `bio: null` + sidecar 缺口（open item O4），不硬失败。
- **投稿方向**：取 `writing-spec.yaml` 的 `submission_direction`；对 `cfp_directions`（columns + special_issue_directions + long_term_scope + special_issue_theme）作**逐字条目归属机检**：命中 → 通过（带注记则记 note）；未命中任何条目 → gap（PF-B16 禁自拟方向）；null → gap（PF-B16 允许 null + 缺口登记）。
- **build-record**：每次运行（含失败与 strict 失败）追加一节，节内含运行命令/模式/版本、骨架清单、图逐项状态、表逐项交付名与题注、字数三元 + 旧口径参考 + 带宽行、缺口摘要、A1–A5 逐项结论与退出码；只追加不改写既有节（PF-B7）。

### 10.3 实施时须交审稿线处理的事项（如实登记，不自行裁定）

1. **P4 正文越上带**：按真非空白口径 **18722 > 16000**（`writing-spec.yaml` `max_chars`），sidecar 记 `above_max` / INFO 级。工具只提示不裁定——PF-RV8 的字数带宽裁定权在审稿线；由 P5 既有裁定口径（`len(re.sub(r'\s','',s))`）复算亦为同一数字，两口径不混用。
2. **投稿方向待确认**：P4 登记值带"（方向条目（一）–（四）待作者确认后细化）"注记，工具判定为"含逐字条目 + 注记"（note，非 gap），`--strict` 不因此拦截；注记本身是 `paper.yaml` `unresolved` 已登记的待确认项。
3. **结语锚点的论文侧对齐**：实测失败集为 **P1（`# 7 结论与后续`）、P2（`# 10 结论`）、P7（合章内嵌）共 3/7**——P3（`# 6  结语`）与 P5（`# 结语`）按 `conclusion_heading: 结语` 子串匹配规则命中，跑 `package` 可正常提取。对 P1/P2/P7 跑 `package` 会在 conclusion 提取处**失败并报 conclusion_heading**，这是 S12 内容级问题（PF-RV8 要求正文标题对齐），属论文侧任务，不在本变更域。（一致性检查 C-2 实测更正：本条与 §7 风险表初稿所列五篇为实施前预估，以本条实测为准。）

### 10.4 越界自检

- 未执行 `git add` / `git commit` / `git stash` / `git checkout` / `git reset`（全程只读 Git 状态与 diff）。
- 未改 `rule-index.yaml`、`project.yaml`、`review.md`、`writing.md`、`polish.md`、`schemas/`、`templates/`、七篇论文仓任何 tracked 文件、`authors/registry.yaml`（他线在途）。
- 全部实跑在 `temp/VERIFY-GC-2026-1112-03/` 沙盒副本内完成；真实 P4 仓 `git status --short` 为空、HEAD `997882a` 未变。
- **验证运行也会留痕**：按 PF-B7「每次构建追加一节」，`package` 的**每次**运行（含 `--verify-only` 与失败运行）都会向论文仓 `build-record.md` 追加一节。因此在真实论文仓上跑一次校验即产生一个 tracked hunk——该 hunk 属**论文线提交域**（随论文内容线提交），不得混入治理提交；本轮全部实跑因此一律在沙盒副本执行。实施期一次以论文号（`--paper P4`）指向真实仓的试跑误留 36 行 hunk，已 `git restore build-record.md` 还原，实测该仓 `git status --short` 复归空、HEAD `997882a` 未变。
- `temp/` 写入仅限本变更的计划/复核/实施报告与沙盒验证留痕（.gitignore 内，不入库）。

---

## 11. O9 收口记录（GC-2026-1112-04）

- 日期：2026-11-12
- 编号：**GC-2026-1112-04**（承接本记录 §9 登记的 **O9** 残留；独立成号，实施域 = `tools/paper.py` + 本记录 §11）
- 计划版本：**v1.1**（`temp/GC-2026-1112-04/plan.md`；v1.0 经 agent-gpt-team（`review-gpt-team.md`）与 agent-glm（`review-glm.md`）并行复核后修订，两份报告在 `temp/GC-2026-1112-04/`，T1/T2 与 G-1/G-2 为实施门禁并已全部吸收）
- 类型：治理工具链实现（PF-B7 之实现；**无新规则正文，rules_version 保持 0.3.0**）
- 规则依据：AGENTS.md F9/F5/F6；PF-B7（02 修订句 + "已发布版本不得就地修改 / 旧版本保留"）、PF-B15/B16、PF-B5、PF-V3/V5/V6/V8
- **流程状态**：**T 已实施**（实施报告 temp/GC-2026-1112-04/impl-minimax.md）；提交与收口见 §11.6

### 11.1 基线（实施时实测）

- **git 基线**：治理仓 HEAD = `9a41208`（"docs(governance): GC-2026-1112-03 记录收口……"）。
- **开工硬性前置**：`git status --short` = ` M authors/registry.yaml`、` M schemas/layout-profile.schema.json`、` M templates/layout/profiles/stie.yaml`、` M templates/layout/refdoc/stie.docx`、` M tools/make_refdoc.py`、` M tools/verify_layout.py`、`?? governance/changes/2026-11-12-stie-venue-template-alignment.md`——**他线 STIE 版式线整线 6 modified + 1 untracked**（复核 T10/G-6 登记的实况）；`git diff --stat tools/paper.py` = **空**（paper.py 相对 HEAD 干净）→ 满足开工条件，开工未停机。
- **论文侧基线**：P4 仓（`P4-CONDITIONAL-COMPLETENESS-20251111`）工作树干净，`build/current.json` → **v0.3.2**；`build/v0.3.2/` 产物为**旧命名**（`面向自然资源文献的条件完整性约束检索方法.docx/.pdf`，无第一作者），manifest **无 `submission` 块**、`review_status` = `pending`；七篇 `paper.yaml` 均登记 `roles: [first]`（P5 仅 paper.yaml 有 roles，authors.yaml 无 roles 键）。
- **宿主工具链**：pandoc 3.9 / LibreOffice 25.2.3.2 / pdffonts / Python 3.13.5 在位（与 P4 既有 manifest 记录的 pandoc 版本一致）。

### 11.2 变更内容（`tools/paper.py`，+466 −18 行，4330 → 4778 行）

| # | 落点 | 内容 |
|---|---|---|
| ① | 命名 | 新增 `_first_author_name`（**paper.yaml authors 优先、authors.yaml 兜底、`roles` 含 `first`**）与 `_release_file_stem`（`_posix_safe_title(f"{title}（{first_author}）")`）两个共享助手；**build 路径与 package 路径调用同一对助手**（原 package 3663–3675 内联取法改为调用共享助手，行为与错误文案不变）→ 产物名与包骨架名不可能分叉。build 侧在**任何构建动作之前**解析第一作者：缺失 → 构建失败（退出码 2，`stage: pre-build`），错误文案报 PF-B7 命名要求与修复指向（`paper.yaml` / `authors.yaml` 的 `roles: [first]`）。 |
| ② | `submission` 块 | docx 阶段向发布 manifest 写入 `submission` 块：`title` / `title_en` / `abstract_zh`（全文）/ `abstract_en_present` / `keywords_zh` / `authors`（name·affiliations·roles·email·corresponding·bio）/ `bio_gaps` / `conclusion`（全文）/ `body_chars{value,methodology,components,band}` / `total_chars{value,methodology,components}` / `submission_direction` / `submission_direction_check` / `counting_note` / `submission_gaps` / `package_manifest_sha256`（初值 null）/ `package_status`（初值 `not_assembled`）。抽取复用 package 侧同源助手（`_extract_abstract` / `_package_authors` / `_package_body` / `_package_direction` / `_count_nonwhitespace_chars`），**逐字段 try/except**：任何异常或未命中 → 该字段 null + `submission_gaps[]` 登记 + 构建输出 warning 行，**构建绝不中断**（`PackageFailure`、yaml 解析异常同被捕获；writing-spec 加载失败归 gaps）。**build 阶段不写论文仓 `build-record.md`**——留痕只走构建输出与 manifest 内 `submission_gaps`（沙盒纪律沿 03 §10.4）。 |
| ③ | 重建保留语义（T1） | docx 阶段重写 manifest 时：旧 manifest 存在则**继承其 `review_status`**（不再恒写 `pending`；已发布版本重建后仍为已发布，不静默重置）；若旧 `submission.package_status == "assembled"` → 新块置 `package_status: "stale"`、`package_manifest_sha256: null`、`stale_note: "rebuild invalidated prior assembly; re-run package"`；`submission` 块本身按当前源重算。 |
| ④ | `cmd_build_pdf` | pdf 阶段对**同一 manifest 整份读改写**（追加 formats/artifacts/pdf 字体与 limitations），`submission` 块原样保留；两处写盘改用原子写。 |
| ⑤ | package 回写 | 断言全过后回写发布 manifest：`submission.package_manifest_sha256`（**64 位全量 hex**，`hashlib.sha256(package/manifest.json)`）+ `submission.package_status = "assembled"`（并清除 `stale_note`）。**守卫 = 版次 == `build/current.json` 指向版次 且 该 manifest `review_status == "pending"`，两判据同时满足才回写**；否则拒绝（退出码 1，提示被取代版次走 sidecar / 版次 bump）。`--verify-only` **零写入**；断言失败或 `--strict` 失败**不回写**；manifest 更新为读 → 改 → **原子写**（临时文件 + `os.replace`）。 |
| ⑥ | A3 扩展 | A3 在既有 `title` / `package_version` 之外，增列**发布 manifest `submission` 块与包 manifest 的集合级相等核验**：title / title_en / abstract_zh / keywords_zh / **authors（子域 = name + roles + corresponding + bio，逐作者）** / conclusion / `body_chars.value` / `total_chars.value` / submission_direction；比较前 strip 规范化（作者子域按 name/roles 列表/bool/简介字段 map 规范化）；不一致即 A3 fail 并列两侧差异。**legacy 发布 manifest 无 `submission` 块时不参与该项比较**（A3 结果记 `submission_compared: false`），既有旧版次仍可打包。 |
| 附 | G-5 旧名滞留声明 | 命名切换后旧名产物滞留于 `build/<version>/`：**不删除**（PF-B7 旧版本保留，F6 约束），只在构建输出以 `stale_artifact_names` / `artifact_name_notices` 声明。 |
| 附 | 原子写 | 新增 `_atomic_write_json`（临时文件 + `fsync` + `os.replace`，并**保持原文件权限位**）；build 与 pdf 的 manifest 写盘、包回写均走该助手。 |

### 11.3 关键裁定

1. **词表统一仅 `pending`**（T3/G-2）：可回写状态**只有 `pending`**（全仓唯一存在值；layout-standards 记录 L327"非 pending 即已发布"的二元语义），**"draft" 废弃不入守卫**——手工置 `draft` 的版本在 build 侧被当作已发布、在 package 侧被拒绝回写，两守卫不再语义相悖。
2. **`current.json` 指向判据**（G-1）：回写守卫为 **`build/current.json` 指向的版次 且 `review_status == "pending"`** 双判据。被取代版次（如 P4 v0.3.0 / v0.3.1）**装配照做、记录落 sidecar（`package-gaps.json`）、发布 manifest 不回写**，退出码 1 并提示版次 bump——既满足 PF-B7 "旧版本保留"，又堵住"review_status 全仓恒 pending、单一判据实践中永不触发"的洞。
3. **重建保留语义**（T1/G-4）：`review_status` 继承 + `assembled → stale`；禁止静默重置为 pending、静默抹除装配痕迹。
4. **A3 子域固定**（T5/G-7）：authors 比较子域 = **name + roles + corresponding + bio（逐作者）**；affiliations 与 email 记录但不比较（属作者登记，非发布/包共享集）。`package_manifest_sha256` 不入比较集（其自身有独立核对：回写值取自包 manifest 文件实算 sha256）。
5. **DD-2 强化**（T4/G-8）：抽取逐字段 try/except；**warning 留痕走构建输出与 manifest 的 `submission_gaps`，不写论文仓 `build-record.md`**（计划原列的 build-record 留痕在本轮按任务书收回，避免在论文仓产生 tracked hunk）。
6. **first_author 取法逐字复刻**（T9）：由共享助手 `_first_author_name` 实现，build 与 package 同源；`title` 用 `paper_cfg['title'].strip()`（多行标题下与 package 一致）。
7. **G-3 legacy 容错**：发布 manifest 缺 `review_status` 字段（legacy）→ 视为**非 pending** → 拒绝回写；缺 `submission` 块 → A3 不参与该项比较。
8. **`submission_block_absent` 第三守卫**（写后复核 V-1 补记）：目标 manifest **不含 `submission` 块**（GC-2026-1112-04 之前构建的 legacy 版次）时，回写同样拒绝（与 superseded/review_status_not_pending 同级守卫原因），装配与缺口照常落 sidecar——防止向 legacy manifest 就地植入新结构；此类版次如需装配记录，重建新版次后由新 manifest 承接。

### 11.4 验证实测结果（沙盒 `temp/VERIFY-GC-2026-1112-04/`，P4 副本；真实 P4 仓零改动）

| # | 验证项 | 退出码 | 实测结果 |
|---|---|---|---|
| 1 | `build docx --paper <沙盒 P4>` | 0 | 产物 `面向自然资源文献的条件完整性约束检索方法（作者A）.docx`；manifest `submission` 块实值（见 §11.5）；`package_status: not_assembled`、`package_manifest_sha256: null`；`review_status: pending` |
| 1 | `build pdf --paper <沙盒 P4>` | 0 | 产物 `面向自然资源文献的条件完整性约束检索方法（作者A）.pdf`；`submission` 块**原样保留**（abstract 383 字符、body 18722 / total 21108、两作者 + corresponding） |
| 2 | **T1 负例 a**：手工置 `review_status: released` 后同版次重跑 `build docx` | 0 | manifest `review_status` **仍为 `released`**（未被重置为 pending）——继承语义生效 |
| 2 | **T1 负例 b**：`package --current` 装配成功后重跑 `build docx` | 0 | `package_status: stale`、`package_manifest_sha256: null`、`stale_note: "rebuild invalidated prior assembly; re-run package"` 三项齐备 |
| 3 | **G-1 负例**：`package --version v0.3.1`（被取代版次、旧命名产物） | 1 | A1–A5 **全过**（旧命名单候选回退命中）；写回拒绝，`reason: superseded_version`，错误文案指向 sidecar 与版次 bump；**v0.3.1 发布 manifest 未被改写**（仍无 `submission` 块），装配与缺口记录在 sidecar |
| 4 | **守卫负例**：当前版次 manifest 手工置 `review_status: released` → `package --current` | 1 | 写回拒绝，`reason: review_status_not_pending`；`package_status` 仍 `not_assembled`、`sha256` 仍 null |
| 5 | **正例**：`package --current` | 0 | A1–A5 全过；回写 `package_manifest_sha256` = 64 位全量 hex（与包 `manifest.json` 实算值**逐字一致**）、`package_status: assembled` |
| 5 | **篡改**：改发布 manifest `submission.abstract_zh` → `package --current --verify-only` | 1 | **A3 fail**，差异列 `abstract_zh`（两侧值并列）；**零写入**——回填的 sha256 **未被清除**、`package_status` 仍 `assembled`；`writeback.reason: verify_only_zero_write` |
| 5b | **断言失败不回写（build 模式）**：同上篡改后跑 `package --current`（非 verify） | 1 | A3 fail → 写回未发生（`reason: assertions_failed_no_writeback`），发布 manifest `package_status` 仍 `stale` |
| 5c | **strict 失败不回写**：删作者简介节副本 → `package --current --strict` | 1 | `strict_status: fail`（2 gap），写回未发生（`reason: strict_failed_no_writeback`） |
| 6 | **回归 a**：`package --version v0.3.1 --verify-only` | 0 | 旧命名产物单候选回退命中、A1–A5 全过；**verify-only 不受写回守卫拦截**（已发布/被取代版次的发送门槛仍可用） |
| 6 | **回归 b**：`package --version v0.3.0` | 1 | 旧命名单候选回退命中、A1–A5 全过；写回按 `superseded_version` 拒绝（退出码 1 为守卫语义，非产物缺失） |
| 6 | **回归 c**：`check --paper` / `build list --paper` | 0 / 0 | `check` status=pass；`build list` 正常返回（P4 无 `output/` 目录，`releases: []` 为既有历史行为，非本次引入） |
| 6 | **回归 d**：`python3 -I -m py_compile tools/paper.py` | 0 | 通过 |
| 7 | **DD-2 降级**：P1 副本（结语锚点不命中）`build docx` | 0 | **构建不中断**：`conclusion` / `body_chars.value` / `total_chars.value` 三项 null + 1 条 `body_extraction_failed` gap + 1 行 warning（点名 `conclusion_heading='结语'` 未命中） |
| 7b | **writing-spec 加载失败**：破坏 YAML 的 P1 副本 `build docx` | 0 | 构建不中断；3 条 gaps（`writing_spec_unreadable` / `body_extraction_failed` / `submission_direction_missing`），下游字段降级为 null |
| 7c | **缺第一作者**：删除 `roles: [first]` 的副本 `build docx` | 2 | 构建失败（`stage: pre-build`），错误文案报 PF-B7 命名要求与修复指向 |
| 8 | **变更域核对**：`git status --short` / `git diff --stat` | — | 治理仓 tracked 改动**恰 2 路径**：`tools/paper.py`（+466 −18）与本记录 §11；**他线 STIE 整线 6 modified + 1 untracked 集合不变、未触碰**；论文仓**零 tracked 改动**（真实 P4 `git status --short` 空，manifest 无 `submission` 块、无新命名产物） |

### 11.5 P4 发布 manifest `submission` 块实值样例（沙盒实测）

```json
{
  "title": "面向自然资源文献的条件完整性约束检索方法",
  "title_en": "Conditional Completeness Constrained Retrieval for Natural Resources Documents",
  "abstract_zh": "自然资源技术文献的指标值、操作要求和判断规则分布于正文、表格、表注及附录。…（383 字符全文）",
  "abstract_en_present": true,
  "keywords_zh": ["条件完整性", "类型化依赖图", "证据包", "检索增强生成", "自然资源技术文献"],
  "authors": [
    {"name": "作者A", "affiliations": ["云南省自然资源厅<单位已脱敏>"], "roles": ["first"],
     "email": "<邮箱已脱敏>", "corresponding": false, "bio": {"出生年": "1978", "…": "十字段全"}},
    {"name": "作者C", "affiliations": ["云南省自然资源厅<单位已脱敏>"], "roles": ["corresponding"],
     "email": "<邮箱已脱敏>", "corresponding": true, "bio": {"出生年": "1986", "…": "十字段全"}}
  ],
  "conclusion": "# 7 结语\n\n## 7.1 工作总结\n…（1407 字符全文）",
  "body_chars": {"value": 18722, "methodology": "非空白字符（len(re.sub(r'\\s','',text))，含标点/数字/字母），与 P5 既有裁定口径一致",
                 "components": {"abstract_zh": 369, "body": 18722, "references": 2017, "total": 21108},
                 "band": {"min_chars": 13000, "max_chars": 16000, "level": "INFO", "status": "above_max"}},
  "total_chars": {"value": 21108, "methodology": "…", "components": {"abstract_zh": 369, "body": 18722, "references": 2017, "total": 21108}},
  "submission_direction": "专刊主题：多模态时空大数据处理关键技术及应用研究（方向条目（一）–（四）待作者确认后细化）",
  "submission_direction_check": {"registered_items": 14, "matched_item": "多模态时空大数据处理关键技术及应用研究", "exact": false},
  "counting_note": "非空白字符（…）口径；total = 摘要 + 正文 + 参考文献；正文带宽 13000–16000 字（writing-spec；INFO 级，裁定权在 PF-RV8）",
  "submission_gaps": [],
  "package_manifest_sha256": null,
  "package_status": "not_assembled"
}
```

- 双字数 **18722（正文）/ 21108（总）** 与 03 记录 §8 第 14 项的口径独立核验值**逐值一致**（真非空白口径，含标点/数字/字母；旧口径 13846 不与之混用）。
- `band.status: above_max` 仍是 §10.3 第 1 项登记的**正文越上带**（INFO 级，裁定权在 PF-RV8 审稿线），本轮未改该事实。

### 11.6 O9 关闭判定与流程状态

- **O9 关闭判定：O9 关闭（本记录 §9 的登记载体在本节收口）**——O9 的两半（① 新构建按"标题（第一作者中文名）"命名；② 发布 manifest 增记 PF-B16 投稿元数据集与包 `manifest.json` 的 sha256）**均已实现并实测通过**；PF-B7 的"发布 manifest 记录包 manifest sha256"义务由 package 回写兑现，"共享字段两侧必须一致否则失败"由 A3 扩展兑现。
- **残留与后续（不自行裁定）**：
  1. **P4 正文越上带**（18722 > 16000）与**投稿方向待确认**沿 §10.3 第 1、2 项，裁定权仍在 PF-RV8 审稿线，本轮只记录不裁定。
  2. **结语锚点对齐**（P1/P2/P7）沿 §10.3 第 3 项，属论文侧任务；本轮 build 侧已按 DD-2 降级为 null + gap（构建不中断），`package` 侧仍按 S12 硬失败。
  3. **旧名产物滞留**：真实论文仓首次以新命名重建后，`build/<version>/` 将并存新旧两套产物，清理策略由论文线裁定（工具只声明、不删除）。
  4. **发表状态翻转方缺失**：`review_status` 全仓恒 `pending`（18/18 份发布 manifest），本轮守卫按"仅 pending 可回写"实现；若将来引入发布流程翻转该字段，须同步复核 build 侧已发布守卫与 package 侧回写守卫（同一闭集）。
- **流程状态**：**已提交**。治理仓提交 **`e1e67ef`**（2026-11-12，恰 2 文件：tools/paper.py +466 −18、本记录 §11 +109）；agent-glm 写后 diff 复核 **PASS**（verify-glm.md，沙盒独立重跑 3 项全部复现）；内容一致性检查 **consistent**（consistency-check-gpt-team.md，六项矩阵全过；其待收口项"提交号回填"由本行收口；STIE 并发线 6+1 文件未混入提交，git show --stat 实证）。实施者实施全程未执行任何 git add/commit，提交由主会话按复核结论执行。

---

*GC-2026-1112-03。规则依据：AGENTS.md F9/F5/F6/F7；构建依据 governance/build.md PF-B5/B6/B7/PF-B15/PF-B16（新增 PF-B16 过渡与执行点条款）；字数口径依据 PF-RV8 带宽与 P5 既有裁定；计划 temp/GC-2026-1112-03/plan.md（v1.1）。*

*GC-2026-1112-04（§11 O9 收口）。规则依据：AGENTS.md F9/F5/F6；PF-B7（02 修订句）、PF-B15/B16、PF-B5、PF-V3/V5/V6/V8；计划 temp/GC-2026-1112-04/plan.md（v1.1），复核报告 review-gpt-team.md / review-glm.md 同目录。*
