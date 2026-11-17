# Writing Mode Rules

## Scope

This file defines the writing mode execution rules. Writing mode covers: paper body generation from outline and research data, citation management, abstract drafting, and terminology management.

## Rules

### PF-W1 真实性

- Facts, experiments, proofs, literature, and authorship must be verifiable. No fabricated data, run records, authors, sources, identifiers, or verification results.
- Do not write proposed work as completed work. Distinguish fact, assumption, observation, interpretation, and speculation.
- Uncertain or time-sensitive content must be actively verified with source and verification date.

### PF-W2 中文正文与双语摘要

- Body text is in Chinese. Abstract is bilingual (Chinese + English).
- English title and keywords follow the venue style guide. Full English body is not supported.
- Title, author order, affiliation, and corresponding author come from `paper.yaml` confirmed config only. Git identity does not imply authorship.
- Abstract must self-contain: research purpose, method, main results, and conclusion boundaries.
- Chinese and English abstracts must match in object, method, numbers, units, negation, and limitations. English must not add innovation or universality not supported by Chinese.
- Abstract must not carry complex derivation, internal numbering, or references requiring body context.

### PF-W3 独立贡献与查新

- For every new claim, topic, modification, or writing requirement, dispatch subagent for novelty search before proceeding.
- When similar published work exists, clearly indicate it. Distinguish: substantial duplication, verifiable increment, or insufficient evidence.
- Recommend only after evidence and independent verification. Cannot confirm "first" from no-search-result alone.
- Internal cross-paper citation requires the cited paper to be formally published with verifiable records. Preprints follow venue policy.

### PF-W4 理论、算法与系统方法

- Research plan must describe: object, input/output, assumptions, constraints, goal, and applicability boundary.
- Theory: definitions, proposition conditions, derivation/proof, key lemmas, counterexample boundaries. Numerical examples do not replace proofs.
- Algorithm: steps, stop conditions, key parameters, correctness basis, time/space complexity. Theoretical vs actual runtime cost reported separately.
- System: component responsibilities, interfaces, data flow, deployment, failure/recovery behavior. Distinguish design, implementation, and measured capability.

### PF-W5 实验、统计与比较

- Experiment design: problem, data split, metrics, baseline, budget, failure criteria. Post-hoc changes must record reasons.
- Record data source, version, license, preprocessing, code version, environment, commands, parameters, raw logs, and result entry.
- Report sample size, denominator, statistical unit, missing values, outliers. Separate independent samples from repeated measures.
- Use "significant" with clarity: statistical vs practical. State method, assumptions, and multiple comparison treatment.
- Body and figure values from same source. Rounding and units consistent. Distinguish simulation, synthetic, estimated from real measurement.

### PF-W6 文献检索与引用核验

- Novelty search must be actually performed by subagent with web access. Cannot use training memory, local lists, or historical search results.
- Record per source: bibliographic authenticity, actual access scope, support level for specific claims.
- Check title, author, version, publication info, and identifiers. Record actual reading scope (full text, abstract, official record, or excerpt).
- Unobtained full text does not automatically disqualify citation. Claims supported by abstract may be cited; method details, parameters, proofs, or boundaries from abstract-only must not be written in.
- Distinguish citation-type from reading-type references. Citation-type must support the specific body claim and be locatable.
- Citation style follows the paper configuration: the venue profile selected by `paper.yaml.layout_profile` is the binding source for bibliographic form.
- For document types the venue does not specify, the reference-entry templates registered in the venue profile's `citation.fallback_entry_forms` are the binding source of truth (GC-2026-1114-01). Online law/policy text follows the venue's own [EB/OL] template by cross-reference and is not duplicated in the profile.
- Every reference-list entry carries a GB/T 7714 document-type identifier ([M]/[J]/[C]/[EB/OL]/[Z]/[S]/[S/OL] etc.), taken per GB/T 7714 (author-date system per venue S13).
- Chinese-language sources are cited in Chinese per GB/T 7714 regardless of the verification channel (CNKI, publisher site, Crossref, OpenAlex, Semantic Scholar, Google Scholar, etc.): authors keep their published Chinese names (romanized forms must not replace them), journal titles stay in Chinese, and document-type identifiers follow [J]/[C]/[M]/[D] etc. Verification-source metadata (database, URL, access scope) is recorded in the entry note or the verification record, never in the rendered citation. When an international database conflicts with the publisher-side record, the publisher-side record prevails. This clause governs the language-of-record dimension only and does not override the venue profile, which remains the binding source for entry structure, punctuation, and ordering (GC-2026-1117-10).
- Direct quotes, translations, and figure adaptations must be marked. Unverified key support relationships must be supplemented or claims narrowed.

