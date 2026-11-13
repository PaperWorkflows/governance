#!/usr/bin/env python3
"""verify_layout — reproducible verification of the GC-2026-1111-02 layout change.

F9 requires the change record's verification results to be reproducible by a third
party. This script re-runs them, including the NEGATIVE cases (a check that cannot
fail is not a check):

  A. schema forward  — every profile and every paper L2 validates against the
                        current schemas/layout-profile.schema.json
  B. schema backward — the pre-change baseline schema rejects the new profiles
                        (proves the new keys are load-bearing, not decorative)
  C. refdoc sync     — regenerating every reference docx reproduces the checked-in
                        file byte for byte, and the generator self-check passes
  D. assertion negatives — the build-time landing assertions actually FAIL when the
                        profile values are removed from the produced docx
                        (line spacing, page size, margins, CJK font, indent)
  E. XML escaping    — a title containing & < > yields a well-formed header part
  F. L2 boundary     — L2 containing a structure-identity key or a venue domain
                        key is rejected
  G. writing-spec    — every paper's writing-spec.yaml parses and carries the
                        target-venue constraints
  H. citation rule   — GC-2026-1112-01 positives: the [N] superscript rule
                        neither misses (docx count == markdown source count,
                        Bibliography excluded on both sides) nor overreaches
                        (comma-space intervals like [12, 40] stay body text)

Usage:
    python3 -I tools/verify_layout.py [--paper-root <papers dir>]

Exit code 0 = all checks passed.
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import pathlib
import re
import sys
import zipfile

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import yaml  # noqa: E402
import jsonschema  # noqa: E402

GOV_ROOT = TOOLS_DIR.parent
PAPERS_ROOT = GOV_ROOT.parent / "papers"

results: list[tuple[str, bool, str]] = []


def record(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(("PASS " if ok else "FAIL ") + label + ((" | " + detail) if detail else ""))


def load_yaml(path: pathlib.Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def section_a() -> None:
    schema = json.loads((GOV_ROOT / "schemas/layout-profile.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    targets = [
        GOV_ROOT / "templates/layout/profiles/draft.yaml",
        GOV_ROOT / "templates/layout/profiles/stie.yaml",
        GOV_ROOT / "templates/layout/profiles/gbt7713-2-2022.yaml",
        GOV_ROOT / "templates/paper/build/layout.yaml",
    ]
    for p in sorted(PAPERS_ROOT.glob("P*/")):
        f = p / "build/layout.yaml"
        if f.exists():
            targets.append(f)
    bad = []
    for t in targets:
        errs = list(validator.iter_errors(load_yaml(t)))
        if errs:
            bad.append(f"{t.name}: {errs[0].message[:80]}")
    record("A. schema forward (all profiles + paper L2)", not bad,
           f"{len(targets)} targets, {len(bad)} failed" + ("; " + "; ".join(bad[:3]) if bad else ""))


def section_b() -> None:
    """The pre-change baseline schema must reject the new profiles."""
    schema = json.loads((GOV_ROOT / "schemas/layout-profile.schema.json").read_text(encoding="utf-8"))
    baseline = copy.deepcopy(schema)
    for key in ("figures", "tables", "references", "pagination", "punctuation", "author_bio_layout"):
        baseline["properties"].pop(key, None)
    for key in ("fonts", "sizes", "paragraph", "heading_numbering",
                "heading_bold", "caption_bold", "abstract_label_alignment"):  # GC-2026-1112-01
        baseline["properties"]["typography"].pop(key, None)
    baseline["properties"]["citation"]["properties"].pop("numeric_superscript", None)  # GC-2026-1112-01
    validator = jsonschema.Draft7Validator(baseline)
    detail = []
    ok = True
    for name in ("stie.yaml", "gbt7713-2-2022.yaml"):
        f = GOV_ROOT / "templates/layout/profiles" / name
        errs = list(validator.iter_errors(load_yaml(f)))
        detail.append(f"{name}: {len(errs)} errors")
        if not errs:
            ok = False
    record("B. schema backward (new profiles rejected by baseline)", ok, "; ".join(detail))


def section_c() -> None:
    import subprocess
    res = subprocess.run([sys.executable, "-I", str(TOOLS_DIR / "make_refdoc.py"), "--check"],
                         capture_output=True, text=True, timeout=180)
    try:
        payload = json.loads(res.stdout)
    except Exception:
        record("C. refdoc generator idempotency", False, res.stdout[-200:] + res.stderr[-200:])
        return
    ok = payload.get("status") == "ok"
    detail = []
    for name, rec in (payload.get("profiles") or {}).items():
        sync = rec.get("in_sync")
        passed = rec.get("self_check", {}).get("pass")
        detail.append(f"{name}: in_sync={sync} self_check={passed}")
        ok = ok and bool(sync) and bool(passed)
    record("C. refdoc generator idempotency + self-check", ok, "; ".join(detail))



def _grid_table(styles: bytes) -> bytes:
    """Turn the three-line table into a full grid table (all rules single)."""
    import re as _re
    text = styles.decode("utf-8")

    def to_single(m):
        tag = m.group(1)
        return (f'<w:{tag} w:val="single" w:sz="4" w:space="0" w:color="000000" />')

    m = _re.search(r"<w:tblBorders>.*?</w:tblBorders>", text, _re.S)
    if not m:
        raise AssertionError("no <w:tblBorders> in the produced styles.xml")
    block = m.group(0)
    new_block = _re.sub(r"<w:(left|right|insideH|insideV)\b[^>]*?/>", to_single, block)
    if new_block == block:
        raise AssertionError("grid mutation did not change the border block")
    return (text[:m.start()] + new_block + text[m.end():]).encode("utf-8")


def _current_docx(paper_root: pathlib.Path) -> list[pathlib.Path]:
    """The newest built docx per paper (build/<version>/ holds superseded versions)."""
    out: list[pathlib.Path] = []
    for p in sorted(paper_root.glob("P*/")):
        docs = list((p / "build").glob("v*/*.docx"))
        if docs:
            out.append(max(docs, key=lambda f: f.stat().st_mtime))
    return out


def _mutate_docx(src: pathlib.Path, dest: pathlib.Path, fn) -> None:
    zin = zipfile.ZipFile(src)
    parts = {n: zin.read(n) for n in zin.namelist()}
    fn(parts)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zout:
        for n, payload in parts.items():
            zout.writestr(n, payload)


def _flip_heading1_bold(styles: bytes) -> bytes:
    """Restore bold on Heading1 (mutation: profile declares heading_bold=false).
    The produced styles.xml is pandoc-serialised ("<w:b w:val="0" />")."""
    text = styles.decode("utf-8")
    m = re.search(r'<w:style [^>]*w:styleId="Heading1"[^>]*>.*?</w:style>', text, re.S)
    if not m:
        raise AssertionError("no Heading1 style block")
    block = m.group(0)
    new_block = re.sub(r'<w:b w:val="0"\s*/>', '<w:b w:val="1" />', block, count=1)
    if new_block == block:
        raise AssertionError("Heading1 carries no explicit w:b val=0")
    return (text[:m.start()] + new_block + text[m.end():]).encode("utf-8")


def _center_abstract_title(styles: bytes) -> bytes:
    """Re-center the abstract/keywords label (mutation: profile declares left)."""
    text = styles.decode("utf-8")
    m = re.search(r'<w:style [^>]*w:styleId="AbstractTitle"[^>]*>.*?</w:style>', text, re.S)
    if not m:
        raise AssertionError("no AbstractTitle style block")
    block = m.group(0)
    if not re.search(r'<w:jc w:val="left"\s*/>', block):
        raise AssertionError("AbstractTitle is not left-aligned")
    new_block = re.sub(r'<w:jc w:val="left"\s*/>', '<w:jc w:val="center" />', block, count=1)
    return (text[:m.start()] + new_block + text[m.end():]).encode("utf-8")


def _drop_citation_superscript(doc: bytes) -> bytes:
    """Strip the superscript from one in-text citation run (mutation: coverage
    assertion must catch the plain citation)."""
    text = doc.decode("utf-8")
    pat = re.compile(
        r'<w:r\b[^>]*>(?:(?!</w:r>).)*?<w:t[^>]*>'
        r'(\[\d{1,3}(?:-\d{1,3})*(?:,\d{1,3}(?:-\d{1,3})*)*\])</w:t></w:r>', re.S)
    m = pat.search(text)
    if not m:
        raise AssertionError("no citation run found in document.xml")
    run = m.group(0)
    if not re.search(r'<w:vertAlign w:val="superscript"\s*/>', run):
        raise AssertionError(f"citation run {m.group(1)!r} is not superscripted (stale artifact?)")
    new_run = re.sub(r'<w:vertAlign w:val="superscript"\s*/>', "", run, count=1)
    return (text[:m.start()] + new_run + text[m.end():]).encode("utf-8")


def _restore_compact_indent(styles: bytes) -> bytes:
    """Re-impose the inherited 2-char first-line indent on Compact (mutation: the
    profile declares cell indent 0). Pre-fix artifacts carry no explicit Compact
    w:ind (they inherit through BodyText -> Normal), so this injects one; the
    regenerated form already has firstLineChars="0", which must be flipped to 200.
    Either way the resulting Compact no longer matches tables.cell_first_line_indent_chars."""
    text = styles.decode("utf-8")
    m = re.search(r'<w:style [^>]*w:styleId="Compact"[^>]*>.*?</w:style>', text, re.S)
    if not m:
        raise AssertionError("no Compact style block")
    block = m.group(0)
    if re.search(r'w:firstLineChars="(\d+)"', block):
        new_block = re.sub(r'w:firstLineChars="\d+"', 'w:firstLineChars="200"', block, count=1)
        if new_block == block:
            raise AssertionError("Compact carries no firstLineChars to mutate")
    else:
        ppr = block.rindex("</w:pPr>")
        new_block = block[:ppr] + '<w:ind w:firstLineChars="200" w:firstLine="400"/>' + block[ppr:]
    return (text[:m.start()] + new_block + text[m.end():]).encode("utf-8")


def section_d(paper_root: pathlib.Path) -> None:
    """Negative tests: removing profile values from the artifact must fail the build."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("paper_mod", TOOLS_DIR / "paper.py")
    paper_mod = importlib.util.module_from_spec(spec)
    sys.modules["paper_mod"] = paper_mod
    spec.loader.exec_module(paper_mod)
    import layoutlib

    docs = _current_docx(paper_root)
    if not docs:
        record("D. assertion negative tests", False, "no built docx found; run build docx first")
        return
    docx = docs[0]
    stack = layoutlib.resolve_profile_stack("stie")
    role = layoutlib.merged_role(stack["merged"])
    merged = stack["merged"]
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="verify_layout_neg_"))

    # M3-a / P2-2: the margin mutation literal must track the profile — a hardcoded
    # w:top="1440" (25.4 mm) becomes a no-op once the profile switches to 20 mm.
    margin_top_tw = int(round((merged.get("page", {}).get("margin", {}) or {})
                              .get("top", 25.4) * 56.6929))
    # M3-b / P1-c-1: the running head reference only exists in header profiles.
    header_mode = (merged.get("pagination", {}) or {}).get("header", "title_center")

    def _replace(payload: bytes, old: bytes, new: bytes) -> bytes:
        if old not in payload:
            raise AssertionError(f"mutation target not found: {old[:60]!r}")
        return payload.replace(old, new)

    mutations = {
        "line_spacing_removed": lambda p: p.__setitem__(
            "word/styles.xml",
            _replace(p["word/styles.xml"], b'w:line="360" w:lineRule="auto"',
                     b'w:line="240" w:lineRule="auto"')),
        "page_size_removed": lambda p: p.__setitem__(
            "word/document.xml",
            _replace(p["word/document.xml"], b'<w:pgSz w:h="16838" w:w="11906" />', b"")),
        "margins_removed": lambda p: p.__setitem__(
            "word/document.xml",
            _replace(p["word/document.xml"], f'w:top="{margin_top_tw}"'.encode("ascii"),
                     b'w:top="720"')),
        "cjk_font_removed": lambda p: p.__setitem__(
            "word/styles.xml",
            _replace(p["word/styles.xml"], 'w:eastAsia="宋体"'.encode("utf-8"),
                     b'w:eastAsia="Calibri"')),
        # first-line indent removed (the profile demands 2 characters)
        "indent_removed": lambda p: p.__setitem__(
            "word/styles.xml",
            _replace(p["word/styles.xml"], b'w:firstLineChars="200" ', b"")),
        # a GRID table must not satisfy the three-line rule. The attribute order
        # in the produced file is whatever pandoc's serialiser emits, so the
        # mutation is regex-based rather than a literal match.
        "grid_table": lambda p: p.__setitem__(
            "word/styles.xml",
            _grid_table(p["word/styles.xml"])),
        # NUMPAGES is not PAGE
        "numpages_not_page": lambda p: p.__setitem__(
            "word/footer1.xml",
            _replace(p["word/footer1.xml"], b" PAGE ", b" NUMPAGES ")),
        # blue heading colour in lower case (case-insensitive detection)
        "blue_lowercase": lambda p: p.__setitem__(
            "word/styles.xml",
            _replace(p["word/styles.xml"], b'w:val="000000"', b'w:val="0f4761"')),
        # GC-2026-1112-01: heiti headings must not be bold; the artifact must carry
        # the explicit w:b val=0 the generator writes
        "heading_bold_restored": lambda p: p.__setitem__(
            "word/styles.xml", _flip_heading1_bold(p["word/styles.xml"])),
        # GC-2026-1112-01: the abstract/keywords label must stay left-aligned
        "abstract_title_centered": lambda p: p.__setitem__(
            "word/styles.xml", _center_abstract_title(p["word/styles.xml"])),
        # GC-2026-1112-01: every in-text citation run must be superscripted
        "citation_superscript_removed": lambda p: p.__setitem__(
            "word/document.xml", _drop_citation_superscript(p["word/document.xml"])),
        # GC-2026-1112-06 follow-up (表单元格缩进归零): restoring the 2-char indent on
        # pandoc Compact (table cells / tight lists) must fail the landing assertion
        "compact_indent_restored": lambda p: p.__setitem__(
            "word/styles.xml", _restore_compact_indent(p["word/styles.xml"])),
    }
    if header_mode == "none":
        # M3-b / P1-c-1: a header=none artifact must carry NO w:headerReference.
        # The old negative targeted a literal rId10 reference that only exists in
        # header profiles, so it cannot mutate a header-less product. Replace it
        # with a POSITIVE assertion (the injectable negative — prove such an
        # artifact would fail — is registered as a separate open item, P1-c-2).
        # NOTE: search the DECOMPRESSED document part, not the raw zip bytes —
        # deflate makes an XML fragment unfindable in read_bytes() (found 2026-11-12).
        raw_doc = zipfile.ZipFile(docx).read("word/document.xml")
        if b"<w:headerReference" in raw_doc:
            record("D. none-mode positive: header=none artifact has no headerReference",
                   False, "w:headerReference present in artifact")
        else:
            record("D. none-mode positive: header=none artifact has no headerReference",
                   True, "no w:headerReference")
    else:
        # the running head must actually be referenced by sectPr (header profiles only)
        mutations["header_reference_removed"] = lambda p: p.__setitem__(
            "word/document.xml",
            _replace(p["word/document.xml"],
                     b'<w:headerReference r:id="rId10" w:type="default" />', b""))
    for label, mutate in mutations.items():
        target = tmp / f"{label}.docx"
        try:
            _mutate_docx(docx, target, mutate)
        except AssertionError as exc:
            record(f"D. negative: {label} must fail assertions", False, f"mutation no-op: {exc}")
            continue
        failures, _notes = paper_mod._assert_layout_landing(target, role, merged)
        record(f"D. negative: {label} must fail assertions", bool(failures),
               f"{len(failures)} failure(s): " + "; ".join(f["check"] for f in failures[:3]))

    failures, notes = paper_mod._assert_layout_landing(docx, role, merged)
    record("D. positive: unmodified artifact passes assertions", not failures,
           f"{len(failures)} failures")


