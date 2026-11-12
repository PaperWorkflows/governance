#!/usr/bin/env python3
"""make_refdoc — generate the pandoc reference docx from a layout profile.

PF-B3 implementation carrier (GC-2026-1111-02): the reference docx is GENERATED
from the profile YAML (single source of truth). Never hand-edit files under
templates/layout/refdoc/ — regenerate with this tool and review the diff.

Usage:
    python3 -I tools/make_refdoc.py                # regenerate every registry profile
    python3 -I tools/make_refdoc.py --profile stie # one profile
    python3 -I tools/make_refdoc.py --check         # verify checked-in refdocs match the profiles

Pipeline: pandoc default reference.docx -> stdlib-only OOXML post-processing driven
by the L0+L1 merged profile (L2 never applies to refdocs) -> deterministic zip.

Dependency policy: STANDARD LIBRARY ONLY. The project toolchain runs under
`python3 -I` (isolated mode), which excludes user site-packages; therefore
python-docx / lxml are NOT available here and must not be relied upon. The
governance toolchain's declared dependencies are yaml + jsonschema (both in
/usr/lib/python3/dist-packages).

Determinism: fixed zip timestamps and core.xml dates so regenerated files are
byte-comparable unless the profile actually changed.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import layoutlib  # noqa: E402

FIXED_DATE = (1980, 1, 1, 0, 0, 0)
FIXED_CORE_DATE = "1980-01-01T00:00:00Z"

MM_TO_TWIPS = 56.6929  # 1440 twips / 25.4 mm

PAGE_SIZES = {  # width x height in mm
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
}

HEADER_RID = "rId31"
FOOTER_RID = "rId32"

# Canonical child order inside <w:pPr> (subset of ECMA-376 CT_PPr).
PPR_ORDER = [
    "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
    "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd",
    "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
    "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
    "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl",
    "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
]

# Canonical child order inside <w:rPr> (subset of ECMA-376 CT_RPr).
RPR_ORDER = [
    "w:rStyle", "w:rFonts", "w:b", "w:bCs", "w:i", "w:iCs", "w:caps",
    "w:smallCaps", "w:strike", "w:dstrike", "w:outline", "w:shadow",
    "w:emboss", "w:imprint", "w:noProof", "w:snapToGrid", "w:vanish",
    "w:webHidden", "w:color", "w:spacing", "w:w", "w:kern", "w:position",
    "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect", "w:bdr", "w:shd",
    "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang",
]


def default_reference_bytes() -> bytes:
    result = subprocess.run(
        ["pandoc", "--print-default-data-file", "reference.docx"],
        capture_output=True, timeout=30,
    )
    if result.returncode != 0 or not result.stdout:
        raise layoutlib.LayoutError(f"cannot get pandoc default reference.docx: {result.stderr[:200]}")
    return result.stdout


# ------------------------------------------------------------------ XML helpers

def _split_top_level(inner: str) -> list[tuple[str, str]]:
    """Split an element's inner XML into (tagname, xml) children."""
    out: list[tuple[str, str]] = []
    i, n = 0, len(inner)
    while i < n:
        if inner[i] != "<":
            i += 1
            continue
        m = re.match(r"<([A-Za-z0-9:]+)", inner[i:])
        if not m:
            i += 1
            continue
        tag = m.group(1)
        j = inner.index(">", i)
        if inner[j - 1] == "/":
            out.append((tag, inner[i:j + 1]))
            i = j + 1
            continue
        depth, k = 1, j + 1
        while depth > 0:
            close = inner.find("</%s>" % tag, k)
            if close == -1:
                raise layoutlib.LayoutError(f"unbalanced <{tag}> in OOXML fragment")
            open_same = inner.find("<%s" % tag, k)
            if open_same != -1 and open_same < close:
                depth += 1
                k = inner.index(">", open_same) + 1
                continue
            depth -= 1
            k = close + len(tag) + 3
        out.append((tag, inner[i:k]))
        i = k
    return out


def _insert_ordered(inner: str, tag: str, xml: str, order: list[str]) -> str:
    """Insert (or replace) a single child element honouring the schema order."""
    children = _split_top_level(inner)
    children = [(t, x) for t, x in children if t != tag]
    try:
        rank = order.index(tag)
    except ValueError:
        rank = len(order)
    pos = len(children)
    for idx, (t, _x) in enumerate(children):
        tr = order.index(t) if t in order else len(order)
        if tr > rank:
            pos = idx
            break
    children.insert(pos, (tag, xml))
    return "".join(x for _t, x in children)


def _find_element(xml: str, tag: str) -> tuple[int, int] | None:
    """Return (start, end) span of the first <tag ...>...</tag> or <tag .../>."""
    m = re.search(r"<%s(?:\s[^>]*)?>" % re.escape(tag), xml)
    if not m:
        return None
    if xml[m.end() - 2] == "/":
        return m.start(), m.end()
    close = xml.find("</%s>" % tag, m.end())
    if close == -1:
        return None
    return m.start(), close + len(tag) + 3


def _element_inner(xml: str, tag: str) -> str:
    span = _find_element(xml, tag)
    if span is None:
        return ""
    s, e = span
    frag = xml[s:e]
    if frag.endswith("/>"):
        return ""
    open_end = frag.index(">") + 1
    return frag[open_end:frag.rindex("</")]


def _replace_element(xml: str, tag: str, new_frag: str) -> str:
    span = _find_element(xml, tag)
    if span is None:
        return xml
    s, e = span
    return xml[:s] + new_frag + xml[e:]


def _ensure_element(block: str, tag: str, before_tags: tuple[str, ...]) -> str:
    """Ensure <tag> exists in a style block; create it before the first of before_tags."""
    if _find_element(block, tag) is not None:
        return block
    for other in before_tags:
        span = _find_element(block, other)
        if span is not None:
            s, _e = span
            return block[:s] + f"<{tag}></{tag}>" + block[s:]
    idx = block.rindex("</w:style>")
    return block[:idx] + f"<{tag}></{tag}>" + block[idx:]


