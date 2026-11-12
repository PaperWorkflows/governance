#!/usr/bin/env python3
"""PaperFactory CLI — proposal, scaffold, check, version-bump, materials, experiments, writing, review, build."""
import sys

if not sys.flags.isolated:
    print('{"status":"error","reason":"python3 -I required"}')
    raise SystemExit(2)

sys.dont_write_bytecode = True

import argparse, hashlib, json, re, subprocess, yaml, zipfile
import xml.etree.ElementTree
from pathlib import Path
from datetime import datetime, timezone

# layoutlib is a sibling module; -I does not prepend the script dir, so insert it explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import layoutlib
except Exception as _exc:  # pragma: no cover - hard dependency for build subcommands
    layoutlib = None
    _layoutlib_error = str(_exc)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PAPER_REPO_PATTERN = re.compile(r'^P([0-9]+)-([A-Z]+)-([0-9]{8})$')
TEMPLATE_PAPER = Path(__file__).resolve().parent.parent / "templates/paper"
GITHUB_ORG = "PaperWorkflows"

# Default chapters per paper_type
DEFAULT_CHAPTERS = {
    "theory": [
        {"number": 1, "slug": "introduction", "title": "Introduction"},
        {"number": 2, "slug": "background", "title": "Background and Related Work"},
        {"number": 3, "slug": "preliminaries", "title": "Preliminaries and Definitions"},
        {"number": 4, "slug": "theory", "title": "Theory and Proofs"},
        {"number": 5, "slug": "discussion", "title": "Discussion"},
        {"number": 6, "slug": "conclusion", "title": "Conclusion"},
    ],
    "algorithm_experiment": [
        {"number": 1, "slug": "introduction", "title": "Introduction"},
        {"number": 2, "slug": "background", "title": "Background and Related Work"},
        {"number": 3, "slug": "method", "title": "Method"},
        {"number": 4, "slug": "algorithm", "title": "Algorithm"},
        {"number": 5, "slug": "evaluation", "title": "Evaluation"},
        {"number": 6, "slug": "results", "title": "Results"},
        {"number": 7, "slug": "discussion", "title": "Discussion"},
        {"number": 8, "slug": "conclusion", "title": "Conclusion"},
    ],
    "software_system": [
        {"number": 1, "slug": "introduction", "title": "Introduction"},
        {"number": 2, "slug": "background", "title": "Background and Related Work"},
        {"number": 3, "slug": "design", "title": "System Design"},
        {"number": 4, "slug": "implementation", "title": "Implementation"},
        {"number": 5, "slug": "evaluation", "title": "Evaluation"},
        {"number": 6, "slug": "discussion", "title": "Discussion"},
        {"number": 7, "slug": "conclusion", "title": "Conclusion"},
    ],
    "empirical": [
        {"number": 1, "slug": "introduction", "title": "Introduction"},
        {"number": 2, "slug": "background", "title": "Background and Related Work"},
        {"number": 3, "slug": "method", "title": "Method"},
        {"number": 4, "slug": "experiment", "title": "Experiment and Evaluation"},
        {"number": 5, "slug": "results", "title": "Results"},
        {"number": 6, "slug": "discussion", "title": "Discussion"},
        {"number": 7, "slug": "conclusion", "title": "Conclusion"},
    ],
    "mixed": [
        {"number": 1, "slug": "introduction", "title": "Introduction"},
        {"number": 2, "slug": "background", "title": "Background and Related Work"},
        {"number": 3, "slug": "method", "title": "Method"},
        {"number": 4, "slug": "experiment", "title": "Experiment and Evaluation"},
        {"number": 5, "slug": "results", "title": "Results"},
        {"number": 6, "slug": "discussion", "title": "Discussion"},
        {"number": 7, "slug": "conclusion", "title": "Conclusion"},
    ],
}

class Parser(argparse.ArgumentParser):
    def error(self, msg):
        print(json.dumps({"status": "error", "error": msg}, ensure_ascii=False))
        raise SystemExit(2)

def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code

# ── helpers ──────────────────────────────────────────────────────

def parse_paper_id(pid: str) -> dict:
    m = PAPER_REPO_PATTERN.match(pid)
    if not m:
        raise ValueError(f"Invalid paper repo name: {pid} (expected P{{N}}-{{AUTHOR_EN}}-{{YYYYMMDD}}, AUTHOR_EN = author pinyin uppercase)")
    return {"number": int(m.group(1)), "author": m.group(2), "date": m.group(3)}

def validate_paper_yaml(path: Path) -> dict:
    """Minimal YAML-free validation for paper.yaml (Python stdlib only)."""
    errors = []
    text = path.read_text(encoding="utf-8")
    required_simple = ["schema_version:", "template:", "id:", "title:", "paper_version:",
                       "authors_confirmed:", "authors:", "language:", "bilingual_abstract:",
                       "full_english_body:", "paper_type:", "stage:", "stage_state:",
                       "manuscript_kind:", "rules_version:", "applicable_rules:",
                       "layout_profile:", "citation_profile:", "target_venue:",
                       "budget:", "unresolved:", "safety:", "repository_mode:"]
    for key in required_simple:
        if key not in text:
            errors.append(f"Missing required key: {key.rstrip(':')}")
    found_id = False
    for line in text.splitlines():
        if line.startswith("id:"):
            val = line.split(":", 1)[1].strip()
            found_id = True
            if not re.match(r'^P[0-9]+$', val):
                errors.append(f"id must be P<number> (e.g. P1), not repo slug: {val}")
            break
    if not found_id:
        errors.append("Missing required key: id")
    for line in text.splitlines():
        if line.startswith("paper_version:"):
            val = line.split(":", 1)[1].strip()
            # SemVer 2.0.0 with v prefix (AGENTS.md F3 / PF-V2 / GC-2026-1111-01-S)
            if not re.match(r'^v[0-9]+\.[0-9]+\.[0-9]+$', val):
                errors.append(f"paper_version must be SemVer vMAJOR.MINOR.PATCH (e.g. v0.1.0): {val}")
            break
    if "chapters:" not in text:
        errors.append("Missing required key: chapters")
    return {"status": "pass" if not errors else "fail", "errors": errors}

def parse_chapters(text: str) -> list:
    """Parse chapters array from paper.yaml (simple indent-based parser).
    
    Returns list of dicts: [{"number": 1, "slug": "introduction", "title": "Introduction"}, ...]
    """
    chapters = []
    in_chapters = False
    current_num = 0
    current_slug = ""
    current_title = ""
    for line in text.splitlines():
        if line and not line[0].startswith(" ") and not line[0].startswith("\t"):
            if line.strip() == "chapters:":
                in_chapters = True
                continue
            else:
                # Save previous chapter if exists
                if current_slug:
                    chapters.append({
                        "number": current_num,
                        "slug": current_slug,
                        "title": current_title or current_slug,
                    })
                    current_slug = ""  # Reset to prevent double-save
                in_chapters = False
                continue
        if in_chapters:
            stripped = line.strip()
            if stripped.startswith("- "):
                # Save previous chapter if exists
                if current_slug:
                    chapters.append({
                        "number": current_num,
                        "slug": current_slug,
                        "title": current_title or current_slug,
                    })
                # Start new chapter
                current_num = len(chapters) + 1
                current_slug = ""
                current_title = ""
            elif stripped.startswith("number:"):
                try:
                    current_num = int(stripped.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("slug:"):
                current_slug = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("title:"):
                current_title = stripped.split(":", 1)[1].strip()
    
    # Save last chapter if exists
    if current_slug:
        chapters.append({
            "number": current_num,
            "slug": current_slug,
            "title": current_title or current_slug,
        })
    
    return chapters

def parse_yaml_value(text: str, key: str) -> str:
    """Extract a simple scalar value from YAML text."""
    prefix = key + ":"
    for line in text.splitlines():
        if line.startswith(prefix):
            val = line[len(prefix):].strip()
            return val if val != "null" else None
    return None

def write_paper_authors(dest: Path, author: dict):
    """Write per-paper authors.yaml (private repo: full details allowed)."""
    authors_path = dest / "authors.yaml"
    entries = [author]
    with open(authors_path, "w", encoding="utf-8") as f:
        yaml.dump(entries, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def check_gh_available() -> dict:
    """Check if gh CLI is installed and authenticated."""
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {"available": False, "reason": "gh CLI not installed"}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"available": False, "reason": "gh CLI not found"}

    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {"available": False, "reason": f"gh not authenticated: {result.stderr.strip()}"}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"available": False, "reason": "gh auth check failed"}

    return {"available": True}

def create_github_repo(repo_name: str, private: bool = True) -> dict:
    """Create GitHub repo using gh CLI."""
    visibility = "--private" if private else "--public"
    # gh repo create <org>/<name> --private
    cmd = ["gh", "repo", "create", f"{GITHUB_ORG}/{repo_name}", visibility]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {"created": False, "error": result.stderr.strip() or result.stdout.strip()}
    return {"created": True, "repo": f"{GITHUB_ORG}/{repo_name}"}

def build_paper_yaml(pid: str, title: str, author_id: str, paper_type: str,
                     rules_version: str = "0.1.0", date: str = None) -> str:
    """Build complete paper.yaml content from proposal inputs."""
    pid_number = pid.split("-")[0]
    chapters = DEFAULT_CHAPTERS.get(paper_type, DEFAULT_CHAPTERS["empirical"])
    today = date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chapter_lines = "\n".join(
        f"  - number: {c['number']}\n    slug: {c['slug']}\n    title: {c['title']}"
        for c in chapters
    )
    return f"""schema_version: 1
template: false
id: {pid_number}
paper_version: 0.1.0
repository_mode: per_paper_independent
title: {title}
authors_confirmed: true
authors_confirmation:
  source: proposal command
  confirmed_on: {today}
authors:
  - author_id: {author_id}
    name: null                  # Author details in authors.yaml (private repo)
    affiliations: []
    roles:
      - first
    email: null
language: zh
bilingual_abstract: true
full_english_body: false
paper_type: {paper_type}
stage: proposal
stage_state: active
manuscript_kind: research
rules_version: {rules_version}
applicable_rules:
  - PF-P1
  - PF-P2
  - PF-P3
  - PF-P4
  - PF-P5
  - PF-P6
  - PF-P7
  - PF-P8
  - PF-W1
  - PF-W2
  - PF-W3
  - PF-W4
  - PF-W5
  - PF-W6
  - PF-W7
  - PF-W8
  - PF-W9
  - PF-W10
  - PF-R1
  - PF-R2
  - PF-R3
  - PF-R4
  - PF-R5
  - PF-R6
  - PF-R7
  - PF-R8
  - PF-B1
  - PF-B2
  - PF-B3
  - PF-B4
  - PF-B5
  - PF-B6
  - PF-B7
  - PF-B8
  - PF-B9
  - PF-B10
  - PF-RV1
  - PF-RV2
  - PF-RV3
  - PF-RV4
  - PF-RV5
  - PF-RV6
  - PF-V1
  - PF-V2
  - PF-V3
  - PF-V4
  - PF-V5
  - PF-V6
  - PF-V7
  - PF-V8
  - PF-V9
  - PF-V10
rule_exemptions: []
layout_profile: draft
citation_profile: null
target_venue: null
budget:
  confirmed: false
  limits: null
isolation_profile: null
unresolved:
  - 大纲待细化
  - 实验方案待设计
  - 目标刊会待确认
next_step: 由主会话按 PF-P7 派发研究方案任务
body_target_chars: 15000
chapters:
{chapter_lines}
safety:
  hooks: pending
  isolation: pending
  independent_backup: pending
  publishing: disabled
"""

# ── proposal ─────────────────────────────────────────────────────