def section_e(paper_root: pathlib.Path) -> None:
    import tempfile
    import importlib.util
    spec = importlib.util.spec_from_file_location("paper_mod2", TOOLS_DIR / "paper.py")
    paper_mod = importlib.util.module_from_spec(spec)
    sys.modules["paper_mod2"] = paper_mod
    spec.loader.exec_module(paper_mod)

    docs = _current_docx(paper_root)
    if not docs:
        record("E. title XML escaping (& < >)", False, "no built docx found")
        return
    docx = docs[0]
    nasty = 'A & B <研究> "x" \\z'
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="verify_layout_esc_")) / "escaped.docx"
    tmp.write_bytes(docx.read_bytes())
    paper_mod._inject_paper_title_header(tmp, nasty)
    z = zipfile.ZipFile(tmp)
    headers = [n for n in z.namelist() if re.match(r"word/header\d*\.xml", n)]
    if not headers:
        # M3-c / P1-d: with pagination.header=none the package has no header part to
        # inject into. Skipping is a recorded note, never a silent pass.
        record("E. title XML escaping (& < >)", True,
               "skipped: no header part (header=none profile)")
        return
    ok = True
    detail = f"{len(headers)} header part(s) well-formed"
    try:
        import xml.etree.ElementTree
        for h in headers:
            xml.etree.ElementTree.fromstring(z.read(h))
    except Exception as exc:  # noqa: BLE001
        ok = False
        detail = str(exc)[:120]
    record("E. title XML escaping (& < >)", ok, detail)


