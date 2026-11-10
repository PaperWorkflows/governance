# PaperFactory 本地文件骨架规划

## 1. 仓库拓扑

```
PaperWorkflows/                        ← GitHub org
├── instruction.git/                    ← public, 治理仓库（canonical AGENTS.md）
│   ├── AGENTS.md                       ← 总原则 F1–F9（canonical）
│   ├── CLAUDE.md                       ← 入口指针
│   ├── project.yaml                    ← 项目配置、能力状态、模式声明
│   ├── README.md                       ← 项目说明
│   ├── .gitignore                      ← 忽略 papers/ temp/
│   ├── governance/                     ← 模式规则文件
│   │   ├── rule-index.yaml             ← 规则索引（唯一真源）
│   │   ├── proposal.md                 ← PF-P1~P8 开题规则
│   │   ├── research.md                 ← PF-R1~R8 科研规则
│   │   ├── writing.md                  ← PF-W1~W10 编写规则
│   │   ├── build.md                    ← PF-B1~B10 构建规则
│   │   ├── review.md                   ← PF-RV1~RV6 审核规则
│   │   └── versions.md                 ← PF-V1~V10 版本与提交规则
│   ├── schemas/                        ← JSON Schema
│   │   ├── paper.schema.json           ← paper.yaml 结构校验
│   │   └── author.schema.json          ← 作者注册表条目校验
│   ├── templates/paper/                ← 论文工作区模板（31 文件）
│   │   ├── AGENTS.md                   ← Governance pointer 模板
│   │   ├── paper.yaml                  ← 论文元数据模板
│   │   ├── abstract.md                 ← 中英双语摘要模板
│   │   ├── outline.md                  ← 大纲模板
│   │   ├── research-plan.md            ← 研究方案模板
│   │   ├── terms.md                    ← 术语表模板
│   │   ├── verification.yaml           ← 文献三维核验记录模板
│   │   ├── references.bib              ← 参考文献模板
│   │   ├── README.md                   ← 论文工作区说明
│   │   ├── body/                       ← 正文（按一级章节拆分）
│   │   │   ├── README.md
│   │   │   ├── 01-introduction.md
│   │   │   ├── 02-background.md
│   │   │   ├── 03-method.md
│   │   │   ├── 04-experiment.md
│   │   │   ├── 05-results.md
│   │   │   ├── 06-discussion.md
│   │   │   └── 07-conclusion.md
│   │   ├── figures/                    ← 图目录
│   │   │   ├── .gitkeep
│   │   │   └── index.yaml              ← 图清单
│   │   ├── tables/                     ← 表目录
│   │   │   ├── .gitkeep
│   │   │   └── index.yaml              ← 表清单
│   │   ├── experiments/                ← 实验数据与代码
│   │   │   ├── data/.gitkeep           ← 原始数据（只读）
│   │   │   ├── code/.gitkeep           ← 可运行代码
│   │   │   ├── logs/.gitkeep           ← 运行日志
│   │   │   └── record.yaml             ← 实验记录
│   │   ├── appendix/                   ← 附录材料
│   │   │   ├── .gitkeep
│   │   │   └── README.md
│   │   └── build/                      ← 构建配置
│   │       └── layout.yaml             ← 论文级版式覆盖
│   ├── tools/
│   │   └── paper.py                    ← CLI：scaffold / check / version-bump
│   └── authors/
│       └── registry.yaml               ← 作者注册表
│
└── papers/                              ← 论文工作区挂载点（.gitignore）
    ├── P1-EXAMPLE-20251110/             ← 独立 git 仓库，独立 remote
    └── P2-ZHANGSAN-20251201/            ← 同上
```

---

## 2. 论文工作区完整骨架