def _rfonts_xml(east_asia: str | None, latin: str | None) -> str:
    attrs = []
    if latin:
        attrs += [f'w:ascii="{latin}"', f'w:hAnsi="{latin}"', f'w:cs="{latin}"']
    if east_asia:
        attrs.append(f'w:eastAsia="{east_asia}"')
    return "<w:rFonts " + " ".join(attrs) + "/>"


def _apply_rpr(block: str, *, fonts: tuple[str | None, str | None] | None = None,
               size_pt: float | None = None, bold: bool | None = None,
               italic: bool | None = None, black: bool = False) -> str:
    block = _ensure_element(block, "w:rPr", ("w:tblPr", "w:trPr", "w:tcPr", "w:tblStylePr"))
    span = _find_element(block, "w:rPr")
    assert span is not None
    s, e = span
    frag = block[s:e]
    if frag.endswith("/>"):
        inner = ""
        close = ""
    else:
        inner = frag[frag.index(">") + 1: frag.rindex("</")]
        close = "</w:rPr>"
    if fonts is not None:
        inner = _insert_ordered(inner, "w:rFonts", _rfonts_xml(fonts[0], fonts[1]), RPR_ORDER)
    if size_pt is not None:
        hp = str(int(round(size_pt * 2)))
        inner = _insert_ordered(inner, "w:sz", f'<w:sz w:val="{hp}"/>', RPR_ORDER)
        inner = _insert_ordered(inner, "w:szCs", f'<w:szCs w:val="{hp}"/>', RPR_ORDER)
    if bold is not None:
        val = "1" if bold else "0"
        inner = _insert_ordered(inner, "w:b", f'<w:b w:val="{val}"/>', RPR_ORDER)
        inner = _insert_ordered(inner, "w:bCs", f'<w:bCs w:val="{val}"/>', RPR_ORDER)
    if italic is not None:
        val = "1" if italic else "0"
        inner = _insert_ordered(inner, "w:i", f'<w:i w:val="{val}"/>', RPR_ORDER)
        inner = _insert_ordered(inner, "w:iCs", f'<w:iCs w:val="{val}"/>', RPR_ORDER)
    if black:
        inner = _insert_ordered(inner, "w:color", '<w:color w:val="000000"/>', RPR_ORDER)
    new_frag = f"<w:rPr>{inner}</w:rPr>"
    return block[:s] + new_frag + block[e:]


def _apply_ppr(block: str, *, align: str | None = None,
               first_line_chars: float | None = None, first_line_pt: float | None = None,
               hanging_cm: float | None = None, space_before_pt: float | None = None,
               space_after_pt: float | None = None, line_spacing: float | None = None,
               keep_with_next: bool | None = None,
               keep_lines: bool | None = None) -> str:
    block = _ensure_element(block, "w:pPr", ("w:rPr", "w:tblPr", "w:trPr", "w:tcPr", "w:tblStylePr"))
    span = _find_element(block, "w:pPr")
    assert span is not None
    s, e = span
    frag = block[s:e]
    if frag.endswith("/>"):
        inner, close = "", ""
    else:
        inner = frag[frag.index(">") + 1: frag.rindex("</")]
        close = "</w:pPr>"
    if keep_with_next is not None:
        inner = _insert_ordered(inner, "w:keepNext",
                                '<w:keepNext w:val="%s"/>' % ("1" if keep_with_next else "0"), PPR_ORDER)
    if keep_lines is not None:
        # Cancel the inherited keepLines: a long abstract must be allowed to break
        # across pages, otherwise it is pushed whole to the next page and leaves a
        # third of the first page empty (found on P2, 2026-11-12).
        inner = _insert_ordered(inner, "w:keepLines",
                                '<w:keepLines w:val="%s"/>' % ("1" if keep_lines else "0"), PPR_ORDER)
    if any(v is not None for v in (space_before_pt, space_after_pt, line_spacing)):
        attrs = []
        if space_before_pt is not None:
            attrs.append(f'w:before="{int(round(space_before_pt * 20))}"')
        if space_after_pt is not None:
            attrs.append(f'w:after="{int(round(space_after_pt * 20))}"')
        if line_spacing is not None:
            attrs.append(f'w:line="{int(round(line_spacing * 240))}"')
            attrs.append('w:lineRule="auto"')
        inner = _insert_ordered(inner, "w:spacing", "<w:spacing " + " ".join(attrs) + "/>", PPR_ORDER)
    if first_line_chars is not None or hanging_cm is not None:
        attrs = []
        if first_line_chars is not None:
            attrs.append(f'w:firstLineChars="{int(round(first_line_chars * 100))}"')
            attrs.append(f'w:firstLine="{int(round((first_line_pt or 0) * 20))}"')
        if hanging_cm is not None:
            tw = str(int(round(hanging_cm * 567)))
            attrs.append(f'w:left="{tw}"')
            attrs.append(f'w:hanging="{tw}"')
        inner = _insert_ordered(inner, "w:ind", "<w:ind " + " ".join(attrs) + "/>", PPR_ORDER)
    if align is not None:
        inner = _insert_ordered(inner, "w:jc", f'<w:jc w:val="{align}"/>', PPR_ORDER)
    new_frag = f"<w:pPr>{inner}</w:pPr>"
    return block[:s] + new_frag + block[e:]


def _neutralise_theme_colours(styles: str) -> str:
    """Replace pandoc's blue theme heading colour with plain black everywhere.

    Pandoc's factory reference doc paints headings in accent1 (#0F4761). A paper
    must never inherit that, and PF-B3 forbids silent style degradation, so the
    sweep is unconditional rather than limited to the styles we patch.
    """
    def repl(m: re.Match) -> str:
        attrs = m.group(1)
        if "0F4761" not in attrs and "themeColor=\"accent1\"" not in attrs:
            return m.group(0)
        attrs = re.sub(r'\s*w:themeColor="[^"]*"', "", attrs)
        attrs = re.sub(r'\s*w:themeShade="[^"]*"', "", attrs)
        attrs = re.sub(r'\s*w:themeTint="[^"]*"', "", attrs)
        attrs = re.sub(r'w:val="[^"]*"', 'w:val="000000"', attrs)
        return f"<w:color{attrs}/>"

    return re.sub(r"<w:color([^>]*)/>", repl, styles)