def section_f() -> None:
    import layoutlib
    cases = {
        "structure-identity page": {"profile": "stie", "kind": "paper", "page": {"size": "A4"}},
        "structure-identity citation": {"profile": "stie", "kind": "paper", "citation": {"style": "x"}},
        "venue domain tables": {"profile": "stie", "kind": "paper", "tables": {"style": "grid"}},
        "venue domain pagination": {"profile": "stie", "kind": "paper", "pagination": {"position": "none"}},
        "valid selection": {"profile": "stie", "kind": "paper"},
        "valid typography override": {"profile": "stie", "kind": "paper", "typography": {"body_pt": 11}},
    }
    for label, l2 in cases.items():
        should_pass = label.startswith("valid")
        try:
            layoutlib.check_l2_overrides(l2)
            ok = should_pass
            detail = "accepted"
        except layoutlib.LayoutError as exc:
            ok = not should_pass
            detail = str(exc)[:110]
        record(f"F. L2 boundary: {label}", ok, detail)


def section_g(paper_root: pathlib.Path) -> None:
    required = ["venue", "abstract_target_chars", "keywords_separator", "title_max_chars",
                "author_bio_required", "conclusion_heading", "min_chars"]
    bad = []
    for p in sorted(paper_root.glob("P*/")):
        f = p / "writing-spec.yaml"
        if not f.exists():
            continue
        try:
            data = load_yaml(f)
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{p.name}: parse error {str(exc)[:60]}")
            continue
        missing = [k for k in required if k not in data]
        if missing:
            bad.append(f"{p.name}: missing {missing}")
    record("G. writing-spec parses and carries venue constraints", not bad,
           f"{len(list(paper_root.glob('P*/writing-spec.yaml')))} papers, {len(bad)} problems"
           + ("; " + "; ".join(bad[:3]) if bad else ""))


