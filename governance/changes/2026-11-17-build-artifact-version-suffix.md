# 治理变更记录 GC-2026-1117-07：构建产物版本号后缀与 build-record 当前版本清理

- 日期：2026-11-17
- 编号：**GC-2026-1117-07**
- 类型：构建规则与工具链修订（PF-B7 产物命名、build-record 历史节清理；PF-B16 投稿包骨架与无 remote 时的 zip 兜底名）
- 规则依据：AGENTS.md **F9**（治理变更纪律）、**F6**（最小改动、据实登记）、**F7**（保留现场、禁止历史改写）；构建 **PF-B5/PF-B7/PF-B16**；版本 **PF-V3/PF-V5**
- 规则版本：**0.4.0 → 0.4.1**。五处声明位同步修改；论文侧十篇 `paper.yaml#rules_version` 不在本变更中铺开。
- 执行边界：治理侧实现 diff 为 6 个已跟踪文件，本记录为新增文件。论文侧 budget 合规、逐篇重建、build-record 清理和投稿邮件重生成分别在各论文仓执行，不混入本治理提交。

---

## 1. 基线（Baseline）

- **治理仓 git 基线**：`master`，HEAD `05f0f7c`（`feat(governance): GC-2026-1117-06 Git 安全规则 F10 + PF-G1–G6（rules_version 0.3.7→0.4.0，四处同步）`）。写记录时，本变更的 6 个实现文件均未提交。
- **规则版本基线**：0.4.0。五处声明位实测为 `project.yaml:3`、`governance/rule-index.yaml:2`、`tools/paper.py:383` 与 `:587`、`templates/paper/paper.yaml:17`；本次均改为 0.4.1，行号不变。
- **命名基线**：`_release_file_stem(title, first_author)` 生成 `第一作者中文名-《中文标题》`，build 与 package 共用该函数，但产物名不含 `paper_version`。同一作者、同一标题的不同版本只能靠目录区分，脱离目录作为邮件附件或单个文件交付时容易混淆。
- **zip 基线**：主名已经是 `<repo-name>-<paper_version>.zip`，本身包含版本号；只有无 git remote 时的兜底 zip 名和 JSON 字段 `submission_name_pf_b7` 仍为 `第一作者中文名-《中文标题》.zip`。
- **记录基线**：`build-record.md` 默认只追加，既有条款没有“用户显式要求只保留当前构建记录”时的精确清理边界；当前版本的 manifest 与 build-record “两份凭证缺一不可”的要求必须继续成立。
- **用户指令（2026-11-17）**：本地和远程构建的 docx/PDF 均增加版本号后缀；删除历史构建记录，各篇 `build-record.md` 只保留当前构建记录；论文侧修复七篇 `paper.yaml` 的 budget 违规。前两项形成本治理变更，第三项按 PF-V5 在论文侧分开执行。

## 2. 现状取证（问题与证据）

| # | 问题 | 证据（2026-11-17 对 HEAD 与当前 diff 实测） |
|---|---|---|
| E1 | docx/PDF 名不含版本号 | HEAD `tools/paper.py::_release_file_stem` 返回 `_posix_safe_title(f"{first_author}-《{title}》")`；build、package 两调用点均只传 title 与 first_author |
| E2 | zip 主名与兜底名的版本语义不一致 | HEAD 主名已为 `<repo-name>-<paper_version>.zip`，无 remote 分支仍是 `_posix_safe(f"{first}-《{title}》") + ".zip"`；因此只需调整兜底名，不应重复修改主名 |
| E3 | build-record 清理缺少可执行定义 | 旧 PF-B7 只规定默认追加及构建目录清理，没有定义保留哪些节、当前版本双凭证如何保留、每篇如何提交，以及旧行号锚点如何追溯 |
| E4 | 函数加参数属于跨调用点签名变更 | 仓内 build/package 两处必须同时补 `version`；工作区级清理助手 `.review_scratch/gc-1117-04-prune.py` 也调用该函数，漏改会在清理阶段直接抛 `TypeError` |
| E5 | 无第一作者守卫属于 fail-closed 关键路径 | 守卫必须在 snapshot 和构建之前返回 exit 2。独立验证曾发现修改文案时误缩进使其成为死代码，缺失作者会继续生成 `None-《…》.docx`，不是单纯提示语问题 |

