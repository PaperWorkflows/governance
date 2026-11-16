#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack the submission zip from an assembled package directory.

Usage:
    pack_submission_zip.py --paper <paper_dir> [--out <output_dir>]

Reads ``paper.yaml`` (title / paper_version / authors) and packs the *contents*
of ``build/<paper_version>/package/`` — flat, no wrapper directory — into
``<title>（<first author Chinese name>）.zip`` (PF-B7 skeleton / venue S19).

Contract with governance:
  * PF-B7   the package directory is zip-ready; packing is the delivery step.
  * PF-B16  ``package --verify-only --strict`` must pass before any zip is sent;
            this tool does not re-verify — callers run the gate first.
  * Determinism: entry timestamps are fixed so two runs over identical inputs
    produce byte-comparable archives (cf. PF-B7 deterministic docx rule).

Exit codes: 0 ok, 2 usage/IO error, 3 package directory missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import yaml

# Fixed timestamp (2026-01-01T00:00:00) — reproducibility, not delivery date.
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def _first_author(paper: dict) -> str:
    """First author's Chinese name: role 'first' in paper.yaml#authors, else the first listed."""
    authors = paper.get("authors") or []
    for a in authors:
        if "first" in (a.get("roles") or []):
            return a["name"]
    if authors:
        return authors[0].get("name") or authors[0].get("author_id")
    raise SystemExit("paper.yaml carries no authors — cannot derive the zip filename")


def pack(paper_dir: Path, out_dir: Path) -> dict:
    meta = yaml.safe_load((paper_dir / "paper.yaml").read_text(encoding="utf-8"))
    title = meta["title"]
    version = meta["paper_version"]
    first = _first_author(meta)

    pkg = paper_dir / "build" / version / "package"
    if not pkg.is_dir():
        print(json.dumps({"status": "error", "error": f"package directory missing: {pkg}",
                          "hint": "run `paper.py package --paper <dir>` first"}, ensure_ascii=False))
        raise SystemExit(3)

    zip_name = f"{title}（{first}）.zip"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / zip_name

    files = sorted(p for p in pkg.rglob("*") if p.is_file())
    if not files:
        print(json.dumps({"status": "error", "error": f"package directory is empty: {pkg}"}, ensure_ascii=False))
        raise SystemExit(3)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(pkg).as_posix()
            info = zipfile.ZipInfo(rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, f.read_bytes())

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(json.dumps({
        "status": "ok",
        "zip": zip_name,
        "path": str(zip_path),
        "version": version,
        "title": title,
        "first_author": first,
        "entries": len(files),
        "bytes": zip_path.stat().st_size,
        "sha256": digest,
    }, ensure_ascii=False, indent=1))
    return {"zip": str(zip_path), "sha256": digest}


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack submission zip (PF-B7 / venue S19)")
    ap.add_argument("--paper", required=True, help="paper workspace directory")
    ap.add_argument("--out", default="dist", help="output directory for the zip")
    args = ap.parse_args()
    pack(Path(args.paper), Path(args.out))


if __name__ == "__main__":
    sys.exit(main())