def cmd_proposal(args):
    errors = []

    # 1. Validate paper repo ID format
    try:
        meta = parse_paper_id(args.id)
    except ValueError as e:
        return emit({"status": "error", "error": str(e)}, 2)

    # 2. Validate required inputs
    if not args.author_name or not args.author_name.strip():
        errors.append("--author-name is required (first author full name)")
    if not args.author_pinyin or not args.author_pinyin.strip():
        errors.append("--author-pinyin is required (first author pinyin, uppercase)")
    if not args.title or not args.title.strip():
        errors.append("--title is required (paper title)")
    if not args.paper_type:
        errors.append("--paper-type is required (theory/algorithm_experiment/software_system/empirical/mixed)")
    elif args.paper_type not in DEFAULT_CHAPTERS:
        errors.append(f"Invalid --paper-type: {args.paper_type}. Choose from: {list(DEFAULT_CHAPTERS.keys())}")

    if errors:
        return emit({"status": "error", "error": "Proposal conditions not met", "errors": errors}, 2)

    author_pinyin = args.author_pinyin.upper()
    dest = Path(args.dest) if args.dest else PROJECT_ROOT / "papers" / args.id

    # 3. Check destination doesn't exist
    if dest.exists():
        return emit({"status": "error", "error": f"Destination already exists: {dest}"}, 2)

    # 4. Check gh CLI
    gh_status = check_gh_available()
    if not gh_status["available"]:
        return emit({
            "status": "error",
            "error": f"Cannot create GitHub repo: {gh_status['reason']}. Install/authenticate gh CLI first.",
            "hint": "https://cli.github.com/"
        }, 2)

    # 5. Write per-paper authors.yaml (private repo: full details allowed)
    author_entry = {
        "id": author_pinyin.lower(),
        "name": args.author_name.strip(),
        "name_en": args.author_name_en or author_pinyin.title(),
        "affiliations": [args.affiliation] if args.affiliation else [],
        "email": args.email,
        "orcid": None,
        "postal_code": None,
        "roles": ["first"],
    }

    # 6. Create paper workspace directory
    dest.mkdir(parents=True, exist_ok=False)

    # 7. Copy template files
    items = list(TEMPLATE_PAPER.rglob("*"))
    created = []
    for item in items:
        rel = item.relative_to(TEMPLATE_PAPER)
        target = dest / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            content = item.read_text(encoding="utf-8")
            content = content.replace("paper_version: 0.1.0", f"paper_version: {args.version or '0.1.0'}")
            target.write_text(content, encoding="utf-8")
            created.append(str(rel))

    # 8. Write confirmed paper.yaml
    paper_yaml_content = build_paper_yaml(
        pid=args.id,
        title=args.title.strip(),
        author_id=author_pinyin.lower(),
        paper_type=args.paper_type,
        rules_version="0.1.0",
        date=args.date,
    )
    (dest / "paper.yaml").write_text(paper_yaml_content, encoding="utf-8")
    created.append("paper.yaml")

    # 9. Generate body chapter files from chapters array (clear old template chapters first)
    chapters = parse_chapters(paper_yaml_content)
    body_dir = dest / "body"
    # Remove old template chapter files to avoid conflicts
    for old_file in body_dir.glob("*.md"):
        if old_file.name != "README.md":
            old_file.unlink()
    for idx, ch in enumerate(chapters, start=1):
        slug = ch.get("slug", f"chapter-{idx}")
        title = ch.get("title", slug.replace("-", " ").title())
        chapter_file = body_dir / f"{idx:02d}-{slug}.md"
        chapter_file.parent.mkdir(parents=True, exist_ok=True)
        chapter_file.write_text(
            f"# {title}\n\n"
            f"<!-- render-note\n  Write chapter {idx} content here.\n-->\n",
            encoding="utf-8"
        )
        created.append(f"body/{idx:02d}-{slug}.md")

    # Write per-paper authors.yaml, funding.yaml, writing-spec.yaml, AGENTS.md pointer
    write_paper_authors(dest, author_entry)
    created.append("authors.yaml")
    # funding.yaml: empty template (optional)
    (dest / "funding.yaml").write_text(
        "# Funding Information (optional)\n# Leave empty if no funding.\n\n",
        encoding="utf-8"
    )
    created.append("funding.yaml")
    # writing-spec.yaml: required but content optional
    (dest / "writing-spec.yaml").write_text(
        "# Writing Specification (required, content optional)\n"
        "# Venue-specific writing requirements.\n\n"
        "venue: null\n"
        "url: null\n"
        "target_chars: 15000\n"
        "citation_style: null\n",
        encoding="utf-8"
    )
    created.append("writing-spec.yaml")
    # AGENTS.md pointer: lightweight governance pointer (PF-V10)
    governance_repo = "PaperWorkflows/instruction"
    (dest / "AGENTS.md").write_text(
        f"# Paper Workspace Governance Pointer\n\n"
        f"This paper workspace is governed by the canonical rules in:\n"
        f"`{governance_repo}/AGENTS.md`\n\n"
        f"## Local Skeleton Members (PF-V9)\n\n"
        f"This paper repo contains the following required governance files:\n"
        f"- `paper.yaml` — paper metadata\n"
        f"- `authors.yaml` — author information\n"
        f"- `funding.yaml` — funding information (optional)\n"
        f"- `writing-spec.yaml` — writing requirements (required, content optional)\n\n"
        f"## How to Read Rules\n\n"
        f"1. Read the canonical `AGENTS.md` in `{governance_repo}/` for all governance principles.\n"
        f"2. Read mode-specific rules in `{governance_repo}/governance/` as needed.\n"
        f"3. Read `schemas/` for paper.yaml and authors.yaml structures.\n"
        f"4. Read `templates/` for file skeletons and examples.\n\n"
        f"## Git Identity\n\n"
        f"All commits use: `janssenkm <janssenkm@users.noreply.github.com>`\n"
        f"Git identity does not imply paper authorship.\n",
        encoding="utf-8"
    )
    created.append("AGENTS.md")

    # 10. Initialize git repo
    git_ok = False
    git_err = None
    try:
        subprocess.run(["git", "init", str(dest)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "janssenkm"], cwd=dest, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "janssenkm@users.noreply.github.com"], cwd=dest, check=True, capture_output=True)
        git_ok = True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        git_err = str(e)

    # 11. Create GitHub repo (private)
    gh_created = False
    gh_error = None
    gh_url = None
    if git_ok:
        gh_result = create_github_repo(args.id, private=True)
        if gh_result.get("created"):
            gh_created = True
            gh_url = f"git@github.com:{GITHUB_ORG}/{args.id}.git"
            # Set remote and push
            try:
                subprocess.run(["git", "remote", "add", "origin", gh_url], cwd=dest, check=True, capture_output=True)
                subprocess.run(["git", "add", "."], cwd=dest, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"feat(proposal): initialize {args.id} workspace"],
                               cwd=dest, check=True, capture_output=True)
                subprocess.run(["git", "branch", "-M", "main"], cwd=dest, check=True, capture_output=True)
                subprocess.run(["git", "push", "-u", "origin", "main"], cwd=dest, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                git_err = f"Git push failed: {e}"
                gh_created = False
        else:
            gh_error = gh_result.get("error", "Unknown error")

    result = {
        "status": "ok" if git_ok else "partial",
        "paper_id": args.id,
        "title": args.title.strip(),
        "author": author_entry,
        "paper_type": args.paper_type,
        "destination": str(dest),
        "github_repo": f"{GITHUB_ORG}/{args.id}" if gh_created else None,
        "github_url": gh_url,
        "github_created": gh_created,
        "github_error": gh_error,
        "git_initialized": git_ok,
        "git_error": git_err,
        "chapters": chapters,
        "files_created": len(set(created)),
        "created": created,
    }
    return emit(result)

# ── scaffold ─────────────────────────────────────────────────────

def cmd_scaffold(args):
    try:
        meta = parse_paper_id(args.id)
    except ValueError as e:
        return emit({"status": "error", "error": str(e)}, 2)

    dest = Path(args.dest) if args.dest else PROJECT_ROOT / "papers" / args.id
    if dest.exists():
        return emit({"status": "error", "error": f"Destination already exists: {dest}"}, 2)

    items = list(TEMPLATE_PAPER.rglob("*"))
    created = []
    for item in items:
        rel = item.relative_to(TEMPLATE_PAPER)
        target = dest / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            content = item.read_text(encoding="utf-8")
            content = content.replace("paper_version: 0.1.0",
                                      f"paper_version: {args.version or '0.1.0'}")
            pid_number = args.id.split("-")[0]
            content = content.replace("id: null", f"id: {pid_number}")
            target.write_text(content, encoding="utf-8")
            created.append(str(rel))

    # Generate body chapter files from paper.yaml chapters array (clear old template chapters first)
    paper_yaml = dest / "paper.yaml"
    if paper_yaml.exists():
        yaml_text = paper_yaml.read_text(encoding="utf-8")
        chapters = parse_chapters(yaml_text)
        body_dir = dest / "body"
        body_dir.mkdir(parents=True, exist_ok=True)
        # Remove old template chapter files to avoid conflicts
        for old_file in body_dir.glob("*.md"):
            if old_file.name != "README.md":
                old_file.unlink()
        for idx, ch in enumerate(chapters, start=1):
            slug = ch.get("slug", f"chapter-{idx}")
            title = ch.get("title", slug.replace("-", " ").title())
            chapter_file = body_dir / f"{idx:02d}-{slug}.md"
            chapter_file.parent.mkdir(parents=True, exist_ok=True)
            chapter_file.write_text(
                f"# {title}\n\n"
                f"<!-- render-note\n  Write chapter {idx} content here.\n-->\n",
                encoding="utf-8"
            )
            created.append(f"body/{idx:02d}-{slug}.md")

    # Initialize git repo
    try:
        subprocess.run(["git", "init", str(dest)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "janssenkm"], cwd=dest, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "janssenkm@users.noreply.github.com"], cwd=dest, check=True, capture_output=True)
        remote_url = f"git@github.com:PaperWorkflows/{args.id}.git"
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=dest, check=True, capture_output=True)
        git_ok = True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        git_ok = False
        git_err = str(e)

    result = {
        "status": "ok",
        "paper_id": args.id,
        "destination": str(dest),
        "git_initialized": git_ok,
        "remote_url": f"git@github.com:PaperWorkflows/{args.id}.git",
        "files_created": len(set(created)),
        "created": created,
    }
    if not git_ok:
        result["git_error"] = git_err
    return emit(result)

# ── check ────────────────────────────────────────────────────────

def cmd_validate(args):
    """Full JSON Schema validation of paper.yaml (PF-PL1 admission gate ①, machine check).

    Unlike `check` (text-level key/path checks), this runs the actual
    schemas/paper.schema.json validator including the budget.confirmed
    conditional branch. Exit code 0 only when the file fully validates.
    """
    dest = Path(args.paper) if args.paper else None
    if not dest:
        return emit({"status": "error", "error": "--paper required"}, 2)
    py = dest / "paper.yaml"
    if not py.exists():
        return emit({"status": "error", "error": f"paper.yaml not found in {dest}"}, 2)
    try:
        import jsonschema
    except ImportError:
        return emit({"status": "error", "error": "jsonschema not installed"}), 2
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "paper.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = yaml.safe_load(py.read_text(encoding="utf-8"))
    errors = [
        {"path": "/".join(map(str, e.absolute_path)) or "<root>", "message": e.message[:200]}
        for e in jsonschema.Draft7Validator(schema).iter_errors(data)
    ]
    payload = {
        "status": "pass" if not errors else "fail",
        "paper": dest.name,
        "schema": str(schema_path),
        "error_count": len(errors),
        "errors": errors,
        "note": "PF-PL1 admission gate: polish entry requires status=pass (incl. budget.confirmed branch)",
    }
    return emit(payload, 0 if not errors else 1)


def cmd_check(args):
    dest = Path(args.paper) if args.paper else None
    if not dest:
        return emit({"status": "error", "error": "--paper required"}, 2)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    results = {}
    overall = "pass"

    py = dest / "paper.yaml"
    if not py.exists():
        results["paper.yaml"] = {"status": "fail", "error": "paper.yaml not found"}
        overall = "fail"
    else:
        results["paper.yaml"] = validate_paper_yaml(py)
        if results["paper.yaml"]["status"] == "fail":
            overall = "fail"

    required = [
        "paper.yaml", "authors.yaml", "funding.yaml", "writing-spec.yaml",
        "abstract.md", "outline.md", "research-plan.md", "terms.md",
        "verification.yaml", "references.bib", "body", "figures", "tables",
        "experiments", "appendix", "build", "AGENTS.md", "materials.yaml",
    ]
    missing = []
    for r in required:
        p = dest / r
        if not p.exists():
            missing.append(r)
    if missing:
        results["required_paths"] = {"status": "fail", "missing": missing}
        overall = "fail"
    else:
        results["required_paths"] = {"status": "pass"}

    # Verify AGENTS.md pointer references correct governance repo (PF-V10)
    agents_md = dest / "AGENTS.md"
    if agents_md.exists():
        pointer_text = agents_md.read_text(encoding="utf-8")
        expected_ref = "PaperWorkflows/instruction"
        results["agents_pointer"] = {
            "status": "pass" if expected_ref in pointer_text else "fail",
            "governance_repo_ref": expected_ref if expected_ref in pointer_text else None,
        }
        if expected_ref not in pointer_text:
            overall = "fail"

    body_dir = dest / "body"
    if body_dir.exists() and py.exists():
        yaml_text = py.read_text(encoding="utf-8")
        declared = parse_chapters(yaml_text)
        existing = sorted([c.stem for c in body_dir.glob("*.md") if c.name not in ("README.md", "paper.md")])
        expected = [f"{i:02d}-{ch.get('slug', '')}" for i, ch in enumerate(declared, start=1)]
        results["body_chapters"] = {
            "status": "pass" if existing == expected else "fail",
            "declared": declared,
            "expected_files": expected,
            "actual_files": existing,
        }
        if existing != expected:
            overall = "fail"

    git_dir = dest / ".git"
    results["git_repo"] = {
        "status": "pass" if git_dir.exists() else "fail",
        "initialized": git_dir.exists(),
    }

    return emit({"status": overall, "paper_id": dest.name, "results": results})

# ── version-bump ─────────────────────────────────────────────────

def cmd_version_bump(args):
    dest = Path(args.paper)
    py = dest / "paper.yaml"
    if not py.exists():
        return emit({"status": "error", "error": "paper.yaml not found"}, 2)

    text = py.read_text(encoding="utf-8")
    m = re.search(r'^paper_version:\s*(.+)$', text, re.MULTILINE)
    if not m:
        return emit({"status": "error", "error": "paper_version not found in paper.yaml"}, 2)
    old_ver = m.group(1).strip()
    try:
        parts = [int(x) for x in old_ver.split(".")]
    except ValueError:
        return emit({"status": "error", "error": f"Invalid version format: {old_ver}"}, 2)

    level = args.level
    if level == "major":
        parts[0] += 1; parts[1] = 0; parts[2] = 0
    elif level == "minor":
        parts[1] += 1; parts[2] = 0
    elif level == "patch":
        parts[2] += 1
    else:
        return emit({"status": "error", "error": f"Invalid level: {level} (major/minor/patch)"}, 2)
    new_ver = ".".join(str(x) for x in parts)

    text = text.replace(f"paper_version: {old_ver}", f"paper_version: {new_ver}", 1)
    py.write_text(text, encoding="utf-8")

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "old_version": old_ver,
        "new_version": new_ver,
        "level": level,
    })

# ── materials ──────────────────────────────────────────────────────

MATERIALS_FILE = "materials.yaml"


def _load_materials(dest: Path) -> dict:
    """Load materials.yaml, returning empty structure if missing."""
    mf = dest / MATERIALS_FILE
    if not mf.exists():
        return {"materials": []}
    try:
        data = yaml.safe_load(mf.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "materials" not in data:
            return {"materials": []}
        return data
    except Exception:
        return {"materials": []}


def _save_materials(dest: Path, data: dict) -> None:
    dest.joinpath(MATERIALS_FILE).write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def cmd_materials_add(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    mat_type = args.type  # paper | dataset | code | tool
    identifier = args.identifier  # DOI, URL, repo slug, etc.
    title = args.title or "(untitled)"
    relevance = args.relevance or "general"

    data = _load_materials(dest)
    materials = data.get("materials", [])

    # Check for duplicates by identifier
    existing = [m for m in materials if m.get("identifier") == identifier]
    if existing:
        return emit({
            "status": "duplicate",
            "message": f"Material already registered: {identifier}",
            "existing": existing[0],
        }, 1)

    entry = {
        "material_id": f"MAT-{len(materials)+1:04d}",
        "type": mat_type,
        "identifier": identifier,
        "title": title,
        "relevance": relevance,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "status": "registered",
    }
    materials.append(entry)
    data["materials"] = materials
    _save_materials(dest, data)

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "added": entry,
        "total_materials": len(materials),
    })


def cmd_materials_list(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    data = _load_materials(dest)
    materials = data.get("materials", [])

    # Optional filter by type
    mat_type = getattr(args, "type", None)
    if mat_type:
        materials = [m for m in materials if m.get("type") == mat_type]

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "count": len(materials),
        "materials": materials,
    })


def cmd_materials_check(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    data = _load_materials(dest)
    materials = data.get("materials", [])

    # Find duplicates by identifier
    seen = {}
    duplicates = []
    for m in materials:
        ident = m.get("identifier")
        if ident in seen:
            duplicates.append({"identifier": ident, "entries": [seen[ident], m]})
        else:
            seen[ident] = m

    # Find near-duplicates by title similarity (simple case-insensitive compare)
    titles = [m.get("title", "").lower().strip() for m in materials]
    title_dups = []
    for i, t1 in enumerate(titles):
        for j, t2 in enumerate(titles):
            if i < j and t1 and t2 and t1 == t2:
                title_dups.append({
                    "title": materials[i].get("title"),
                    "entries": [materials[i], materials[j]],
                })

    status = "pass" if not duplicates and not title_dups else "fail"
    return emit({
        "status": status,
        "paper_id": dest.name,
        "total": len(materials),
        "duplicate_identifiers": duplicates,
        "duplicate_titles": title_dups,
    })


def cmd_materials_debate(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    data = _load_materials(dest)
    materials = data.get("materials", [])

    if not materials:
        return emit({"status": "error", "error": "No materials registered. Use 'materials add' first."}, 2)

    # Build context from materials
    context_lines = [f"Paper: {dest.name}", f"Total materials: {len(materials)}", ""]
    for m in materials:
        context_lines.append(f"- [{m.get('type', '?')}] {m.get('title', '?')} ({m.get('identifier', '?')})")
    context = "\n".join(context_lines)

    prompt = (
        "Evaluate the following research materials for completeness, "
        "relevance, and potential gaps. Identify any missing material types "
        "or weak coverage. Be concise.\n\n" + context
    )

    # Import debate module
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from debate import run_debate
        result = run_debate(prompt, rounds=1)
    except Exception as exc:
        return emit({"status": "error", "error": f"Debate module error: {exc}"}, 2)

    # Write debate output to paper workspace
    debate_file = dest / "materials" / "debate-assessment.md"
    try:
        debate_file.parent.mkdir(parents=True, exist_ok=True)
        from debate import debate_to_markdown
        debate_file.write_text(debate_to_markdown(result), encoding="utf-8")
        debate_path = str(debate_file)
    except Exception:
        debate_path = None

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "debate_path": debate_path,
        "consensus_preview": str(result.get("final_consensus", {}))[:500],
    })