## 3. 精确变更清单（逐文件；6 修改 + 1 新建）

写记录前，对下列 6 个实现路径单独执行 `git diff --stat`，实测：**6 files changed, 30 insertions(+), 29 deletions(-)**。该统计不含尚未跟踪的本记录。

| 文件 | 新增 | 删除 |
|---|---:|---:|
| `tools/paper.py` | 12 | 12 |
| `tools/pack_submission_zip.py` | 9 | 9 |
| `governance/build.md` | 6 | 5 |
| `project.yaml` | 1 | 1 |
| `governance/rule-index.yaml` | 1 | 1 |
| `templates/paper/paper.yaml` | 1 | 1 |
| **合计** | **30** | **29** |

### 3.1 `tools/paper.py`

1. **release 文件名增加版本参数**：`tools/paper.py:2374` 的 `_release_file_stem` 改为 `(title, first_author, version)`，返回 `_posix_safe_title(f"{first_author}-《{title}》-{version}")`。版本值取当前 `paper.yaml#paper_version` 经构建流程解析出的 `version`，不另写版本号格式。
2. **两个正式调用点同步**：build 路径 `:4341` 与 package 路径 `:5682` 均补传 `version`，继续共用一个 stem 计算入口，保证 release 产物与 package 骨架同名。
3. **说明和错误契约同步**：构建处 PF-B7 注释、函数 docstring 和“无第一作者”错误信息改为带 `-v{版本号}` 的形态，错误信息保留 GC-2026-1112-04、GC-2026-1117-04 并追加本编号。当前 docstring 尚有一处括号错位，见 §6.4，不把它误记为已完成终修。
4. **无第一作者守卫归位**：最终当前工作树中，`if not first_author:` 位于 `:4075`，在 `:4082` 创建 snapshot 之前返回 exit 2。独立验证抓出的误缩进死代码已经修复，fail-closed 行为恢复。
5. **rules_version 两处同步**：`build_paper_yaml` 默认参数 `:383` 和 `cmd_proposal` 显式传参 `:587` 均由 0.4.0 改为 0.4.1，保证新脚手架不会继续生成旧声明。

### 3.2 `tools/pack_submission_zip.py`

1. **只改无 remote 兜底名**：`:128` 改为 `_posix_safe(f"{first}-《{title}》-{version}") + ".zip"`；`:161` 的 `submission_name_pf_b7` 使用同一表达式。`_posix_safe` 的转义规则不变。
2. **主名保持不变**：有仓库名时仍为 `<repo-name>-<paper_version>.zip`。该名字已经含版本号，再追加一次只会形成重复后缀，也会无必要地改变既有 CI artifact 主名。
3. **文档同步**：模块 docstring 的 Naming、PF-B7 契约和 argparse 描述均补版本后缀及 GC-2026-1117-07。pack 的退出码、确定性 entry timestamp、strict 闸门边界均不改。

### 3.3 `governance/build.md`

1. **PF-B7 命名形态**：改为 `第一作者中文名-《中文标题》-v{版本号}`，示例取 P10 执行时的 `v0.5.2` 活值。P10 后续被并发流程推进到 `v0.5.3`，工具按执行时活值取号的行为正确，不能把旧示例误当成硬编码版本。
2. **PF-B7 增补 build-record 清理例外**，明确四个定义点：
   - 保留节是记录版本等于 `paper.yaml#paper_version` 的节，即当前版本的手写 `R<N>` 节和全部 `PKG-<version>` 节；保留节号不重排，文件头保留；
   - “manifest.json + build-record.md 两份凭证缺一不可”约束**当前版本**，清理历史节不等于允许删除当前构建记录；
   - 仅在用户显式指令下清理，每篇论文仓各做一次提交，提交信息载明用户指令、清理节范围和保留节；
   - 引证 build-record 节号或行号的 provenance 锚点，清理后在工作树中会失效，仅存于 git 历史；清理提交必须钉住清理前 commit，保证旧锚点可解析。
