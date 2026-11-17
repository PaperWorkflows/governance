# 治理变更记录 GC-2026-1117-04：构建产物命名重构、历史版本清理与 zip 双通道交付

- 日期：2026-11-17
- 编号：**GC-2026-1117-04**
- 类型：构建规则与工具链修订（PF-B7 产物命名、发布守卫与保留条款；PF-B16 本地/远程 zip 交付；打包错误契约与同 build 产物核对）
- 计划：`temp/GC-2026-1117-04/plan.md`（**v1.0.0**）曾成文，独立评审提出放行条件 C1–C4 及若干 P2 建议；该文件随后被并发会话清理 `temp/` 时一并删除。本记录按最终 diff 和实测结果自包含撰写，基线、变更清单与恢复方式均不依赖该计划文件。
- 规则依据：AGENTS.md **F9**（治理变更纪律）、**F6**（最小改动、据实登记）、**F7**（保留现场、禁止历史改写）；构建 **PF-B5/PF-B7/PF-B16**；版本 **PF-V3/PF-V5**
- 规则版本：**0.3.7 → 0.3.7（不重复升版）**。`94b404a` 已于同日由 GC-2026-1117-05 将 0.3.6 升至 0.3.7；本变更沿用该版本，五处同步位不变。论文侧十篇 `paper.yaml#rules_version` 的铺开继续暂缓，本变更不触碰该字段。

---

## 1. 基线（Baseline）

- **治理仓 git 基线**：`master`，HEAD `94b404a`（`fix(governance): GC-2026-1117-05 构建门禁——围栏 div 引号 lint + Bibliography 落地断言`）。本变更实施时工作树有 4 个已跟踪文件修改：`tools/paper.py`、`tools/pack_submission_zip.py`、`governance/build.md`、`templates/ci/build-submission.yml`；本记录为新增的第 5 个文件。写记录时均未提交。
- **规则版本基线**：0.3.7。五处声明位实测为 `project.yaml:3`、`governance/rule-index.yaml:2`、`tools/paper.py:383` 与 `:587`、`templates/paper/paper.yaml:17`，本变更均不修改。
- **命名基线**：release 与 package 骨架使用 `标题（第一作者中文名）.docx|pdf`；zip 主名已经使用 `<repo-name>-<paper_version>.zip`，无 git remote 时的兜底投稿名仍为 `标题（第一作者中文名）.zip`。
- **交付基线**：远程 CI 已执行 pack 并上传 `submission-zip` artifact；本地没有 `paper.py build zip` 子命令，只能直接调用 `tools/pack_submission_zip.py`。
- **论文侧执行边界**：产物重建与历史清理在十篇论文工作区执行，论文仓只提交 CI 注释和 `build-record.md`（P10 仅 CI 注释）；构建产物本体仍按 `.gitignore` 不入库。各篇 `rules_version` 不变，承接 `e95881f` 的暂缓裁定。
- **用户指令（2026-11-17）**：将 docx/PDF 改为 `第一作者中文名-《中文标题》.docx|pdf`；完整重构相关构建规则；经显式授权清理历史构建、只保留当前版本；本地与远程均提供包含投稿包的 zip。

## 2. 现状取证（问题与证据）

| # | 问题 | 证据（2026-11-17 对 HEAD 与备份实测） |
|---|---|---|
| E1 | 旧产物名不符合本次用户裁定 | HEAD `tools/paper.py::_release_file_stem` 返回 `_posix_safe_title(f"{title}（{first_author}）")`；`governance/build.md` PF-B7/PF-B16 同样写死旧形态 |
| E2 | 改名会绕过旧发布守卫 | 旧守卫以 `if docx_out.exists()` 为前置。切换到新名后，新路径初次构建必然不存在，即使同版本 manifest 已发布，旧逻辑也不会进入已发布内容核对 |
| E3 | 仅靠文件存在性可能混装不同 build 的 docx/PDF | 旧 `_package_plan` 解析 docx/PDF 后不核对其 basename 与 release manifest 记录，也不核对 sha；新 docx 配旧名 PDF 时，A1–A5 的存在性检查不能识别这种陈旧混装，违反 PF-B5 同 build 要求 |
| E4 | 本地交付没有统一的 build 入口，pack 也不便作为库复用 | HEAD build 子命令无 `zip`；`pack()` 在成功路径直接 print JSON，只返回精简字典。新增 wrapper 若直接复用，会造成输出重复或 payload 不完整 |
| E5 | 历史构建目录量大，用户已明确要求只留当前版本 | 重建前备份中十篇共有 **191** 个版本目录；当前每篇仅保留 1 个，共 10 个，因此实际清理 **181** 个。清理不是工具默认行为，而是本次用户显式指令 |
| E6 | 无 remote 的 zip 兜底名与 release 新命名会漂移 | HEAD `pack_submission_zip.py` 的兜底 zip 名和 `submission_name_pf_b7` 仍使用 `标题（作者）.zip`，且未走与 `_posix_safe_title` 相同的转义 |

