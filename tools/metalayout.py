#!/usr/bin/env python3
"""metalayout — metadata-driven docx front/back matter generator.

GC-2026-1112-06 phase 2a implementation carrier. Reads the per-paper metadata
(paper.yaml / authors.yaml / abstract.md / funding.yaml), validates it against
the phase-0/1 contract (author.schema.json + semantic hard-gate rules), and
generates the markdown for the front page and the end-of-paper author-info
section. The build pipeline (tools/paper.py `cmd_build_docx`) assembles these
with body/paper.md (chapters + references + appendix only after migration) and
hands the assembled markdown to pandoc.

Contract sources:
  - schemas/author.schema.json        (document-level container, urn:paperfactory:author:3)
  - templates/layout/profiles/stie.yaml  authors: domain (front_order, bio_section, ...)
  - templates/layout/profiles/ 范本形态   (extract-report.md §2/§8: front-page line
    order and the end-of-paper author-info section)

Block shape: each front/back block is a pandoc custom-style div
(`::: {custom-style="..."}`) following the §12 landed convention already used in
P5/P6 — the Chinese title is NOT repeated as a block: it comes from the pandoc
metadata `title` and lands in the Title style (pf: it would otherwise duplicate).

Dependency policy: same as the rest of the governance toolchain — yaml +
jsonschema (both in /usr/lib/python3/dist-packages, usable under `python3 -I`).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import layoutlib  # noqa: E402

GOV_ROOT = Path(__file__).resolve().parent.parent
AUTHOR_SCHEMA_PATH = GOV_ROOT / "schemas" / "author.schema.json"

# GC-2026-1112-06 transitional hard gate: a BARE-LIST (legacy P1/P2/P3 style)
# authors.yaml — or any non-container shape — fails the build with this message.
# There is no fallback to the legacy path.
MIGRATION_MSG = (
    "authors.yaml 需迁移为文档级容器格式（GC-2026-1112-06 元数据迁移）：顶层必须是 "
    "schema_version/affiliations（注册表）/authors 容器（见 schemas/author.schema.json），"
    "不允许旧式裸列表（- id: ...）"
)

# bio block keys (author.schema.json snake_case) required by venue S17; the
# end-of-paper full bio (范本 §8) prints the whole set.
REQUIRED_BIO_FIELDS = (
    "birth_year", "gender", "hometown", "degree", "title",
    "research_direction", "address", "postcode", "email", "phone",
)

# Full-width separators used verbatim by the 范本 (§2 / §8).
_ZH_KW_SEP = "；"     # Chinese keywords list
_EN_KW_SEP = "; "     # English keywords list (half-width semicolon + space)
_PROJ_SEP_FRONT = "、"
_PROJ_SEP_BACK = "；"

# GC-2026-1112-06 终审返工（P2-2）：关键词锚点大小写不敏感、容忍空格变体。事故回
# 顾：英文侧原正则 `Keywords` 大小写敏感，P3 abstract.md 原「**Key words**」不命中
# → 首建缺失英文 Keywords 块；中文侧同时容忍 `关键词`/`关键字` 变体。
# `Key\s*words` 同时匹配 `Keywords` 与 `Key words`（以及大小写任意组合）。
_ZH_KW_FULL = re.compile(r"^\*{0,2}\s*关键(?:词|字)\s*\*{0,2}\s*[：:]\s*(.*)$")
_EN_KW_FULL = re.compile(r"^\*{0,2}\s*Key\s*words\s*\*{0,2}\s*[：:]\s*(.*)$",
                         re.IGNORECASE)

# bio_field_order fallback when the profile carries none (GB/T 7713.2 + 范本 full set).
FALLBACK_BIO_ORDER = [
    "出生年", "性别", "籍贯", "学位", "职称", "单位",
    "研究方向", "通信地址", "邮政编码", "电子邮箱", "电话",
]
FALLBACK_REDUCED_ORDER = ["出生年", "性别", "单位", "从事工作"]

# 通信作者* 简式八字段（范本 §8 [JT] 实测序）：无籍贯/学位/职称；电子邮箱、电话在
# 通信地址之前；地址与邮编合写「通信地址：<addr>，邮政编码 <pc>」。stie.yaml
# bio_section.corresponding_bio_fields 给出同序（终审返工 P2-4 落位）。
CORRESPONDING_BIO_FIELDS = [
    "出生年", "性别", "单位", "研究方向", "电子邮箱", "电话", "通信地址", "邮政编码",
]


class MetalayoutError(Exception):
    """Metadata load / assembly failure. Build path treats it as hard."""


def _load_yaml_file(path: Path) -> Any:
    if not path.exists():
        raise MetalayoutError(f"file not found: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MetalayoutError(f"{path} is not valid YAML: {exc}") from None


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_paper_metadata(dest: Path) -> dict:
    """Read paper.yaml / authors.yaml / abstract.md / funding.yaml → structured meta.

    Raises MetalayoutError for the transitional hard gate (authors.yaml not the
    document-level container), YAML parse errors araising to the shape gate, and
    jsonschema violations of author.schema.json. Semantic checks live in
    validate_metadata (check command); load only enforces what the file must be
    to be processable at all.
    """
    dest = Path(dest)
    paper_path = dest / "paper.yaml"
    if not paper_path.exists():
        raise MetalayoutError(f"paper.yaml not found in {dest}")
    paper = _load_yaml_file(paper_path)
    if not isinstance(paper, dict):
        raise MetalayoutError(f"{paper_path} must parse to a mapping")

    authors_path = dest / "authors.yaml"
    if not authors_path.exists():
        raise MetalayoutError(f"authors.yaml not found in {dest}")
    authors_raw = _load_yaml_file(authors_path)

    # ── transitional hard gate: the document must be the container format ──
    if not isinstance(authors_raw, dict) or not isinstance(authors_raw.get("authors"), list) \
            or not authors_raw["authors"]:
        raise MetalayoutError(MIGRATION_MSG)

    _validate_authors_schema(paper.get("id") or dest.name, authors_raw, authors_path)

    registry, registry_by_id = _build_registry(authors_raw)
    abstract = _parse_abstract(dest)
    funding = _parse_funding(dest)
    byline = _build_byline(paper, authors_raw, registry_by_id)
    first, corresponding, others = _split_roles(byline)

    return {
        "paper_id": paper.get("id") or dest.name,
        "dest": dest,
        "paper": paper,
        "authors_path": authors_path,
        "authors_raw": authors_raw,
        "registry": registry,
        "registry_by_id": registry_by_id,
        "byline": byline,
        "first_author": first,
        "corresponding_author": corresponding,
        "other_authors": others,
        "abstract": abstract,
        "funding": funding,
    }


def _validate_authors_schema(paper_id: str, authors_raw: dict, authors_path: Path) -> None:
    """jsonschema validation against schemas/author.schema.json (draft 2020-12)."""
    from jsonschema import Draft202012Validator

    try:
        schema = json.loads(AUTHOR_SCHEMA_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MetalayoutError(f"author.schema.json unreadable: {exc}") from None
    errors = sorted(
        Draft202012Validator(schema).iter_errors(authors_raw),
        key=lambda e: list(e.path),
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message[:140]}" for e in errors[:6])
        raise MetalayoutError(
            f"authors.yaml does not conform to author.schema.json (paper {paper_id}): {detail}")


def _build_registry(authors_raw: dict) -> tuple[list, dict]:
    """Numbered registry (1-based, array order) + id-index.

    Numbers are the units' byline superscript values and the affiliation-list
    numbers; they derive from REGISTRY position, never from author count.
    """
    registry: list[dict] = []
    by_id: dict[str, dict] = {}
    for i, item in enumerate(authors_raw.get("affiliations") or [], start=1):
        if not isinstance(item, dict):
            continue
        entry = {k: item.get(k) for k in ("id", "name", "name_en", "city", "city_en", "postcode")}
        entry["number"] = i
        registry.append(entry)
        if entry.get("id"):
            by_id[entry["id"]] = entry
    return registry, by_id


def _build_byline(paper: dict, authors_raw: dict, registry_by_id: dict) -> list[dict]:
    """Byline-ordered author entries joined from paper.yaml + authors.yaml registry.

    paper.yaml.authors drives the order and the roles (GC-2026-1112-06 division of
    labour); the matching authors.yaml entry (looked up by author id) supplies
    affiliation_ids / name_en / bio. When paper.yaml carries no authors (legacy
    fallback), the authors.yaml byline order is used without roles.
    """
    author_by_id = {e.get("id"): e for e in authors_raw.get("authors") or []
                    if isinstance(e, dict) and e.get("id")}
    paper_authors = paper.get("authors")
    if isinstance(paper_authors, list) and paper_authors:
        source = paper_authors
    else:
        source = authors_raw.get("authors") or []

    byline: list[dict] = []
    for a in source:
        if not isinstance(a, dict):
            continue
        author_id = a.get("author_id") or a.get("id")
        entry = author_by_id.get(author_id) or {}
        roles = list(a.get("roles") or [])
        numbers: list[int] = []
        for aff_id in entry.get("affiliation_ids") or []:
            r = registry_by_id.get(aff_id)
            if r is not None:
                numbers.append(r["number"])
        byline.append({
            "author_id": author_id,
            "name": (a.get("name") or entry.get("name") or "").strip(),
            "name_en": entry.get("name_en"),
            "roles": roles,
            "corresponding": bool(a.get("corresponding")) or ("corresponding" in roles),
            "affiliation_numbers": numbers,
            "bio": entry.get("bio") if isinstance(entry.get("bio"), dict) else None,
            "email": a.get("email") or entry.get("email"),
        })
    return byline


def _split_roles(byline: list[dict]) -> tuple[Any, Any, list]:
    """first / corresponding / other-authors split (范本: dedicated paragraphs for
    first + corresponding, the rest merged; an author that is both counts once)."""
    first = next((a for a in byline if "first" in (a.get("roles") or [])), None)
    if first is None and byline:
        first = byline[0]
    corresponding = next((a for a in byline if a.get("corresponding")), None)
    first_id = first.get("author_id") if first else None
    corr_id = corresponding.get("author_id") if corresponding else None
    others = [a for a in byline if a is not first and a is not corresponding
              and a.get("author_id") != first_id and a.get("author_id") != corr_id]
    return first, corresponding, others


# ---------------------------------------------------------------------------
# abstract.md / funding.yaml parsing
# ---------------------------------------------------------------------------

def _parse_abstract(dest: Path) -> dict:
    """Split abstract.md into zh/en paragraphs and keyword lists.

    The Chinese abstract lives under `## 中文摘要` (keyword line stripped); the
    English section (`## English Abstract`) additionally drops the English title
    (bold line), the byline (superscript lines) and the affiliation list
    (parenthesized numbered lines) — those are generated from the registry.
    """
    path = dest / "abstract.md"
    if not path.exists():
        raise MetalayoutError(f"abstract.md not found in {dest}")
    text = path.read_text(encoding="utf-8")

    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)

    zh_section = next((k for k in sections if k.strip() == "中文摘要"), None)
    en_section = next((k for k in sections
                       if k.strip().lower() in ("english abstract", "abstract")
                       or "english" in k.strip().lower()), None)

    def _zh_kw(value: str) -> list[str]:
        return [p.strip() for p in value.split(_ZH_KW_SEP) if p.strip()]

    def _en_kw(value: str) -> list[str]:
        return [p.strip() for p in re.split(r";\s*|；", value) if p.strip()]

    abstract_zh = keywords_zh = ""
    kw_zh_list: list[str] = []
    if zh_section is not None:
        keep: list[str] = []
        for line in sections[zh_section]:
            s = line.strip()
            m = _ZH_KW_FULL.match(s)
            if m:
                keywords_zh = m.group(1).strip()
                continue
            if s and not s.startswith("#"):
                keep.append(s)
        abstract_zh = "\n\n".join(p.strip() for p in "\n".join(keep).split("\n\n") if p.strip())
        kw_zh_list = _zh_kw(keywords_zh)

    abstract_en = ""
    kw_en_list: list[str] = []
    if en_section is not None:
        keep_en: list[str] = []
        seen_para = False
        for line in sections[en_section]:
            s = line.strip()
            if _EN_KW_FULL.match(s):
                continue  # keyword line handled below
            if not s or s.startswith("#"):
                continue
            # English title: a lone bold line early in the section (dropped).
            if not seen_para and re.match(r"^\*\*.+\*\*\s*$", s):
                continue
            # byline / affiliation lines (superscript names / (1. ...; ...) list).
            if _is_en_remark(s):
                continue
            seen_para = True
            keep_en.append(s)
        abstract_en = "\n\n".join(p.strip() for p in "\n".join(keep_en).split("\n\n") if p.strip())
        for line in sections[en_section]:
            m = _EN_KW_FULL.match(line.strip())
            if m:
                kw_en_list = _en_kw(m.group(1).strip())
                break

    return {
        "zh": abstract_zh,
        "keywords_zh": kw_zh_list,
        "en": abstract_en,
        "keywords_en": kw_en_list,
        "zh_section_present": zh_section is not None,
        "en_section_present": en_section is not None,
    }


_SUPERSCRIPT_CHARS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def _is_en_remark(line: str) -> bool:
    """True for an English byline / affiliation-list line inside abstract.md.

    Byline: contains Unicode superscript digits (作者B¹) or pandoc ^..^ markers.
    Affiliation list: starts with a parenthesized unit number, e.g. "(1. ...)".
    """
    if any(ch in line for ch in _SUPERSCRIPT_CHARS):
        return True
    if re.search(r"\^\^|\^[^\^]{1,40}\^", line):
        return True
    if re.match(r"^\s*[（(]\s*\d+\s*[.、].*", line):
        return True
    if re.match(r"^\s*\d+\s*[.、]\s*[A-Za-z]", line):
        # a parenthesized affiliation list that wrapped onto a numbered continuation.
        return True
    if re.match(r"^\s*postal\s+code\s*\d", line, re.IGNORECASE):
        return True
    return False


def _parse_funding(dest: Path) -> list[dict]:
    """funding.yaml → ordered list of {name, code}. Empty on missing/empty file."""
    path = dest / "funding.yaml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []
    sources = data.get("funding_sources")
    if not isinstance(sources, list):
        return []
    out: list[dict] = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        code = str(item.get("code") or "").strip()
        out.append({"name": name, "code": code})
    return out


# ---------------------------------------------------------------------------
# Validation (check command hard gate)
# ---------------------------------------------------------------------------

def validate_metadata(meta: dict) -> list[str]:
    """Semantic hard errors (empty = pass). Every entry is actionable and names
    the file and the field (PF-B16 style). Also self-contained: the container
    shape is re-checked so a caller can rely on it without load raising.
    """
    errors: list[str] = []
    paper_id = meta.get("paper_id") or "?"
    raw = meta.get("authors_raw")
    if not isinstance(raw, dict) or not isinstance(raw.get("authors"), list) or not raw["authors"]:
        errors.append(f"[{paper_id}] {MIGRATION_MSG}")
        return errors

    registry = meta.get("registry") or []
    registry_ids = [r.get("id") for r in registry if r.get("id")]
    seen = set()
    for rid in registry_ids:
        if rid in seen:
            errors.append(f"[{paper_id}] authors.yaml#affiliations: duplicate registry id {rid!r} "
                          f"(affiliation numbering would be ambiguous)")
        seen.add(rid)

    # dangling affiliation_ids
    for entry in raw.get("authors") or []:
        if not isinstance(entry, dict):
            continue
        for aid in entry.get("affiliation_ids") or []:
            if aid not in seen:
                errors.append(
                    f"[{paper_id}] authors.yaml#authors.{entry.get('id')!r}.affiliation_ids: "
                    f"{aid!r} does not resolve to an affiliations registry id "
                    f"(registry has {sorted(seen) or 'none'})")

    # registry missing name_en (venue S5 Chinese/English pair)
    for rid in registry:
        if not str(rid.get("name_en") or "").strip():
            errors.append(f"[{paper_id}] authors.yaml#affiliations.{rid.get('id')!r}: "
                          f"missing name_en (venue S5 requires the English unit pair; "
                          f"the English affiliation list is generated from it)")

    # bio field completeness (S17)
    author_ids = set()
    for entry in raw.get("authors") or []:
        if not isinstance(entry, dict):
            continue
        aid = entry.get("id")
        author_ids.add(aid)
        bio = entry.get("bio")
        missing = [f for f in REQUIRED_BIO_FIELDS if not isinstance(bio, dict) or bio.get(f) in (None, "")]
        if missing:
            errors.append(
                f"[{paper_id}] authors.yaml#authors.{aid!r} ({entry.get('name')}): "
                f"missing bio field(s) — {', '.join(missing)} (venue S17; see author.schema.json)")

    # paper.yaml.authors author_id resolution + role uniqueness
    paper_authors = meta.get("paper", {}).get("authors") or []
    firsts, corrs = [], []
    for a in paper_authors:
        if not isinstance(a, dict):
            continue
        pid = a.get("author_id")
        if pid and pid not in author_ids and pid not in seen:
            errors.append(
                f"[{paper_id}] paper.yaml#authors: author_id {pid!r} has no matching "
                f"authors.yaml entry (registry ids: {sorted(author_ids) or 'none'})")
        roles = a.get("roles") or []
        if "first" in roles:
            firsts.append(a.get("name") or pid)
        if "corresponding" in roles:
            corrs.append(a.get("name") or pid)
    if len(firsts) != 1:
        errors.append(f"[{paper_id}] paper.yaml#authors.roles: exactly one 'first' author "
                      f"is required; found {firsts or 'none'}")
    if len(corrs) > 1:
        errors.append(f"[{paper_id}] paper.yaml#authors.roles: at most one 'corresponding' "
                      f"author allowed; found {corrs}")

    # P2-1 (终审返工): 每位署名作者必须有 name_en（S5 中英成对）。英文署名由
    # name_en 生成，缺省时 `_byline` 英文分支会静默跳过该作者 → 英文署名少人
    # （P3 曾因大小写关键字事故牵连此类静默问题；此处改为硬闸，缺了即失败并列人名）。
    for a in meta.get("byline") or []:
        if not str(a.get("name") or "").strip():
            continue  # 无显示名（未真正署名），不计入 byline 成员
        if a.get("author_id") in (None, ""):
            continue
        if not str(a.get("name_en") or "").strip():
            errors.append(
                f"[{paper_id}] authors.yaml#authors.{a.get('author_id')!r} "
                f"({a.get('name')}): missing name_en (venue S5 requires the English name; "
                f"the English byline would silently omit this author)")

    # P1-1 (终审返工 — init 骨架闸): 每位署名作者必须有 ≥1 条 affiliation_ids——
    # byline 上标编号与单位编号列表由它生成；空即渲染不出署名单位（新论文 init
    # 骨架未填元数据时 check/build 必须点名该缺失，而非静默产出无编号署名）。
    for a in meta.get("byline") or []:
        if not str(a.get("name") or "").strip():
            continue
        if a.get("author_id") in (None, ""):
            continue
        if not (a.get("affiliation_numbers") or []):
            errors.append(
                f"[{paper_id}] authors.yaml#authors.{a.get('author_id')!r} "
                f"({a.get('name')}): empty affiliation_ids — at least one affiliations "
                f"registry unit is required for the byline unit numbers")

    # abstract.md sections
    abst = meta.get("abstract") or {}
    if not abst.get("zh_section_present"):
        errors.append(f"[{paper_id}] abstract.md: missing '## 中文摘要' section")
    if not abst.get("en_section_present"):
        errors.append(f"[{paper_id}] abstract.md: missing '## English Abstract' section")

    # P2-2 (终审返工): 关键词非空闸——前端关键词块由本列表生成，解析不到即失败并
    # 指名 abstract.md 标签问题（标签错误 = `**关键词**：…`/`**Keywords**: …` 行
    # 缺失或错拼；中文容忍 `关键字` 变体、英文大小写不敏感且容忍 `Key words`）。
    if not (abst.get("keywords_zh") or []):
        errors.append(
            f"[{paper_id}] abstract.md: 中文关键词解析为空——需要 `**关键词**：…` 行"
            f"（或用 `关键字` 变体），请检查中文摘要节的标签与内容（P2-2）")
    if not (abst.get("keywords_en") or []):
        errors.append(
            f"[{paper_id}] abstract.md: English keywords 解析为空——需要 `**Keywords**：…` "
            f"行（大小写不敏感，容忍 `Key words` 变体），请检查 English Abstract 节的"
            f"标签与内容（P2-2）")

    # P3-layout 卫生闸 (2026-11-13, 用户发现)：markdown ATX 标题行（`^#…`）的
    # 前一行必须为空行（文件首行除外）。pandoc 把「段落后紧接 # 标题」当作段落
    # 的惰续行（字面 `#` 直接进正文），导致 docx 标题不落 Heading 样式、PDF
    # 书签丢失（P3 曾 31 个标题中 28 个被吞成段落、书签只剩 4 个）。违例即构建
    # 失败并列出行号+标题文本。栅栏代码块内的 `#` 行不是标题，跳过。
    paper_dir = meta.get("dest")
    if paper_dir is not None:
        _check_atx_heading_hygiene(Path(paper_dir), paper_id, errors)

    return errors


def _check_atx_heading_hygiene(dest: Path, paper_id: str, errors: list) -> None:
    """P3-layout 硬闸 — body/paper.md 每个 ATX 标题行前必须有空行。"""
    body_path = Path(dest) / "body" / "paper.md"
    if not body_path.exists():
        return
    try:
        lines = body_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"[{paper_id}] body/paper.md: ATX 卫生检查无法读取 ({exc})")
        return
    in_fence = None
    for idx, line in enumerate(lines):
        fm = re.match(r"^\s*(```+|~~~+)(.*)$", line)
        if fm:
            marker = fm.group(1)
            if in_fence is None:
                in_fence = marker
            elif in_fence == marker:
                in_fence = None
            continue
        if in_fence is not None:
            continue
        if not re.match(r"^#", line):
            continue
        if idx == 0:
            continue  # the file's first line is exempt
        if lines[idx - 1].strip() != "":
            errors.append(
                f"[{paper_id}] body/paper.md:{idx + 1}: ATX 标题前缺少空行——"
                f"`{line.strip()}` 会被 pandoc 当作段落惰续行渲染（字面 `#` 进正文、"
                f"标题不落 Heading 样式、PDF 书签丢失）；请在标题行前插入空行"
                f"（P3-layout 卫生闸）")


# ---------------------------------------------------------------------------
# Generation: front matter
# ---------------------------------------------------------------------------

def _div(style: str, content: str) -> str:
    return f'::: {{custom-style="{style}"}}\n{content}\n:::'.strip("\n")


def _funding_items(meta: dict, back: bool) -> str:
    items = [f"{f['name']}（{f['code']}）" if f.get("code") else f["name"] for f in meta.get("funding") or []]
    if not items:
        return ""
    sep = _PROJ_SEP_BACK if back else _PROJ_SEP_FRONT
    return sep.join(items)


def _byline_superscript(author: dict, ap: dict) -> str:
    """Byline superscript '^1,2,\\*^' (numbers first, then the corresponding mark
    — corresponding_mark_position=after_numbers per the 范本)."""
    num_sep = ap.get("number_separator", ",")
    mark = ap.get("corresponding_mark", "*")
    position = ap.get("corresponding_mark_position", "after_numbers")
    parts: list[str] = []
    nums = [str(n) for n in author.get("affiliation_numbers") or []]
    if position == "after_name":
        if author.get("corresponding"):
            parts.append(mark)
        parts.extend(nums)
    else:
        parts.extend(nums)
        if author.get("corresponding"):
            parts.append(mark)
    if not parts:
        return ""
    return "^" + num_sep.join(parts).replace("*", "\\*") + "^"


def _surname_given(name_en: str) -> str:
    """SURNAME Given form for the English byline (范本 §2 line 8: 'ZHANG San').

    Contract (GC-2026-1112-06 P5 试点修正): name_en 以「姓前名后」登记——首词为姓
    （authors.txt 唯一信息源与任务指令均此序：「英文名 : Author B」），生成器把首词
    大写为姓、余词为名。e.g. 'Author B' → 'ZHANG San'；'Author A' → 'AUTHOR A'。
    修正前契约误取"末词大写为姓"（Given Surname 西语序），会把中文姓前名后的
    英文名末词当姓，渲染成 'San ZHANG'——与范本 'ZHANG San' 相反（P5 试点发现；
    见 papers/P5-*/build-record.md R10；templates/paper/authors.yaml 已同步）。
    """
    parts = [p for p in str(name_en or "").split() if p.strip()]
    if not parts:
        return ""
    surname = parts[0].upper()
    given = " ".join(parts[1:])
    return f"{surname} {given}" if given else surname


def _byline(authors: list[dict], ap: dict, zh: bool) -> str:
    sep = ap.get("name_separator_zh", "，") if zh else ap.get("name_separator_en", ", ")
    segments = []
    for a in authors:
        if zh:
            name = a.get("name") or ""
        else:
            name = _surname_given(a.get("name_en"))
        if not name:
            continue
        segments.append(name + _byline_superscript(a, ap))
    return sep.join(segments)


def _referenced_registry(meta: dict) -> list[dict]:
    """Registry items actually referenced by the byline, in registry order."""
    numbers = {n for a in meta.get("byline") or [] for n in a.get("affiliation_numbers") or []}
    return [r for r in meta.get("registry") or [] if r["number"] in numbers]


def _affiliation_list(meta: dict, ap: dict, zh: bool) -> str:
    entries = []
    for r in _referenced_registry(meta):
        if zh:
            city, pc = r.get("city"), r.get("postcode")
            if city or pc:
                tail = f"，{city} {pc}" if city and pc else ""
                entries.append(f"{r['number']}. {r.get('name')}{tail}")
            else:
                entries.append(f"{r['number']}. {r.get('name')}")
        else:
            name_en = str(r.get("name_en") or "").strip()
            if not name_en:
                continue
            # GC-2026-1112-06 收尾: the English unit line city must be the romanized
            # `city_en` (范本 'Haikou 570208, China'); fall back to the Chinese `city`
            # for registries that predate the key so the old output is preserved.
            city, pc = r.get("city_en") or r.get("city"), r.get("postcode")
            tail = " ".join(x for x in (city, pc) if x)
            entries.append(f"{r['number']}. {name_en}"
                           + (f", {tail}, China" if tail else ", China"))
    if zh:
        return "（" + "；".join(entries) + "）"
    return "(" + "; ".join(entries) + ")"


def _front_notes_blocks(meta: dict) -> list[str]:
    notes = meta.get("paper", {}).get("front_notes")
    if not isinstance(notes, list):
        return []
    blocks = []
    for line in notes:
        if isinstance(line, str) and line.strip():
            blocks.append(_div("BlockText", line.strip()))
    return blocks


def generate_front_matter(meta: dict, authors_profile: dict) -> str:
    """Front page in front_order (stie.yaml authors.front_order), 范本 §2 逐行对应.

    The Chinese title_block is rendered by pandoc from the YAML frontmatter
    `title` (Title style) and is intentionally NOT repeated here.
    front_notes (paper.yaml, optional) land between keywords and funding.
    """
    ap = authors_profile or {}
    order = ap.get("front_order") or []
    blocks: list[str] = []
    for key in order:
        if key == "title_zh":
            continue
        if key == "authors_zh":
            blocks.append(_div("Author", _byline(meta.get("byline") or [], ap, zh=True)))
        elif key == "affiliations_zh":
            blocks.append(_div("Affiliation", _affiliation_list(meta, ap, zh=True)))
        elif key == "abstract":
            zh = (meta.get("abstract") or {}).get("zh") or ""
            if zh.strip():
                blocks.append(_div("Abstract", f"摘要：{zh.strip()}"))
        elif key == "keywords":
            kws = (meta.get("abstract") or {}).get("keywords_zh") or []
            if kws:
                blocks.append(_div("Abstract", f"关键词：{_ZH_KW_SEP.join(kws)}"))
            blocks.extend(_front_notes_blocks(meta))
        elif key == "funding":
            items = _funding_items(meta, back=False)
            if items and "front" in (ap.get("funding_positions") or []):
                blocks.append(_div("BlockText", f"基金项目：{items}"))
        elif key == "title_en":
            title_en = str(meta.get("paper", {}).get("title_en") or "").strip()
            if title_en:
                blocks.append(_div("Subtitle", title_en))
        elif key == "authors_en":
            blocks.append(_div("Author", _byline(meta.get("byline") or [], ap, zh=False)))
        elif key == "affiliations_en":
            blocks.append(_div("Affiliation", _affiliation_list(meta, ap, zh=False)))
        elif key == "abstract_en":
            en = (meta.get("abstract") or {}).get("en") or ""
            if en.strip():
                blocks.append(_div("Abstract", f"Abstract: {en.strip()}"))
        elif key == "keywords_en":
            kws = (meta.get("abstract") or {}).get("keywords_en") or []
            if kws:
                blocks.append(_div("Abstract", f"Keywords: {_EN_KW_SEP.join(kws)}"))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Generation: back matter (end-of-paper author info)
# ---------------------------------------------------------------------------

def _units_joined(author: dict, meta: dict) -> str:
    """Registry unit names joined by '、' in registry order (范本 §8 单位并接)."""
    by_number = {r["number"]: r for r in meta.get("registry") or []}
    names = [str(by_number[n]["name"]).strip() for n in author.get("affiliation_numbers") or []
             if n in by_number and str(by_number[n].get("name") or "").strip()]
    return "、".join(names)


def _bio_full(author: dict, meta: dict, authors_profile: dict) -> str:
    """Full bio in bio_field_order (范本 §8: name + 出生年/…/单位 inline, then
    ;研究方向为…；通信地址：…；…；电话：….）。 Fields it lacks are skipped (no
    fabrication); the '单位' field resolves from the registry."""
    ap = authors_profile or {}
    order = (ap.get("bio_section", {}) or {}).get("bio_field_order") or FALLBACK_BIO_ORDER
    bio = author.get("bio") or {}
    units = _units_joined(author, meta)
    inline: list[str] = []
    labeled: list[str] = []
    for field in order:
        if field == "出生年":
            v = bio.get("birth_year")
            if v not in (None, ""):
                inline.append(f"（{v} 年生）")
        elif field == "性别":
            v = bio.get("gender")
            if v:
                inline.append(f"，{v}")
        elif field == "籍贯":
            v = bio.get("hometown")
            if v:
                inline.append(f"，{v}人")
        elif field == "学位":
            v = bio.get("degree")
            if v:
                inline.append(f"，{v}")
        elif field == "职称":
            v = bio.get("title")
            if v:
                inline.append(f"，{v}")
        elif field == "单位":
            if units:
                inline.append(f"，{units}")
        elif field == "研究方向":
            v = bio.get("research_direction")
            if v:
                labeled.append(f"研究方向为{v}")
        elif field == "通信地址":
            v = bio.get("address")
            if v:
                labeled.append(f"通信地址：{v}")
        elif field == "邮政编码":
            v = bio.get("postcode")
            if v:
                labeled.append(f"邮政编码：{v}")
        elif field == "电子邮箱":
            v = bio.get("email")
            if v:
                labeled.append(f"电子邮箱：{v}")
        elif field == "电话":
            v = bio.get("phone")
            if v:
                labeled.append(f"电话：{v}")
    text = (author.get("name") or "") + "".join(inline)
    if labeled:
        text += "；" + "；".join(labeled)
    return text + "。"


def _bio_reduced(author: dict, meta: dict, authors_profile: dict) -> str:
    """Reduced bio for the merged 其他作者 paragraph (范本 §8: 出生年、性别、
    单位、从事工作). 从事工作 maps to bio.research_direction — author.schema.json
    has no dedicated key (noted in the report). GC-2026-1112-06 终审返工（P3-2）:
    从事工作按范本包装为「主要从事<rd>等工作」（段内「；」接排、段末「。」由调用方
    拼）。"""
    ap = authors_profile or {}
    order = (ap.get("bio_section", {}) or {}).get("other_author_reduced_fields") \
        or FALLBACK_REDUCED_ORDER
    bio = author.get("bio") or {}
    units = _units_joined(author, meta)
    text = author.get("name") or ""
    for field in order:
        if field == "出生年":
            v = bio.get("birth_year")
            if v not in (None, ""):
                text += f"（{v} 年生）"
        elif field == "性别":
            v = bio.get("gender")
            if v:
                text += f"，{v}"
        elif field == "单位":
            if units:
                text += f"，{units}"
        elif field == "从事工作":
            v = bio.get("research_direction")
            if v:
                text += f"，主要从事{v}等工作"
    return text


def _bio_corresponding(author: dict, meta: dict, authors_profile: dict) -> str:
    """Corresponding-author simple bio (范本 §8 简式八字段, P2-4 终审返工).

    与首作者全字段（_bio_full）不同：无籍贯/学位/职称；电子邮箱、电话在通信地址
    之前；通信地址与邮政编码合写为「通信地址：<addr>，邮政编码 <pc>」（邮政编码后
    无冒号）。字段表由 profile bio_section.corresponding_bio_fields 给定，缺省回落
    CORRESPONDING_BIO_FIELDS。
    """
    ap = authors_profile or {}
    order = (ap.get("bio_section", {}) or {}).get("corresponding_bio_fields") \
        or CORRESPONDING_BIO_FIELDS
    bio = author.get("bio") or {}
    units = _units_joined(author, meta)
    inline: list[str] = []
    labeled: list[str] = []
    postcode_consumed = False
    for field in order:
        if field == "出生年":
            v = bio.get("birth_year")
            if v not in (None, ""):
                inline.append(f"（{v} 年生）")
        elif field == "性别":
            v = bio.get("gender")
            if v:
                inline.append(f"，{v}")
        elif field == "单位":
            if units:
                inline.append(f"，{units}")
        elif field == "研究方向":
            v = bio.get("research_direction")
            if v:
                labeled.append(f"研究方向为{v}")
        elif field == "电子邮箱":
            v = bio.get("email")
            if v:
                labeled.append(f"电子邮箱：{v}")
        elif field == "电话":
            v = bio.get("phone")
            if v:
                labeled.append(f"电话：{v}")
        elif field == "通信地址":
            addr = bio.get("address")
            pc = bio.get("postcode")
            segment = f"通信地址：{addr}" if addr else ""
            if addr and pc:
                segment += f"，邮政编码 {pc}"
                postcode_consumed = True
            if segment:
                labeled.append(segment)
        elif field == "邮政编码":
            if postcode_consumed:
                continue
            pc = bio.get("postcode")
            if pc:
                labeled.append(f"邮政编码：{pc}")
    text = (author.get("name") or "") + "".join(inline)
    if labeled:
        text += "；" + "；".join(labeled)
    return text + "。"


def generate_back_matter(meta: dict, authors_profile: dict) -> str:
    """`# 作者信息` + the four paragraphs (范本 §8). Each paragraph is a BlockText
    div with a full-width-colon label. funding goes first only when
    funding_positions includes 'back'; 其他作者 is suppressed when there is none.
    The corresponding paragraph is emitted whenever a corresponding author exists
    — even when that author is also the first author (范本实证)."""
    ap = authors_profile or {}
    bs = (ap.get("bio_section", {}) or {})
    labels = bs.get("paragraph_labels") or {}
    heading = str(bs.get("heading") or "作者信息").strip()

    parts = [f"# {heading}"]

    if "back" in (ap.get("funding_positions") or ["back"]):
        items = _funding_items(meta, back=True)
        if items:
            parts.append(_div("BlockText", f"{labels.get('funding', '基金项目')}：{items}。"))

    first = meta.get("first_author")
    if first is not None:
        parts.append(_div("BlockText",
                          f"{labels.get('first_author', '作者简介')}：{_bio_full(first, meta, ap)}"))

    corresponding = meta.get("corresponding_author")
    if corresponding is not None:
        # P2-4 (终审返工): 通信作者* 段改用范本简式八字段（_bio_corresponding），
        # 不再复用首作者全字段（_bio_full）。
        parts.append(_div("BlockText",
                          f"{labels.get('corresponding', '通信作者*')}："
                          f"{_bio_corresponding(corresponding, meta, ap)}"))

    others = meta.get("other_authors") or []
    if others:
        segs = [_bio_reduced(o, meta, ap) for o in others]
        segs = [s for s in segs if s.strip()]
        if segs:
            parts.append(_div("BlockText",
                              f"{labels.get('other_authors', '其他作者')}：{'；'.join(segs)}。"))

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _yaml_scalar(value: str) -> str:
    """A YAML double-quoted scalar. yaml.safe_dump appends a '...' document-end
    marker after a bare scalar, which would confuse pandoc's frontmatter parser;
    a JSON double-quoted string is valid YAML for a title value."""
    return json.dumps(str(value), ensure_ascii=False)


def _resolve_authors_profile(dest: Path, meta: dict) -> dict:
    """Resolve the authors domain of the profile a paper is bound to (used when the
    caller has not already resolved the layout, e.g. standalone assembly/tests)."""
    profile_name = meta.get("paper", {}).get("layout_profile") or "draft"
    l2 = None
    l2_path = Path(dest) / "build" / "layout.yaml"
    if l2_path.exists():
        try:
            loaded = yaml.safe_load(l2_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                l2 = loaded
        except yaml.YAMLError:
            l2 = None
    stack = layoutlib.resolve_profile_stack(profile_name, l2)
    return stack["merged"].get("authors") or {}


def assemble_document(dest: Path, out_path: Path, authors_profile: dict | None = None) -> dict:
    """Assemble the pandoc input: YAML frontmatter + generated front matter +
    body/paper.md (chapters + references + appendix) + generated back matter.

    out_path is a temporary assembly file (PF-B5 temp discipline); the caller
    (tools/paper.py build) passes the already-resolved authors_profile. Returns a
    small record for the build log.
    """
    dest = Path(dest)
    out_path = Path(out_path)
    meta = load_paper_metadata(dest)
    if authors_profile is None:
        authors_profile = _resolve_authors_profile(dest, meta)

    body_path = dest / "body" / "paper.md"
    if not body_path.exists():
        raise MetalayoutError(f"single body source missing: {body_path} (PF-B2)")
    body_text = body_path.read_text(encoding="utf-8")

    front = generate_front_matter(meta, authors_profile)
    back = generate_back_matter(meta, authors_profile)

    title = str(meta.get("paper", {}).get("title") or "").strip()
    frontmatter = f"---\ntitle: {_yaml_scalar(title)}\nlang: zh-CN\n---\n"

    assembled = (frontmatter
                 + ("\n" + front if front else "")
                 + "\n\n" + body_text.rstrip("\n")
                 + ("\n\n" + back if back else "")
                 + "\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(assembled, encoding="utf-8")

    return {
        "assembly_path": str(out_path),
        "front_matter_generated": bool(front),
        "back_matter_generated": bool(back),
        "front_blocks": [b for b in front.split("\n\n") if b.strip()],
        "back_blocks": [b for b in back.split("\n\n") if b.strip()],
    }


if __name__ == "__main__":
    # Standalone smoke: `python3 -I tools/metalayout.py <paper-dir> [--check]`
    import argparse

    parser = argparse.ArgumentParser(description="metadata load/validate (GC-2026-1112-06)")
    parser.add_argument("paper", help="paper workspace directory")
    parser.add_argument("--check", action="store_true", help="run validate_metadata")
    args = parser.parse_args()
    meta = load_paper_metadata(Path(args.paper))
    errors = validate_metadata(meta)
    print(json.dumps({
        "status": "fail" if errors else "ok",
        "paper_id": meta.get("paper_id"),
        "byline": [a.get("name") for a in meta.get("byline") or []],
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)