3. **PF-B16 骨架同步**：docx/PDF 骨架名均补 `-v{版本号}`；无 remote 的 zip 兜底名同步，仓库名主 zip、双通道交付、zip 不进入 release manifest `artifacts`、`build zip` 不重复 strict 校验等边界不变。
4. 当前 PF-B7 的转义字符表和 P10 示例引号仍与代码实算不一致，详见 §6.4；这两项是验证曾抓出、但记录落笔时尚未在工作树落实的 P2 修订。

### 3.4 `project.yaml`

仅 `:3` 的 `rules_version: 0.4.0` 改为 `0.4.1`。

### 3.5 `governance/rule-index.yaml`

仅 `:2` 的 `rules_version: 0.4.0` 改为 `0.4.1`。索引结构和规则清单不变。

### 3.6 `templates/paper/paper.yaml`

仅 `:17` 的 `rules_version: 0.4.0` 改为 `0.4.1`。本文件不改 budget：intake 阶段 `confirmed: false` 或 `null` 按条件 schema 合法，不能把 staged 论文的预算确认要求误套到模板。

### 3.7 `governance/changes/2026-11-17-build-artifact-version-suffix.md`

新建本记录。论文侧 budget 修复、产物重建、build-record 清理和 eml 重生成均不列入上述治理仓 6 文件 diff。

## 4. 理由（Rationale）

1. **版本号必须随单个产物走**：`build/<version>/` 在仓内可以区分版本，但 docx/PDF 作为附件、下载文件或送审材料离开目录后，目录信息随即丢失。把版本写进 stem，比依赖交付人员另附说明更可靠。
2. **build 与 package 仍只留一个计算入口**：两处补传同一个 `version`，避免一个路径带后缀、另一个路径仍按旧名寻找产物，也继续接受既有 POSIX 转义和同 build manifest 核对。
3. **zip 主名无需重复加版本**：`<repo-name>-<paper_version>.zip` 已满足识别和双通道交付要求。本次“加后缀”的实质缺口是 docx/PDF 和无 remote 的 PF-B7 兜底名，不应扩大为所有 zip 一律改名。
4. **清理是显式授权下的例外，不改变默认追加语义**：条款只处理本次用户指令，不把“只留当前”变成以后每次构建的自动行为。保留当前版本节和文件头，既满足精简要求，也保住当前发布的可复现说明。
5. **当前版本与历史版本的凭证义务要分开**：“两份凭证缺一不可”若被解释成每个历史节都永远不得清理，就与用户指令冲突；若解释成清理后可以连当前记录也删掉，又会破坏发布审计。将约束明确落在当前版本，边界最清楚。
6. **旧锚点要靠 commit 固定，不能假装行号仍有效**：build-record 行号必然随清理变化。清理提交记录清理前 commit，旧引证至少还能在确定历史中复核；后续再把长期锚点改为 commit-pinned 形式。
7. **治理升版与论文侧声明铺开分开**：本次改变 PF-B7/PF-B16 的对外产物契约，治理五处同步升至 0.4.1；论文仓若只改 `rules_version` 而不按新工具重建，声明与产物不符，因此继续暂缓逐篇铺开。

## 5. 备选方案（被拒）

| 方案 | 否准 |
|---|---|
| 只手工给现有 docx/PDF 改名 | 下次 build/package 会恢复旧名，远程 CI 和后续版本仍漂移，不能替代工具与规则修订 |
| 只改 build，不改 package，或两处分别拼接版本 | package 会按旧 stem 查找并破坏同 build 核对；分别拼接还会产生两套命名规则 |
| 给 `<repo-name>-<paper_version>.zip` 再追加一次版本 | 主名已有版本，重复后缀没有新增信息，还会改变既有本地/远程交付名 |
| 无 remote 时继续沿用无版本兜底名 | 与 release/package 新名不一致，裸源码树交付时再次丢失版本信息 |
| 每次构建自动清空 build-record，或按修改时间猜“最新节” | 默认追加是既有审计规则；保留范围必须由 `paper.yaml#paper_version` 决定，并由用户显式授权，不能靠时间或目录顺序猜测 |
| 清理后重排 R/PKG 节号，或删除当前版本旧节只留新 PKG 节 | 重排会进一步破坏引证；当前版本的手写 R 节与 PKG 节共同构成记录，不能只留下最后一段 |
| 只改 `paper.py` 两个调用点，不同步 scratch 清理助手 | 助手调用旧两参形式会直接 `TypeError`，使重建后的历史目录清理中断 |
| 本变更顺带把十篇论文 `rules_version` 全改为 0.4.1 | 未重建篇目会账实不符；必须按重建结果逐篇同步，不能批量回填声明 |