## 3. 精确变更清单（逐文件；4 修改 + 1 新建）

写记录前 `git diff --stat` 实测：**4 files changed, 195 insertions(+), 57 deletions(-)**。该统计不含尚未跟踪的本记录。

| 文件 | 新增 | 删除 |
|---|---:|---:|
| `tools/paper.py` | 110 | 32 |
| `tools/pack_submission_zip.py` | 77 | 18 |
| `governance/build.md` | 7 | 6 |
| `templates/ci/build-submission.yml` | 1 | 1 |
| **合计** | **195** | **57** |

### 3.1 `tools/paper.py`

1. **统一 release 文件名表达式**：`_release_file_stem` 改为 `_posix_safe_title(f"{first_author}-《{title}》")`，docstring 同步。build 路径和 package 路径继续调用同一函数，POSIX 转义函数本身不变。
2. **同步命名说明和错误文案**：docx 构建处的 PF-B7 注释及“无第一作者”错误信息改为新形态，错误信息标注 `GC-2026-1117-04`。
3. **重构已发布版本守卫（评审 C2）**：不再以“新名 docx 是否存在”为前置，改为读取 `build/<version>/manifest.json`：
   - manifest 不可读时拒绝原地重建，避免无法证明发布状态时静默放行；
   - `review_status != "pending"` 时，读取 manifest 中 docx 的记录 sha，与新 docx 的 sha256 前 16 位比较；
   - 记录 sha 与新产物一致时允许字节相同的幂等重 Materialisation，例如只改文件名的重建；
   - 记录 sha 缺失或与新内容不同则拒绝，要求按 PF-V3 升版。
4. **新增本地 `build zip`**：顶部软依赖导入 `pack_submission_zip`；新增 `cmd_build_zip`、argparse `zip` 子命令及两处 dispatch 注册。默认输出到 `build/<paper_version>/`，支持 `--out` 和 `--name`；委托 `pack_submission_zip.pack()`，捕获 `PackError`（透传退出码 3/2/1）和 `OSError`（退出码 2）。zip 不写入 release manifest 的 `artifacts`，本命令不重复执行 strict 校验。
5. **新增 package 同 build 核对（评审 C3）**：`_package_plan` 对解析出的 docx/PDF 逐一核对 release manifest：对应 format 条目必须存在，`path` 的 basename 必须相同；记录 sha 非空时，实际 sha256 同长度前缀必须相同。缺条目、文件名不符或 sha 不符均抛 `PackageFailure`，阻止“新 docx 配旧 PDF”进入投稿包。

### 3.2 `tools/pack_submission_zip.py`

1. **建立明确错误契约**：新增 `PackError`，约定 3 = package 缺失或为空、2 = 用法/IO/元数据不可读、1 = 未登记第一作者；成功仍为 0。
2. **分离库逻辑与 CLI 输出**：`pack()` 成功时返回完整 payload、不再 print；失败抛 `PackError`。`main()` 负责以 `ensure_ascii=False, indent=1` 打印并退出，成功 JSON 的键序和缩进与改前一致；同时捕获 `PackError` 和 `OSError`，直接脚本入口也遵守退出码契约。
3. **补齐元数据错误处理**：`paper.yaml` 不存在、YAML 不可解析、顶层不是 mapping、缺 `title` 或 `paper_version` 均明确失败；package 缺失/空目录保留原提示和退出码 3。
4. **同步 zip 兜底投稿名**：无 remote 时的 zip 名及 JSON 字段 `submission_name_pf_b7` 改为 `作者-《标题》.zip`，并经新增的 `_posix_safe()` 转义。主名仍为 `<repo-name>-<paper_version>.zip`，未改。
5. **有意复刻转义规则**：`_posix_safe()` 与 `paper._posix_safe_title` 使用同一正则和去首尾下划线规则；因 `paper.py` 已导入本模块，不复用后者的原因是避免循环 import，docstring 已注明。模块 docstring、argparse 描述和 Exit codes 文档同步。