# ── experiments ────────────────────────────────────────────────────

EXPERIMENTS_FILE = "experiments/record.yaml"


def _load_experiments(dest: Path) -> dict:
    """Load experiments/record.yaml, returning empty structure if missing."""
    exp_file = dest / EXPERIMENTS_FILE
    if not exp_file.exists():
        return {"experiments": []}
    try:
        data = yaml.safe_load(exp_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "experiments" not in data:
            return {"experiments": []}
        return data
    except Exception:
        return {"experiments": []}


def _save_experiments(dest: Path, data: dict) -> None:
    dest.joinpath(EXPERIMENTS_FILE).write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def cmd_experiments_add(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    name = args.name
    description = args.description or "(no description)"
    parameters = args.parameters or "{}"

    data = _load_experiments(dest)
    experiments = data.get("experiments", [])

    # Check for duplicates by name
    existing = [e for e in experiments if e.get("name") == name]
    if existing:
        return emit({
            "status": "duplicate",
            "message": f"Experiment already registered: {name}",
            "existing": existing[0],
        }, 1)

    entry = {
        "experiment_id": f"EXP-{len(experiments)+1:04d}",
        "name": name,
        "description": description,
        "parameters": parameters,
        "status": "planned",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    experiments.append(entry)
    data["experiments"] = experiments
    _save_experiments(dest, data)

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "added": entry,
        "total_experiments": len(experiments),
    })


def cmd_experiments_list(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    data = _load_experiments(dest)
    experiments = data.get("experiments", [])

    # Optional filter by status
    status_filter = getattr(args, "status", None)
    if status_filter:
        experiments = [e for e in experiments if e.get("status") == status_filter]

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "count": len(experiments),
        "experiments": experiments,
    })


def cmd_experiments_update(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    exp_id = args.experiment_id
    data = _load_experiments(dest)
    experiments = data.get("experiments", [])

    # Find experiment by ID or name
    target = None
    for e in experiments:
        if e.get("experiment_id") == exp_id or e.get("name") == exp_id:
            target = e
            break

    if not target:
        return emit({"status": "error", "error": f"Experiment not found: {exp_id}"}, 2)

    # Update fields
    updates = {}
    if args.new_status:
        target["status"] = args.new_status
        updates["status"] = args.new_status
    if args.result:
        target["result"] = args.result
        updates["result"] = args.result
    if args.notes:
        target["notes"] = args.notes
        updates["notes"] = args.notes

    target["updated_at"] = datetime.now(timezone.utc).isoformat()

    _save_experiments(dest, data)

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "experiment_id": target["experiment_id"],
        "updated": updates,
    })


def cmd_experiments_compare(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    id_a = args.experiment_a
    id_b = args.experiment_b

    data = _load_experiments(dest)
    experiments = data.get("experiments", [])

    # Find experiments
    exp_a = None
    exp_b = None
    for e in experiments:
        if e.get("experiment_id") == id_a or e.get("name") == id_a:
            exp_a = e
        if e.get("experiment_id") == id_b or e.get("name") == id_b:
            exp_b = e

    if not exp_a or not exp_b:
        missing = []
        if not exp_a:
            missing.append(id_a)
        if not exp_b:
            missing.append(id_b)
        return emit({"status": "error", "error": f"Experiment(s) not found: {', '.join(missing)}"}, 2)

    # Simple comparison
    comparison = {
        "experiment_a": {
            "id": exp_a.get("experiment_id"),
            "name": exp_a.get("name"),
            "status": exp_a.get("status"),
            "parameters": exp_a.get("parameters"),
        },
        "experiment_b": {
            "id": exp_b.get("experiment_id"),
            "name": exp_b.get("name"),
            "status": exp_b.get("status"),
            "parameters": exp_b.get("parameters"),
        },
        "differences": [],
    }

    # Detect differences
    for key in ["status", "parameters"]:
        if exp_a.get(key) != exp_b.get(key):
            comparison["differences"].append({
                "field": key,
                "a": exp_a.get(key),
                "b": exp_b.get(key),
            })

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "comparison": comparison,
    })


def cmd_experiments_debate(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    data = _load_experiments(dest)
    experiments = data.get("experiments", [])

    if not experiments:
        return emit({"status": "error", "error": "No experiments registered. Use 'experiments add' first."}, 2)

    # Build context from experiments
    context_lines = [f"Paper: {dest.name}", f"Total experiments: {len(experiments)}", ""]
    for e in experiments:
        context_lines.append(
            f"- {e.get('experiment_id', '?')}: {e.get('name', '?')} "
            f"[{e.get('status', '?')}] — {e.get('description', '?')}"
        )
    context = "\n".join(context_lines)

    prompt = (
        "Evaluate the following experiment plan for scientific rigor, "
        "reproducibility, and completeness. Identify any design flaws, "
        "missing controls, or statistical issues. Be concise.\n\n" + context
    )

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from debate import run_debate, debate_to_markdown
        result = run_debate(prompt, rounds=1)
    except Exception as exc:
        return emit({"status": "error", "error": f"Debate module error: {exc}"}, 2)

    # Write debate output
    debate_file = dest / "experiments" / "debate-assessment.md"
    try:
        debate_file.parent.mkdir(parents=True, exist_ok=True)
        debate_file.write_text(debate_to_markdown(result), encoding="utf-8")
        debate_path = str(debate_file)
    except Exception:
        debate_path = None

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "debate_path": debate_path,
        "consensus_preview": str(result.get("final_consensus", {}))[:500],
    })


# ── writing ────────────────────────────────────────────────────────

def _count_chinese_chars(text: str) -> int:
    """Count Chinese characters and words in mixed Chinese/English text."""
    import re
    # Count CJK characters
    cjk = re.findall(r'[\u4e00-\u9fff]', text)
    # Count non-CJK words (split by whitespace)
    non_cjk = re.sub(r'[\u4e00-\u9fff]', ' ', text)
    words = len(non_cjk.split())
    return len(cjk) + words


def _get_chapter_status(dest: Path, chapter_file: str) -> dict:
    """Get status and word count for a chapter file."""
    chapter_path = dest / "body" / chapter_file
    if not chapter_path.exists():
        return {"file": chapter_file, "exists": False, "status": "missing", "word_count": 0}

    text = chapter_path.read_text(encoding="utf-8")
    word_count = _count_chinese_chars(text)

    # Check for manual status override
    manual_status = None
    lines = text.splitlines()
    if lines and lines[0].startswith("<!-- writing-status:"):
        import re
        m = re.match(r'<!-- writing-status: (\w+) -->', lines[0])
        if m:
            manual_status = m.group(1)

    # Determine status based on content (only if no manual override)
    if manual_status:
        status = manual_status
    elif not text.strip() or len(text.strip()) < 50:
        status = "outline"
    elif word_count < 500:
        status = "draft"
    elif word_count < 1000:
        status = "developing"
    else:
        status = "complete"

    return {
        "file": chapter_file,
        "exists": True,
        "status": status,
        "word_count": word_count,
    }


def cmd_writing_status(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    py = dest / "paper.yaml"
    if not py.exists():
        return emit({"status": "error", "error": "paper.yaml not found"}, 2)

    # Parse chapters from paper.yaml
    yaml_text = py.read_text(encoding="utf-8")
    chapters = parse_chapters(yaml_text)

    if not chapters:
        return emit({"status": "error", "error": "No chapters declared in paper.yaml"}, 2)

    chapter_statuses = []
    total_words = 0
    status_counts = {"outline": 0, "draft": 0, "developing": 0, "complete": 0, "missing": 0}

    for ch in chapters:
        slug = ch.get("slug", "")
        chapter_file = f"{ch['number']:02d}-{slug}.md"
        status = _get_chapter_status(dest, chapter_file)
        chapter_statuses.append(status)
        total_words += status.get("word_count", 0)
        status_counts[status["status"]] = status_counts.get(status["status"], 0) + 1

    # Get target from writing-spec.yaml
    writing_spec = dest / "writing-spec.yaml"
    target_chars = 15000
    if writing_spec.exists():
        try:
            spec = yaml.safe_load(writing_spec.read_text(encoding="utf-8"))
            target_chars = spec.get("target_chars", 15000)
        except Exception:
            pass

    progress_pct = min(100, int(total_words / target_chars * 100)) if target_chars > 0 else 0

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "total_chapters": len(chapters),
        "total_words": total_words,
        "target_chars": target_chars,
        "progress_pct": progress_pct,
        "status_breakdown": status_counts,
        "chapters": chapter_statuses,
    })


def cmd_writing_update(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    chapter = args.chapter  # e.g., "01-introduction" or "introduction"
    new_status = args.status

    # Normalize chapter identifier
    if not chapter.startswith("0") and not chapter[0].isdigit():
        # It's a slug, find the matching file
        body_dir = dest / "body"
        if not body_dir.exists():
            return emit({"status": "error", "error": "body/ directory not found"}, 2)

        py = dest / "paper.yaml"
        if not py.exists():
            return emit({"status": "error", "error": "paper.yaml not found"}, 2)

        yaml_text = py.read_text(encoding="utf-8")
        chapters = parse_chapters(yaml_text)

        chapter_file = None
        for ch in chapters:
            if ch.get("slug", "") == chapter:
                chapter_file = f"{ch['number']:02d}-{chapter}.md"
                break

        if not chapter_file:
            return emit({"status": "error", "error": f"Chapter slug not found: {chapter}"}, 2)
    else:
        chapter_file = chapter if chapter.endswith(".md") else f"{chapter}.md"

    chapter_path = dest / "body" / chapter_file
    if not chapter_path.exists():
        return emit({"status": "error", "error": f"Chapter file not found: {chapter_file}"}, 2)

    # Write status as YAML frontmatter comment
    text = chapter_path.read_text(encoding="utf-8")
    status_line = f"<!-- writing-status: {new_status} -->\n"

    # Remove old status line if present
    lines = text.splitlines()
    if lines and lines[0].startswith("<!-- writing-status:"):
        lines[0] = f"<!-- writing-status: {new_status} -->"
        text = "\n".join(lines)
    else:
        text = status_line + text

    chapter_path.write_text(text, encoding="utf-8")

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "chapter": chapter_file,
        "writing_status": new_status,
    })


def cmd_writing_debate(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    chapter = args.chapter  # optional: specific chapter to review

    # Build context from chapters
    py = dest / "paper.yaml"
    if not py.exists():
        return emit({"status": "error", "error": "paper.yaml not found"}, 2)

    yaml_text = py.read_text(encoding="utf-8")
    chapters = parse_chapters(yaml_text)

    if not chapters:
        return emit({"status": "error", "error": "No chapters declared in paper.yaml"}, 2)

    context_lines = [f"Paper: {dest.name}", "Chapters:", ""]

    target_chapters = []
    if chapter:
        # Find specific chapter
        for ch in chapters:
            if ch.get("slug", "") == chapter or f"{ch['number']:02d}-{ch.get('slug','')}.md" == chapter:
                target_chapters.append(ch)
                break
        if not target_chapters:
            return emit({"status": "error", "error": f"Chapter not found: {chapter}"}, 2)
    else:
        target_chapters = chapters

    for ch in target_chapters:
        slug = ch.get("slug", "")
        chapter_file = f"{ch['number']:02d}-{slug}.md"
        chapter_path = dest / "body" / chapter_file
        if chapter_path.exists():
            content = chapter_path.read_text(encoding="utf-8")[:2000]
            context_lines.append(f"\n### {ch['number']:02d}-{slug}: {ch.get('title', '')}")
            context_lines.append(content)
        else:
            context_lines.append(f"\n### {ch['number']:02d}-{slug}: {ch.get('title', '')} [MISSING]")

    context = "\n".join(context_lines)

    prompt = (
        "Evaluate the following paper chapter(s) for academic writing quality, "
        "clarity, structure, and compliance with these rules (PF-W1 to PF-W10):\n"
        "- W1: Authenticity (no fabricated claims)\n"
        "- W2: Chinese body text, bilingual abstract\n"
        "- W3: Independent contribution, novelty\n"
        "- W4: Theory/algorithm/system methods\n"
        "- W5: Experiment design and statistics\n"
        "- W6: Literature citation verification\n"
        "- W7: Privacy, license, technical conditions\n"
        "- W8: Figures, tables, formulas, terminology\n"
        "- W9: Self-sufficiency and reader understanding\n"
        "- W10: Claim-evidence correspondence and limitations\n\n"
        "Provide: (1) overall assessment, (2) strengths, (3) weaknesses, "
        "(4) specific improvements. Be concise.\n\n" + context
    )

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from debate import run_debate, debate_to_markdown
        result = run_debate(prompt, rounds=1)
    except Exception as exc:
        return emit({"status": "error", "error": f"Debate module error: {exc}"}, 2)

    # Write debate output
    chapter_slug = chapter if chapter else "all"
    debate_file = dest / "body" / f"{chapter_slug}-writing-debate.md"
    try:
        debate_file.write_text(debate_to_markdown(result), encoding="utf-8")
        debate_path = str(debate_file)
    except Exception:
        debate_path = None

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "chapter": chapter_slug,
        "debate_path": debate_path,
        "consensus_preview": str(result.get("final_consensus", {}))[:500],
    })


# ── review ────────────────────────────────────────────────────────

REVIEWS_DIR = "reviews"
ISSUES_FILE = "reviews/issues.yaml"

PERSPECTIVES = {
    "R-A": {
        "name": "Venue/Editor",
        "rules": ["PF-W1", "PF-W2", "PF-W3", "PF-W4", "PF-W9", "PF-W10"],
        "focus": "Problem value, contribution, related work, logic, independence, submission fit",
    },
    "R-B": {
        "name": "Technical/Reproducibility",
        "rules": ["PF-W4", "PF-W5", "PF-W6", "PF-W7", "PF-W8", "PF-W10"],
        "focus": "Proof, algorithm, system, data, experiment, statistics, source support, reproduction",
    },
    "R-C": {
        "name": "Editor/Reader",
        "rules": ["PF-W1", "PF-W2", "PF-W3", "PF-W6", "PF-W7", "PF-W8", "PF-W9", "PF-W10"],
        "focus": "Bilingual consistency, terminology, citations, authorship, structure, self-sufficiency",
    },
    "R-D": {
        "name": "Layout/Output",
        "rules": ["PF-W2", "PF-W8"],
        "focus": "Docx, PDF, captions, formulas, figures, tables, layout",
    },
}