```
P{N}-{AUTHOR_EN}-{YYYYMMDD}/                ← 论文工作区根目录（独立 git 仓库）
├── .git/                                 ← 独立 git 仓库
├── .gitignore                            ← 忽略 temp/ .venv/ __pycache__/
├── AGENTS.md                             ← 【骨架】Governance pointer → instruction/AGENTS.md
├── paper.yaml                            ← 【骨架】论文元数据（唯一权威源）
├── README.md                             ← 工作区说明（临时材料位置、阶段、版本策略）
├── authors.yaml                          ← 【骨架成员】作者信息（私有仓库，可放敏感信息）
├── funding.yaml                          ← 【骨架成员】基金项目信息（可选）
├── writing-spec.yaml                     ← 【骨架成员】编写规范（必选文件，内容可选）
├── abstract.md                           ← 中英双语摘要
├── outline.md                            ← 大纲（章节树 + 要点 + 字数预估）
├── research-plan.md                      ← 研究方案（假设、指标、基线、预算、失败判据）
├── terms.md                              ← 术语表（缩写、符号、英译）
├── verification.yaml                     ← 文献三维核验记录（真实性/访问范围/支持度）
├── references.bib                        ← 参考文献（BibTeX）
├── body/                                 ← 正文（按一级章节拆分，主源合并为 paper.md）
│   ├── README.md
│   ├── 01-introduction.md
│   ├── 02-background.md
│   ├── 03-method.md
│   ├── 04-experiment.md
│   ├── 05-results.md
│   ├── 06-discussion.md
│   └── 07-conclusion.md
├── figures/                              ← 图文件
│   ├── .gitkeep
│   └── index.yaml                        ← 图清单（编号、文件名、来源、生成脚本、题注）
├── tables/                               ← 表文件
│   ├── .gitkeep
│   └── index.yaml                        ← 表清单
├── experiments/                          ← 实验数据、代码、日志
│   ├── data/                             ← 原始数据（只读，不原地清洗）
│   │   └── .gitkeep
│   ├── code/                             ← 可运行代码
│   │   └── .gitkeep
│   ├── logs/                             ← 运行日志（时间戳、参数、退出码）
│   │   └── .gitkeep
│   └── record.yaml                       ← 实验记录（环境、命令、参数、产物摘要）
├── appendix/                             ← 附录材料
│   ├── .gitkeep
│   └── README.md
└── build/                                ← 构建配置
    └── layout.yaml                       ← 论文级版式覆盖（合并到全局 profile）
```

**骨架成员（Skeleton Members）**：`paper.yaml`, `authors.yaml`, `funding.yaml`, `writing-spec.yaml`, `abstract.md`, `outline.md`, `research-plan.md`, `terms.md`, `verification.yaml`, `references.bib`, `body/`, `figures/`, `tables/`, `experiments/`, `appendix/`, `build/`, `materials.yaml` — 共 17 类，构成每篇论文的最小完整工作区。

---

## 3. 文件用途与治理规则映射

### 3.1 元数据层

| 文件 | 用途 | 对应规则 |
|---|---|---|
| `paper.yaml` | 论文身份、标题、作者、版本、阶段、适用规则集合、预算、未决项 | PF-P3, PF-V2, PF-W2 |
| `README.md` | 工作区说明、权威源声明、临时材料位置、Git 策略 | PF-P5, PF-V7 |

### 3.2 正文层

| 文件 | 用途 | 对应规则 |
|---|---|---|
| `abstract.md` | 中英双语摘要（自足：目的、方法、结果、结论边界） | PF-W2 |
| `outline.md` | 大纲（章节树、每节要点、预估字数、证据来源） | PF-P6 |
| `body/*.md` | 正文按一级章节拆分，主源合并为 `paper.md` | PF-W9, PF-B2 |
| `terms.md` | 术语表（缩写、符号、英译、首次出现定义） | PF-W8 |

### 3.3 文献层

| 文件 | 用途 | 对应规则 |
|---|---|---|
| `references.bib` | BibTeX 参考文献（只填核验条目） | PF-W6 |
| `verification.yaml` | 每条文献的三维核验记录（真实性/访问范围/支持度） | PF-W6 |