### PF-W7 隐私、许可与真实技术条件

- Determine desensitization based on publicity, authorization, personal information, and reproduction needs.
- Report actual model, version, call date, key configuration, and availability. Commercial models are not automatically anonymized.
- Formal authorship and affiliation require confirmation. Funding, ethics, data authorization, conflict of interest, and AI use disclosure must reflect reality.

### PF-W8 图表、公式与术语

- Figures and tables must serve specific arguments. Introduce purpose and reference in body before including. Numbering, captions, sources follow venue style.
- Scientific figures preserve data and generation scripts. System diagrams preserve editable source files.
- Mark units, legends, necessary error info in figures. Check arrows, labels, readability after scaling, grayscale, cropping, overlap.
- Generative AI diagrams are not measurement evidence. Choose tool by task: scientific plotting, code, or vector tool.
- Formulas define symbols, conditions, units. Distinguish scalar, vector, matrix. Numbering and cross-references consistent. Proofs and calculations cannot be provided as images only.
- Existing standardized terminology takes priority. New concepts require necessity check and first-use definition. Maintain per-paper terminology table.
- Before proposing new terminology, dispatch subagent to assess existing concepts and search for conflicts in related fields.

### PF-W9 自足、务实与读者理解

- Write for domain readers without access to internal workspaces. Explain "what it is, where it comes from, why it matters" at first mention.
- Use concrete problems, mechanisms, conditions, and results. Do not oversimplify or inflate complexity.
- Do not attribute intent, emotion, subjective experience, or autonomous judgment to algorithms, models, or systems.
- No unsupported superlatives: "leading", "perfect", "universal", "breakthrough". "Improved" or "superior" must name comparison object and conditions.
- Do not use detector scores, punctuation density, or fixed word blacklists as quality substitutes.
- Check necessity paragraph by paragraph against fixed body. Identify repetition, empty transitions, concept stacking, and padding.

### PF-W10 主张证据与局限

- Core contributions, important facts, and quantitative conclusions maintain claim-evidence correspondence with body location, source or run entry, input version, verification status, and open items.
- Distinguish model judgment, original verification, independent derivation, actual run, and recalculation. Multiple model agreement does not replace evidence.
- Conclusions answer the research question without adding unverified capability. Limitations specify assumptions, scope, negative results, and external validity. Future plans are not completed contributions.
- Work records are separate from body text. After body, evidence, figures, or dependency changes, re-verify affected review items.

### PF-W11 目标刊格式约束

- The target venue's own submission format requirements are binding and are recorded machine-checkably in `writing-spec.yaml` (per-paper, collected from the venue).
- When the venue is silent, the national-standard baseline (GB/T 7713.2-2022 附录 B, CY/T 170-2019, GB/T 3179-2009, and GB/T 7714 for bibliographic description) applies; the applicable version of each standard is recorded, not assumed. GB/T 7713.2-2022 附录 B, CY/T 170-2019, and GB/T 3179-2009 govern layout and publishing form; **GB/T 7714 governs bibliographic description (著录)**, and its applicable edition is the one registered in the venue profile's `citation.standard_edition`.
- Venue-specific constraints include, where stated by the venue: title length and punctuation policy, abstract length and writing person, keyword count and separator, bilingual block pairing, funding note order, heading numbering sequence, formula source format and symbol classes, figure/table caption requirements, reference citation system and entry order, corresponding-author marking, and author biography fields.
- A constraint stated as advisory by the venue ("一般不超过…", "…为宜") is treated as a target with tolerance, not as a hard threshold; the tolerance is recorded.
- Venue constraints are verified by the review mode (PF-RV7) and by build-time checks where they are mechanically decidable (length, separator, presence of required blocks).

### PF-W12 目标刊优先

- Where a target venue requirement is stricter than the generic rules in this file, the venue requirement governs. The stricter requirement is recorded in `writing-spec.yaml` with its source.
- Generic rules here still apply where the venue is silent, except where the venue contradicts them; a contradiction must be recorded with both texts and the decision.
- Changing a venue requirement means re-verifying every affected review item (PF-W10); stale review reports cannot be reused.