def _load_issues(dest: Path) -> dict:
    """Load reviews/issues.yaml, returning empty structure if missing."""
    issues_file = dest / ISSUES_FILE
    if not issues_file.exists():
        return {"issues": []}
    try:
        data = yaml.safe_load(issues_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "issues" not in data:
            return {"issues": []}
        return data
    except Exception:
        return {"issues": []}


def _save_issues(dest: Path, data: dict) -> None:
    dest.joinpath(ISSUES_FILE).write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def cmd_review_create(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    perspective = args.perspective.upper()
    if perspective not in PERSPECTIVES:
        return emit({
            "status": "error",
            "error": f"Invalid perspective: {perspective}. Choose from: {', '.join(PERSPECTIVES.keys())}",
        }, 2)

    # Create reviews directory
    reviews_dir = dest / REVIEWS_DIR
    reviews_dir.mkdir(parents=True, exist_ok=True)

    # Get paper version
    py = dest / "paper.yaml"
    version = "0.1.0"
    if py.exists():
        text = py.read_text(encoding="utf-8")
        m = re.search(r'^paper_version:\s*(.+)$', text, re.MULTILINE)
        if m:
            version = m.group(1).strip()

    # Generate report filename
    report_file = reviews_dir / f"{perspective}-{dest.name}-v{version}.md"

    # Load template
    template_path = Path(__file__).resolve().parent.parent / "templates/paper/reviews/report-template.md"
    template_content = ""
    if template_path.exists():
        template_content = template_path.read_text(encoding="utf-8")

    # Fill in template (escape any remaining braces)
    perspective_info = PERSPECTIVES[perspective]
    try:
        report_content = template_content.format(
            PERSPECTIVE=perspective,
            PERSPECTIVE_DESCRIPTION=perspective_info["name"],
            PAPER_ID=dest.name,
            VERSION=version,
            DATE=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            APPLICABLE_RULES=", ".join(perspective_info["rules"]),
            COMMIT_SHA="(pending)",
            RULE_ID="PF-XX",
            RULE_TITLE="(to be filled)",
            FINDING_SUMMARY="(to be filled)",
            CHECK_METHOD_DESCRIPTION=perspective_info["focus"],
            EXECUTION_RECORD="(to be filled)",
            N=1,
            TITLE="(to be filled)",
            FILE_PATH="(to be filled)",
            LINE_NUMBER="(to be filled)",
            IMPACT_DESCRIPTION="(to be filled)",
            EVIDENCE="(to be filled)",
            SUGGESTED_FIX="(to be filled)",
            COUNT=0,
            LIMITATIONS="(to be filled)",
        )
    except KeyError as exc:
        # Template has unmatched braces, use raw template with replacements
        report_content = template_content.replace("{", "{{").replace("}", "}}")
        report_content = report_content.replace("{{PERSPECTIVE}}", perspective)
        report_content = report_content.replace("{{PERSPECTIVE_DESCRIPTION}}", perspective_info["name"])
        report_content = report_content.replace("{{PAPER_ID}}", dest.name)
        report_content = report_content.replace("{{VERSION}}", version)
        report_content = report_content.replace("{{DATE}}", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        report_content = report_content.replace("{{APPLICABLE_RULES}}", ", ".join(perspective_info["rules"]))
        report_content = report_content.replace("{{COMMIT_SHA}}", "(pending)")

    report_file.write_text(report_content, encoding="utf-8")

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "perspective": perspective,
        "perspective_name": perspective_info["name"],
        "applicable_rules": perspective_info["rules"],
        "report_path": str(report_file),
    })


def cmd_review_issues(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    data = _load_issues(dest)
    issues = data.get("issues", [])

    # Optional filter by grade
    grade_filter = getattr(args, "grade", None)
    if grade_filter:
        issues = [i for i in issues if i.get("grade", "").upper() == grade_filter.upper()]

    # Optional filter by status
    status_filter = getattr(args, "status", None)
    if status_filter:
        issues = [i for i in issues if i.get("status", "") == status_filter]

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "total_issues": len(issues),
        "issues": issues,
    })


def cmd_review_close(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    issue_id = args.issue_id
    new_status = args.new_status
    evidence = args.evidence or ""

    if new_status not in ["fixed-pending-verify", "re-verified", "rebuttal-valid", "not-applicable", "unresolved"]:
        return emit({
            "status": "error",
            "error": f"Invalid status: {new_status}. Choose from: fixed-pending-verify, re-verified, rebuttal-valid, not-applicable, unresolved",
        }, 2)

    data = _load_issues(dest)
    issues = data.get("issues", [])

    # Find issue by ID
    target = None
    for issue in issues:
        if issue.get("issue_id") == issue_id:
            target = issue
            break

    if not target:
        return emit({"status": "error", "error": f"Issue not found: {issue_id}"}, 2)

    # Update issue
    target["status"] = new_status
    target["resolution_evidence"] = evidence
    target["resolved_at"] = datetime.now(timezone.utc).isoformat()

    _save_issues(dest, data)

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "issue_id": issue_id,
        "new_status": new_status,
        "evidence": evidence,
    })


def cmd_review_debate(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    issue_id = args.issue_id

    # Load issue
    data = _load_issues(dest)
    issues = data.get("issues", [])

    target = None
    for issue in issues:
        if issue.get("issue_id") == issue_id:
            target = issue
            break

    if not target:
        return emit({"status": "error", "error": f"Issue not found: {issue_id}"}, 2)

    # Build context from issue
    context_lines = [
        f"Paper: {dest.name}",
        f"Issue: {issue_id}",
        f"Grade: {target.get('grade', '?')}",
        f"Status: {target.get('status', '?')}",
        f"Rule: {target.get('rule', '?')} — {target.get('rule_title', '?')}",
        f"Location: {target.get('location', '?')}",
        "",
        "Description:",
        target.get("description", "(no description)"),
        "",
        "Suggested Fix:",
        target.get("suggested_fix", "(none)"),
        "",
        "Evidence:",
        target.get("evidence", "(none)"),
    ]
    context = "\n".join(context_lines)

    prompt = (
        "Two reviewers disagree on this issue. Evaluate both sides and propose a resolution.\n"
        "Issue grading (PF-RV4): P0=blocking, P1=important, P2=improvement.\n"
        "Provide: (1) summary of disagreement, (2) evidence evaluation, "
        "(3) recommended resolution with rationale.\n\n" + context
    )

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from debate import run_debate, debate_to_markdown
        result = run_debate(prompt, rounds=1)
    except Exception as exc:
        return emit({"status": "error", "error": f"Debate module error: {exc}"}, 2)

    # Write debate output
    debate_file = dest / REVIEWS_DIR / f"{issue_id}-dispute-debate.md"
    try:
        debate_file.write_text(debate_to_markdown(result), encoding="utf-8")
        debate_path = str(debate_file)
    except Exception:
        debate_path = None

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "issue_id": issue_id,
        "debate_path": debate_path,
        "consensus_preview": str(result.get("final_consensus", {}))[:500],
    })
    parser = Parser(description="PaperFactory CLI")
    sub = parser.add_subparsers(dest="command")

    p_proposal = sub.add_parser("proposal", help="Execute full proposal flow: author + materials → GitHub repo")
    p_proposal.add_argument("--id", required=True, help="Paper repo name, e.g. P1-EXAMPLE-20251110")
    p_proposal.add_argument("--author-name", required=True, help="First author full name (native script)")
    p_proposal.add_argument("--author-pinyin", required=True, help="First author pinyin (uppercase, e.g. EXAMPLE)")
    p_proposal.add_argument("--title", required=True, help="Paper title")
    p_proposal.add_argument("--paper-type", required=True,
                            choices=["theory", "algorithm_experiment", "software_system", "empirical", "mixed"],
                            help="Paper type (determines default chapter structure)")
    p_proposal.add_argument("--author-name-en", default=None, help="Author name in English (optional)")
    p_proposal.add_argument("--affiliation", default=None, help="Author affiliation (optional)")
    p_proposal.add_argument("--email", default=None, help="Author email (optional, null for privacy)")
    p_proposal.add_argument("--date", default=None, help="Proposal date (ISO format, default: now)")
    p_proposal.add_argument("--dest", help="Destination directory (default: papers/<id>)")
    p_proposal.add_argument("--version", default="0.1.0", help="Initial paper_version (default: 0.1.0)")

    p_scaffold = sub.add_parser("scaffold", help="Create a new paper workspace from template (no GitHub)")
    p_scaffold.add_argument("--id", required=True, help="Paper repo name, e.g. P1-EXAMPLE-20251110")
    p_scaffold.add_argument("--dest", help="Destination directory (default: papers/<id>)")
    p_scaffold.add_argument("--version", default="0.1.0", help="Initial paper_version (default: 0.1.0)")

    p_check = sub.add_parser("check", help="Validate a paper workspace against schema and required paths")
    p_validate = sub.add_parser("validate", help="Full JSON Schema validation of paper.yaml (PF-PL1 admission gate)")
    p_check.add_argument("--paper", required=True, help="Path to paper workspace directory")
    p_validate.add_argument("--paper", required=True, help="Path to paper workspace directory")

    p_bump = sub.add_parser("version-bump", help="Bump paper_version in paper.yaml")
    p_bump.add_argument("--paper", required=True, help="Path to paper workspace directory")
    p_bump.add_argument("--level", required=True, choices=["major", "minor", "patch"])

    p_materials = sub.add_parser("materials", help="Manage research materials")
    p_materials_sub = p_materials.add_subparsers(dest="materials_command")

    p_mat_add = p_materials_sub.add_parser("add", help="Register a new material")
    p_mat_add.add_argument("--paper", required=True, help="Path to paper workspace")
    p_mat_add.add_argument("--type", required=True, choices=["paper", "dataset", "code", "tool"], help="Material type")
    p_mat_add.add_argument("--identifier", required=True, help="DOI, URL, or unique identifier")
    p_mat_add.add_argument("--title", default=None, help="Material title")
    p_mat_add.add_argument("--relevance", default="general", help="Relevance to paper (general | core | supporting)")

    p_mat_list = p_materials_sub.add_parser("list", help="List registered materials")
    p_mat_list.add_argument("--paper", required=True, help="Path to paper workspace")
    p_mat_list.add_argument("--type", default=None, help="Filter by type")

    p_mat_check = p_materials_sub.add_parser("check", help="Check for duplicate or missing materials")
    p_mat_check.add_argument("--paper", required=True, help="Path to paper workspace")

    p_mat_debate = p_materials_sub.add_parser("debate", help="Assess materials quality via mmx/agy debate")
    p_mat_debate.add_argument("--paper", required=True, help="Path to paper workspace")

    p_experiments = sub.add_parser("experiments", help="Manage experiments")
    p_exp_sub = p_experiments.add_subparsers(dest="experiments_command")

    p_exp_add = p_exp_sub.add_parser("add", help="Register a new experiment")
    p_exp_add.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_add.add_argument("--name", required=True, help="Experiment name")
    p_exp_add.add_argument("--description", default=None, help="Experiment description")
    p_exp_add.add_argument("--parameters", default="{}", help="Parameters as JSON string")

    p_exp_list = p_exp_sub.add_parser("list", help="List experiments")
    p_exp_list.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_list.add_argument("--status", default=None, help="Filter by status")

    p_exp_update = p_exp_sub.add_parser("update", help="Update experiment status or result")
    p_exp_update.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_update.add_argument("--experiment-id", required=True, help="Experiment ID or name")
    p_exp_update.add_argument("--new-status", default=None, help="New status: planned|running|completed|failed")
    p_exp_update.add_argument("--result", default=None, help="Result summary")
    p_exp_update.add_argument("--notes", default=None, help="Additional notes")

    p_exp_compare = p_exp_sub.add_parser("compare", help="Compare two experiments")
    p_exp_compare.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_compare.add_argument("--experiment-a", required=True, help="First experiment ID or name")
    p_exp_compare.add_argument("--experiment-b", required=True, help="Second experiment ID or name")

    p_exp_debate = p_exp_sub.add_parser("debate", help="Assess experiment design via mmx/agy debate")
    p_exp_debate.add_argument("--paper", required=True, help="Path to paper workspace")

    p_writing = sub.add_parser("writing", help="Manage paper writing progress")
    p_writing_sub = p_writing.add_subparsers(dest="writing_command")

    p_writing_status = p_writing_sub.add_parser("status", help="Show writing progress across all chapters")
    p_writing_status.add_argument("--paper", required=True, help="Path to paper workspace")

    p_writing_update = p_writing_sub.add_parser("update", help="Update chapter writing status")
    p_writing_update.add_argument("--paper", required=True, help="Path to paper workspace")
    p_writing_update.add_argument("--chapter", required=True, help="Chapter slug or file (e.g., introduction or 01-introduction)")
    p_writing_update.add_argument("--status", required=True, choices=["outline", "draft", "developing", "complete"], help="Writing status")

    p_writing_debate = p_writing_sub.add_parser("debate", help="Assess chapter writing quality via mmx/agy debate")
    p_writing_debate.add_argument("--paper", required=True, help="Path to paper workspace")
    p_writing_debate.add_argument("--chapter", default=None, help="Specific chapter slug (optional, default: all)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        raise SystemExit(2)

    cmds = {
        "proposal": cmd_proposal,
        "scaffold": cmd_scaffold,
        "check": cmd_check,
        "validate": cmd_validate,
        "version-bump": cmd_version_bump,
        "materials": lambda args: {
            "add": cmd_materials_add,
            "list": cmd_materials_list,
            "check": cmd_materials_check,
            "debate": cmd_materials_debate,
        }[args.materials_command](args),
        "experiments": lambda args: {
            "add": cmd_experiments_add,
            "list": cmd_experiments_list,
            "update": cmd_experiments_update,
            "compare": cmd_experiments_compare,
            "debate": cmd_experiments_debate,
        }[args.experiments_command](args),
        "writing": lambda args: {
            "status": cmd_writing_status,
            "update": cmd_writing_update,
            "debate": cmd_writing_debate,
        }[args.writing_command](args),
        "review": lambda args: {
            "create": cmd_review_create,
            "issues": cmd_review_issues,
            "close": cmd_review_close,
            "debate": cmd_review_debate,
        }[args.review_command](args),
        "build": lambda args: {
            "init": cmd_build_init,
            "snapshot": cmd_build_snapshot,
            "docx": cmd_build_docx,
            "pdf": cmd_build_pdf,
            "list": cmd_build_list,
            "debate": cmd_build_debate,
        }[args.build_command](args),
    }
    code = cmds[args.command](args)
    raise SystemExit(code)


# ── build ─────────────────────────────────────────────────────────

def _get_paper_info(dest: Path) -> dict:
    """Extract basic paper info from paper.yaml.

    The values are read from the parsed YAML, not from a regex over the raw
    text: a regex mis-reads YAML block scalars ('title: >' yielded '>'), and the
    title drives both the artifact filename and the running head.
    """
    py = dest / "paper.yaml"
    info = {"id": dest.name, "version": "0.1.0", "title": "(untitled)", "stage": "proposal", "paper_type": "empirical"}
    if not py.exists():
        return info
    try:
        data = yaml.safe_load(py.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return info
    if not isinstance(data, dict):
        return info
    for key in ("paper_version", "version"):
        if data.get(key):
            info["version"] = str(data[key]).strip()
            break
    title = data.get("title")
    if isinstance(title, str) and title.strip():
        info["title"] = title.strip().splitlines()[0].strip()
    if data.get("stage"):
        info["stage"] = str(data["stage"]).strip()
    if data.get("paper_type"):
        info["paper_type"] = str(data["paper_type"]).strip()
    return info


def _create_snapshot(dest: Path) -> dict:
    """Create input snapshot for build (PF-B4)."""
    snapshot = {"created_at": datetime.now(timezone.utc).isoformat(), "paper_id": dest.name, "files": []}
    key_files = [
        "paper.yaml", "authors.yaml", "funding.yaml", "writing-spec.yaml",
        "abstract.md", "outline.md", "research-plan.md", "terms.md",
        "verification.yaml", "references.bib",
    ]
    body_dir = dest / "body"
    if body_dir.exists():
        for f in sorted(body_dir.glob("*.md")):
            key_files.append(f"body/{f.name}")
    for subdir in ["figures", "tables", "experiments", "appendix", "build"]:
        subdir_path = dest / subdir
        if subdir_path.exists():
            for f in sorted(subdir_path.rglob("*")):
                if f.is_file():
                    key_files.append(f"{subdir}/{f.relative_to(subdir_path)}")
    for rel_path in key_files:
        full_path = dest / rel_path
        if full_path.exists() and full_path.is_file():
            try:
                content = full_path.read_bytes()
                import hashlib
                snapshot["files"].append({"path": rel_path, "sha256": hashlib.sha256(content).hexdigest()[:16], "size": len(content)})
            except Exception:
                pass
    return snapshot


def cmd_build_init(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)
    temp_dir = dest / "temp"
    output_dir = dest / "output"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    current_json = output_dir / "current.json"
    if not current_json.exists():
        current_json.write_text('{"status": "no-build-yet", "message": "Run build docx or build pdf to create first release"}', encoding="utf-8")
    return emit({"status": "ok", "paper_id": dest.name, "temp_dir": str(temp_dir), "output_dir": str(output_dir)})


def cmd_build_snapshot(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)
    snapshot = _create_snapshot(dest)
    snapshot_file = dest / "temp" / "build-snapshot.json"
    try:
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        import json
        snapshot_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return emit({"status": "ok", "paper_id": dest.name, "snapshot_path": str(snapshot_file), "file_count": len(snapshot["files"])})
    except Exception as exc:
        return emit({"status": "error", "error": f"Failed to write snapshot: {exc}"}, 2)


def _posix_safe_title(title: str) -> str:
    """PF-B7 filename rule: POSIX-safe escaping, CJK preserved."""
    return re.sub(r'[/\\:*?"<>|\s]+', "_", title).strip("_") or "paper"


def _norm_version(v: str) -> str:
    v = (v or "0.1.0").strip()
    return v if v.startswith("v") else f"v{v}"


def _load_paper_yaml(dest: Path) -> dict:
    """Load paper.yaml. A malformed file is a build failure, not a silent fallback.

    Falling back to {} here would silently downgrade the paper to the L0 draft
    profile (PF-B11: no silent degradation).
    """
    py = dest / "paper.yaml"
    if not py.exists():
        return {}
    try:
        return yaml.safe_load(py.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"{py} is not valid YAML: {exc}") from None


# PDF font families that satisfy a profile font requirement, including the
# LibreOffice / fontconfig substitutions observed on this build host.
_FONT_SUBSTITUTIONS = {
    "宋体": ["SimSun", "NSimSun", "NotoSerifCJKsc", "Songti", "STSong", "SourceHanSerif"],
    "新宋体": ["NSimSun", "SimSun", "NotoSerifCJKsc", "Songti"],
    "黑体": ["SimHei", "NotoSansCJKsc", "Heiti", "STHeiti", "SourceHanSans"],
    "楷体": ["KaiTi", "Kaiti", "NotoSerifCJKsc", "AR PL UKai"],
    "仿宋": ["FangSong", "Fangsong", "NotoSerifCJKsc"],
    "Times New Roman": ["TimesNewRoman", "LiberationSerif", "NimbusRoman", "TeX Gyre Termes"],
    # LibreOffice renders OMML with its own math-font configuration, NOT with the
    # document's m:mathFont, so the PDF embeds its symbol/math substitutes even
    # when the docx declares the right font. The control point for the math font
    # is therefore the docx declaration (asserted as math_font_declared), and the
    # PDF-level check only records that the host substituted.
    "Cambria Math": ["CambriaMath", "STIXTwoMath", "LatinModernMath", "XITS Math",
                     "OpenSymbol", "SymbolMT", "DejaVuSerif"],
    "Consolas": ["Consolas", "DejaVuSansMono", "LiberationMono", "Sarasa Mono"],
}

# PostScript style suffixes pdffonts reports after the family name.
_FONT_STYLE_SUFFIXES = (
    "PSMT", "PS-BoldMT", "PS-ItalicMT", "PS-BoldItalicMT",
    "BoldMT", "ItalicMT", "BoldItalicMT", "Bold", "Italic", "BoldItalic",
    "Regular", "Light", "Medium", "Semibold", "BoldItalic",
)


def _canonical_font(name: str) -> str:
    """Normalise a PDF font name to its family: drop the subset prefix and the
    PostScript style suffix, keep everything else. 'TimesNewRomanPSMT' ->
    'timesnewroman'; 'ConsolasX' -> 'consolasx' (a different family)."""
    s = name.split("+")[-1]           # drop the ABCDEF+ subset prefix
    for suffix in _FONT_STYLE_SUFFIXES:
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)]
            break
    return "".join(ch for ch in s if ch.isalnum()).lower()


