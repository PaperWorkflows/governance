# Build Mode Rules

## Scope

This file defines the build mode execution rules. Build mode covers: typesetting configuration, docx and PDF production, figure embedding, and build validation.

## Rules

### PF-B1 稿件类别

- Distinguish: research draft, submission draft, published archive.
- Research draft: internal evidence and content review complete.
- Submission draft: also satisfies target venue template, anonymization, and material requirements.
- Archive draft: preserves verifiable publication info and version relationships.

### PF-B2 单一正文

- `body/paper.md` is the single authoritative source for paper text. Parallel maintenance of multiple manual final drafts is forbidden.
- Complete build inputs: `paper.yaml`, references, figures, layout config, necessary filters, and fixed toolchain.
- Title and confirmed authorship come from config. Conflicts stop build or release.

### PF-B3 版式配置

- Default draft profile: A4, 25.4mm margins, 12pt body, 1.5x line spacing (overridable).
- Layout profile has three layers: L0 project draft, L1 venue profile, L2 paper overrides. Merge order: L0 → L1 → L2.
- Structure-identity keys (`page`, `citation`, `formulas`, `target_venue`) cannot be overridden by paper config. Changes require profile versioning.
- `profile` and `kind` are **selection keys**, not structure-identity keys: L2 uses them to name the L1 profile it builds against, and they are legal in L2 (see PF-B13).
- Each profile layer validates against `schemas/layout-profile.schema.json` (additionalProperties: false). Unknown keys fail build.

### PF-B4 固定输入快照

- Build reads fixed read-only input snapshot covering: body, config, references, figures, valid code or result dependencies, templates, toolchain, environment notes. Include file manifest and checksums.
- Snapshot must not change with workspace edits. Review and release bind to same snapshot. Content fixes generate new snapshot.

### PF-B5 暂存构建

- Build intermediate files go to `temp/P<ID>-<DATE>-<TITLE>-<AUTHOR>/TASK-<NNNN>/`.
- Failed build artifacts stay in temp task directory marked invalid. Do not enter current release.
- Record: input, command, tool parameters, version, logs, check conclusions, and artifact checksums.
- Confirm docx and PDF come from same build. Conversion failure, missing files, or incomplete checks cannot be补齐ed with old PDF or old reports.

### PF-B6 图表验收

- Check both source structure and actual docx/PDF rendering.
- Structure check: front matter, cross-references, references, figures, tables, formulas, footnotes, necessary metadata.
- Scientific figures: verify data, script, body values. Image figures: check legend, units, arrows, fonts, grayscale, overlap, cropping.
- PDF: page-by-page visual check of key formulas, wide tables, figures, references, and anomalous pages.
- Check consistency between docx and PDF in title, authorship, body, numbers, citations, figures, formulas.
- Figure issues require second-executor or source confirmation before modification.

### PF-B7 版本发布

- Target directory: `build/<version>/`, where `<version>` is the paper's SemVer version (e.g., `v1.0.0`).
- Filenames use the paper's Chinese full title with POSIX-safe escaping: spaces and special characters (`/ \ : * ? " < > |`) replaced with `_`; Chinese characters preserved as UTF-8.
  Example: `基于辩论的可解释AI验证框架研究.pdf`, `基于辩论的可解释AI验证框架研究.docx`.
- Published versions cannot be modified in place. Old versions preserved.
- Manifest records: paper identity, paper_version, manuscript_kind, title and authorship config, input snapshot, rules_version, toolchain version, environment, both artifact checksums, review and re-verification relationships, open limitations, timestamp.
- After all checks complete, atomically switch `build/current.json` within publish lock. Read first parses manifest, then reads referenced full version.
- **产物本体不入版本库**：`build/`、`temp/`、`output/` 由论文仓 `.gitignore` 排除，docx/PDF/manifest 留在本地工作区，**不得 `git add -f`** 强行入库。
- **入库的凭据有两份，缺一不可**：机器可读的 `build/<version>/manifest.json`（输入快照、profile 与 reference docx 的 sha256、规则版本、产物 sha256、页数）与**人可读的 `build-record.md`**（每次构建的可复现步骤、产物校验、版式决策与取舍登记、已发现但未修的问题）。前者说明"是什么"，后者说明"为什么"。
- 论文仓根目录必须存在 `build-record.md`（脚手架随模板创建）；每次构建**追加**一节，不改写既有节，与"已发布版本不得就地修改"一致。

### PF-B8 本地交付

- Delivery subagent verifies: paper workspace git repo integrity, local identity, no nested .git, no remote configured, no push.
- Publishing record traces: source version, snapshot, review, dependencies, artifacts, large files, restricted data, external environment, backup location.
- Main session only receives and checks deliverables for completeness; does not build, release, commit, or sign off on papers.

### PF-B9 渲染指令过滤

- Writing-period instructions use `::: render-*` container blocks: `render-note` for human-readable guidance, `render-spec` for machine-readable payload (single JSON object per block).
- Instruction filtering must execute before all writers. Missing or failed filter loading is a build failure.
- Unclosed instruction blocks, blocks containing prose sentences (complete sentences ending with period or overly long paragraphs), or payload parse failure = build failure.
- Build must report: V1 docx has no residue, V2 PDF has no residue, V3 structure equivalence, V4 count self-consistency, V5 bilateral independence, V6 failure semantics.

### PF-B10 版式 Profile 分层