def _ensure_style(styles: str, style_id: str, name: str, **kwargs) -> str:
    """Create a minimal paragraph style if absent, then patch it (see _patch_style).

    pandoc's base reference doc lacks venue-specific roles (e.g. AuthorBio/S17);
    profiles declare them, so the generator materialises the style on demand.
    """
    pattern = r'<w:style [^>]*w:styleId="%s"[^>]*>' % re.escape(style_id)
    if re.search(pattern, styles):
        return _patch_style(styles, style_id, **kwargs)
    block = (f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{style_id}">'
             f'<w:name w:val="{name}"/><w:basedOn w:val="Normal"/>'
             f'<w:pPr></w:pPr><w:rPr></w:rPr></w:style>')
    idx = styles.rindex("</w:styles>")
    return _patch_style(styles[:idx] + block + styles[idx:], style_id, **kwargs)


def _patch_style(styles: str, style_id: str, **kwargs) -> str:
    """Patch one <w:style> block inside styles.xml."""
    pattern = r'<w:style [^>]*w:styleId="%s"[^>]*>.*?</w:style>' % re.escape(style_id)
    m = re.search(pattern, styles, re.S)
    if not m:
        return styles
    block = m.group(0)
    if "rpr" in kwargs:
        block = _apply_rpr(block, **kwargs["rpr"])
    if "ppr" in kwargs:
        block = _apply_ppr(block, **kwargs["ppr"])
    return styles[:m.start()] + block + styles[m.end():]


# ------------------------------------------------------------------ table style

def _border_el(tag: str, sz_pt: float) -> str:
    return (f'<{tag} w:val="single" w:sz="{int(round(sz_pt * 8))}" '
            f'w:space="0" w:color="000000"/>')


def _none_border(tag: str) -> str:
    return f'<{tag} w:val="none" w:sz="0" w:space="0" w:color="auto"/>'


def _apply_three_line(styles: str, tables_cfg: dict) -> str:
    widths = tables_cfg.get("border_widths_pt") or {"top": 1.0, "header": 0.5, "bottom": 1.0}
    pattern = r'<w:style [^>]*w:styleId="Table"[^>]*>.*?</w:style>'
    m = re.search(pattern, styles, re.S)
    if not m:
        return styles
    block = m.group(0)

    borders = ("<w:tblBorders>"
               + _border_el("w:top", widths.get("top", 1.0))
               + _none_border("w:left")
               + _border_el("w:bottom", widths.get("bottom", 1.0))
               + _none_border("w:right")
               + _none_border("w:insideH")
               + _none_border("w:insideV")
               + "</w:tblBorders>")

    tbl_pr = _element_inner(block, "w:tblPr")
    if not tbl_pr:
        block = _ensure_element(block, "w:tblPr", ("w:tblStylePr",))
        tbl_pr = _element_inner(block, "w:tblPr")
    # tblBorders sits after tblInd and before tblCellMar (CT_TblPrBase order).
    inner = _insert_ordered(tbl_pr, "w:tblBorders", borders, [
        "w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual",
        "w:tblStyleRowBandSize", "w:tblStyleColBandSize", "w:tblW", "w:jc",
        "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd", "w:tblLayout",
        "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription",
    ])
    block = _replace_element(block, "w:tblPr", f"<w:tblPr>{inner}</w:tblPr>")

    # header-row rule via conditional formatting (pandoc tables set firstRow look).
    # C-1 header_fill (journal-measured 2026-11-12): when tables.header_fill is not
    # "none", paint the header-row cells with a w:shd fill (e.g. E5EBF0) — the light
    # grey header band the model journal shows. Text colour is left untouched (black
    # on the fill, as measured). Absent/"none" writes no w:shd (previous behaviour).
    header_fill = tables_cfg.get("header_fill") or "none"
    fill_xml = ""
    if header_fill != "none":
        fill = re.sub(r"^#", "", str(header_fill)).strip() or "E5EBF0"
        fill_xml = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill.upper()}"/>'
    block = re.sub(r"<w:tblStylePr\b.*?</w:tblStylePr>", "", block, flags=re.S)
    style_pr = (
        '<w:tblStylePr w:type="firstRow"><w:tcPr><w:tcBorders>'
        + _border_el("w:bottom", widths.get("header", 0.5))
        + "</w:tcBorders>"
        + fill_xml
        + '<w:vAlign w:val="bottom"/></w:tcPr></w:tblStylePr>'
    )
    idx = block.rindex("</w:style>")
    block = block[:idx] + style_pr + block[idx:]
    return styles[:m.start()] + block + styles[m.end():]


# -------------------------------------------------------------- header / footer

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _run_props_xml(latin: str, east_asia: str, pt: float) -> str:
    hp = str(int(round(pt * 2)))
    return (f'<w:rPr><w:rFonts w:ascii="{latin}" w:hAnsi="{latin}" w:cs="{latin}" '
            f'w:eastAsia="{east_asia}"/><w:sz w:val="{hp}"/><w:szCs w:val="{hp}"/></w:rPr>')


_PAGE_FIELD_XML = (
    '<w:r>{rp}<w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r>{rp}<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
    '<w:r>{rp}<w:fldChar w:fldCharType="end"/></w:r>'
)

# Page-number placement per pagination.page_number_position. "none" means the
# part is not created at all; the value must agree with the schema enum.
_PAGE_FIELD_ALIGN = {
    "footer_center": ("w:ftr", "center"),
    "footer_right": ("w:ftr", "right"),
    "header_right": ("w:hdr", "right"),
}


def _page_field_part(kind: str, align: str, latin: str, east_asia: str, pt: float) -> bytes:
    rp = _run_props_xml(latin, east_asia, pt)
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<{kind} xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
        f'<w:p><w:pPr><w:pStyle w:val="{"Footer" if kind == "w:ftr" else "Header"}"/>'
        f'<w:jc w:val="{align}"/></w:pPr>'
        + _PAGE_FIELD_XML.format(rp=rp)
        + "</w:p></"
        + kind
        + ">"
    )
    return xml.encode("utf-8")