def _profile_font_families(role: dict) -> list[str]:
    """Distinct font families the profile requires, in a stable order."""
    out: list[str] = []
    for _key, pair in (role.get("fonts") or {}).items():
        for fam in pair:
            if fam and fam not in out:
                out.append(fam)
    return out


def _expected_pdf_fonts(layout_block: dict) -> list[str]:
    """Profile font families that must be present in the built PDF."""
    out: list[str] = []
    for family in (layout_block.get("profile_fonts") or []):
        if family and family not in out:
            out.append(family)
    return out


def _font_present(family: str, embedded: list[str]) -> bool:
    """True when the family (or a declared substitution for it) is embedded.

    Matching is on the canonical family name (subset prefix and PostScript style
    suffix removed), and only exact — a bidirectional substring test would let
    'ConsolasX' satisfy 'Consolas' and 'SimHeiSun' satisfy 'SimHei'.
    """
    names = [family] + _FONT_SUBSTITUTIONS.get(family, [])
    targets = {_canonical_font(n) for n in names}
    targets.discard("")
    return any(_canonical_font(emb) in targets for emb in embedded)


def _resolve_layout_for_build(dest: Path, paper_cfg: dict) -> dict:
    """PF-B3/PF-B10: paper.yaml.layout_profile -> registry -> L0->L1->L2 merge.

    Returns {"profile_name", "merged", "role", "override_log", "refdoc_path"}.
    Raises layoutlib.LayoutError on any failure (build fails, no silent fallback).
    """
    if layoutlib is None:
        raise RuntimeError(f"layoutlib import failed: {_layoutlib_error}")
    profile_name = paper_cfg.get("layout_profile") or "draft"
    l2_path = dest / "build" / "layout.yaml"
    l2 = None
    if l2_path.exists():
        l2 = yaml.safe_load(l2_path.read_text(encoding="utf-8"))
        if not isinstance(l2, dict):
            raise layoutlib.LayoutError(f"L2 {l2_path} must parse to a mapping")
    stack = layoutlib.resolve_profile_stack(profile_name, l2)
    entry = stack["registry_entry"]
    return {
        "profile_name": profile_name,
        "merged": stack["merged"],
        "role": layoutlib.merged_role(stack["merged"]),
        "override_log": stack["override_log"],
        "refdoc_path": layoutlib.refdoc_path(entry),
    }


def _style_block(styles_xml: str, style_id: str) -> str:
    m = re.search(
        r'<w:style [^>]*w:styleId="' + re.escape(style_id) + r'"[^>]*>.*?</w:style>',
        styles_xml, re.S,
    )
    return m.group(0) if m else ""


def _assert_layout_landing(docx_path: Path, role: dict, merged: dict) -> tuple[list, list]:
    """Profile-landing assertions on the produced docx (PF-B3 implementation carrier).

    Returns (failures, notes): failures must be empty or the build fails;
    notes are recorded in the manifest (no silent degradation).
    """
    failures, notes = [], []
    z = zipfile.ZipFile(docx_path)
    styles = z.read("word/styles.xml").decode("utf-8")
    docxml = z.read("word/document.xml").decode("utf-8")
    parts = z.namelist()

    def twips(mm: float) -> int:
        return int(round(mm * 56.6929))

    t = merged.get("typography", {}) or {}
    body_pt = t.get("body_pt")
    sizes = t.get("sizes", {}) or {}

    def check(name, expected, actual):
        if expected is None:
            # The profile does not state this dimension. Record it as skipped so the
            # manifest shows which dimensions were NOT verified (never a silent pass).
            notes.append({"check": name, "value": None, "status": "skipped_no_profile_value"})
        elif actual != expected:
            failures.append({"check": name, "expected": expected, "actual": actual})
        else:
            notes.append({"check": name, "value": actual})

    # No theme/accent heading colour may survive — in any part, in any case form.
    header_footer_xml = "".join(
        z.read(n).decode("utf-8", "ignore") for n in parts
        if re.match(r"word/(header|footer)\d*\.xml", n))
    if layoutlib.blue_colour_present(styles, docxml, header_footer_xml):
        failures.append({"check": "heading_color_accent_absent",
                         "expected": "no accent/theme heading colour", "actual": "found"})
    else:
        notes.append({"check": "heading_color_accent_absent", "value": True})

    def attr(tag: str, name: str, xml: str) -> int | None:
        m = re.search(r"<" + tag + r"\b[^>]*\b" + name + r'="(\d+)"', xml)
        return int(m.group(1)) if m else None

    normal = _style_block(styles, "Normal")
    # The generator writes the body size from typography.sizes.body (which falls back
    # to body_pt); assert against the same source of truth so an L2 override of
    # body_pt cannot make the generator and the assertion disagree.
    body_size_pt = sizes.get("body", body_pt)
    if body_size_pt is not None:
        m = re.search(r'<w:sz w:val="(\d+)"', normal)
        check("normal_sz_halfpt", int(round(body_size_pt * 2)), int(m.group(1)) if m else None)
    indent = t.get("first_line_indent_chars")
    if indent:
        m = re.search(r'w:firstLineChars="(\d+)"', normal)
        check("normal_first_line_chars", int(round(indent * 100)), int(m.group(1)) if m else None)

    # line spacing: the regression that silently drops 1.5x spacing must fail the build.
    # Normal may define it directly or inherit it from docDefaults.
    line_spacing = t.get("line_spacing")
    if line_spacing:
        check("effective_line_240", int(round(line_spacing * 240)),
              layoutlib.effective_line_spacing(styles))

    for sid, key in (("Title", "title_zh"), ("Heading1", "heading1"), ("Heading2", "heading2")):
        block = _style_block(styles, sid)
        m = re.search(r'<w:sz w:val="(\d+)"', block)
        check(f"{sid.lower()}_sz_halfpt", int(round(sizes[key] * 2)) if sizes.get(key) else None,
              int(m.group(1)) if m else None)

    east = t.get("east_asia_font")
    if east:
        m = re.search(r'w:eastAsia="([^"]+)"', normal)
        check("normal_east_asia_font", east, m.group(1) if m else None)

    latin = t.get("latin_font")
    if latin:
        m = re.search(r'w:ascii="([^"]+)"', normal)
        check("normal_latin_font", latin, m.group(1) if m else None)
        m_h = re.search(r'w:hAnsi="([^"]+)"', normal)
        check("normal_latin_font_hAnsi", latin, m_h.group(1) if m_h else None)

    # The math font must be DECLARED in the produced document. pandoc drops
    # m:mathPr from the reference settings.xml, so the build re-applies it; this
    # assertion makes sure that actually happened (the PDF's font is the host's
    # LibreOffice math configuration and is recorded separately).
    math_font = (role.get("fonts", {}).get("math") or (None, None))[1]
    if math_font:
        settings = z.read("word/settings.xml").decode("utf-8") if "word/settings.xml" in parts else ""
        m = re.search(r'<m:mathFont m:val="([^"]+)"', settings)
        check("math_font_declared", math_font, m.group(1) if m else None)

    # header/footer parts must be well-formed XML (title injection escapes the title)
    for part in [n for n in parts if re.match(r"word/(header|footer)\d*\.xml", n)]:
        try:
            xml.etree.ElementTree.fromstring(z.read(part))
            notes.append({"check": f"{part}_wellformed", "value": True})
        except Exception as exc:  # noqa: BLE001
            failures.append({"check": f"{part}_wellformed", "expected": "well-formed XML",
                             "actual": str(exc)[:160]})

    # Every header/footer reference in sectPr must resolve to a relationship of the
    # right type whose target part exists — a dangling reference silently drops the
    # running head while the build still passes.
    rels_xml = z.read("word/_rels/document.xml.rels").decode("utf-8") if \
        "word/_rels/document.xml.rels" in parts else ""
    rel_map = {m.group(2): (m.group(1), m.group(3)) for m in
               re.finditer(r'<Relationship Type="([^"]+)" Id="([^"]+)" Target="([^"]+)"', rels_xml)}
    part_names = set(parts)
    for ref_kind, tag in (("header", "w:headerReference"), ("footer", "w:footerReference")):
        for m in re.finditer(r"<" + tag + r'\b[^>]*r:id="([^"]+)"', docxml):
            rid = m.group(1)
            entry = rel_map.get(rid)
            if entry is None:
                failures.append({"check": f"{ref_kind}_reference_resolves",
                                 "expected": rid, "actual": "no such relationship"})
            else:
                rel_type, target = entry
                if not rel_type.endswith("/" + ref_kind):
                    failures.append({"check": f"{ref_kind}_reference_type",
                                     "expected": ref_kind, "actual": rel_type})
                elif ("word/" + target) not in part_names:
                    failures.append({"check": f"{ref_kind}_reference_target_exists",
                                     "expected": "word/" + target, "actual": "missing"})

    pagination = merged.get("pagination", {}) or {}
    if pagination.get("header", "title_center") != "none":
        check("header_referenced", True, bool(re.search(r"<w:headerReference\b", docxml)))
        check("header_part_present", True,
              any(re.match(r"word/header\d*\.xml", n) for n in parts))
    if pagination.get("page_number_position", "footer_center") != "none":
        page_field_parts = [n for n in parts if re.match(r"word/(header|footer)\d*\.xml", n)]
        check("page_number_field", True,
              any(layoutlib.has_exact_page_field(z.read(n).decode("utf-8", "ignore"))
                  for n in page_field_parts))

    # page geometry from EVERY sectPr (a multi-section document may differ)
    page = merged.get("page", {}) or {}
    size_mm = {"A4": (210.0, 297.0), "A3": (297.0, 420.0), "letter": (215.9, 279.4), "legal": (215.9, 355.6)}
    w_mm, h_mm = size_mm.get(page.get("size", "A4"), (210.0, 297.0))
    sect_blocks = re.findall(r"<w:sectPr\b.*?</w:sectPr>", docxml, re.S) or [docxml]
    margin = page.get("margin", {}) or {}
    for idx, sect in enumerate(sect_blocks):
        suffix = "" if idx == 0 else f"_sect{idx + 1}"
        check(f"page_width_twips{suffix}", twips(w_mm), attr("w:pgSz", "w:w", sect))
        check(f"page_height_twips{suffix}", twips(h_mm), attr("w:pgSz", "w:h", sect))
        for side in ("top", "bottom", "left", "right"):
            val = attr("w:pgMar", f"w:{side}", sect)
            if val is None:
                failures.append({"check": f"margin_{side}_twips{suffix}",
                                 "expected": twips(margin.get(side, 25.4)), "actual": None})
            else:
                check(f"margin_{side}_twips{suffix}", twips(margin.get(side, 25.4)), val)

    # three-line table style: a grid table must NOT satisfy this
    tables_cfg = merged.get("tables", {}) or {}
    if tables_cfg.get("style") == "three_line":
        block = _style_block(styles, "Table")
        check("table_three_line_borders", True, layoutlib.three_line_table_ok(block))

    # ── GC-2026-1112-01: heiti weight / abstract-label alignment / citation
    # superscript. When the profile states a dimension, the artifact must carry
    # it; when it does not, the dimension is skipped (never a silent pass).
    heading_bold = role.get("heading_bold")
    caption_bold = role.get("caption_bold")
    label_align = role.get("abstract_label_alignment")

    def bold_val_of(style_id: str) -> str | None:
        # pandoc re-serialises the produced styles.xml ("<w:b w:val="0" />" with
        # space before the slash), so the pattern must tolerate whitespace.
        m = re.search(r'<w:b w:val="(\d)"\s*/>', _style_block(styles, style_id))
        return m.group(1) if m else None

    if heading_bold is False:
        for sid in ("Heading1", "Heading2", "Heading3", "Heading4", "Heading5", "AbstractTitle"):
            check(f"{sid.lower()}_bold_off", "0", bold_val_of(sid))
    if caption_bold is False:
        for sid in ("Caption", "ImageCaption", "TableCaption"):
            check(f"{sid.lower()}_bold_off", "0", bold_val_of(sid))
    if label_align:
        m = re.search(r'<w:jc w:val="([a-z]+)"\s*/>', _style_block(styles, "AbstractTitle"))
        check("abstract_title_alignment", label_align, m.group(1) if m else None)

    citation_cfg = merged.get("citation", {}) or {}
    if citation_cfg.get("numeric_superscript"):
        marked_total, plain = 0, 0
        for pm in re.finditer(r"<w:p\b.*?</w:p>", docxml, re.S):
            para = pm.group(0)
            st = re.search(r'<w:pStyle w:val="([^"]+)"', para)
            if st and st.group(1) in _CITE_EXCLUDED_STYLES:
                continue
            for rm in re.finditer(r"<w:r\b[^>]*>.*?</w:r>", para, re.S):
                tm = re.search(r"<w:t[^>]*>([^<]*)</w:t>", rm.group(0))
                if not tm:
                    continue
                hits = _CITATION_PATTERN.findall(tm.group(1))
                if not hits:
                    continue
                marked_total += len(hits)
                if not re.search(r'<w:vertAlign w:val="superscript"\s*/>', rm.group(0)):
                    plain += 1
        if marked_total == 0:
            notes.append({"check": "citation_superscript_coverage", "value": 0,
                          "status": "no_numeric_citations_in_body"})
        elif plain:
            failures.append({"check": "citation_superscript_coverage",
                             "expected": f"all {marked_total} citation run(s) superscripted",
                             "actual": f"{plain} run(s) left plain"})
        else:
            notes.append({"check": "citation_superscript_coverage", "value": marked_total})


    # formula objects: OMML present iff source math markers exist (checked by caller)
    notes.append({"check": "omath_count", "value": docxml.count("<m:oMath")})
    notes.append({"check": "media_images", "value": len([n for n in parts if n.startswith("word/media/")])})

    # Role coverage: a profile role whose paragraph style is defined but never used
    # in the product means the role silently did not reach the page. This is recorded
    # as a limitation, so a reviewer can see it (PF-B12 no-silent-degradation).
    used = set(re.findall(r'<w:pStyle w:val="([^"]+)"', docxml))
    # The style each profile role is expected to land in. `affiliation` is NOT
    # Subtitle: Subtitle carries the English title; the affiliation line falls
    # back to BlockText until the body is restructured (see change-record §9).
    role_styles = {
        "abstract": "Abstract", "abstract_label": "AbstractTitle",
        "reference_entry": "Bibliography", "reference_heading": "Bibliography",
        "caption": "Caption", "table_caption": "TableCaption",
        "figure_caption": "ImageCaption", "author": "Author",
        "title_zh": "Title", "title_en": "Subtitle",
    }
    unused = sorted({style for style in role_styles.values() if style not in used})
    notes.append({"check": "role_style_coverage", "value": {
        "used_paragraph_styles": sorted(used),
        "profile_role_styles_not_used": unused,
    }})
    if unused:
        notes.append({"check": "role_styles_unused_limitation", "value": unused})
    return failures, notes