- Three-layer structure: L0 project draft profile, L1 venue profile (registered in templates/layout/registry.yaml), L2 paper overrides.
- Merge order L0 → L1 → L2, key-by-key override. Each overridden key must appear in build log with old/new/source-layer.
- L2 boundary: besides the selection keys `profile`/`kind`, L2 may only carry `typography` (PF-B13). Any other domain key in L2 fails the build.
- Semantic conflicts (incompatible units or semantics for same key) fail build after profile Schema reconciliation attempt.
- `paper.yaml` semantic keys (`language`, `bilingual_abstract`, `full_english_body`) must not conflict with global profile.

### PF-B11 版式实现载体

- A layout profile is a declaration; it becomes binding only through a generated **reference docx** consumed by the build (`pandoc --reference-doc`).
- The reference docx is **generated from the profile** by `tools/make_refdoc.py` (single source of truth). Hand-editing files under `templates/layout/refdoc/` is forbidden; profile change ⇒ regenerate ⇒ review the diff.
- Registry entries carry the reference docx path. A missing reference docx **fails the build**; silent fallback to the pandoc default reference doc is forbidden (it silently drops page size, margins, line spacing and CJK font — verified on 2026-11-11 against the v0.3.1 artifacts).
- The refdoc generator writes OOXML directly with the **standard library only** — `python-docx`/`lxml` live in user site-packages and are unavailable under `python3 -I`, so they must not be relied upon. The toolchain's declared third-party dependencies are `yaml` and `jsonschema` (both in `/usr/lib/python3/dist-packages`).
- **The build verifies that the checked-in reference docx still matches its profile**: it regenerates the refdoc and compares byte for byte. A stale or hand-edited refdoc **fails the build** — otherwise the "generated from the profile" promise would be unenforced.
- Reference docx generation must be **deterministic** (fixed zip timestamps and core.xml dates) so that regeneration is byte-comparable and a profile change is visible as a diff.
- Role weight and abstract-label alignment are **profile keys** (GC-2026-1112-01): `typography.heading_bold`, `typography.caption_bold`, `typography.abstract_label_alignment`. Rationale: 黑体（heiti）faces carry their own weight, so headings and captions in a heiti face are **not bolded** (no faux-bold), and the 摘要/Abstract/关键词/Keywords labels are **left-aligned**. An absent key keeps the generator's pre-GC-2026-1112-01 default (bold on, label centered) so older profiles still validate.

### PF-B12 版式落地校验

- After building, the produced docx is re-parsed and asserted against the merged profile: page size, margins, body font family (Latin and CJK), body size, line spacing, first-line indent, heading sizes, table rule style, page-number field, header/footer part well-formedness, and absence of the pandoc default blue heading colour.
- Any failed assertion **fails the build**. The manifest records the assertion notes and any declared limitation (e.g. formulas not carried as editable equation objects, or a profile role whose paragraph style the produced document never uses).
- Assertions must cover the **regression** case as well: a build that loses page size, margins, line spacing or CJK font relative to the profile is a failure even when the file opens correctly. `tools/verify_layout.py` proves this by mutating a built artifact and requiring the assertion layer to fail.
- Font substitution by the PDF conversion step is recorded, never silent: the build compares the font families the profile requires against the families actually embedded in the PDF, and any family that is absent is written to the manifest as a limitation with the missing list. A PDF whose font inventory cannot be produced (`pdffonts` unavailable) **fails the build** — an unverifiable PDF must not be published.
- The **math font** is controlled at the document level: the produced docx must declare `m:mathFont` for the profile's math family (pandoc drops `m:mathPr` from the reference settings.xml, so the build re-applies it). The PDF's math glyphs come from the host's LibreOffice math configuration and are therefore a **host substitution**, recorded as such rather than as a profile failure.
- Where the profile states a dimension the document does not (e.g. a role the body never uses), the assertion records it as **skipped**, so the manifest shows which dimensions were not verified.
- In-text numeric citations `[N]` / `[1,3]` / `[2-5]` are rendered **superscript** when the profile declares `citation.numeric_superscript` (GC-2026-1112-01; reference-list entries, code, OMML math, 4-digit forms such as access dates `[2026-11-11]`, and comma-space interval forms `[12, 40]` are excluded). The build asserts **coverage**: every citation run outside the excluded contexts must carry the superscript, so a missed citation fails the build instead of silently rendering as body text.

### PF-B13 L2 覆盖边界

- L2 (`build/layout.yaml`) carries **selection keys only**: `profile` (must equal `paper.yaml.layout_profile`) and `kind: paper`.
- Structure-identity keys (`page`, `citation`, `formulas`, `target_venue`) appearing in L2 **fail the build**; changing them requires profile versioning (PF-B3).
- L2 may override `typography` keys only, and within `typography` only `body_pt`, `line_spacing` and `first_line_indent_chars`. The role table (`fonts` / `sizes` / `heading_numbering`) is a **venue decision**; overriding it from a paper would bypass profile versioning, so it fails the build. Every override is logged with old/new/source-layer (PF-B10).
- Each layer and the merged result validate against `schemas/layout-profile.schema.json`; unknown keys fail the build.

### PF-B14 版式数值来源等级

- Every numeric value in a profile that is not stated verbatim by the target venue carries a provenance annotation: the profile comments tag each value with its source level (e.g. `[S#]` venue, `[GB]` national standard, `[CY]` industry standard, `[JT]` journal-measured, `[TD]` common practice); a structured key-level provenance block remains an open item (GC-2026-1111-02 open list).
- Source levels: `national_standard`, `national_standard_advisory`, `industry_standard`, `venue_requirement`, `venue_advisory`, `journal_measured`, `common_practice`, `self_chosen`.
- `self_chosen` values must never be presented to the venue, the user, or in a manifest as a venue requirement. Profile comments must mark each value with its source level.
- Venue requirements take precedence over the national-standard fallback for the same key; the fallback applies only where the venue is silent.
