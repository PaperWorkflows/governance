#!/usr/bin/env python3
"""layoutlib — shared layout-profile machinery for PaperFactory build tooling.

GC-2026-1111-02 implementation carrier (PF-B3/PF-B10):
  - resolve paper.yaml.layout_profile against templates/layout/registry.yaml
  - merge L0 (draft) -> L1 (venue) -> L2 (paper) key-by-key, logging overrides
  - validate every layer and the merged result against schemas/layout-profile.schema.json
  - enforce structure-identity key rules for L2

Imported by tools/paper.py and tools/make_refdoc.py. Both insert this file's
directory into sys.path explicitly because the recommended invocation is
`python3 -I` (isolated mode does not prepend the script directory).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

GOV_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = GOV_ROOT / "templates" / "layout" / "registry.yaml"
SCHEMA_PATH = GOV_ROOT / "schemas" / "layout-profile.schema.json"

# Keys reserved for L0/L1; presence in L2 (paper overrides) fails the build.
# profile/kind are the L2 *selection* keys and are legal there (PF-B3, GC-02).
STRUCTURE_IDENTITY_KEYS = ("page", "citation", "formulas", "target_venue")

# PF-B13: beyond the selection keys, L2 may only override typography. Every other
# domain (tables/pagination/figures/references/punctuation/author_bio_layout) is a
# venue decision; letting a paper silently override it would bypass the profile.
L2_ALLOWED_KEYS = ("profile", "kind", "typography")

# PF-B13 further limits WHICH typography keys a paper may override: the venue owns
# the role table (fonts / sizes / heading_numbering); a paper may only change the
# body size, the line spacing and the first-line indent.
L2_ALLOWED_TYPOGRAPHY_KEYS = ("body_pt", "line_spacing", "first_line_indent_chars")

L0_PROFILE = "draft"


class LayoutError(Exception):
    """Raised for any profile resolution / merge / validation failure."""


def _load_yaml(path: Path) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError:
        raise LayoutError(f"file not found: {path}") from None
    except yaml.YAMLError as exc:
        raise LayoutError(f"YAML parse error in {path}: {exc}") from None


def load_registry() -> dict:
    reg = _load_yaml(REGISTRY_PATH)
    if not isinstance(reg.get("profiles"), dict) or not reg["profiles"]:
        raise LayoutError(f"registry has no profiles: {REGISTRY_PATH}")
    return reg


def validate_profile(data: dict, source: str) -> None:
    from jsonschema import Draft7Validator

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        msg = "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message[:160]}" for e in errors[:6])
        raise LayoutError(f"profile schema validation failed for {source}: {msg}")


def deep_merge(base: dict, override: dict, log: list, layer: str, prefix: str = "") -> dict:
    """Key-by-key override; every changed key is logged as (key, old, new, source-layer)."""
    merged = dict(base)
    for key, value in override.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value, log, layer, prefix=f"{path}.")
            continue
        if key in merged and merged[key] != value:
            log.append({"key": path, "old": merged[key], "new": value, "source_layer": layer})
        elif key not in merged:
            log.append({"key": path, "old": None, "new": value, "source_layer": layer})
        merged[key] = value
    return merged


def check_l2_overrides(l2: dict) -> None:
    for key in STRUCTURE_IDENTITY_KEYS:
        if key in l2:
            raise LayoutError(
                f"L2 paper config must not contain structure-identity key '{key}' "
                f"(reserved for L0/L1 per PF-B3; L2 only selects profile/kind and overrides typography)"
            )
    for key in l2:
        if key not in L2_ALLOWED_KEYS:
            raise LayoutError(
                f"L2 paper config may only contain {list(L2_ALLOWED_KEYS)} (PF-B13); "
                f"found '{key}'. Venue decisions (tables/pagination/figures/references/"
                f"punctuation/author_bio_layout) must be changed in the venue profile, "
                f"which requires profile versioning."
            )
    typography = l2.get("typography") or {}
    for key in typography:
        if key not in L2_ALLOWED_TYPOGRAPHY_KEYS:
            raise LayoutError(
                f"L2 may only override {list(L2_ALLOWED_TYPOGRAPHY_KEYS)} (PF-B13); "
                f"found 'typography.{key}'. The role table (fonts / sizes / "
                f"heading_numbering) is a venue decision and must be changed in the "
                f"venue profile, which requires profile versioning."
            )
    if l2.get("kind") not in (None, "paper"):
        raise LayoutError(f"L2 profile kind must be 'paper', got: {l2.get('kind')!r}")


def resolve_profile_stack(profile_name: str, paper_l2: dict | None = None) -> dict:
    """Resolve registry -> L0 -> L1 -> L2 merge with override log and validation.

    Returns {"merged": dict, "override_log": list, "layers": {...}, "registry_entry": {...}}.
    """
    registry = load_registry()
    entry = registry["profiles"].get(profile_name)
    if entry is None:
        raise LayoutError(
            f"layout_profile '{profile_name}' not found in registry {REGISTRY_PATH}; "
            f"available: {sorted(registry['profiles'])}"
        )
    layers: dict[str, dict] = {}
    merged: dict = {}

    l0_path = GOV_ROOT / "templates" / "layout" / registry["profiles"][L0_PROFILE]["file"]
    layers["L0"] = _load_yaml(l0_path)
    validate_profile(layers["L0"], f"L0 {l0_path.name}")
    merged = dict(layers["L0"])

    log: list[dict] = []
    if profile_name != L0_PROFILE:
        l1_path = GOV_ROOT / "templates" / "layout" / entry["file"]
        layers["L1"] = _load_yaml(l1_path)
        validate_profile(layers["L1"], f"L1 {l1_path.name}")
        if layers["L1"].get("profile") != profile_name:
            raise LayoutError(f"profile id mismatch in {l1_path}: {layers['L1'].get('profile')!r}")
        merged = deep_merge(merged, layers["L1"], log, "L1")

    if paper_l2 is not None:
        check_l2_overrides(paper_l2)
        validate_profile({**paper_l2, "kind": "paper"}, "L2 build/layout.yaml")
        if paper_l2.get("profile") != profile_name:
            raise LayoutError(
                f"L2 build/layout.yaml selects profile {paper_l2.get('profile')!r} "
                f"but paper.yaml.layout_profile is {profile_name!r}"
            )
        merged = deep_merge(merged, paper_l2, log, "L2")

    validate_profile(merged, "merged")
    return {"merged": merged, "override_log": log, "layers": layers, "registry_entry": entry}


def refdoc_path(entry: dict) -> Path:
    rel = entry.get("refdoc")
    if not rel:
        raise LayoutError(f"registry entry has no refdoc; generate with tools/make_refdoc.py")
    path = GOV_ROOT / "templates" / "layout" / rel
    if not path.exists():
        raise LayoutError(
            f"reference docx missing: {path} — regenerate with tools/make_refdoc.py "
            f"(silent fallback to pandoc defaults is forbidden per PF-B3)"
        )
    return path


# ---------------------------------------------------------------------------
# Shared OOXML checks. Used by tools/make_refdoc.py (self-check) and
# tools/paper.py (build-time landing assertions) so the two cannot drift.
# ---------------------------------------------------------------------------

# pandoc's factory reference doc paints headings in accent1 (#0F4761) and other
# theme colours. None of them may survive into a paper.
_BLUE_HEXES = ("0f4761", "156082", "4472c4", "1f4e79", "2e74b5")


def blue_colour_present(*xml_texts: str) -> bool:
    """True when any theme/accent heading colour is still present.

    Checks the literal hex (case-insensitively), the theme colour reference, and
    scans every supplied part — not only styles.xml.
    """
    for text in xml_texts:
        if not text:
            continue
        low = text.lower()
        if "themecolor=\"accent1\"" in low:
            return True
        for hexval in _BLUE_HEXES:
            if hexval in low:
                return True
    return False


def has_exact_page_field(xml_text: str) -> bool:
    """True when the part carries a PAGE field.

    A substring test would also accept NUMPAGES / SECTIONPAGES, which are a
    different field and must not satisfy the page-number requirement.
    """
    import re

    for tok in re.findall(r"<w:instrText[^>]*>([^<]*)</w:instrText>", xml_text):
        if tok.strip() == "PAGE":
            return True
    return False


def three_line_table_ok(table_style_block: str) -> bool:
    """True for a three-line table style.

    Requires top/bottom single, left/right/insideH/insideV none, and exactly one
    single rule in the firstRow conditional format (the header separator).
    A full grid table must NOT satisfy this.
    """
    import re

    borders = re.search(r"<w:tblBorders>(.*?)</w:tblBorders>", table_style_block, re.S)
    if not borders:
        return False
    inner = borders.group(1)

    def val(tag: str):
        m = re.search(r"<" + tag + r'\b[^>]*w:val="([^"]+)"', inner)
        return m.group(1) if m else None

    if val("w:top") != "single" or val("w:bottom") != "single":
        return False
    for tag in ("w:left", "w:right", "w:insideH", "w:insideV"):
        if val(tag) != "none":
            return False
    first_row = re.search(r'<w:tblStylePr w:type="firstRow">(.*?)</w:tblStylePr>',
                          table_style_block, re.S)
    if not first_row:
        return False
    singles = re.findall(r'<w:(top|bottom|left|right|insideH|insideV)\b[^>]*w:val="single"',
                         first_row.group(1))
    return singles == ["bottom"]


def effective_line_spacing(styles_xml: str) -> int | None:
    """The line spacing actually in force (w:line, 1/240 of a line).

    Normal may define it directly or inherit it from docDefaults; the effective
    value is Normal's when present, otherwise docDefaults'.
    """
    import re

    spacing_re = r'<w:spacing[^>]*w:line="(\d+)"[^>]*w:lineRule="auto"'
    normal = re.search(r'<w:style [^>]*w:styleId="Normal"[^>]*>.*?</w:style>', styles_xml, re.S)
    m = re.search(spacing_re, normal.group(0)) if normal else None
    if m:
        return int(m.group(1))
    dd = re.search(r"<w:docDefaults>.*?</w:docDefaults>", styles_xml, re.S)
    m = re.search(spacing_re, dd.group(0)) if dd else None
    return int(m.group(1)) if m else None


def apply_math_font(settings_xml: str, math_font: str | None) -> str:
    """Set the OMML math font in settings.xml (m:mathPr/m:mathFont).

    Word renders equations with the math font declared here. pandoc emits
    <m:oMath> without per-run fonts AND drops m:mathPr from the reference
    document's settings.xml, so the declaration must be re-applied to the
    produced document as well.
    """
    import re

    if not math_font:
        return settings_xml
    m = re.search(r"<m:mathPr\b.*?</m:mathPr>", settings_xml, re.S)
    if m:
        inner = m.group(0)
        if "m:mathFont" in inner:
            new_inner = re.sub(r"<m:mathFont\b[^>]*/>",
                               f'<m:mathFont m:val="{math_font}" />', inner)
        else:
            new_inner = inner.replace("<m:mathPr>", f'<m:mathPr><m:mathFont m:val="{math_font}" />')
        return settings_xml[:m.start()] + new_inner + settings_xml[m.end():]
    frag = f'<m:mathPr><m:mathFont m:val="{math_font}" /></m:mathPr>'
    idx = settings_xml.rindex("</w:settings>")
    return settings_xml[:idx] + frag + settings_xml[idx:]


def merged_role(merged: dict) -> dict:
    """Flatten the merged profile into the role view used by refdoc generation
    and build assertions (with PF-B10 fallback to body_pt / base fonts)."""
    t = merged.get("typography", {}) or {}
    fonts = dict(t.get("fonts", {}) or {})
    sizes = dict(t.get("sizes", {}) or {})
    body_pt = t.get("body_pt")
    east = t.get("east_asia_font")
    latin = t.get("latin_font")

    def font(role_east: str | None, role_latin: str | None) -> tuple[str, str]:
        return (role_east or east or "", role_latin or latin or "")

    def size(key: str) -> float | None:
        return sizes.get(key, body_pt)

    return {
        "body_pt": body_pt,
        "line_spacing": t.get("line_spacing"),
        "first_line_indent_chars": t.get("first_line_indent_chars", 0),
        "paragraph": t.get("paragraph", {}) or {},
        "heading_numbering": t.get("heading_numbering", {}) or {},
        # GC-2026-1112-01: heiti-face weight / abstract-label alignment. None means
        # the profile does not state the dimension — the generator then keeps its
        # pre-GC-2026-1112-01 behaviour (bold on, label centered) and the landing
        # assertion records the dimension as skipped (PF-B12 no-silent-degradation).
        "heading_bold": t.get("heading_bold"),
        "caption_bold": t.get("caption_bold"),
        "abstract_label_alignment": t.get("abstract_label_alignment"),
        "fonts": {
            "body": font(None, None),
            "title": font(fonts.get("title_east_asia"), fonts.get("title_latin") or latin),
            "author": font(fonts.get("author_east_asia"), latin),
            "affiliation": font(fonts.get("affiliation_east_asia"), latin),
            "abstract": font(fonts.get("abstract_east_asia"), latin),
            "heading": font(fonts.get("heading_east_asia"), fonts.get("heading_latin") or latin),
            "caption": font(fonts.get("caption_east_asia"), latin),
            "table_body": font(fonts.get("table_body_east_asia") or east, latin),
            "reference": font(fonts.get("reference_east_asia") or east, latin),
            "math": (None, fonts.get("math_latin") or latin),
            "code": (None, fonts.get("code_latin") or "Consolas"),
        },
        "sizes": {
            "title_zh": size("title_zh"),
            "title_en": size("title_en"),
            "author": size("author"),
            "affiliation": size("affiliation"),
            "abstract": size("abstract"),
            "abstract_label": size("abstract_label"),
            "keywords": size("keywords"),
            "heading1": size("heading1"),
            "heading2": size("heading2"),
            "heading3": size("heading3"),
            "heading4": size("heading4"),
            "heading5": size("heading5"),
            "body": size("body"),
            "caption": size("caption"),
            "table_body": size("table_body"),
            "table_note": size("table_note"),
            "reference_heading": size("reference_heading"),
            "reference_entry": size("reference_entry"),
            "footnote": size("footnote"),
            "author_bio": size("author_bio"),
            "funding": size("funding"),
            "page_number": size("page_number"),
            "header": size("header"),
            "code": size("code"),
        },
        "figures": merged.get("figures", {}) or {},
        "tables": merged.get("tables", {}) or {},
        "formulas": merged.get("formulas", {}) or {},
        "citation": merged.get("citation", {}) or {},
        "references": merged.get("references", {}) or {},
        "pagination": merged.get("pagination", {}) or {},
        "punctuation": merged.get("punctuation", {}) or {},
        "author_bio_layout": merged.get("author_bio_layout", {}) or {},
        "page": merged.get("page", {}) or {},
    }