def _xml_escape_text(text: str) -> str:
    """Escape a string for insertion into XML text content.

    A title containing & < > would otherwise produce a malformed header part that
    LibreOffice/Word refuse to open (verified 2026-11-11).
    """
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))




def _harden_tables(docx_path: Path) -> int:
    """Keep table rows intact across page breaks (cantSplit) and repeat the header
    row (tblHeader) — carries over the pre-refactor pipeline's post-processing
    (P2 REL-0002 practice) into the governed build. Returns rows patched."""
    import io
    src = zipfile.ZipFile(docx_path)
    doc = src.read("word/document.xml").decode("utf-8")
    out = {}
    patched = 0
    for name in src.namelist():
        payload = src.read(name)
        if name == "word/document.xml":
            text = payload.decode("utf-8")
            parts = re.split(r"(<w:tbl>.*?</w:tbl>)", text, flags=re.S)
            for pi, part in enumerate(parts):
                if not part.startswith("<w:tbl>"):
                    continue
                rows = re.split(r"(<w:tr[ >])", part)
                first_row = True
                rebuilt = []
                for seg in rows:
                    if seg == "<w:tr>" or seg == "<w:tr ":
                        if first_row:
                            rebuilt.append(seg + "<w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>")
                            first_row = False
                        else:
                            rebuilt.append(seg + "<w:trPr><w:cantSplit/></w:trPr>")
                        patched += 1
                    else:
                        rebuilt.append(seg)
                parts[pi] = "".join(rebuilt)
            payload = "".join(parts).encode("utf-8")
        out[name] = payload
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for name, payload in out.items():
            dst.writestr(name, payload)
    docx_path.write_bytes(_zip_parts(out))
    return patched


# ── GC-2026-1112-01: in-text numeric citations as superscript ────────────────
# GB/T 7714 numeric-citation convention (common practice; user directive
# 2026-11-12, profile citation.numeric_superscript). The pattern is deliberately
# narrow, shaped by false positives actually observed in the P1–P7 bodies:
#   - 1–3 digit numbers only: access dates like [2026-11-11] (GB/T 7714 引用日期)
#     never match;
#   - no space after the comma: interval notation like [12, 40] (P4 §5) never
#     matches;
#   - OMML math (<m:t>) is not <w:t> and is skipped outright ($\sigma \in [0, 1]$).
# Reference-list entries (Bibliography style) and code blocks (SourceCode style)
# are excluded by paragraph style.
_CITATION_PATTERN = re.compile(r"\[\d{1,3}(?:-\d{1,3})*(?:,\d{1,3}(?:-\d{1,3})*)*\]")
_CITE_EXCLUDED_STYLES = ("Bibliography", "SourceCode")
# Runs carrying these are never plain-text citation carriers.
_RUN_NON_TEXT_MARKERS = ("<w:drawing", "<w:pict", "<w:fldChar", "<w:instrText",
                         "<w:footnoteRef", "<w:endnoteRef", "<w:sep", "<w:object")


def _superscript_run_parts(run: str, t_open: str, text: str) -> tuple[list[str], int]:
    """Split one run's text at citation boundaries; citation segments keep the
    original rPr plus <w:vertAlign w:val="superscript"/> (inserted at its
    ECMA-376 position — after w:fitText, before w:rtl/w:cs/w:em/w:lang)."""
    m = re.search(r"<w:rPr>(.*?)</w:rPr>", run, re.S)
    rpr_inner = m.group(1) if m else ""
    if "<w:vertAlign" in rpr_inner:
        return [run], 0  # already raised (e.g. ^sup^ in source); never double-apply
    # t_open is "<w:t" + attributes + ">"; keep the attribute slice verbatim
    t_attrs = t_open[len("<w:t"):-1]
    el = '<w:vertAlign w:val="superscript"/>'
    insert_at = len(rpr_inner)
    for anchor in ("<w:rtl", "<w:cs", "<w:em", "<w:lang"):
        i = rpr_inner.find(anchor)
        if i != -1:
            insert_at = min(insert_at, i)
    segs, last, marked = [], 0, 0
    for cm in _CITATION_PATTERN.finditer(text):
        if cm.start() > last:
            segs.append((text[last:cm.start()], False))
        segs.append((cm.group(0), True))
        last = cm.end()
        marked += 1
    if last < len(text):
        segs.append((text[last:], False))
    out = []
    run_open = run[:run.index(">") + 1]
    for seg_text, is_cite in segs:
        if is_cite:
            rpr = f"<w:rPr>{rpr_inner[:insert_at]}{el}{rpr_inner[insert_at:]}</w:rPr>"
        else:
            rpr = f"<w:rPr>{rpr_inner}</w:rPr>" if m else ""
        out.append(f"{run_open}{rpr}<w:t{t_attrs}>{seg_text}</w:t></w:r>")
    return out, marked