## 6. 验证（2026-11-17 实测）

### 6.1 独立验证与返工处置

验证由未参与实施的独立审查执行，主会话负责修复和复跑。本记录另做了只读 diff、语法和十篇 stem 复核。

| 轮次 | 结论与发现 | 处置与当前状态 |
|---|---|---|
| 首轮 | **有条件通过**：C1 补列六处引述点；C2 scratch 清理助手同步签名；C3 示例使用版本活值；C4 build-record 清理补齐四个定义点 | 四项均进入实施；清理助手第三参已同步为 `keep`，仓内两调用点也已同步 |
| 第二轮 | 主体验证通过；另抓出 **1 个 P1**：无第一作者守卫误缩进为死代码，可产出 `None-《…》.docx`；**2 个 P2**：PF-B7 转义表引号不符、P10 示例标题引号误用 | P1 已修复并复跑确认；主会话交接称两个 P2 亦已修复，但本记录落笔时仍能复现，故按 §6.4 重新打开，不登记为关闭 |
| 记录复核 | 6 文件 diff 30/29；`git diff --check` 无输出；两个 Python 文件只读 `compile()` 均通过；十篇 stem 可实算 | 实现统计和主体功能与交接一致；另发现 `_release_file_stem` docstring 书名号/花括号错位，列入同一轮文案收尾 |

本轮 P1 说明验证门禁有实际价值：纯文案修订也可能改变缩进和控制流。不能以“只改提示语”为由跳过无作者夹具和 P9 冒烟。

### 6.2 冒烟、打包、错误路径与清理干跑

独立验证的已执行项目如下：

- P9 依次执行 `build pdf → build snapshot → package → package --verify-only --strict → build zip`，五步均 exit 0。
- P9 新名 docx 的 sha256 前 16 位为 `6ac1d9e396003152`，与改名前一致，证明该次命名重建对 docx 内容中性。
- 本地 wrapper 与直接 pack 两条通道生成的 zip 逐字节一致；确定性打包行为未受兜底名调整影响。
- pack 错误路径 exit 3/2 均实测：package 缺失或为空为 3，用法、IO 或元数据错误为 2；成功为 0。
- 无第一作者夹具在 P1 修复后返回 exit 2，不再产生 `None-《…》.docx`；P9 冒烟和 `compile` 复跑通过。
- 已发布版本守卫与同 build 混装防线均做回归，未因 stem 增加版本参数而绕过 manifest 核对。
- build-record 清理干跑符合“保留文件头 + 追加当前 PKG 节”的时序：先清理历史节，再由重建追加当前记录；失败篇按 runbook 还原，不把失败构建写成有效当前记录。

### 6.3 十篇真实 stem 复算

本记录使用当前 `_release_file_stem` 逐篇读取 `paper.yaml` 和第一作者实算。下表字符数为 Python 字符数，字节数为 **stem 的 UTF-8 字节数，不含扩展名**；P10 是写记录时的活值。