def _footer_xml(latin: str, east_asia: str, pt: float, position: str = "footer_center") -> bytes:
    kind, align = _PAGE_FIELD_ALIGN.get(position, ("w:ftr", "center"))
    return _page_field_part(kind, align, latin, east_asia, pt)


def _header_xml(latin: str, east_asia: str, pt: float, mode: str = "title_center") -> bytes:
    """Running head. `title_center` carries the paper title (replaced at build
    time); `journal` carries a venue/label placeholder."""
    rp = _run_props_xml(latin, east_asia, pt)
    text = "{{PAPER_TITLE}}" if mode != "journal" else "{{JOURNAL_LABEL}}"
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:hdr xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
        '<w:p><w:pPr><w:pStyle w:val="Header"/><w:jc w:val="center"/></w:pPr>'
        f'<w:r>{rp}<w:t>{text}</w:t></w:r>'
        "</w:p></w:hdr>"
    )
    return xml.encode("utf-8")


def _header_footer_styles(styles: str, header_pt: float, page_pt: float) -> str:
    def mk(style_id: str, name: str, pt: float) -> str:
        hp = str(int(round(pt * 2)))
        return (
            f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{style_id}">'
            f'<w:name w:val="{name}"/><w:basedOn w:val="Normal"/>'
            f'<w:pPr><w:jc w:val="center"/></w:pPr>'
            f'<w:rPr><w:sz w:val="{hp}"/><w:szCs w:val="{hp}"/></w:rPr></w:style>'
        )
    extra = mk("Header", "header", header_pt) + mk("Footer", "footer", page_pt)
    idx = styles.rindex("</w:styles>")
    return styles[:idx] + extra + styles[idx:]


# ------------------------------------------------------------------ section/doc

def _apply_section(doc_xml: str, page_cfg: dict, refs: dict[str, str]) -> str:
    """Rewrite the section properties.

    `refs` maps "header"/"footer" to a relationship id, and contains only the
    parts that were actually created. Emitting a reference to a part that does
    not exist (or has no relationship) yields a package whose relationship graph
    is not closed — LibreOffice/Word then refuse to open it. Hence the references
    are driven by what was created, never by a fixed constant.
    """
    size = page_cfg.get("size", "A4")
    w_mm, h_mm = PAGE_SIZES.get(size, PAGE_SIZES["A4"])
    margin = page_cfg.get("margin", {}) or {}

    def tw(mm: float) -> int:
        return int(round(mm * MM_TO_TWIPS))

    head = ""
    if refs.get("header"):
        head += f'<w:headerReference w:type="default" r:id="{refs["header"]}"/>'
    if refs.get("footer"):
        head += f'<w:footerReference w:type="default" r:id="{refs["footer"]}"/>'

    sect = (
        "<w:sectPr>"
        + head
        + '<w:footnotePr><w:numRestart w:val="eachSect"/></w:footnotePr>'
        f'<w:pgSz w:w="{tw(w_mm)}" w:h="{tw(h_mm)}"/>'
        f'<w:pgMar w:top="{tw(margin.get("top", 25.4))}" w:bottom="{tw(margin.get("bottom", 25.4))}" '
        f'w:left="{tw(margin.get("left", 25.4))}" w:right="{tw(margin.get("right", 25.4))}" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        '<w:cols w:space="425"/>'
        # docGrid removed: grid snapping inflated CJK advance widths (9pt rendered
        # ~9.7pt pitch), breaking size verification (PF-B12, 2026-11-11)
        "</w:sectPr>"
    )
    span = _find_element(doc_xml, "w:sectPr")
    if span is None:
        idx = doc_xml.rindex("</w:body>")
        return doc_xml[:idx] + sect + doc_xml[idx:]
    s, e = span
    return doc_xml[:s] + sect + doc_xml[e:]


def _apply_doc_defaults(styles: str, role: dict) -> str:
    span = _find_element(styles, "w:docDefaults")
    if span is None:
        return styles
    s, e = span
    frag = styles[s:e]
    inner = _element_inner(frag, "w:docDefaults")

    body_east, body_latin = role["fonts"]["body"]
    rprd = _element_inner(inner, "w:rPrDefault")
    rpr = _element_inner(rprd, "w:rPr")
    rpr = _insert_ordered(rpr, "w:rFonts", _rfonts_xml(body_east, body_latin), RPR_ORDER)
    if role["body_pt"]:
        hp = str(int(round(role["body_pt"] * 2)))
        rpr = _insert_ordered(rpr, "w:sz", f'<w:sz w:val="{hp}"/>', RPR_ORDER)
        rpr = _insert_ordered(rpr, "w:szCs", f'<w:szCs w:val="{hp}"/>', RPR_ORDER)
    rprd = _replace_element(rprd, "w:rPr", f"<w:rPr>{rpr}</w:rPr>")
    inner = _replace_element(inner, "w:rPrDefault", f"<w:rPrDefault>{rprd}</w:rPrDefault>")

    pprd = _element_inner(inner, "w:pPrDefault")
    ppr = _element_inner(pprd, "w:pPr")
    attrs = ['w:before="0"', 'w:after="0"']
    if role["line_spacing"]:
        attrs.append(f'w:line="{int(round(role["line_spacing"] * 240))}"')
        attrs.append('w:lineRule="auto"')
    ppr = _insert_ordered(ppr, "w:spacing", "<w:spacing " + " ".join(attrs) + "/>", PPR_ORDER)
    pprd = _replace_element(pprd, "w:pPr", f"<w:pPr>{ppr}</w:pPr>")
    inner = _replace_element(inner, "w:pPrDefault", f"<w:pPrDefault>{pprd}</w:pPrDefault>")

    new_frag = f"<w:docDefaults>{inner}</w:docDefaults>"
    return styles[:s] + new_frag + styles[e:]


# --------------------------------------------------------------- package plumbing

def _apply_math_font(settings_xml: str, math_font: str | None) -> str:
    """Set the OMML math font in settings.xml (m:mathPr/m:mathFont).

    Word renders equations with the math font declared here; without it the
    formulas fall back to the body's Latin font. pandoc emits <m:oMath> without
    per-run fonts, so this is the only place the math font can be applied.
    """
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