### 3.4 实验层

| 文件 | 用途 | 对应规则 |
|---|---|---|
| `experiments/data/` | 原始数据（只读，原地清洗禁止） | PF-R2, PF-R5 |
| `experiments/code/` | 可运行代码（记录版本、依赖、运行命令） | PF-R6 |
| `experiments/logs/` | 运行日志（时间戳、参数、退出码） | PF-R7 |
| `experiments/record.yaml` | 实验记录（环境、命令、参数、输入输出、校验值、状态） | PF-R2, PF-R7, PF-R8 |

### 3.5 图表层

| 文件 | 用途 | 对应规则 |
|---|---|---|
| `figures/index.yaml` | 图清单（编号、文件名、来源类型、生成脚本、题注） | PF-W8, PF-B6 |
| `figures/*.png/svg/pdf` | 图文件 | PF-W8 |
| `tables/index.yaml` | 表清单 | PF-W8 |

### 3.6 构建层

| 文件 | 用途 | 对应规则 |
|---|---|---|
| `build/layout.yaml` | 论文级版式覆盖（合并到 L0→L1→L2） | PF-B3, PF-B10 |

### 3.7 附录层

| 文件 | 用途 | 对应规则 |
|---|---|---|
| `appendix/` | 补充材料（代码、数据、推导、审稿回复等） | PF-P8 |

---

## 4. 命名规范

| 概念 | 格式 | 示例 |
|---|---|---|
| 论文编号 | `P` + 正整数 | `P1`, `P2`, ... `P999` |
| 论文仓库名 | `P{N}-{AUTHOR_EN}-{YYYYMMDD}` | `P1-EXAMPLE-20251110` |
| 本地工作区目录 | `papers/P{N}-{AUTHOR_EN}-{YYYYMMDD}/` | `papers/P1-EXAMPLE-20251110/` |
| 正文章节文件 | `{NN}-{slug}.md` | `01-introduction.md` |
| 图文件 | `fig{N}-{slug}.{png\|svg\|pdf}` | `fig1-handshake-flow.svg` |
| 表文件 | `table{N}-{slug}.{csv\|tsv}` | `table1-matrix-results.csv` |
| 实验记录 | `experiments/record.yaml` | 固定路径 |
| 临时目录 | `temp/P{N}-{AUTHOR_EN}-{YYYYMMDD}/TASK-{NNNN}/` | `temp/P1-EXAMPLE-20251110/TASK-0001/` |

**注意**：
- 仓库名中的 AUTHOR 为第一作者拼音大写（如 `EXAMPLE`）
- 日期为论文立项/创建日期（`YYYYMMDD`）
- 题名变更不影响仓库名（仓库名只含编号+作者+日期，题名在 `paper.yaml.title` 中）

---

## 5. 作者信息结构

`authors.yaml`（每篇论文私有仓库）：

```yaml
authors:
  - name: 作者A                      # 中文名
    name_en: Author A              # 英文名
    pinyin: EXAMPLE                # 拼音（大写，用于仓库命名）
    affiliations:
      - 某某大学计算机学院            # 单位
    email: null                    # 隐私保护，null 表示不公开
    orcid: null                    # 无 ORCID 时 null
    roles:
      - first                      # first / second / corresponding / other
```

`paper.yaml` 中引用：

```yaml
authors:
  - name: 作者A
    affiliations:
      - 某某大学计算机学院
    roles:
      - first
    email: null
```

---

## 6. 版本号管理

| 版本 | 含义 | 示例 |
|---|---|---|
| `0.1.0` | 初稿 | 刚 scaffold 完成 |
| `0.x.0` | 研究期 minor（核心框架成立，新增内容） | 增加实验数据 |
| `1.0.0` | 首份通过全部验收的成稿 | 写完 + 审核通过 + 构建通过 |
| `x.0.0` | major（研究问题/核心方法/核心结论实质改变） | 重做实验推翻结论 |
| `x.x.1` | patch（措辞、排版、不影响结论的纠错） | 修正错别字、图表 |