### 3.3 `governance/build.md`

1. **PF-B7 命名段重写**：改为 `第一作者中文名-《中文标题》`，补入 P10 实算示例；空格和 `/ \ : * ? " < > |` 替换为 `_` 的规则不变，中文、全角书名号、连字符保留。
2. **PF-B7 发布条款重写**：已发布版本不得就地改写；仅记录 docx sha 相同的幂等重 Materialisation 例外，内容变化必须升版。
3. **PF-B7 保留条款重写**：旧版本默认保留；只有用户显式指令才可清理。清理时必须保留 `paper.yaml#paper_version` 对应版本，且 `build/current.json` 必须先指向该版本；先备份、记入 `build-record.md`，版本失配先裁定再清理。保留目录内旧名 docx/PDF 只有在新名产物存在且 `package --verify-only --strict` 通过后才可删除。
4. **PF-B16 骨架和 zip 交付条款重写**：骨架文件名改为新形态；本地由 `paper.py build zip` 产生，远程由 CI 上传 `submission-zip` artifact。zip 内容就是 package 骨架（docx、PDF、图、表、package manifest）；主名保持仓库名加版本，无 remote 时回退新 PF-B7 投稿名。zip 是交付物而非发布物，不进入 release manifest `artifacts`；`build zip` 不复检，投稿闸门仍是 `package --verify-only --strict`。

### 3.4 `templates/ci/build-submission.yml`

仅第 7 行注释由“PF-B7 传统名”改为“PF-B7 投稿名”。workflow 的触发条件、构建步骤、门禁、pack 和 artifact 上传逻辑均不动；远程通道继续使用同一 `pack_submission_zip.py`。

### 3.5 `governance/changes/2026-11-17-build-artifact-naming-and-zip-delivery.md`

新建本记录。除此之外，本变更不修改 `project.yaml`、`governance/rule-index.yaml`、`templates/paper/paper.yaml`、schema/profile、论文正文或任何论文侧 `rules_version`。

## 4. 理由（Rationale）

1. **命名只留一个计算入口**：新形态由 `_release_file_stem` 统一生成，build 和 package 不各写一份，避免同名规则在两处漂移。zip 无 remote 兜底名同步采用该形态。
2. **发布状态必须看发布记录，不能看文件名**：manifest 才是 release 记录。改名后沿用“目标文件存在才检查”的旧守卫会整体绕过已发布保护；改为读取 manifest 后，命名迁移和发布状态判断解耦。
3. **幂等重建与内容变更要分开**：纯改名不应强迫十篇论文全部升版，但同版本内容变化也不能静默覆盖。记录 docx sha 相同才放行，既支持字节相同的重 Materialisation，也守住 PF-V3。
4. **docx/PDF 必须来自同一 release**：C3 把解析结果与 manifest 的文件名、sha 对齐，堵上存在性检查无法发现的新旧混装；这比再增加一条人工检查更可靠。
5. **pack 作为库和 CLI 应有同一契约**：成功返回完整 payload、由 CLI 单独打印，避免 wrapper 双份 JSON；3/2/1 错误码让本地命令和 CI 都能按失败类型处理。终版在 `main()` 直跑入口也捕获 `OSError`，不是只修 wrapper。
6. **zip 是投递封装，不改变发布边界**：package 已经过 strict 闸门，zip 只封装其骨架。把 zip 排除在 release `artifacts` 外，避免把重复投递动作混入 docx/PDF 发布清单；远程和本地复用同一 pack 逻辑，产物结构一致。
7. **历史清理必须有明确授权和回退点**：本次删除来自用户指令，不把“只留最新”写成默认行为。先全量备份，再核对 current 与 paper_version，最后清理并登记，兼顾磁盘整理和可恢复性。
8. **不制造额外版本噪声**：治理仓当日已经升至 0.3.7，本变更不重复升版；论文侧只改声明而不重建会制造账实不符，因此继续承接 `e95881f` 的暂缓状态。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 只把现有 docx/PDF 手工改名，不改工具与规则 | 下次构建会恢复旧名，package、manifest 与 zip 兜底名继续漂移，不能持久解决问题 |
| 保留“新名文件是否存在”的旧发布守卫 | 新名首次构建直接绕过已发布检查，是本次必须消除的回归，不可接受 |
| 已发布版本一律禁止原地重建，包括 sha 完全不变 | 会把纯改名也强制变成版本升级，增加无内容变化的版本号；采用字节相同的幂等例外更准确 |
| package 继续任选目录内唯一 docx/PDF | 无法排除旧 PDF 与新 docx 混装；必须核对 release manifest 的名称和 sha |
| 让 `pack_submission_zip.py` 反向 import `paper.py` 共用转义函数 | 当前 `paper.py` 已导入 pack 模块，反向 import 会形成循环依赖；保留小函数复刻并登记同步义务 |
| 把 zip 纳入 release manifest `artifacts`，或在 `build zip` 内重跑全部校验 | 混淆交付物与发布物，并重复既有 strict 闸门；zip 只负责封装，发送前仍须先通过 package strict |
| 无备份直接删除全部旧版本，或自动选择“看起来最新”的目录 | 版本号目录不等于有效 current；失配时误删会破坏回退点。必须用户显式授权、先备份并核对 current/paper_version |
| 本变更再次升治理 rules_version，并顺带批量修改十篇论文 rules_version | 前者重复当日升版，后者会超出本变更范围并违反论文侧逐篇重建后再升版的暂缓裁定 |

