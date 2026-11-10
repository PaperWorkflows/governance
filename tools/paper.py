#!/usr/bin/env python3
"""PaperFactory CLI — proposal, scaffold, check, version-bump, materials, experiments, writing, review, build."""
import sys

if not sys.flags.isolated:
    print('{"status":"error","reason":"python3 -I required"}')
    raise SystemExit(2)

sys.dont_write_bytecode = True

import argparse, json, re, subprocess, yaml
from pathlib import Path
from datetime import datetime, timezone

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
            if not re.match(r'^[0-9]+\.[0-9]+\.[0-9]+$', val):
                errors.append(f"paper_version must be semver: {val}")
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
    p_check.add_argument("--paper", required=True, help="Path to paper workspace directory")

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
    """Extract basic paper info from paper.yaml."""
    py = dest / "paper.yaml"
    info = {"id": dest.name, "version": "0.1.0", "title": "(untitled)", "stage": "proposal", "paper_type": "empirical"}
    if not py.exists():
        return info
    text = py.read_text(encoding="utf-8")
    m = re.search(r'^paper_version:\s*(.+)$', text, re.MULTILINE)
    if m:
        info["version"] = m.group(1).strip()
    m = re.search(r'^title:\s*["\']?([^"\'\n]+)', text, re.MULTILINE)
    if m:
        info["title"] = m.group(1).strip()
    m = re.search(r'^stage:\s*(.+)$', text, re.MULTILINE)
    if m:
        info["stage"] = m.group(1).strip()
    m = re.search(r'^paper_type:\s*(.+)$', text, re.MULTILINE)
    if m:
        info["paper_type"] = m.group(1).strip()
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


def cmd_build_docx(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)
    info = _get_paper_info(dest)
    snapshot = _create_snapshot(dest)
    try:
        result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=5)
        pandoc_available = result.returncode == 0
        pandoc_version = result.stdout.splitlines()[0] if pandoc_available else "not found"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pandoc_available = False
        pandoc_version = "not found"
    if not pandoc_available:
        return emit({"status": "error", "error": "pandoc not found. Install pandoc to build docx.", "hint": "apt-get install pandoc || brew install pandoc"}, 2)
    build_task_id = f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    temp_build_dir = dest / "temp" / f"{info['id']}-{build_task_id}"
    temp_build_dir.mkdir(parents=True, exist_ok=True)
    try:
        output_file = temp_build_dir / "paper.docx"
        body_files = sorted((dest / "body").glob("*.md"))
        if not body_files:
            return emit({"status": "error", "error": "No body/*.md files found"}, 2)
        cmd = ["pandoc"] + [str(f) for f in body_files] + ["--output", str(output_file), "--from", "markdown", "--to", "docx"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and output_file.exists():
            import shutil, json, hashlib
            rel_id = f"REL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            output_rel_dir = dest / "output" / rel_id
            output_rel_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output_file, output_rel_dir / "paper.docx")
            manifest = {
                "release_id": rel_id,
                "paper_id": info["id"],
                "paper_version": info["version"],
                "paper_title": info["title"],
                "manuscript_kind": "research",
                "formats": ["docx"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "snapshot": snapshot,
                "toolchain": {"pandoc": pandoc_version},
                "artifacts": [{"format": "docx", "path": f"output/{rel_id}/paper.docx", "sha256": hashlib.sha256(output_file.read_bytes()).hexdigest()[:16], "size": output_file.stat().st_size}],
                "review_status": "pending",
                "limitations": [],
            }
            manifest_file = output_rel_dir / "manifest.json"
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            current_json = dest / "output" / "current.json"
            current_json.write_text(json.dumps({"release_id": rel_id, "manifest_path": f"output/{rel_id}/manifest.json"}, ensure_ascii=False), encoding="utf-8")
            return emit({"status": "ok", "paper_id": info["id"], "release_id": rel_id, "format": "docx", "output_path": str(output_rel_dir / "paper.docx"), "manifest_path": str(manifest_file)})
        else:
            return emit({"status": "error", "error": result.stderr.strip() or "pandoc failed", "stderr": result.stderr[:500]}, 1)
    except subprocess.TimeoutExpired:
        return emit({"status": "error", "error": "pandoc timeout (120s)"}, 2)
    except Exception as exc:
        return emit({"status": "error", "error": str(exc)}, 2)


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
    docx_result = cmd_build_docx(args)
    if docx_result.get("status") != "ok":
        return docx_result
    docx_path = Path(docx_result["output_path"])
    pdf_path = docx_path.with_suffix(".pdf")
    try:
        result = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(docx_path.parent), str(docx_path)], capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and pdf_path.exists():
            manifest_path = Path(docx_result["manifest_path"])
            if manifest_path.exists():
                import json, hashlib
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["formats"].append("pdf")
                manifest["artifacts"].append({"format": "pdf", "path": str(pdf_path.relative_to(dest)), "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16], "size": pdf_path.stat().st_size})
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return emit({"status": "ok", "paper_id": dest.name, "format": "pdf", "output_path": str(pdf_path), "manifest_path": str(manifest_path)})
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
    p_check.add_argument("--paper", required=True, help="Path to paper workspace directory")

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
