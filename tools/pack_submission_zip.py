#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack the submission zip from an assembled package directory.

Usage:
    pack_submission_zip.py --paper <paper_dir> [--out <output_dir>] [--name <repo_name>]

Naming (2026-11-17 GC-2026-1117-04)：
    产物 zip 名 = **仓库名 + 版本号**，即 ``<repo-name>-<paper_version>.zip``。
    仓库名按以下优先级取得：``--name`` 显式指定 > 论文仓 git remote origin 的仓名 >
    兜底投稿名 ``{first}-《{title}》.zip``（无 remote 时，使用第一作者中文名加
    标题的全角书名号）（GC-2026-1117-04）。
    PF-B7/venue S19 的投稿名 ``{first}-《{title}》.zip`` 随 JSON 输出一并打印，
    便于编辑部场景取用（GC-2026-1117-04）。

Contract with governance:
  * PF-B7   the package directory is zip-ready; packing is the delivery step.
  * PF-B7   release filenames: ``{first_author}-《{title}》.docx/pdf`` (GC-2026-1117-04).
  * PF-B16  ``package --verify-only --strict`` must pass before any zip is sent;
            this tool does not re-verify — callers run the gate first.
  * ``paper.py build zip`` is a thin wrapper that delegates to ``pack_submission_zip.pack()``.
  * Determinism: entry timestamps are fixed so two runs over identical inputs
    produce byte-comparable archives (cf. PF-B7 deterministic docx rule).

Exit codes: 0 ok, 1 no first author registered, 2 usage/IO error, 3 package directory missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

# Fixed timestamp (2026-01-01T00:00:00) — reproducibility, not delivery date.
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


class PackError(Exception):
    """Pack failure carrying the CLI exit code.

    3 = package directory missing/empty (delivery not ready), 2 = usage/IO/
    unreadable metadata, 1 = no first author registered.
    """

    def __init__(self, message: str, exit_code: int = 3, payload: dict | None = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.payload = payload or {"status": "error", "error": message}


def _posix_safe(name: str) -> str:
    """PF-B7 POSIX-safe escaping (mirrors paper._posix_safe_title; duplicated to
    avoid a circular import — paper.py imports this module)."""
    return re.sub(r'[/\\:*?"<>|\s]+', "_", name).strip("_") or "paper"


def _first_author(paper: dict) -> str:
    """First author's Chinese name: role 'first' in paper.yaml#authors, else the first listed."""
    authors = paper.get("authors") or []
    for a in authors:
        if "first" in (a.get("roles") or []):
            return a["name"]
    if authors:
        return authors[0].get("name") or authors[0].get("author_id")
    raise PackError("paper.yaml carries no authors — cannot derive the zip filename", 1)


def _repo_name(paper_dir: Path) -> str | None:
    """Repository name from the paper repo's git remote origin (None when absent)."""
    try:
        r = subprocess.run(["git", "-C", str(paper_dir), "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    url = r.stdout.strip().rstrip("/")
    name = url.split("/")[-1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return name or None


def pack(paper_dir: Path, out_dir: Path, name: str | None = None) -> dict:
    # Read paper.yaml with error handling
    try:
        raw = (paper_dir / "paper.yaml").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise PackError(f"paper.yaml not found: {paper_dir / 'paper.yaml'}", 2)
    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise PackError(f"paper.yaml is unreadable: {exc}", 2)
    if not isinstance(meta, dict):
        raise PackError("paper.yaml must contain a YAML mapping (dict)", 2)
    if "title" not in meta:
        raise PackError("paper.yaml missing 'title'", 2)
    if "paper_version" not in meta:
        raise PackError("paper.yaml missing 'paper_version'", 2)

    title = meta["title"]
    version = meta["paper_version"]
    first = _first_author(meta)

    pkg = paper_dir / "build" / version / "package"
    if not pkg.is_dir():
        raise PackError(
            f"package directory missing: {pkg}",
            3,
            {"status": "error",
             "error": f"package directory missing: {pkg}",
             "hint": "run `paper.py package --paper <dir>` first"},
        )

    repo = name or _repo_name(paper_dir)
    if repo:
        zip_name = f"{repo}-{version}.zip"
        naming = "repo+version"
    else:
        # No git remote (e.g. a bare source tree) — fall back to the PF-B7 name.
        # (GC-2026-1117-04)
        zip_name = _posix_safe(f"{first}-《{title}》") + ".zip"
        naming = "pf-b7-title"

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / zip_name

    files = sorted(p for p in pkg.rglob("*") if p.is_file())
    if not files:
        raise PackError(
            f"package directory is empty: {pkg}",
            3,
            {"status": "error",
             "error": f"package directory is empty: {pkg}"},
        )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(pkg).as_posix()
            info = zipfile.ZipInfo(rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, f.read_bytes())

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    result = {
        "status": "ok",
        "zip": zip_name,
        "naming": naming,
        "repo": repo,
        "path": str(zip_path),
        "version": version,
        "title": title,
        "first_author": first,
        "submission_name_pf_b7": _posix_safe(f"{first}-《{title}》") + ".zip",  # (GC-2026-1117-04)
        "entries": len(files),
        "bytes": zip_path.stat().st_size,
        "sha256": digest,
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Pack submission zip (repo-name + version; fallback: {first}-《{title}》.zip per GC-2026-1117-04)")
    ap.add_argument("--paper", required=True, help="paper workspace directory")
    ap.add_argument("--out", default="dist", help="output directory for the zip")
    ap.add_argument("--name", default=None, help="explicit repository name for the zip filename")
    args = ap.parse_args()
    try:
        payload = pack(Path(args.paper), Path(args.out), args.name)
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        sys.exit(0)
    except PackError as exc:
        print(json.dumps(exc.payload, ensure_ascii=False, indent=1))
        raise SystemExit(exc.exit_code)
    except OSError as exc:
        print(json.dumps({"status": "error", "error": str(exc), "stage": "pack"},
                         ensure_ascii=False, indent=1))
        raise SystemExit(2)


if __name__ == "__main__":
    sys.exit(main())