| 论文 | 当前版本 | 新 stem | 字符数 | 字节数 |
|---|---|---|---:|---:|
| P1 | v0.4.21 | `杨森-《基于多模型集合关系辩论的自然资源多模态资料质量评估与矛盾检出》-v0.4.21` | 43 | 111 |
| P2 | v0.4.26 | `刘馨-《公共部门知识资产分层治理：机制与实证》-v0.4.26` | 31 | 75 |
| P3 | v0.3.28 | `李丽英-《面向自然资源全生命周期的时空大数据治理平台设计与实现》-v0.3.28` | 40 | 102 |
| P4 | v0.3.18 | `杨森-《面向自然资源文献的条件完整性约束检索方法》-v0.3.18` | 33 | 81 |
| P5 | v0.4.22 | `刘馨-《面向审计整改的全链路证据知识库构建方法》-v0.4.22` | 32 | 78 |
| P6 | v0.2.22 | `杨森-《面向自然资源规范文献的沿革条款对齐方法》-v0.2.22` | 32 | 78 |
| P7 | v0.2.22 | `杨森-《面向可信智能检索的知识库治理体系设计》-v0.2.22` | 31 | 75 |
| P8 | v0.1.14 | `刘英豪-《自然资源时空数据的实时采集与版本追溯》-v0.1.14` | 32 | 78 |
| P9 | v0.1.11 | `伍红玲-《大数据驱动的人地协同感知：移动信令数据赋能生态保护红线动态监管的技术路径与约束》-v0.1.11` | 53 | 141 |
| P10 | v0.5.3 | `伍红玲-《自然资源“一张图”多源时空数据治理与语义对齐》-v0.5.3` | 35 | 89 |

十项均为 `{作者}-《{标题}》-v{版本}`，无首尾下划线，未超过 255 字节。P9 最长，为 53 字符、141 字节。P10 从验证示例时的 v0.5.2 推进到 v0.5.3，当前工具输出随活值变化；全角弯引号 `“”` 按代码规则保留。

### 6.4 记录落笔时发现尚未落实的文案修订

以下不是对历史验证结论的改写，而是对**当前工作树**的直接复核结果：

1. **P2-1 仍未关闭**：`governance/build.md:54` 的 POSIX 特殊字符表写成 `/ \ : * ? “ < > |`，但 `tools/paper.py:2350` 实际正则包含 ASCII 直引号 `"`，不包含全角弯引号 `“`。规则文本必须恢复 ASCII `"`，否则会把代码明确保留的弯引号误写成需要转义。
2. **P2-2 仍未关闭**：`governance/build.md:55` 示例写成 `自然资源”一张图”…`，起始引号误用右弯引号；工具实算为 `自然资源“一张图”…`。示例应与真实输出逐字一致。
3. **P3 文案错位**：`tools/paper.py:2375` docstring 当前为 `{第一作者中文名}-《{中文标题》-v{版本号}`，`中文标题` 的右花括号和右书名号位置错误；正确形态应为 `{第一作者中文名}-《{中文标题}》-v{版本号}`。它不影响运行，但与本变更要说明的接口形态不符。

P2 按门禁规则默认应在治理提交前修复并复跑相关文本核对；P3 可随同一小批修订收尾。本记录只登记事实，不代改实现文件。

### 6.5 论文侧执行状态（PF-V5，与本治理提交分离）

- budget 合规修复已提交 6 篇，commit subject 和 hash 已核对：P1 `c28e5b1`、P2 `458eb65`、P3 `37316f4`、P4 `11f20a9`、P6 `14782d9`、P7 `4c1fd9b`。修复内容为 `confirmed: true` 与标准 limits 文本，validate 均通过。
- 第七篇 P8 暂缓：并发会话正在调整作者阵容，新增杨礼飞且 bio 待补；其 budget 修复和重建随该作者轮次处理，不在半成品元数据上强行重建。
- 十篇重建和 build-record 清理按 `/home/yangsen/workspaces/PaperWorkflows/.review_scratch/gc-1117-07-rebuild-runbook.md` 执行中。该 runbook 要求逐篇预检、五步重建、清理后只提交 `build-record.md`，不得裹挟正文或配置的在途修改。
- P10 投稿邮件 eml 仍须按新附件名重生成：带版本后缀的 docx/PDF 加仓库名 zip，共 3 个附件；不能继续发送内嵌旧名的邮件。

## 7. 风险与处置