def _apply_citation_superscript(docx_path: Path) -> int:
    """Mark every in-text numeric citation as superscript on the produced docx.

    A citation split across two runs is NOT re-joined — the coverage assertion
    fails the build visibly instead of silently mis-rendering (PF-B12).
    Returns the number of citations marked."""
    src = zipfile.ZipFile(docx_path)
    parts = {n: src.read(n) for n in src.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")
    total = 0

    def superscript_runs_in(segment: str) -> tuple[str, int]:
        out, last, marked = [], 0, 0
        for rm in re.finditer(r"<w:r\b[^>]*>.*?</w:r>", segment, re.S):
            run = rm.group(0)
            out.append(segment[last:rm.start()])
            last = rm.end()
            tm = re.search(r"(<w:t[^>]*>)([^<]*)</w:t>", run)
            if not tm or any(marker in run for marker in _RUN_NON_TEXT_MARKERS) \
                    or not _CITATION_PATTERN.search(tm.group(2)):
                out.append(run)
                continue
            rebuilt, n = _superscript_run_parts(run, tm.group(1), tm.group(2))
            out.extend(rebuilt)
            marked += n
        out.append(segment[last:])
        return "".join(out), marked

    def process_paragraph(para: str) -> tuple[str, int]:
        st = re.search(r'<w:pStyle w:val="([^"]+)"', para)
        if st and st.group(1) in _CITE_EXCLUDED_STYLES:
            return para, 0
        pieces, last, marked = [], 0, 0
        # OMML math spans are passed through untouched
        for mm in re.finditer(r"<m:oMathPara\b.*?</m:oMathPara>|<m:oMath\b.*?</m:oMath>", para, re.S):
            piece, n = superscript_runs_in(para[last:mm.start()])
            pieces += [piece, para[mm.start():mm.end()]]
            marked += n
            last = mm.end()
        piece, n = superscript_runs_in(para[last:])
        pieces.append(piece)
        marked += n
        return "".join(pieces), marked

    new_doc, last = [], 0
    for pm in re.finditer(r"<w:p\b.*?</w:p>", doc, re.S):
        new_doc.append(doc[last:pm.start()])
        piece, n = process_paragraph(pm.group(0))
        new_doc.append(piece)
        total += n
        last = pm.end()
    new_doc.append(doc[last:])
    doc = "".join(new_doc)
    if doc != parts["word/document.xml"].decode("utf-8"):
        parts["word/document.xml"] = doc.encode("utf-8")
        docx_path.write_bytes(_zip_parts(parts))
    return total


def _assert_refdoc_in_sync(profile_name: str, refdoc_path: Path) -> dict:
    """Regenerate the reference docx from its profile and compare it with the
    checked-in file (PF-B11: the refdoc is generated, never hand-edited)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_refdoc_mod", Path(__file__).resolve().parent / "make_refdoc.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["make_refdoc_mod"] = mod
    spec.loader.exec_module(mod)
    try:
        data, checks = mod.build_refdoc(profile_name, mod.default_reference_bytes())
    except Exception as exc:  # noqa: BLE001
        return {"in_sync": False, "reason": f"regeneration failed: {exc}",
                "refdoc": str(refdoc_path)}
    current = refdoc_path.read_bytes() if refdoc_path.exists() else b""
    return {
        "in_sync": current == data,
        "checked_in_sha256_16": hashlib.sha256(current).hexdigest()[:16] if current else None,
        "regenerated_sha256_16": hashlib.sha256(data).hexdigest()[:16],
        "self_check_pass": checks.get("pass"),
        "refdoc": str(refdoc_path),
        "reason": None if current == data else "checked-in refdoc differs from the profile",
    }


def _apply_math_font_to_output(docx_path: Path, math_font: str | None) -> bool:
    """Re-apply the OMML math font to the produced document.

    pandoc drops m:mathPr from the reference document's settings.xml, so the
    math font declared in the profile would otherwise never reach the output.
    """
    import io
    if not math_font:
        return False
    src = zipfile.ZipFile(docx_path)
    parts = {n: src.read(n) for n in src.namelist()}
    if "word/settings.xml" not in parts:
        return False
    text = parts["word/settings.xml"].decode("utf-8")
    new_text = layoutlib.apply_math_font(text, math_font)
    if new_text == text:
        return False
    parts["word/settings.xml"] = new_text.encode("utf-8")
    docx_path.write_bytes(_zip_parts(parts))
    return True


SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"


def _strip_svg_alternatives(docx_path: Path) -> dict:
    """Drop the SVG alternative from picture blips, keeping the PNG fallback.

    pandoc embeds an SVG source as BOTH an <a:blip> PNG fallback and an
    <asvg:svgBlip> SVG alternative. Word 2016+ renders the SVG; LibreOffice
    (the PDF conversion step) picks the SVG and renders NOTHING, so the PDF
    shipped with empty figure slots (P1/P3, 2026-11-12). Removing the SVG
    alternative leaves the PNG as the single image, which every reader renders.

    The SVG sources stay in the paper's figures/ directory for the venue's
    separate SVG attachment (S19), so nothing is lost.
    """
    import io
    src = zipfile.ZipFile(docx_path)
    parts = {n: src.read(n) for n in src.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")
    if "svgBlip" not in doc:
        return {"stripped": 0, "removed_parts": []}
    rels_name = "word/_rels/document.xml.rels"
    rels = parts[rels_name].decode("utf-8")

    dropped_rids = set()

    def fix_blip(m):
        """Within one <a:blip>: drop the SVG alternative only if a raster fallback exists."""
        blk = m.group(0)
        open_tag = blk[:blk.index(">") + 1]
        primary = re.search(r'r:embed="([^"]+)"', open_tag)
        svgs = re.findall(r'<asvg:svgBlip[^>]*r:embed="([^"]+)"', blk)
        if not svgs or not primary or primary.group(1) in svgs:
            return blk          # the SVG IS the only image — keep it
        for rid in svgs:
            dropped_rids.add(rid)
        # remove the <a:ext> wrapper that holds only the svgBlip
        def kill_ext(em):
            return "" if "svgBlip" in em.group(0) else em.group(0)
        blk = re.sub(r"<a:ext [^>]*>.*?</a:ext>", kill_ext, blk, flags=re.S)
        return blk

    doc = re.sub(r"<a:blip\b[^>]*>.*?</a:blip>", fix_blip, doc, flags=re.S)

    removed_parts = []
    for rid in sorted(dropped_rids):
        m = re.search(r'<Relationship [^>]*Id="' + re.escape(rid) + r'"[^>]*Target="([^"]+)"[^>]*/>', rels)
        if not m:
            continue
        target = m.group(1)
        if not target.lower().endswith(".svg"):
            continue
        rels = rels.replace(m.group(0), "")
        part = "word/" + target.lstrip("/")
        if part in parts:
            del parts[part]
            removed_parts.append(part)

    parts["word/document.xml"] = doc.encode("utf-8")
    parts[rels_name] = rels.encode("utf-8")
    docx_path.write_bytes(_zip_parts(parts))
    return {"stripped": len(dropped_rids), "removed_parts": removed_parts}


def _repair_header_footer_relationships(docx_path: Path) -> dict:
    """Close the header/footer relationship graph of a pandoc-produced docx.

    pandoc copies the reference doc's header/footer PARTS into the output but does
    not copy their RELATIONSHIPS, leaving sectPr pointing at relationship ids that
    do not exist. LibreOffice tolerates that and renders the parts anyway; Word
    may not, and the package is formally invalid. This adds the missing
    relationships (or corrects a wrong target) so the delivered docx is well-formed.

    Returns {"repaired": [...], "skipped": [...]}.
    """
    import io
    src = zipfile.ZipFile(docx_path)
    parts = {n: src.read(n) for n in src.namelist()}
    names = set(parts)
    doc = parts["word/document.xml"].decode("utf-8")
    rels_name = "word/_rels/document.xml.rels"
    rels = parts[rels_name].decode("utf-8")

    rel_map = {m.group(2): (m.group(1), m.group(3)) for m in
               re.finditer(r'<Relationship Type="([^"]+)" Id="([^"]+)" Target="([^"]+)"', rels)}
    repaired, skipped = [], []

    for ref_kind, tag, part_prefix in (("header", "w:headerReference", "word/header"),
                                       ("footer", "w:footerReference", "word/footer")):
        for m in re.finditer(r"<" + tag + r'\b[^>]*r:id="([^"]+)"', doc):
            rid = m.group(1)
            candidates = sorted(n for n in names if re.fullmatch(re.escape(part_prefix) + r"\d*\.xml", n))
            if not candidates:
                skipped.append({"kind": ref_kind, "rid": rid, "reason": "no part in package"})
                continue
            target = candidates[0].split("/", 1)[1]
            entry = rel_map.get(rid)
            if entry and entry[1] == target and entry[0].endswith("/" + ref_kind):
                continue
            rel_type = ("http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                        + ref_kind)
            if entry is None:
                rel = (f'<Relationship Type="{rel_type}" Id="{rid}" Target="{target}" />')
                rels = rels.replace("</Relationships>", rel + "</Relationships>")
                rel_map[rid] = (rel_type, target)
                repaired.append({"kind": ref_kind, "rid": rid, "target": target})
            else:
                rels = re.sub(r'(<Relationship Type="[^"]+" Id="%s" Target=")[^"]*(")' % re.escape(rid),
                               r"\g<1>" + target + r"\g<2>", rels)
                rel_map[rid] = (rel_type, target)
                repaired.append({"kind": ref_kind, "rid": rid, "target": target,
                                 "was": entry[1]})

    if repaired:
        parts[rels_name] = rels.encode("utf-8")
        docx_path.write_bytes(_zip_parts(parts))
    return {"repaired": repaired, "skipped": skipped}


def _zip_parts(parts: dict[str, bytes]) -> bytes:
    """Deterministic zip: fixed timestamps and fixed core.xml dates, so the
    artifact hash is reproducible across builds (PF-B4 snapshot comparability)."""
    import io
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for name in sorted(parts):
            payload = parts[name]
            if name == "docProps/core.xml":
                text = payload.decode("utf-8")
                text = re.sub(r"(<dcterms:created[^>]*>)[^<]*(</dcterms:created>)",
                               r"\g<1>1980-01-01T00:00:00Z\g<2>", text)
                text = re.sub(r"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                               r"\g<1>1980-01-01T00:00:00Z\g<2>", text)
                payload = text.encode("utf-8")
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            dst.writestr(info, payload)
    return out.getvalue()


def _inject_paper_title_header(docx_path: Path, title: str) -> None:
    """Replace the {{PAPER_TITLE}} placeholder left by the refdoc header part."""
    import io
    src = zipfile.ZipFile(docx_path)
    parts = {n: src.read(n) for n in src.namelist()}
    replaced = False
    escaped = _xml_escape_text(title).encode("utf-8")
    for name in list(parts):
        if re.match(r"word/header\d*\.xml", name) and b"{{PAPER_TITLE}}" in parts[name]:
            parts[name] = parts[name].replace(b"{{PAPER_TITLE}}", escaped)
            replaced = True
    if replaced:
        docx_path.write_bytes(_zip_parts(parts))


def _cmd_build_docx_impl(args) -> tuple:
    """Build docx; returns (payload, exit_code) without printing."""
    dest = Path(args.paper)
    if not dest.exists():
        return ({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)
    info = _get_paper_info(dest)
    try:
        paper_cfg = _load_paper_yaml(dest)
    except Exception as exc:
        # A malformed paper.yaml is a build failure, not a fallback to the draft profile.
        return ({"status": "error", "error": f"paper.yaml is unreadable: {exc}", "stage": "pre-build"}, 2)
    snapshot = _create_snapshot(dest)
    try:
        result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=5)
        pandoc_available = result.returncode == 0
        pandoc_version = result.stdout.splitlines()[0] if pandoc_available else "not found"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pandoc_available = False
        pandoc_version = "not found"
    if not pandoc_available:
        return ({"status": "error", "error": "pandoc not found. Install pandoc to build docx.", "hint": "apt-get install pandoc || brew install pandoc"}, 2)

    # PF-B3 implementation carrier: profile resolution (fails hard, no silent fallback)
    try:
        layout = _resolve_layout_for_build(dest, paper_cfg)
    except Exception as exc:
        return ({"status": "error", "error": f"layout profile resolution failed: {exc}", "stage": "pre-build"}, 2)
    import hashlib
    refdoc_sha = hashlib.sha256(layout["refdoc_path"].read_bytes()).hexdigest()[:16]
    # PF-B11: the reference docx is GENERATED from the profile. A checked-in
    # refdoc that no longer matches its profile would silently produce the wrong
    # layout, so the build regenerates it and compares byte for byte.
    refdoc_sync = _assert_refdoc_in_sync(layout["profile_name"], layout["refdoc_path"])
    if not refdoc_sync["in_sync"]:
        return ({"status": "error",
                 "error": ("reference docx is out of sync with its profile — regenerate "
                           "with `python3 -I tools/make_refdoc.py` and review the diff "
                           f"(profile={layout['profile_name']}, refdoc={refdoc_sync['refdoc']})"),
                 "stage": "pre-build", "refdoc_sync": refdoc_sync}, 2)

    version = _norm_version(info["version"])
    title = info["title"] if info["title"] != "(untitled)" else paper_cfg.get("title") or "未命名稿件"
    title_en = paper_cfg.get("title_en")
    manuscript_kind = paper_cfg.get("manuscript_kind") or "research"

    body_source = dest / "body" / "paper.md"
    if not body_source.exists():
        return ({"status": "error", "error": f"single body source missing: body/paper.md (PF-B2)"}, 2)

    build_task_id = f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    temp_build_dir = dest / "temp" / f"{info['id']}-{build_task_id}"
    temp_build_dir.mkdir(parents=True, exist_ok=True)
    try:
        output_file = temp_build_dir / "paper.docx"
        cmd = [
            "pandoc", str(body_source),
            "--from", "markdown", "--to", "docx",
            "--output", str(output_file),
            "--reference-doc", str(layout["refdoc_path"]),
            # Resource path: the paper root resolves 'figures/x.svg' (as used by
            # P1/P4/P6/P7); the body dir additionally resolves '../figures/x.svg'
            # (as used by P2/P3). Without the second entry those papers silently
            # shipped with NO figures (pandoc only warns) — found 2026-11-12.
            "--resource-path", str(dest),
            "--resource-path", str(dest / "body"),
            "--metadata", f"title={title}",
        ]
        if title_en:
            cmd += ["--metadata", f"subtitle={title_en}"]
        # NOTE: author line is NOT injected from paper.yaml — the authoritative author
        # line (S2 inline affiliation + S18 corresponding-author *) lives in
        # body/paper.md front matter; duplicating it here produced a second,
        # marker-less author line (PF-B6 visual round 2026-11-11).
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not output_file.exists():
            return ({"status": "error", "error": result.stderr.strip() or "pandoc failed", "stderr": result.stderr[:500]}, 1)
        # A figure that could not be resolved is only a pandoc WARNING — the build
        # used to succeed with an empty figure slot (found on P2/P3, 2026-11-12).
        # PF-B6 requires the actual rendering to be checked, so the produced package
        # must contain every figure the body references.
        src_text = body_source.read_text(encoding="utf-8")
        refs = [m.group(1).strip() for m in
                re.finditer(r"!\[[^\]]*\]\(([^)\s]+)", src_text)]
        with zipfile.ZipFile(output_file) as _z:
            embedded = [n for n in _z.namelist() if n.startswith("word/media/")]
        missing_figures = max(0, len(refs) - len(embedded))
        if missing_figures:
            return ({"status": "error",
                     "error": (f"{missing_figures} of {len(refs)} referenced figures are absent "
                               f"from the produced document — shipping it would deliver the "
                               f"paper with missing figures (PF-B6)"),
                     "figure_refs": len(refs), "figures_embedded": len(embedded),
                     "stage": "build", "stderr": result.stderr[:500]}, 1)

        _inject_paper_title_header(output_file, title)
        # pandoc copies the header/footer parts but not their relationships;
        # close the graph so the delivered docx is a valid package.
        hf_repair = _repair_header_footer_relationships(output_file)
        # LibreOffice renders the SVG alternative as nothing; keep the PNG fallback.
        svg_stripped = _strip_svg_alternatives(output_file)
        # pandoc drops m:mathPr from the reference settings.xml; re-apply it so the
        # profile's math font actually reaches the document.
        math_font = (layout["role"].get("fonts", {}).get("math") or (None, None))[1]
        math_applied = _apply_math_font_to_output(output_file, math_font)
        table_rows_hardened = _harden_tables(output_file)
        # GC-2026-1112-01: in-text numeric citations become superscript when the
        # profile declares citation.numeric_superscript (reference list, code and
        # math excluded — see _apply_citation_superscript).
        citations_marked = None
        if (layout["merged"].get("citation", {}) or {}).get("numeric_superscript"):
            citations_marked = _apply_citation_superscript(output_file)

        # ── profile-landing assertions (hard fail; no silent degradation) ──
        failures, layout_notes = _assert_layout_landing(output_file, layout["role"], layout["merged"])
        layout_notes.append({"check": "table_rows_cantsplit_tblheader", "value": table_rows_hardened})
        layout_notes.append({"check": "header_footer_relationship_repair", "value": hf_repair})
        if citations_marked is not None:
            layout_notes.append({"check": "citation_superscript_marked", "value": citations_marked})
        layout_notes.append({"check": "svg_alternatives_stripped", "value": svg_stripped})

        # ── content-compliance assertion: equations must be OMML, not images (S9) ──
        source_text = body_source.read_text(encoding="utf-8")
        math_markers = len(re.findall(r'\$[^$\n]+\$', source_text)) + len(re.findall(r'\$\$.+?\$\$', source_text, re.S))
        omath_count = next((n["value"] for n in layout_notes if n["check"] == "omath_count"), 0)
        math_issue = None
        if math_markers > 0 and omath_count == 0:
            math_issue = {"check": "formulas_omml", "expected": "oMath objects for source math",
                          "actual": "0 oMath objects (possible image formulas)"}
            if manuscript_kind == "submission":
                failures.append(math_issue)
            else:
                layout_notes.append({"check": "formulas_omml_limitation", **math_issue})

        if failures:
            return ({"status": "error", "error": "layout landing assertions failed (PF-B3: no silent degradation)",
                         "failures": failures, "artifact_kept_in_temp": str(temp_build_dir)}, 1)

        import shutil
        out_dir = dest / "build" / version
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_title = _posix_safe_title(title)
        docx_out = out_dir / f"{safe_title}.docx"
        # PF-B7: a PUBLISHED version must not be modified in place; old versions are
        # preserved. A pending draft (review_status != "pending") is not published and
        # may be rebuilt in place. Rebuilding a published release with different
        # content silently destroys its release record — refuse and ask for a
        # version bump (PF-V3) instead.
        if docx_out.exists():
            existing = docx_out.read_bytes()
            if existing != output_file.read_bytes():
                published = False
                prev_manifest = out_dir / "manifest.json"
                if prev_manifest.exists():
                    try:
                        published = json.loads(prev_manifest.read_text(encoding="utf-8")).get(
                            "review_status", "pending") != "pending"
                    except Exception:  # noqa: BLE001
                        published = True
                if published:
                    return ({"status": "error",
                             "error": (f"build/{version}/ holds a PUBLISHED release with "
                                       f"different content; modifying a published version "
                                       f"in place would destroy its release record "
                                       f"(PF-B7). Bump paper_version (PF-V3) to publish a "
                                       f"new version."),
                             "stage": "publish", "existing_artifact": str(docx_out)}, 2)
        shutil.copy2(output_file, docx_out)
        manifest = {
            "release_id": f"BUILD-{version}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "paper_id": info["id"],
            "paper_version": version,
            "paper_title": title,
            "paper_title_en": title_en,
            "manuscript_kind": manuscript_kind,
            "formats": ["docx"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "snapshot": snapshot,
            "toolchain": {"pandoc": pandoc_version},
            "layout": {
                "profile": layout["profile_name"],
                "rules_version": "0.2.1",
                "merge_order": "L0(draft) -> L1(venue) -> L2(paper)",
                "override_log": layout["override_log"],
                "reference_doc": str(layout["refdoc_path"].relative_to(layoutlib.GOV_ROOT)),
                "reference_doc_sha256_16": refdoc_sha,
                "assertions": {"failed": 0, "notes": layout_notes},
                # Font families the profile requires; the PDF step checks each of them
                # against the embedded set and records any absence as a limitation.
                "profile_fonts": _profile_font_families(layout["role"]),
            },
            "body_source": "body/paper.md",
            "artifacts": [{"format": "docx", "path": str(docx_out.relative_to(dest)), "sha256": hashlib.sha256(docx_out.read_bytes()).hexdigest()[:16], "size": docx_out.stat().st_size}],
            "review_status": "pending",
            "limitations": [n for n in layout_notes if n.get("check", "").endswith("_limitation")],
        }
        manifest_file = out_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        current_json = dest / "build" / "current.json"
        current_json.write_text(json.dumps({"paper_version": version, "manifest_path": f"build/{version}/manifest.json"}, ensure_ascii=False), encoding="utf-8")
        return ({"status": "ok", "paper_id": info["id"], "paper_version": version, "layout_profile": layout["profile_name"],
                     "format": "docx", "output_path": str(docx_out), "manifest_path": str(manifest_file),
                     "layout_assertions": "pass", "override_log_entries": len(layout["override_log"])}, 0)
    except subprocess.TimeoutExpired:
        return ({"status": "error", "error": "pandoc timeout (120s)"}, 2)
    except Exception as exc:
        return ({"status": "error", "error": str(exc)}, 2)


def cmd_build_docx(args):
    payload, code = _cmd_build_docx_impl(args)
    return emit(payload, code)


def cmd_build_pdf(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)
    try:
        result = subprocess.run(["soffice", "--version"], capture_output=True, text=True, timeout=5)
        lo_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        lo_available = False
    if not lo_available:
        return emit({"status": "error", "error": "LibreOffice not found. Install to build PDF.", "hint": "apt-get install libreoffice"}, 2)
    import hashlib, json
    docx_result, docx_code = _cmd_build_docx_impl(args)
    if docx_result.get("status") != "ok":
        return emit(docx_result, docx_code)
    docx_path = Path(docx_result["output_path"])
    pdf_path = docx_path.with_suffix(".pdf")
    try:
        result = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(docx_path.parent), str(docx_path)], capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and pdf_path.exists():
            manifest_path = Path(docx_result["manifest_path"])
            pdf_fonts: list[str] = []
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["formats"].append("pdf")
                manifest["artifacts"].append({"format": "pdf", "path": str(pdf_path.relative_to(dest)), "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16], "size": pdf_path.stat().st_size})
                # PDF font inventory: declared profile fonts vs actually embedded (LibreOffice
                # substitutions are recorded here, never silent — PF-B3 no-silent-degradation)
                fonts_verifiable = True
                try:
                    pf = subprocess.run(["pdffonts", str(pdf_path)], capture_output=True, text=True, timeout=30)
                    if pf.returncode == 0:
                        pdf_fonts = [ln.split()[0] for ln in pf.stdout.splitlines()[2:] if ln.strip()]
                    else:
                        pdf_fonts = []
                        fonts_verifiable = False
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pdf_fonts = []
                    fonts_verifiable = False
                if not fonts_verifiable:
                    # An unverifiable PDF must not pass the build: PF-B12 forbids a
                    # silent pass on something that could not be checked.
                    manifest.setdefault("limitations", []).append(
                        {"kind": "font_inventory_unavailable",
                         "detail": "pdffonts could not be run; embedded fonts could not be verified"})
                    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                    return ({"status": "error",
                             "error": "PDF font inventory could not be produced (pdffonts unavailable) — "
                                      "the PDF cannot be verified and must not be published",
                             "stage": "pdf-verify", "pdf_path": str(pdf_path)}, 1)
                manifest.setdefault("layout", {})["pdf_fonts_embedded"] = sorted(set(pdf_fonts))
                # PF-B12: every profile font family must be present in the PDF, either as
                # itself or through a declared substitution. A missing family is recorded
                # as a limitation, never a silent pass.
                expected = _expected_pdf_fonts(manifest.get("layout", {}))
                missing = [f for f in expected if not _font_present(f, pdf_fonts)]
                manifest["layout"]["pdf_fonts_expected"] = expected
                manifest["layout"]["pdf_fonts_missing"] = missing
                if missing:
                    manifest.setdefault("limitations", []).append(
                        {"kind": "font_substitution", "detail": "profile fonts absent from PDF",
                         "missing": missing})
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return emit({"status": "ok", "paper_id": dest.name, "format": "pdf", "output_path": str(pdf_path), "manifest_path": str(manifest_path), "pdf_fonts": sorted(set(pdf_fonts)) if pdf_fonts else []})
        else:
            return emit({"status": "error", "error": "LibreOffice PDF conversion failed", "stderr": result.stderr[:500]}, 1)
    except Exception as exc:
        return emit({"status": "error", "error": str(exc)}, 2)


def cmd_build_list(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)
    output_dir = dest / "output"
    if not output_dir.exists():
        return emit({"status": "ok", "paper_id": dest.name, "releases": []})
    releases = []
    for rel_dir in sorted(output_dir.iterdir()):
        if rel_dir.is_dir() and rel_dir.name.startswith("REL-"):
            manifest_file = rel_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                    releases.append({"release_id": rel_dir.name, "paper_version": manifest.get("paper_version", "?"), "formats": manifest.get("formats", []), "created_at": manifest.get("created_at", "?")})
                except Exception:
                    pass
    current_file = output_dir / "current.json"
    current = None
    if current_file.exists():
        try:
            current = json.loads(current_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return emit({"status": "ok", "paper_id": dest.name, "releases": releases, "current": current})


def cmd_build_debate(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)
    info = _get_paper_info(dest)
    output_dir = dest / "output"
    builds_exist = output_dir.exists() and any(output_dir.iterdir())
    context_lines = [f"Paper: {info['id']}", f"Title: {info['title']}", f"Version: {info['version']}", f"Stage: {info['stage']}", f"Type: {info['paper_type']}", "", f"Builds exist: {builds_exist}"]
    if builds_exist:
        try:
            current_file = output_dir / "current.json"
            if current_file.exists():
                current = json.loads(current_file.read_text(encoding="utf-8"))
                context_lines.append(f"Current release: {current.get('release_id', '?')}")
        except Exception:
            pass
    context_lines.extend(["", "Build requirements (PF-B1 to PF-B10):", "- PF-B1: Manuscript kind (research/submission/archive)", "- PF-B2: Single authoritative body source", "- PF-B3: Layout profile (L0/L1/L2)", "- PF-B4: Fixed input snapshot", "- PF-B5: Staged build in temp/", "- PF-B6: Figure and table acceptance", "- PF-B7: Version release in output/", "- PF-B8: Local delivery verification", "- PF-B9: Render directive filtering", "- PF-B10: Layout profile layering"])
    context = "\n".join(context_lines)
    prompt = "Evaluate the paper build readiness against these criteria (PF-B1 to PF-B10). Identify any blockers, missing artifacts, or compliance issues. Provide: (1) overall readiness assessment, (2) blockers (if any), (3) recommended next steps. Be concise.\n\n" + context
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from debate import run_debate, debate_to_markdown
        result = run_debate(prompt, rounds=1)
    except Exception as exc:
        return emit({"status": "error", "error": f"Debate module error: {exc}"}, 2)
    debate_file = dest / "temp" / "build-readiness-debate.md"
    try:
        debate_file.parent.mkdir(parents=True, exist_ok=True)
        debate_file.write_text(debate_to_markdown(result), encoding="utf-8")
        debate_path = str(debate_file)
    except Exception:
        debate_path = None
    return emit({"status": "ok", "paper_id": info["id"], "debate_path": debate_path, "consensus_preview": str(result.get("final_consensus", {}))[:500]})


def main():
    parser = Parser(description="PaperFactory CLI")
    sub = parser.add_subparsers(dest="command")

    p_proposal = sub.add_parser("proposal", help="Execute full proposal flow: author + materials → GitHub repo")
    p_proposal.add_argument("--id", required=True, help="Paper repo name, e.g. P1-EXAMPLE-20251110")
    p_proposal.add_argument("--author-name", required=True, help="First author full name (native script)")
    p_proposal.add_argument("--author-pinyin", required=True, help="First author pinyin (uppercase, e.g. EXAMPLE)")
    p_proposal.add_argument("--title", required=True, help="Paper title")
    p_proposal.add_argument("--paper-type", required=True, choices=list(DEFAULT_CHAPTERS.keys()), help="Paper type")
    p_proposal.add_argument("--author-name-en", default=None, help="Author name in English (optional)")
    p_proposal.add_argument("--affiliation", default=None, help="Author affiliation (optional)")
    p_proposal.add_argument("--email", default=None, help="Author email (optional, null for privacy)")
    p_proposal.add_argument("--date", default=None, help="Proposal date (ISO format, default: now)")
    p_proposal.add_argument("--dest", default=None, help="Destination directory (default: papers/<id>)")
    p_proposal.add_argument("--version", default="0.1.0", help="Initial paper_version (default: 0.1.0)")

    p_scaffold = sub.add_parser("scaffold", help="Create paper workspace from template (no GitHub)")
    p_scaffold.add_argument("--id", required=True, help="Paper repo name, e.g. P1-EXAMPLE-20251110")
    p_scaffold.add_argument("--dest", help="Destination directory (default: papers/<id>)")
    p_scaffold.add_argument("--version", default="0.1.0", help="Initial paper_version (default: 0.1.0)")

    p_check = sub.add_parser("check", help="Validate a paper workspace against schema and required paths")
    p_validate = sub.add_parser("validate", help="Full JSON Schema validation of paper.yaml (PF-PL1 admission gate)")
    p_check.add_argument("--paper", required=True, help="Path to paper workspace directory")
    p_validate.add_argument("--paper", required=True, help="Path to paper workspace directory")

    p_bump = sub.add_parser("version-bump", help="Bump paper_version in paper.yaml")
    p_bump.add_argument("--paper", required=True, help="Path to paper workspace directory")
    p_bump.add_argument("--level", required=True, choices=["major", "minor", "patch"])

    p_materials = sub.add_parser("materials", help="Manage research materials")
    p_materials_sub = p_materials.add_subparsers(dest="materials_command")

    p_mat_add = p_materials_sub.add_parser("add", help="Register a new material")
    p_mat_add.add_argument("--paper", required=True, help="Path to paper workspace")
    p_mat_add.add_argument("--type", required=True, choices=["paper", "dataset", "code", "tool"], help="Material type")
    p_mat_add.add_argument("--identifier", required=True, help="DOI, URL, or unique identifier")
    p_mat_add.add_argument("--title", default=None, help="Material title")
    p_mat_add.add_argument("--relevance", default="general", help="Relevance to paper (general | core | supporting)")

    p_mat_list = p_materials_sub.add_parser("list", help="List registered materials")
    p_mat_list.add_argument("--paper", required=True, help="Path to paper workspace")
    p_mat_list.add_argument("--type", default=None, help="Filter by type")

    p_mat_check = p_materials_sub.add_parser("check", help="Check for duplicate or missing materials")
    p_mat_check.add_argument("--paper", required=True, help="Path to paper workspace")

    p_mat_debate = p_materials_sub.add_parser("debate", help="Assess materials quality via mmx/agy debate")
    p_mat_debate.add_argument("--paper", required=True, help="Path to paper workspace")

    p_experiments = sub.add_parser("experiments", help="Manage experiments")
    p_exp_sub = p_experiments.add_subparsers(dest="experiments_command")

    p_exp_add = p_exp_sub.add_parser("add", help="Register a new experiment")
    p_exp_add.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_add.add_argument("--name", required=True, help="Experiment name")
    p_exp_add.add_argument("--description", default=None, help="Experiment description")
    p_exp_add.add_argument("--parameters", default="{}", help="Parameters as JSON string")

    p_exp_list = p_exp_sub.add_parser("list", help="List experiments")
    p_exp_list.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_list.add_argument("--status", default=None, help="Filter by status")

    p_exp_update = p_exp_sub.add_parser("update", help="Update experiment status or result")
    p_exp_update.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_update.add_argument("--experiment-id", required=True, help="Experiment ID or name")
    p_exp_update.add_argument("--new-status", default=None, help="New status: planned|running|completed|failed")
    p_exp_update.add_argument("--result", default=None, help="Result summary")
    p_exp_update.add_argument("--notes", default=None, help="Additional notes")

    p_exp_compare = p_exp_sub.add_parser("compare", help="Compare two experiments")
    p_exp_compare.add_argument("--paper", required=True, help="Path to paper workspace")
    p_exp_compare.add_argument("--experiment-a", required=True, help="First experiment ID or name")
    p_exp_compare.add_argument("--experiment-b", required=True, help="Second experiment ID or name")

    p_exp_debate = p_exp_sub.add_parser("debate", help="Assess experiment design via mmx/agy debate")
    p_exp_debate.add_argument("--paper", required=True, help="Path to paper workspace")

    p_writing = sub.add_parser("writing", help="Manage paper writing progress")
    p_writing_sub = p_writing.add_subparsers(dest="writing_command")

    p_writing_status = p_writing_sub.add_parser("status", help="Show writing progress across all chapters")
    p_writing_status.add_argument("--paper", required=True, help="Path to paper workspace")

    p_writing_update = p_writing_sub.add_parser("update", help="Update chapter writing status")
    p_writing_update.add_argument("--paper", required=True, help="Path to paper workspace")
    p_writing_update.add_argument("--chapter", required=True, help="Chapter slug or file (e.g., introduction or 01-introduction)")
    p_writing_update.add_argument("--status", required=True, choices=["outline", "draft", "developing", "complete"], help="Writing status")

    p_writing_debate = p_writing_sub.add_parser("debate", help="Assess chapter writing quality via mmx/agy debate")
    p_writing_debate.add_argument("--paper", required=True, help="Path to paper workspace")
    p_writing_debate.add_argument("--chapter", default=None, help="Specific chapter slug (optional, default: all)")

    p_review = sub.add_parser("review", help="Manage review process")
    p_review_sub = p_review.add_subparsers(dest="review_command")

    p_review_create = p_review_sub.add_parser("create", help="Create a review task for a perspective")
    p_review_create.add_argument("--paper", required=True, help="Path to paper workspace")
    p_review_create.add_argument("--perspective", required=True, choices=list(PERSPECTIVES.keys()), help="Review perspective (R-A, R-B, R-C, R-D)")

    p_review_issues = p_review_sub.add_parser("issues", help="List review issues")
    p_review_issues.add_argument("--paper", required=True, help="Path to paper workspace")
    p_review_issues.add_argument("--grade", default=None, help="Filter by grade (P0, P1, P2)")
    p_review_issues.add_argument("--status", default=None, help="Filter by status")

    p_review_close = p_review_sub.add_parser("close", help="Close an issue with status and evidence")
    p_review_close.add_argument("--paper", required=True, help="Path to paper workspace")
    p_review_close.add_argument("--issue-id", required=True, help="Issue ID (e.g., ISS-0001)")
    p_review_close.add_argument("--new-status", required=True, choices=["fixed-pending-verify", "re-verified", "rebuttal-valid", "not-applicable", "unresolved"], help="New issue status")
    p_review_close.add_argument("--evidence", default="", help="Resolution evidence")

    p_review_debate = p_review_sub.add_parser("debate", help="Resolve issue dispute via mmx/agy debate")
    p_review_debate.add_argument("--paper", required=True, help="Path to paper workspace")
    p_review_debate.add_argument("--issue-id", required=True, help="Issue ID to dispute")

    p_build = sub.add_parser("build", help="Manage build process (docx, PDF, snapshot)")
    p_build_sub = p_build.add_subparsers(dest="build_command")

    p_build_init = p_build_sub.add_parser("init", help="Initialize build directories (temp/, output/)")
    p_build_init.add_argument("--paper", required=True, help="Path to paper workspace")

    p_build_snapshot = p_build_sub.add_parser("snapshot", help="Create input snapshot for build")
    p_build_snapshot.add_argument("--paper", required=True, help="Path to paper workspace")

    p_build_docx = p_build_sub.add_parser("docx", help="Build docx (requires pandoc)")
    p_build_docx.add_argument("--paper", required=True, help="Path to paper workspace")

    p_build_pdf = p_build_sub.add_parser("pdf", help="Build PDF (requires LibreOffice)")
    p_build_pdf.add_argument("--paper", required=True, help="Path to paper workspace")

    p_build_list = p_build_sub.add_parser("list", help="List build releases")
    p_build_list.add_argument("--paper", required=True, help="Path to paper workspace")

    p_build_debate = p_build_sub.add_parser("debate", help="Assess build readiness via mmx/agy debate")
    p_build_debate.add_argument("--paper", required=True, help="Path to paper workspace")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        raise SystemExit(2)

    cmds = {
        "proposal": cmd_proposal,
        "scaffold": cmd_scaffold,
        "check": cmd_check,
        "validate": cmd_validate,
        "version-bump": cmd_version_bump,
        "materials": lambda args: {
            "add": cmd_materials_add,
            "list": cmd_materials_list,
            "check": cmd_materials_check,
            "debate": cmd_materials_debate,
        }[args.materials_command](args),
        "experiments": lambda args: {
            "add": cmd_experiments_add,
            "list": cmd_experiments_list,
            "update": cmd_experiments_update,
            "compare": cmd_experiments_compare,
            "debate": cmd_experiments_debate,
        }[args.experiments_command](args),
        "writing": lambda args: {
            "status": cmd_writing_status,
            "update": cmd_writing_update,
            "debate": cmd_writing_debate,
        }[args.writing_command](args),
        "review": lambda args: {
            "create": cmd_review_create,
            "issues": cmd_review_issues,
            "close": cmd_review_close,
            "debate": cmd_review_debate,
        }[args.review_command](args),
        "build": lambda args: {
            "init": cmd_build_init,
            "snapshot": cmd_build_snapshot,
            "docx": cmd_build_docx,
            "pdf": cmd_build_pdf,
            "list": cmd_build_list,
            "debate": cmd_build_debate,
        }[args.build_command](args),
    }
    code = cmds[args.command](args)
    raise SystemExit(code)

if __name__ == "__main__":
    main()
