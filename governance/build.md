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
- Structure-identity keys (`profile`, `kind`, `target_venue`, `page`, `citation`, `formulas`) cannot be overridden by paper config. Changes require profile versioning.
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

- Target directory: `output/REL-0001/{paper.docx,paper.pdf,manifest.json}`. Subsequent numbers increment.
- Published versions cannot be modified in place. Old versions preserved.
- Manifest records: non-reusable REL ID, paper identity, paper_version, manuscript_kind, title and authorship config, input snapshot, rules_version, toolchain version, environment, both artifact checksums, review and re-verification relationships, open limitations, timestamp.
- After all checks complete, atomically switch `output/current.json` within publish lock. Read first parses manifest, then reads referenced full version.

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
- Semantic conflicts (incompatible units or semantics for same key) fail build after profile Schema reconciliation attempt.
- `paper.yaml` semantic keys (`language`, `bilingual_abstract`, `full_english_body`) must not conflict with global profile.
