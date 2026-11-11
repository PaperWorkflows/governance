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
    for key in ("fonts", "sizes", "paragraph", "heading_numbering"):
        baseline["properties"]["typography"].pop(key, None)
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
            _replace(p["word/document.xml"], b'w:top="1440"', b'w:top="720"')),
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
        # the running head must actually be referenced by sectPr
        "header_reference_removed": lambda p: p.__setitem__(
            "word/document.xml",
            _replace(p["word/document.xml"], b'<w:headerReference r:id="rId10" w:type="default" />', b"")),
        # blue heading colour in lower case (case-insensitive detection)
        "blue_lowercase": lambda p: p.__setitem__(
            "word/styles.xml",
            _replace(p["word/styles.xml"], b'w:val="000000"', b'w:val="0f4761"')),
    }
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
    ok = bool(headers)
    detail = "no header part"
    if headers:
        try:
            import xml.etree.ElementTree
            for h in headers:
                xml.etree.ElementTree.fromstring(z.read(h))
            detail = f"{len(headers)} header part(s) well-formed"
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

    failed = [r for r in results if not r[1]]
    print(f"\nTOTAL {len(results)}  PASS {len(results) - len(failed)}  FAIL {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