- changelog 通过 commit message 体现
- 升级高位后低位归零
- `paper_version` 在 `paper.yaml` 中维护，独立于 `rules_version`

---

## 7. Git 策略

### 7.1 治理仓库（`PaperWorkflows/governance`）

- 单一仓库，包含所有治理文件
- 提交分区：纯治理（规范、模板、Schema、工具）或纯某篇论文（迁移记录）
- 禁止混入论文正式内容
- `papers/` 和 `temp/` 在 `.gitignore` 中

### 7.2 论文仓库（`PaperWorkflows/P{N}-{AUTHOR_EN}-{YYYYMMDD}`）

- 每篇论文独立仓库
- 各自拥有独立的 GitHub remote（private）
- 提交分区：恰一个论文工作区的内容
- 禁止混入治理文件或其他论文内容
- 本地 git identity：`janssenkm <janssenkm@users.noreply.github.com>`
- Git identity ≠ 论文作者身份

---

## 8. 临时材料策略

- 论文临时材料、构建中间文件、缓存、临时配置统一在：
  ```
  temp/P{N}-{AUTHOR_EN}-{YYYYMMDD}/TASK-{NNNN}/
  ```
- 治理合成测试使用：`temp/P9999/TASK-{NNNN}/`
- 临时目录 `gitignore`，不提交
- 正式证据归档后，临时材料按授权清理

---

## 9. 当前实现状态

| 能力 | 状态 | 说明 |
|---|---|---|
| 治理文件 | ✅ 已实现 | 6 个规则文件 + rule-index.yaml |
| Schema | ✅ 已实现 | paper.schema.json + author.schema.json |
| 模板骨架 | ✅ 已实现 | 28 文件，覆盖完整论文工作区 |
| scaffold 工具 | ✅ 已实现 | 创建论文工作区、git init、设置 remote |
| check 工具 | ✅ 已实现 | 校验 paper.yaml、必需路径、git 仓库 |
| version-bump 工具 | ✅ 已实现 | major/minor/patch 自动升级 |
| 构建管道（docx/PDF） | ✅ 已实现 | P1/P2/P3 全流水线执行验证：三篇论文均完成 REL-0001 docx+pdf 构建（P3 另有 REL-0002 视觉修复重建），paper_version 0.3.1，产物在各自 output/REL-*（GC-2026-1111-01，2026-11-11；注：paper.py build 子命令与 PF-B9 过滤器仍未落地，见治理变更记录开放项） |
| 审核派发 | ✅ 已实现 | P1/P2/P3 四视角审核（R-A/R-B/R-C/R-D）+ PF-RV6 修复闭环执行验证：证据在各论文 reviews/20261111-round2/（closure.md 含 transferred-to-governance 清单）（GC-2026-1111-01，2026-11-11） |
| MCP/Skill 配置 | 🔴 未实现 | 待 Phase 2 |
| 论文仓库 .gitignore | 🟡 部分实现 | 模板中未包含，需补充 |
| 冗余 references/ 子目录 | 🟡 待决策 | 模板中有根 `references.bib` 和 `references/references.bib`，保留还是删除？ |

---

## 10. 待决策事项

1. **论文仓库 `.gitignore` 模板**：是否将 `temp/`、`.venv/`、`__pycache__/`、`.DS_Store` 加入模板？
2. **`references/` 子目录**：模板中同时存在根 `references.bib` 和 `references/references.bib`，是否删除子目录？
3. **正文章节数**：当前模板固定 7 章（01–07），是否允许论文自定义章节数？如何配置？
4. **正文主源**：是否在构建时合并 `body/*.md` 为 `paper.md`，还是直接以 `body/` 目录为输入？
5. **Phase 2 优先级**：构建管道 vs 审核派发 vs MCP/Skill，哪个先做？