def section_h(paper_root: pathlib.Path) -> None:
    """GC-2026-1112-01 positives: the citation rule must neither miss nor overreach."""
    pat = re.compile(r"\[\d{1,3}(?:-\d{1,3})*(?:,\d{1,3}(?:-\d{1,3})*)*\]")
    interval = re.compile(r"\[\d+,\s+\d+\]")
    # <paper>/build/<version>/<title>.docx -> the paper dir is three levels up;
    # taking .parent.parent yields "build" for every paper (collapsed into one
    # key and made paper_root/key resolve to papers/build — found 2026-11-12).
    docs = {d.parents[2].name: d for d in _current_docx(paper_root)}

    # (1) P4's interval notation [12, 40] must NOT be superscripted
    p4 = next((v for k, v in docs.items() if k.startswith("P4-")), None)
    if p4 is None:
        record("H. interval [12, 40] not superscripted (P4)", False, "no P4 build found")
    else:
        doc = zipfile.ZipFile(p4).read("word/document.xml").decode("utf-8")
        plain, raised = 0, 0
        for rm in re.finditer(r"<w:r\b[^>]*>.*?</w:r>", doc, re.S):
            tm = re.search(r"<w:t[^>]*>([^<]*)</w:t>", rm.group(0))
            if tm and interval.search(tm.group(1)):
                if re.search(r'<w:vertAlign w:val="superscript"\s*/>', rm.group(0)):
                    raised += 1
                else:
                    plain += 1
        record("H. interval [12, 40] not superscripted (P4)",
               plain > 0 and raised == 0,
               f"{plain} plain interval run(s), {raised} wrongly raised")

    # (2) per paper: docx citation count == markdown source count (Bibliography
    #     entries excluded on both sides)
    detail, ok = [], True
    for key in sorted(docs):
        paper_dir = paper_root / key
        md = (paper_dir / "body" / "paper.md").read_text(encoding="utf-8")
        md_wo_bib = re.sub(
            r'::: \{custom-style="Bibliography"\}\n.*?\n:::\n', "", md, flags=re.S)
        src_count = len(pat.findall(md_wo_bib))
        doc = zipfile.ZipFile(docs[key]).read("word/document.xml").decode("utf-8")
        docx_count = 0
        for pm in re.finditer(r"<w:p\b.*?</w:p>", doc, re.S):
            para = pm.group(0)
            st = re.search(r'<w:pStyle w:val="([^"]+)"', para)
            if st and st.group(1) in ("Bibliography", "SourceCode"):
                continue
            for tm in re.finditer(r"<w:t[^>]*>([^<]*)</w:t>", para):
                docx_count += len(pat.findall(tm.group(1)))
        detail.append(f"{key[:2]}={docx_count}/{src_count}")
        if docx_count != src_count:
            ok = False
    record("H. citation count parity (docx == markdown source)", ok, "; ".join(detail))


def main() -> int:
    ap = argparse.ArgumentParser(description="Reproducible verification of the layout change")
    ap.add_argument("--paper-root", default=str(PAPERS_ROOT))
    args = ap.parse_args()
    paper_root = pathlib.Path(args.paper_root)

    section_a()
    section_b()
    section_c()
    section_d(paper_root)
    section_e(paper_root)
    section_f()
    section_g(paper_root)
    section_h(paper_root)

    failed = [r for r in results if not r[1]]
    print(f"\nTOTAL {len(results)}  PASS {len(results) - len(failed)}  FAIL {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