## 6. 验证（2026-11-17 实测）

### 6.1 独立验证与返工处置

验证由未参与实施的 `agent-gpt-plus` 执行。

| 轮次 | 结论与发现 | 处置 |
|---|---|---|
| 计划评审 | 提出 C1–C4 放行条件及若干 P2 建议 | C2 发布守卫、C3 同 build 核对已在最终 diff 落实；计划文件虽被删，最终实现可直接核验 |
| 首轮代码验证 | **有条件通过**；2 个 P1：`pack()` 复用后产生双份 JSON；C3 未实现。后者查明为主会话派单漏项 | 修复输出职责分离，补上 C3 后复验 |
| 第二轮验证 | 修复通过；另提 1 个 P2：直接运行 `main()` 时 `OSError` 未遵守退出码契约，影响 CI 实际使用的远程入口；另有 3 个 P3 | `main()` 增加 `OSError` 捕获和退出码 2；其余问题终修，P3-3 单独裁决 |
| 终确认 | **可提交** | P3-3 按返工熔断规则登记备忘，不阻断本轮，见 §9 |

### 6.2 冒烟、确定性与错误路径

- 在治理仓外的 P9 拷贝上执行 `build pdf → snapshot → package → package --verify-only --strict → build zip`，各步均 exit 0。
- P9 新名 docx 的 sha256 前 16 位为 `6ac1d9e396003152`，与改名前备份一致；PDF 前缀 `b519ee5db3428d58` 也一致，证明这次重建对该稿是纯改名、内容中性。
- 同一输入连续两次打包，zip 逐字节一致；固定 entry timestamp 的确定性行为未被重构破坏。
- 错误路径退出码 3/2/1 均实测：package 缺失或为空为 3，用法/IO/元数据错误为 2，无第一作者为 1；成功为 0。
- 最终治理 diff 的 `git diff --check` 无输出；两份 Python 文件语法编译通过。

### 6.3 十篇真实 stem 实算

下表字节数均为 **stem 的 UTF-8 字节数，不含扩展名**。P1–P9 同时是当前磁盘产物名；P10 因 §7/R2 未重建，为新规则实算值。