| # | 风险 | 处置 |
|---|---|---|
| R1 | `_release_file_stem` 增加必填参数，漏改任一调用点即 `TypeError` | 仓内 build/package 两处与 `.review_scratch/gc-1117-04-prune.py` 同批修改；十篇 stem 实算和清理干跑覆盖调用形式 |
| R2 | 修改守卫文案时误缩进，fail-closed 退化为 fail-open | 本轮 P1 已实际发生并被独立验证抓住；修复后复跑语法检查、P9 五步冒烟和无第一作者夹具，确认 exit 2，后续同类修订必须保留该夹具 |
| R3 | build-record 清理误删当前凭证，或旧锚点断链后无法追溯 | 条款把双凭证义务限定到当前版本，保留当前 R/PKG 节；P1 L2481–2482 被 `stie.yaml:160`、`schema:647` 引证，P5 R10 被 `metalayout.py:608`、`authors.yaml:17` 引证，清理提交必须钉住清理前 commit，后续再固化长期锚点 |
| R4 | 论文侧只升 `rules_version` 而未按新规则重建 | 当前实测仍为 0.3.3×9、0.3.6×1，治理仓为 0.4.1；承接 `e95881f` 的裁定继续暂缓，逐篇重建后再同步声明，避免账实不符 |
| R5 | P4/P7/P8/P9/P10 存在并发内容或元数据轮次，重建可能混入进行中的修改 | 编队按“内容静默性”预检逐篇裁定，活跃篇跳过；被跳篇目在其自身会话后续重建时，因使用同一工具链会自动获得版本后缀，不在本轮抢写 |
| R6 | §6.4 文案仍未落实，若直接提交会让规则示例与工具行为不一致 | 两个 P2 在提交前修复并复核；docstring P3 同批校正。功能验证通过不能替代对最终 diff 的文本核对 |

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
git checkout HEAD^ -- project.yaml
git checkout HEAD^ -- governance/rule-index.yaml
git checkout HEAD^ -- templates/paper/paper.yaml
```

本记录随 revert 一并移除。若在当前尚未提交状态撤回，应对当前 HEAD `05f0f7c` 逐文件执行 `git checkout HEAD -- <file>`，再删除本新记录；不要把提交后的 `HEAD^` 用法误用于提交前。

### 8.2 论文仓

每篇 build-record 清理提交信息都必须记录清理前 commit。需要恢复该篇完整历史记录时，在对应论文仓执行：

```bash
git checkout <清理前 commit> -- build-record.md
```

该操作只恢复记录文件，不会恢复被 `.gitignore` 排除的旧构建产物，也不代替产物层备份恢复。禁止 `git reset --hard`、其他 `--hard` 操作和任何历史改写；不得为恢复一篇而清除其他篇目或并发会话的在途工作（F7）。

## 9. 开放项

1. **论文侧 rules_version 铺开**：当前仍为 0.3.3×9、0.3.6×1；须按 R4 在逐篇重建后单独同步，不能回填成本次治理提交内容。
2. **P8 budget 合规与重建**：等待并发会话的作者阵容和 bio 落定，再完成元数据校验、budget 修复及版本后缀重建。
3. **build-record 清理后的锚点固化**：相关 profile、schema 和引用文件仍有并发修改；待其提交后，把 stie.yaml/schema 等行号或节号引证改为 commit-pinned 形式。
4. **被跳篇目的版本后缀重建收尾**：P4/P7/P8/P9/P10 中本轮未重建者，在各自内容静默后按同一五步流程重建，并更新当前 build-record；P10 同时重生成 3 附件 eml。
5. **最终 diff 文案收尾**：关闭 §6.4 的两个 P2 和一个 P3，再复核 PF-B7 字符表、P10 示例及 `_release_file_stem` docstring；此项是当前工作树的实测待办，不得写成已在第二轮验证关闭。

---

*GC-2026-1117-07。规则依据：AGENTS.md F9/F6/F7；构建依据 governance/build.md PF-B5/PF-B7/PF-B16；版本依据 governance/versions.md PF-V3/PF-V5；治理规则版本 0.4.0 → 0.4.1。主体功能验证通过，最终提交前仍须完成 §6.4 文案核对。*