def _assert_relationship_closure(doc_xml: str, rels: str, parts: dict[str, bytes]) -> None:
    """Every header/footer reference in sectPr must resolve to a relationship of
    the matching type whose target part exists. A dangling reference produces a
    package that LibreOffice/Word refuse to open."""
    rel_map = {}
    for m in re.finditer(r'<Relationship Type="([^"]+)" Id="([^"]+)" Target="([^"]+)"', rels):
        rel_map[m.group(2)] = (m.group(1), m.group(3))
    for ref_kind, tag in (("header", "w:headerReference"), ("footer", "w:footerReference")):
        for m in re.finditer(r"<" + tag + r'\b[^>]*r:id="([^"]+)"', doc_xml):
            rid = m.group(1)
            if rid not in rel_map:
                raise layoutlib.LayoutError(
                    f"sectPr {tag} points at {rid}, which has no relationship")
            rel_type, target = rel_map[rid]
            if not rel_type.endswith("/" + ref_kind):
                raise layoutlib.LayoutError(
                    f"sectPr {tag} points at {rid} whose relationship type is {rel_type!r}, "
                    f"expected a {ref_kind} relationship")
            part = "word/" + target.lstrip("/")
            if part not in parts:
                raise layoutlib.LayoutError(
                    f"sectPr {tag} points at {rid} -> {part}, which is not in the package")


def _next_rid(rels: str) -> str:
    """First unused rIdNNN in the document relationships (never assume a fixed id)."""
    used = {int(m) for m in re.findall(r'Id="rId(\d+)"', rels)}
    n = 1
    while n in used:
        n += 1
    return f"rId{n}"


def _add_relationship(rels: str, rid: str, rel_type: str, target: str) -> str:
    """Add a relationship. An occupied Id is an error, never a silent skip —
    a silent skip leaves sectPr pointing at an unrelated part."""
    if f'Id="{rid}"' in rels:
        raise layoutlib.LayoutError(
            f"relationship Id {rid} already exists; refusing to reuse it "
            f"(it would point sectPr at an unrelated part)"
        )
    rel = (f'<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/'
           f'relationships/{rel_type}" Id="{rid}" Target="{target}" />')
    idx = rels.rindex("</Relationships>")
    return rels[:idx] + rel + rels[idx:]


def _add_content_type(ct: str, part: str, kind: str) -> str:
    if f'PartName="/{part}"' in ct:
        return ct
    override = (f'<Override PartName="/{part}" ContentType="application/vnd.'
                f'openxmlformats-officedocument.wordprocessingml.{kind}+xml" />')
    idx = ct.rindex("</Types>")
    return ct[:idx] + override + ct[idx:]