| 论文 | 新 stem | 字节数 |
|---|---|---:|
| P1 | `杨森-《基于多模型集合关系辩论的自然资源多模态资料质量评估与矛盾检出》` | 103 |
| P2 | `刘馨-《公共部门知识资产分层治理：机制与实证》` | 67 |
| P3 | `李丽英-《面向自然资源全生命周期的时空大数据治理平台设计与实现》` | 94 |
| P4 | `杨森-《面向自然资源文献的条件完整性约束检索方法》` | 73 |
| P5 | `刘馨-《面向审计整改的全链路证据知识库构建方法》` | 70 |
| P6 | `杨森-《面向自然资源规范文献的沿革条款对齐方法》` | 70 |
| P7 | `杨森-《面向可信智能检索的知识库治理体系设计》` | 67 |
| P8 | `刘英豪-《自然资源时空数据的实时采集与版本追溯》` | 70 |
| P9 | `伍红玲-《大数据驱动的人地协同感知：移动信令数据赋能生态保护红线动态监管的技术路径与约束》` | 133 |
| P10 | `伍红玲-《自然资源“一张图”多源时空数据治理与语义对齐》` | 82 |

十项均无首尾连字符、无 Windows/POSIX 转义规则禁止的 `/ \ : * ? " < > |`，均不超过 255 字节。P9 最长，为 133 字节；P10 的全角弯引号按规则保留。

### 6.4 论文侧重建与内容中性核对

- P1–P9 九篇按同一五步流程重建，全部 exit 0，strict 全 pass。逐篇比较重建前备份与当前 docx/PDF 的完整 sha256：**P1、P2、P4、P5、P6、P7、P8、P9 八篇两种产物均完全一致**。
- P3 是唯一内容变化稿：v0.3.28 docx 前缀由 `e7b1e0296d49398a` 变为 `b0cbeb954dcc832c`，PDF 前缀由 `526deb97777b2412` 变为 `7b65cc13a0892c4c`。原因是本次重建纳入了 2026-11-17 01:07 的正文修订，而原 v0.3.28 构建于 2026-11-16 15:35；不是改名导致的字节差异。
- P10 未重建。新增钟锐、李纯后，作者简介必填项未补齐，S17 语义闸拒绝；`build/v0.5.1/` 保留加人前的完整旧名交付物。
- `verify_layout` 全量结果：**TOTAL 27 / PASS 27 / FAIL 0**。

### 6.5 历史清理、CI 与提交域

- 清理前备份有 191 个版本目录，清理后十篇各留 1 个当前版本目录，差值 **181**。每篇 `build/` 保留 `current.json`、`layout.yaml`、（有则）`README.md` 和当前版本目录。
- P8 保留目录内另删除一个并发会话遗留的旧 PF-B7 名 zip。其内嵌 docx/PDF 与新 zip 内对应内容逐字节相同，只是旧命名条目构成的陈旧孪生；当前仓库名加版本的新 zip 保留。
- 十篇 `.github/workflows/build-submission.yml` 已与当前模板逐字节一致；各篇该文件的提交 diff 均只触及 L7 注释，工作步骤没有变化。
- 论文仓本地提交如下，均已核对 commit subject 和文件清单；P1–P9 各含 `.github/workflows/build-submission.yml` 与 `build-record.md`，P10 仅含前者。

| 论文 | commit | 论文 | commit |
|---|---|---|---|
| P1 | `b8bb78b` | P6 | `eb52457` |
| P2 | `27e60b8` | P7 | `e00dadd` |
| P3 | `3586767` | P8 | `42010f3` |
| P4 | `c97aa0e` | P9 | `7f090ec` |
| P5 | `93af173` | P10 | `18a22d9` |

P10 的 17 个并发会话在途文件未纳入 `18a22d9`。上述治理仓和论文仓提交均未 push。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | P10 投稿邮件 `build/v0.5.1/P10-投稿邮件-自然资源一张图-伍红玲.eml` 内嵌旧名附件 | P10 未重建，邮件附件名与当前旧名产物仍一致，尚未发生引用断裂。待作者资料补齐并重建后，应重新生成 eml；若用户按现值发送，则明确它仍是旧名交付物。**待用户处置** |
| R2 | P10 构建被作者资料阻塞 | 钟锐、李纯各有 **7 项**待补：`birth_year/gender/hometown/degree/title/email/phone`；`research_direction/address/postcode` 已有值。补齐后按同一五步流程重建，即得到新名 docx/PDF 与 zip；其 17 个在途文件不得被其他提交裹挟 |
| R3 | P3 v0.3.28 版本号未升但内容更新 | 前会话 01:07 修订未升版即被本次重建纳入；`build-record.md` 已追加新节留痕。若团队要求版本号与内容严格一一对应，应另行裁定升版，不在本变更中偷偷改号 |
| R4 | 本地提交未 push，远程 CI 仍可能取得旧工具链 | 推送须待用户授权。CI 拉取远端治理仓 `master`，只有治理仓 4 个实现文件推送后，新命名和新 pack 契约才在远程构建生效；推送顺序应先治理仓、后触发论文远程构建 |
| R5 | `_posix_safe` 与 `_posix_safe_title` 是有意复刻，未来可能漂移 | 后续修改转义规则必须同时改两处并跑本地/远程 pack 名称对比；已列入 §9 开放项 |
| R6 | 重建和 181 个目录清理需要可回退 | 全量备份位于工作区级 `/home/yangsen/workspaces/PaperWorkflows/.review_scratch/build-refactor-backup-20261117/`，`du -sh` 实测 **468M**，覆盖十篇重建前 build 内容；该目录不在治理仓内，恢复时从对应论文、对应版本目录取回 |

## 8. 恢复方式（Recovery）

### 8.1 治理仓

本变更提交后，整体恢复使用：

```bash
git revert <本提交>
```

本提交为 HEAD、只需逐文件撤回实现时，可从其直接父版本取回：

```bash
git checkout HEAD^ -- tools/paper.py
git checkout HEAD^ -- tools/pack_submission_zip.py
git checkout HEAD^ -- governance/build.md
git checkout HEAD^ -- templates/ci/build-submission.yml
```

本记录随 revert 一并移除。若在当前尚未提交的状态撤回，已跟踪 4 文件应对当前 HEAD `94b404a` 执行 `git checkout HEAD -- <file>`，再删除本新记录；不要把提交后的 `HEAD^` 用法误用于提交前。

### 8.2 论文仓

按 §6.5 表格逐篇执行 `git revert <对应 commit>`。P1–P9 的 revert 只撤回 CI 注释和构建记录，P10 的 revert 只撤回 CI 注释；**构建产物被 `.gitignore` 排除，git revert 不会恢复已删除的版本目录，也不会把新名产物自动改回旧名**。

### 8.3 产物层

需要恢复历史产物时，先停止相关构建并核对 `paper.yaml#paper_version` 与 `build/current.json`，再从 §7/R6 备份中对应 `<论文仓名>/<版本>/` 复制回该论文 `build/<版本>/`。P3 如需恢复重建前 v0.3.28，也必须从备份取回，不能只 revert 文本提交。

禁止 `git reset --hard` 等 `--hard` 操作与任何历史改写；不得为恢复某一篇而清空其他论文或并发会话的在途工作（AGENTS.md F7）。

## 9. 开放项

1. **P3-3：C3 对 manifest 空 sha 仍 fail-open**。当前实现只在记录 sha 非空时比较；主会话按 2 轮返工熔断规则裁决本轮不修。理由是 manifest 由工具生成时 sha 恒非空，空值通常需手工篡改才会出现；在本轮重建前夜收紧 package 路径，回归风险大于收益。后续可为“format 条目存在但 sha 缺失/为空”补专门失败测试后再收紧。
2. **论文侧 rules_version 铺开继续暂缓**。承接 `e95881f`，本变更没有修改该字段；十篇已提交基线仍为 0.3.3/0.3.6 混布（P10 为 0.3.6，其余为 0.3.3）。本轮九篇已完成重建，后续可据此派单逐篇升版，但须单独登记，不能回填成本次提交内容。
3. **P10 作者资料与投稿邮件再生成**。等待钟锐、李纯各 7 项 bio 字段由用户补全；之后重建新名产物并重新生成 eml，或用户明确按现有旧名交付物发送（R1/R2）。
4. **两处 POSIX 转义实现的同步义务**。`pack_submission_zip._posix_safe` 与 `paper._posix_safe_title` 当前规则一致；未来改规则须两处同改并增加一致性测试（R5）。

---

*GC-2026-1117-04。规则依据：AGENTS.md F9/F6/F7；构建依据 governance/build.md PF-B5/PF-B7/PF-B16；版本依据 governance/versions.md PF-V3/PF-V5；规则版本维持 0.3.7。*