def _deterministic_zip(parts: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for name in sorted(parts):
            payload = parts[name]
            if name == "docProps/core.xml":
                text = payload.decode("utf-8")
                text = re.sub(r"(<dcterms:created[^>]*>)[^<]*(</dcterms:created>)",
                              r"\g<1>" + FIXED_CORE_DATE + r"\g<2>", text)
                text = re.sub(r"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                              r"\g<1>" + FIXED_CORE_DATE + r"\g<2>", text)
                payload = text.encode("utf-8")
            info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            dst.writestr(info, payload)
    return out.getvalue()


# ------------------------------------------------------------------ main transform

def build_refdoc(profile_name: str, base_bytes: bytes) -> tuple[bytes, dict]:
    stack = layoutlib.resolve_profile_stack(profile_name)
    role = layoutlib.merged_role(stack["merged"])

    src = zipfile.ZipFile(io.BytesIO(base_bytes))
    parts = {name: src.read(name) for name in src.namelist()}

    styles = parts["word/styles.xml"].decode("utf-8")
    doc_xml = parts["word/document.xml"].decode("utf-8")
    rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
    ctypes = parts["[Content_Types].xml"].decode("utf-8")

    f, s, p = role["fonts"], role["sizes"], role["paragraph"]
    indent_chars = role["first_line_indent_chars"] or 0
    body_pt = role["body_pt"] or 10.5
    # GC-2026-1112-01: heiti (黑体) faces carry their own weight — setting bold on
    # top of them produces faux-bold (double-struck) strokes. The profile decides;
    # absence keeps the pre-GC-2026-1112-01 behaviour (bold on, label centered).
    heading_bold = True if role.get("heading_bold") is None else role["heading_bold"]
    caption_bold = True if role.get("caption_bold") is None else role["caption_bold"]
    label_align = role.get("abstract_label_alignment") or "center"

    # 1. doc defaults
    styles = _apply_doc_defaults(styles, role)

    # 2. table rule style
    if (role["tables"] or {}).get("style") == "three_line":
        styles = _apply_three_line(styles, role["tables"])

    # 3. paragraph styles
    styles = _patch_style(styles, "Normal",
                           rpr={"fonts": f["body"], "size_pt": s.get("body")},
                           ppr={"align": "both",
                                "first_line_chars": indent_chars,
                                "first_line_pt": indent_chars * body_pt,
                                "space_before_pt": p.get("spacing_before_pt", 0),
                                "space_after_pt": p.get("spacing_after_pt", 0),
                                "line_spacing": role["line_spacing"]})
    styles = _patch_style(styles, "Title",
                           rpr={"fonts": f["title"], "size_pt": s.get("title_zh"), "black": True},
                           ppr={"align": "center", "first_line_chars": 0, "first_line_pt": 0,
                                "space_before_pt": 0, "space_after_pt": 12, "keep_with_next": True})
    styles = _patch_style(styles, "Subtitle",
                           rpr={"fonts": f["title"], "size_pt": s.get("title_en"), "black": True},
                           ppr={"align": "center", "first_line_chars": 0, "first_line_pt": 0,
                                "space_before_pt": 0, "space_after_pt": 12, "keep_with_next": True})
    # linked character styles carry the same face; they also hold pandoc's default
    # blue heading colour and theme fonts, which must not survive into a paper.
    styles = _patch_style(styles, "TitleChar",
                           rpr={"fonts": f["title"], "size_pt": s.get("title_zh"), "black": True})
    styles = _patch_style(styles, "SubtitleChar",
                           rpr={"fonts": f["title"], "size_pt": s.get("title_en"), "black": True})
    styles = _patch_style(styles, "Author",
                           rpr={"fonts": f["author"], "size_pt": s.get("author"), "black": True},
                           ppr={"align": "center", "first_line_chars": 0, "first_line_pt": 0,
                                "space_before_pt": 0, "space_after_pt": 0})
    styles = _patch_style(styles, "AbstractTitle",
                           rpr={"fonts": f["heading"], "size_pt": s.get("abstract_label"),
                                "bold": heading_bold, "black": True},
                           ppr={"align": label_align, "first_line_chars": 0, "first_line_pt": 0,
                                "space_before_pt": 6, "space_after_pt": 0,
                                "keep_with_next": True, "keep_lines": False})
    styles = _patch_style(styles, "Abstract",
                           rpr={"fonts": f["abstract"], "size_pt": s.get("abstract"), "black": True},
                           ppr={"align": "both", "first_line_chars": 0, "first_line_pt": 0,
                                "space_before_pt": 0, "space_after_pt": 6,
                                "keep_with_next": False,  # break keepNext chain: abstract body must not
                                # drag keywords/intro to the next page (PF-B6 round 2, 2026-11-11)
                                "keep_lines": False})  # cancel the inherited keepLines: a long abstract
                                # is otherwise pushed whole to the next page, leaving page 1 a third
                                # empty (found on P2, 2026-11-12)

    heading_space = {1: (12, 6), 2: (6, 3), 3: (6, 3), 4: (3, 0), 5: (3, 0)}
    for level in range(1, 6):
        before, after = heading_space.get(level, (3, 0))
        styles = _patch_style(styles, f"Heading{level}",
                               rpr={"fonts": f["heading"], "size_pt": s.get(f"heading{level}"),
                                    "bold": heading_bold, "italic": False, "black": True},
                               ppr={"align": "left", "first_line_chars": 0, "first_line_pt": 0,
                                    "space_before_pt": before, "space_after_pt": after,
                                    "keep_with_next": True})
        # linked character style carries the same face; it also holds pandoc's
        # default blue heading colour, which must not survive into a paper.
        styles = _patch_style(styles, f"Heading{level}Char",
                               rpr={"fonts": f["heading"], "size_pt": s.get(f"heading{level}"),
                                    "bold": heading_bold, "italic": False, "black": True})

    # Safety net: no style may keep pandoc's blue theme heading colour.
    styles = _neutralise_theme_colours(styles)

    for name in ("Caption", "ImageCaption", "TableCaption"):
        styles = _patch_style(styles, name,
                               rpr={"fonts": f["caption"], "size_pt": s.get("caption"),
                                    "italic": False, "bold": caption_bold, "black": True},
                               ppr={"align": "center", "first_line_chars": 0, "first_line_pt": 0,
                                    "space_before_pt": 3, "space_after_pt": 6,
                                    "keep_with_next": name == "TableCaption"})

    refs = role["references"] or {}
    styles = _patch_style(styles, "Bibliography",
                           rpr={"fonts": f["reference"], "size_pt": refs.get("entry_pt", s.get("reference_entry")),
                                "black": True},
                           ppr={"align": "both",
                                "hanging_cm": refs.get("hanging_indent_cm", 0.74) if refs.get("hanging_indent", True) else None,
                                "space_before_pt": 0, "space_after_pt": refs.get("entry_spacing_pt", 0)})

    styles = _patch_style(styles, "BlockText",
                           rpr={"fonts": f["abstract"], "size_pt": s.get("abstract"), "black": True},
                           ppr={"align": "both", "first_line_chars": 0, "first_line_pt": 0,
                                "space_before_pt": 0, "space_after_pt": 6})

    # AuthorBio: venue S17 role — profile author_bio_layout driven: body font family, 9pt,
    # justify, first-line indent per profile (stie current: first_line_indent_chars=0 顶格,
    # one_paragraph_per_author=false 即首作者/通信作者各一段、其余作者合并一段；键缺省时
    # 回落默认 2 chars); created on demand because pandoc's base reference doc has no such style.
    apl = role.get("author_bio_layout") or {}
    styles = _ensure_style(styles, "AuthorBio", "author bio",
                           rpr={"fonts": f["body"], "size_pt": apl.get("pt", s.get("author_bio")),
                                "black": True},
                           ppr={"align": "both",
                                "first_line_chars": apl.get("first_line_indent_chars", 2),
                                "first_line_pt": apl.get("first_line_indent_chars", 2) * (apl.get("pt", s.get("author_bio")) or 9),
                                "space_before_pt": 0, "space_after_pt": 3})

    # Affiliation: venue role (GC-2026-1112-06) driven by the profile authors
    # domain — profile fonts.affiliation_east_asia / latin + sizes.affiliation,
    # falling back to the body slot when the profile states no affiliation size.
    # Centered, NOT bold, line spacing follows the body (范本 §2 line 4/8: affiliation
    # list centered). Generated ONLY when the profile declares the authors domain:
    # draft/gbt7713 carry affiliation fonts but no authors domain and must remain
    # byte-identical.
    if "authors" in stack["merged"]:
        aff_pt = s.get("affiliation") or body_pt
        styles = _ensure_style(styles, "Affiliation", "affiliation",
                               rpr={"fonts": f["affiliation"], "size_pt": aff_pt,
                                    "bold": False, "black": True},
                               ppr={"align": "center", "first_line_chars": 0, "first_line_pt": 0,
                                    "space_before_pt": 0, "space_after_pt": 0,
                                    "line_spacing": role["line_spacing"]})

    styles = _patch_style(styles, "SourceCode",
                           rpr={"fonts": (None, f["code"][1]), "size_pt": s.get("code")})
    styles = _patch_style(styles, "VerbatimChar",
                           rpr={"fonts": (None, f["code"][1]), "size_pt": s.get("code")})
    styles = _patch_style(styles, "FootnoteText",
                           rpr={"size_pt": s.get("footnote")})

    # 4. header / footer styles + parts
    pagination = role["pagination"] or {}
    styles = _header_footer_styles(styles, s.get("header") or 9, s.get("page_number") or 7.5)
    latin_body = f["body"][1] or "Times New Roman"
    east_body = f["body"][0] or "宋体"
    refs: dict[str, str] = {}
    page_pos = pagination.get("page_number_position", "footer_center")
    header_mode = pagination.get("header", "title_center")
    if page_pos != "none":
        kind, _align = _PAGE_FIELD_ALIGN.get(page_pos, ("w:ftr", "center"))
        part_name = "word/footer1.xml" if kind == "w:ftr" else "word/header1.xml"
        rel_kind = "footer" if kind == "w:ftr" else "header"
        parts[part_name] = _page_field_part(kind, _align, latin_body, east_body,
                                            s.get("page_number") or 7.5)
        rid = _next_rid(rels)
        rels = _add_relationship(rels, rid, rel_kind, part_name.split("/", 1)[1])
        ctypes = _add_content_type(ctypes, part_name, rel_kind)
        refs["footer" if kind == "w:ftr" else "header"] = rid
    if header_mode != "none":
        parts["word/header1.xml"] = _header_xml(latin_body, east_body, s.get("header") or 9, header_mode)
        rid = _next_rid(rels)
        rels = _add_relationship(rels, rid, "header", "header1.xml")
        ctypes = _add_content_type(ctypes, "word/header1.xml", "header")
        refs["header"] = rid

    # 5. section geometry — references only the parts that were actually created
    doc_xml = _apply_section(doc_xml, role["page"], refs)

    # 5b. relationship closure: every header/footer reference must resolve to a
    # relationship of the right type whose target part exists in the package.
    _assert_relationship_closure(doc_xml, rels, parts)

    parts["word/styles.xml"] = styles.encode("utf-8")
    parts["word/document.xml"] = doc_xml.encode("utf-8")
    parts["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    parts["[Content_Types].xml"] = ctypes.encode("utf-8")
    # OMML math font: pandoc emits <m:oMath> without per-run fonts, so the only
    # place the math font can be applied is settings.xml / m:mathPr / m:mathFont.
    if "word/settings.xml" in parts:
        parts["word/settings.xml"] = _apply_math_font(
            parts["word/settings.xml"].decode("utf-8"),
            (role["fonts"].get("math") or (None, None))[1]).encode("utf-8")

    data = _deterministic_zip(parts)
    checks = self_check(data, role)
    return data, checks


def self_check(data: bytes, role: dict) -> dict:
    z = zipfile.ZipFile(io.BytesIO(data))
    styles = z.read("word/styles.xml").decode("utf-8")
    docxml = z.read("word/document.xml").decode("utf-8")
    names = z.namelist()
    checks: dict[str, object] = {}

    def style_block(sid: str) -> str:
        m = re.search(r'<w:style [^>]*w:styleId="%s"[^>]*>.*?</w:style>' % re.escape(sid), styles, re.S)
        return m.group(0) if m else ""

    def sz_of(sid: str):
        m = re.search(r'<w:sz w:val="(\d+)"', style_block(sid))
        return int(m.group(1)) / 2 if m else None

    checks["title_pt"] = sz_of("Title")
    checks["title_pt_expected"] = role["sizes"].get("title_zh")
    checks["heading1_pt"] = sz_of("Heading1")
    checks["heading1_pt_expected"] = role["sizes"].get("heading1")

    # GC-2026-1112-01: heiti weight + abstract-label alignment must land in the
    # refdoc exactly as the profile declares them.
    def bold_of(sid: str) -> bool | None:
        m = re.search(r'<w:b w:val="(\d)"/>', style_block(sid))
        return bool(int(m.group(1))) if m else None

    def align_of(sid: str) -> str | None:
        m = re.search(r'<w:jc w:val="([a-z]+)"/>', style_block(sid))
        return m.group(1) if m else None

    expected_heading_bold = True if role.get("heading_bold") is None else role["heading_bold"]
    expected_caption_bold = True if role.get("caption_bold") is None else role["caption_bold"]
    expected_label_align = role.get("abstract_label_alignment") or "center"
    checks["heading1_bold"] = bold_of("Heading1")
    checks["heading1_bold_expected"] = expected_heading_bold
    checks["abstract_title_bold"] = bold_of("AbstractTitle")
    checks["abstract_title_bold_expected"] = expected_heading_bold
    checks["abstract_title_alignment"] = align_of("AbstractTitle")
    checks["abstract_title_alignment_expected"] = expected_label_align
    checks["table_caption_bold"] = bold_of("TableCaption")
    checks["table_caption_bold_expected"] = expected_caption_bold
    normal = style_block("Normal")
    m = re.search(r'w:firstLineChars="(\d+)"', normal)
    checks["normal_first_line_chars"] = int(m.group(1)) / 100 if m else None
    checks["normal_first_line_chars_expected"] = role["first_line_indent_chars"]
    m = re.search(r'<w:pgSz w:w="(\d+)" w:h="(\d+)"', docxml)
    w_tw = int(m.group(1)) if m else 0
    h_tw = int(m.group(2)) if m else 0
    checks["page_mm"] = [round(w_tw / MM_TO_TWIPS, 1), round(h_tw / MM_TO_TWIPS, 1)]
    checks["page_mm_expected"] = list(PAGE_SIZES.get(role["page"].get("size", "A4"), PAGE_SIZES["A4"]))
    m = re.search(r'<w:pgMar [^>]*w:top="(\d+)"[^>]*w:bottom="(\d+)"[^>]*w:left="(\d+)"[^>]*w:right="(\d+)"', docxml)
    checks["margins_mm"] = [round(int(m.group(i)) / MM_TO_TWIPS, 1) for i in range(1, 5)] if m else None
    checks["no_blue_headings"] = not layoutlib.blue_colour_present(styles)
    tbl = style_block("Table")
    checks["table_three_line"] = layoutlib.three_line_table_ok(tbl)
    # C-1 header_fill: when the profile asks for a header-row fill, the firstRow
    # conditional format must actually carry the w:shd (journal-measured 2026-11-12).
    tables_cfg = role.get("tables") or {}
    header_fill = tables_cfg.get("header_fill") or "none"
    if header_fill != "none":
        fill = re.sub(r"^#", "", str(header_fill)).strip().upper() or "E5EBF0"
        first_row = re.search(r'<w:tblStylePr w:type="firstRow">.*?</w:tblStylePr>', tbl, re.S)
        checks["first_row_shd"] = bool(first_row) and f'w:fill="{fill}"' in first_row.group(0)
        checks["first_row_shd_expected"] = f"w:shd fill={fill} in firstRow"
    else:
        checks["first_row_shd"] = None  # not demanded by this profile
    # fonts must be explicit, not theme-resolved
    m = re.search(r'w:eastAsia="([^"]+)"', normal)
    checks["normal_east_asia_font"] = m.group(1) if m else None
    checks["normal_east_asia_font_expected"] = role["fonts"]["body"][0] or None
    m = re.search(r'w:ascii="([^"]+)"', normal)
    checks["normal_latin_font"] = m.group(1) if m else None
    checks["normal_latin_font_expected"] = role["fonts"]["body"][1] or None
    # the page-number field must be an exact PAGE token, not NUMPAGES/SECTIONPAGES
    checks["footer_page_field"] = any(
        layoutlib.has_exact_page_field(z.read(n).decode("utf-8", "ignore"))
        for n in names if re.match(r"word/(header|footer)\d*\.xml", n))
    # P1-a / A-3: with pagination.header=none the package must have NO header part
    # at all. An unconditional "any(placeholder in header parts)" reads False on an
    # empty sequence and would fail a legitimately header-less refdoc (exit code 2).
    # Condition the check on the profile's header mode: none asserts absence, any
    # other mode asserts the placeholder is genuinely present.
    header_parts = [n for n in names if re.match(r"word/header\d*\.xml", n)]
    header_mode = (role.get("pagination") or {}).get("header", "title_center")
    if header_mode == "none":
        checks["header_placeholder"] = not header_parts
        checks["header_placeholder_expected"] = "none (no header part)"
        checks["header_part_absent_when_none"] = not header_parts
        checks["no_header_reference_when_none"] = "<w:headerReference" not in docxml
    else:
        checks["header_placeholder"] = any(
            ("{{PAPER_TITLE}}" in z.read(n).decode("utf-8", "ignore")
             or "{{JOURNAL_LABEL}}" in z.read(n).decode("utf-8", "ignore"))
            for n in header_parts)
        checks["header_placeholder_expected"] = "{{PAPER_TITLE}}/{{JOURNAL_LABEL}} placeholder"
        checks["no_header_reference_when_none"] = None  # not applicable to this mode
    # every header/footer reference must resolve
    rels_xml = z.read("word/_rels/document.xml.rels").decode("utf-8")
    rel_map = {m.group(2): m.group(3) for m in
               re.finditer(r'<Relationship Type="([^"]+)" Id="([^"]+)" Target="([^"]+)"', rels_xml)}
    refs_ok = True
    for m in re.finditer(r'<w:(header|footer)Reference[^>]*r:id="([^"]+)"', docxml):
        target = rel_map.get(m.group(2))
        refs_ok = refs_ok and target is not None and ("word/" + target) in names
    checks["header_footer_refs_resolve"] = refs_ok

    margins_expected = [round(float((role["page"].get("margin") or {}).get(side, 25.4)), 1)
                        for side in ("top", "bottom", "left", "right")]

    ok = (
        checks["title_pt"] == checks["title_pt_expected"]
        and checks["heading1_pt"] == checks["heading1_pt_expected"]
        and checks["heading1_bold"] == checks["heading1_bold_expected"]
        and checks["abstract_title_bold"] == checks["abstract_title_bold_expected"]
        and checks["abstract_title_alignment"] == checks["abstract_title_alignment_expected"]
        and checks["table_caption_bold"] == checks["table_caption_bold_expected"]
        and checks["normal_first_line_chars"] == checks["normal_first_line_chars_expected"]
        and checks["page_mm"] == checks["page_mm_expected"]
        and checks["margins_mm"] == margins_expected
        and checks["no_blue_headings"]
        and checks["footer_page_field"]
        and checks["header_placeholder"]
        and checks["table_three_line"]
        and (checks["no_header_reference_when_none"] is None
             or checks["no_header_reference_when_none"])
        and (checks["first_row_shd"] is None or checks["first_row_shd"])
        and checks["normal_east_asia_font"] == checks["normal_east_asia_font_expected"]
        and checks["normal_latin_font"] == checks["normal_latin_font_expected"]
        and checks["header_footer_refs_resolve"]
    )
    return {"checks": checks, "pass": bool(ok)}





def main() -> int:
    ap = argparse.ArgumentParser(description="Generate reference docx from layout profiles")
    ap.add_argument("--profile", default="all", help="profile name from registry, or 'all'")
    ap.add_argument("--check", action="store_true",
                    help="verify checked-in refdocs match the profiles; do not write")
    args = ap.parse_args()

    registry = layoutlib.load_registry()
    names = sorted(registry["profiles"]) if args.profile == "all" else [args.profile]
    base = default_reference_bytes()
    results: dict[str, object] = {}
    failed = False
    for name in names:
        entry = registry["profiles"].get(name)
        if entry is None:
            print(json.dumps({"status": "error", "profile": name,
                              "error": f"not in registry {sorted(registry['profiles'])}"},
                             ensure_ascii=False))
            failed = True
            continue
        out_path = layoutlib.GOV_ROOT / "templates" / "layout" / entry["refdoc"]
        try:
            data, checks = build_refdoc(name, base)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"status": "error", "profile": name, "error": str(exc)},
                             ensure_ascii=False))
            failed = True
            continue
        record = {"path": str(out_path.relative_to(layoutlib.GOV_ROOT)),
                  "bytes": len(data), "self_check": checks}
        if args.check:
            current = out_path.read_bytes() if out_path.exists() else None
            record["in_sync"] = current == data
            if current != data:
                failed = True
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
        results[name] = record
        if not checks["pass"]:
            failed = True
    print(json.dumps({"status": "error" if failed else "ok",
                      "mode": "check" if args.check else "write",
                      "profiles": results,
                      "generated_at": datetime.now(timezone.utc).isoformat()},
                     ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
