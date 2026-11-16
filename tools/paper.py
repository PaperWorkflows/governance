#!/usr/bin/env python3
"""PaperFactory CLI — proposal, scaffold, check, version-bump, materials, experiments, writing, review, build."""
import sys

if not sys.flags.isolated:
    print('{"status":"error","reason":"python3 -I required"}')
    raise SystemExit(2)

sys.dont_write_bytecode = True

import argparse, hashlib, io, json, re, subprocess, yaml, zipfile
import xml.etree.ElementTree
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

# layoutlib is a sibling module; -I does not prepend the script dir, so insert it explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import layoutlib
except Exception as _exc:  # pragma: no cover - hard dependency for build subcommands
    layoutlib = None
    _layoutlib_error = str(_exc)
# GC-2026-1112-06: metadata-driven front/back matter generation. Same dependency
# surface as layoutlib (yaml + jsonschema under python3 -I).
try:
    import metalayout
except Exception as _mexc:  # pragma: no cover - hard dependency for build/check
    metalayout = None
    _metalayout_error = str(_mexc)

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
    """Write per-paper authors.yaml (private repo: full details allowed).

    GC-2026-1112-06: the format is the DOCUMENT-LEVEL CONTAINER — schema_version +
    affiliations registry + authors list, validated by
    schemas/author.schema.json (urn:paperfactory:author:3). The init state is a
    VALID container with an EMPTY registry and a skeleton author entry (name_en /
    affiliation_ids / email / bio unfilled): jsonschema passes, while the SEMANTIC
    gates (metalayout.validate_metadata, wired into both `check` and the build
    path) fail with field-level, actionable messages listing what to fill in. That
    failure state is the correct opening state for a new paper (as verified in the
    GC-2026-1112-06 final-review rework). The old bare-list output
    (yaml.dump([author_entry])) overwrote the container template and is gone.
    """
    authors_path = dest / "authors.yaml"
    author_id = (author.get("id") or "author").lower()
    name = json.dumps(str(author.get("name") or ""), ensure_ascii=False)
    skeleton = f"""# Per-Paper Author Registry — 文档级容器格式（GC-2026-1112-06）
#
# 顶层必须是映射：schema_version / affiliations（单位注册表，全文唯一一份）/ authors 列表，
# 由 schemas/author.schema.json 校验；旧式裸列表（顶层 `- id: ...` 数组）已作废。
# 本文件是 `init` 的骨架开篇：仅预填作者 id/姓名，其余元数据未填——`check`/`build`
# 会因缺 name_en、affiliation_ids、bio 十字段而失败，并按字段点名（这是新论文的
# 正确开局状态）。请参照 templates/paper/authors.yaml 的字段注释与格式补齐后再构建。

schema_version: 1

affiliations: []        # 单位注册表（当前为空，init 骨架）。
  # 全文只声明一份；作者经 affiliation_ids 引用条目 id（^[a-z][a-z0-9_]*$）。
  # 每条格式：- id: <键>
  #            name: <中文全称>（一级+二级单位全称，S2）
  #            name_en: <英文全称>（S5 中英成对，缺失即校验失败）
  #            city: <市> / city_en: <市拼音> / postcode: <邮编>

authors:
  # 按署名顺序排列；roles 在 paper.yaml 维护（这里不写角色）。
  - id: {author_id}
    name: {name}
    name_en: null          # 英文名（姓前名后，首词为姓）；缺失即校验失败（S5 中英成对）
    affiliation_ids: []    # 引用上方 affiliations 注册表条目 id；缺失即校验失败
    bio:                   # S17 十字段全必填（author.schema.json required）
      birth_year: null     # 出生年（整数；渲染为「（YYYY 年生）」）
      gender: null         # 性别（男/女）
      hometown: null       # 籍贯（渲染为「××人」）
      degree: null         # 学位
      title: null          # 职称
      research_direction: null   # 研究方向（文末简介与「其他作者·从事工作」）
      address: null        # 通信地址
      postcode: null       # 邮政编码
      email: null          # 电子邮箱（bio 内 S17 字段）
      phone: null          # 电话（字符串）
    email: null            # 条目级联系邮箱（可选）；bio.email 为简介用
    orcid: null
"""
    authors_path.write_text(skeleton, encoding="utf-8")

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
                     rules_version: str = "0.3.3", date: str = None) -> str:
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
        rules_version="0.3.3",
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
            # GC-2026-1112-06 终审返工（P1-2）：必须行锚定替换。旧写法的子串替换
            # `content.replace("id: null", ...)` 会把 authors.yaml 的 `orcid: null`
            # 误改成 `orcid: P<n>`（"or**cid: null**" 含 "id: null" 子串）。行首
            # 锚定 `^id: null$`（多行模式）只命中独立的 `id:` 键行，orcid 行不命中。
            content = re.sub(r"^\s*id: null\s*$", f"id: {pid_number}", content,
                             flags=re.MULTILINE)
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

    # GC-2026-1112-06: full metadata hard validation (authors.yaml container format,
    # jsonschema, semantic hard-gate rules). Any error fails the check with the
    # file and field named (PF-B16 style).
    if metalayout is None:
        results["metadata"] = {"status": "fail",
                               "error": f"metalayout unavailable: {_metalayout_error}"}
        overall = "fail"
    else:
        try:
            meta = metalayout.load_paper_metadata(dest)
            meta_errors = metalayout.validate_metadata(meta)
        except metalayout.MetalayoutError as exc:
            results["metadata"] = {"status": "fail", "error": str(exc)}
            overall = "fail"
        else:
            if meta_errors:
                results["metadata"] = {"status": "fail", "errors": meta_errors}
                overall = "fail"
            else:
                results["metadata"] = {"status": "pass"}

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

    # GC-2026-1113-05: fail 必须显式非零退出码（PF-B12——失败静默放行修复）。
    # overall 只取 pass/fail（初始 pass，各闸仅置 fail），与 error 早返回的 exit 2 对齐。
    return emit({"status": overall, "paper_id": dest.name, "results": results},
                0 if overall == "pass" else 2)

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
    old_ver_raw = m.group(1).strip()
    # GC-2026-1112-06 (P5 试点发现的修正): paper_version 按 PF-V2 带 'v' 前缀
    # （如 v0.4.7）。数值解析前剥掉前缀，输出与 replace 用原始记号，避免
    # 'v0.4.7'.split('.') → ['v0','4','7'] 触发 int() ValueError 阻断升版。
    prefix = ""
    old_ver = old_ver_raw
    if old_ver_raw[:1].lower() == "v":
        prefix = old_ver_raw[:1]
        old_ver = old_ver_raw[1:]
    try:
        parts = [int(x) for x in old_ver.split(".")]
    except ValueError:
        return emit({"status": "error", "error": f"Invalid version format: {old_ver_raw}"}, 2)

    level = args.level
    if level == "major":
        parts[0] += 1; parts[1] = 0; parts[2] = 0
    elif level == "minor":
        parts[1] += 1; parts[2] = 0
    elif level == "patch":
        parts[2] += 1
    else:
        return emit({"status": "error", "error": f"Invalid level: {level} (major/minor/patch)"}, 2)
    new_ver = prefix + ".".join(str(x) for x in parts)

    text = text.replace(f"paper_version: {old_ver_raw}", f"paper_version: {new_ver}", 1)
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


class MaterialsFormatError(Exception):
    """materials.yaml 不可解析/不可读/结构不可识别——拒绝静默返回空（PF-B12）。"""


# 判重键字段回退链：identifier → id → title → sha256。
# P7/P8/P9（顶层 list 形态）条目只有 id，P4/P5 只有 id+title，P6 各块只有 id；
# 旧实现只按 identifier 判重，字段缺失即把全部条目误报为同一重复组。
_DEDUP_KEY_FIELDS = ("identifier", "id", "title", "sha256")


def _entry_dedup_key(entry):
    """返回条目的判重键；四个字段全部缺失（None/空）或条目非 dict 时返回 None（跳过判重）。"""
    if not isinstance(entry, dict):
        return None
    for field in _DEDUP_KEY_FIELDS:
        value = entry.get(field)
        if value is None:
            continue
        value = str(value).strip()
        if value:
            return f"{field}={value}"
    return None


def _entry_label(entry) -> str:
    """条目的单行可读描述（debate 上下文用）；容忍非 dict 条目与缺失字段。"""
    if not isinstance(entry, dict):
        return str(entry)
    ident = entry.get("identifier") or entry.get("id") or entry.get("sha256") or "?"
    title = entry.get("title") or "(untitled)"
    return f"[{entry.get('type', '?')}] {title} ({ident})"


def _load_materials(dest: Path) -> dict:
    """Load materials.yaml, recognizing all three registry formats (GC-2026-1113-04).

    全库实际存在三种形态：① "materials"——dict + materials: 键（P1–P5）；
    ② "keyed"——dict + 其他顶层键，键下为条目 list/dict（P6）；③ "list"——顶层
    list（P7/P8/P9）。旧实现只认 ①，其余静默返回空，导致 add 覆写毁数据、
    check 恒放行。

    Returns {"format": "materials"|"keyed"|"list"|"empty"|"missing",
             "raw": <原始解析数据或 None>,
             "entries": [扁平条目],
             "blocks": [(键名, [条目]), ...]}   # 仅 keyed 形态非空
    Raises MaterialsFormatError on parse failure / unreadable file /
    unrecognized structure.
    """
    mf = dest / MATERIALS_FILE
    if not mf.exists():
        return {"format": "missing", "raw": None, "entries": [], "blocks": []}
    try:
        data = yaml.safe_load(mf.read_text(encoding="utf-8"))
    except Exception as exc:
        raise MaterialsFormatError(
            f"materials.yaml 解析失败或不可读: {mf} — {type(exc).__name__}: {exc}"
        ) from exc

    if data is None:  # 空文件或纯注释：合法空登记
        return {"format": "empty", "raw": None, "entries": [], "blocks": []}
    if isinstance(data, list):
        return {"format": "list", "raw": data, "entries": list(data), "blocks": []}
    if isinstance(data, dict):
        if "materials" in data:
            materials = data["materials"]
            if not isinstance(materials, list):
                raise MaterialsFormatError(
                    f"materials.yaml 的 materials 键不是列表: {mf}"
                    f"（type={type(materials).__name__}）"
                )
            return {"format": "materials", "raw": data,
                    "entries": list(materials), "blocks": []}
        blocks = []
        for key, value in data.items():
            if isinstance(value, list):
                blocks.append((str(key), list(value)))
            elif isinstance(value, dict):
                blocks.append((str(key), [v for v in value.values() if isinstance(v, dict)]))
        entries = [e for _, block in blocks for e in block]
        return {"format": "keyed", "raw": data, "entries": entries, "blocks": blocks}
    raise MaterialsFormatError(
        f"materials.yaml 顶层结构不可识别（既非 dict 也非 list）: {mf}"
        f"（type={type(data).__name__}）"
    )


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

    try:
        data = _load_materials(dest)
    except MaterialsFormatError as exc:
        return emit({"status": "error", "error": str(exc)}, 2)

    fmt = data["format"]
    if fmt in ("keyed", "list"):
        # 这两种形态下旧实现会先读成空、再把新条目写进 data["materials"] 整体覆写，
        # 静默摧毁既有登记（GC-2026-1113-04 主缺陷）——拒绝执行且绝不写盘。
        return emit({
            "status": "error",
            "error": (f"materials.yaml 为 {fmt} 形态，`materials add` 仅支持 materials: dict "
                      f"形态；请手工登记或先转换格式（文件未改动）: {dest / MATERIALS_FILE}"),
            "format": fmt,
        }, 2)

    materials = data["entries"]

    # Check for duplicates by identifier
    existing = [m for m in materials
                if isinstance(m, dict) and m.get("identifier") == identifier]
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
    # 只把 materials 列表写回：materials 形态保留原始其他顶层键；新建/空文件写标准 dict。
    # 绝不把 _format/_raw 等内部标记泄进 YAML。
    out = dict(data["raw"]) if fmt == "materials" else {}
    out["materials"] = materials
    _save_materials(dest, out)

    return emit({
        "status": "ok",
        "paper_id": dest.name,
        "format": fmt,
        "added": entry,
        "total_materials": len(materials),
    })


def cmd_materials_list(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    try:
        data = _load_materials(dest)
    except MaterialsFormatError as exc:
        return emit({"status": "error", "error": str(exc)}, 2)

    fmt = data["format"]

    # Optional filter by type
    mat_type = getattr(args, "type", None)

    def _filt(entries):
        if not mat_type:
            return list(entries)
        return [m for m in entries if isinstance(m, dict) and m.get("type") == mat_type]

    materials = _filt(data["entries"])
    payload = {
        "status": "ok",
        "paper_id": dest.name,
        "format": fmt,
        "count": len(materials),
        "materials": materials,
    }
    if fmt == "keyed":
        # 按键分组给出，保证 primary_source 等分块条目可辨识；计数与过滤同步。
        payload["blocks"] = [
            {"key": key, "count": len(_filt(entries)), "entries": _filt(entries)}
            for key, entries in data["blocks"]
        ]
    return emit(payload)


def cmd_materials_check(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    try:
        data = _load_materials(dest)
    except MaterialsFormatError as exc:
        return emit({
            "status": "fail",
            "paper_id": dest.name,
            "format": "unreadable",
            "total": 0,
            "error": str(exc),
            "duplicate_identifiers": [],
            "duplicate_titles": [],
        }, 2)

    fmt = data["format"]
    if fmt == "keyed":
        # 各顶层键独立成组判重：figures/tables 与 primary_source 语义不同，跨块不合并。
        groups = data["blocks"]
    else:
        groups = [("", data["entries"])]

    # Find duplicates by robust key (identifier → id → title → sha256;
    # entries missing all key fields are skipped, never mass-reported as duplicates)
    duplicates = []
    total = 0
    for key, entries in groups:
        total += len(entries)
        seen = {}
        for m in entries:
            dk = _entry_dedup_key(m)
            if dk is None:
                continue
            if dk in seen:
                dup = {"identifier": dk.split("=", 1)[1], "key": dk,
                       "entries": [seen[dk], m]}
                if key:
                    dup["block"] = key
                duplicates.append(dup)
            else:
                seen[dk] = m

    # Find near-duplicates by title similarity (simple case-insensitive compare)
    title_dups = []
    for key, entries in groups:
        titles = [(m.get("title") or "").lower().strip() if isinstance(m, dict) else ""
                  for m in entries]
        for i, t1 in enumerate(titles):
            for j, t2 in enumerate(titles):
                if i < j and t1 and t2 and t1 == t2:
                    dup = {
                        "title": entries[i].get("title"),
                        "entries": [entries[i], entries[j]],
                    }
                    if key:
                        dup["block"] = key
                    title_dups.append(dup)

    status = "pass" if not duplicates and not title_dups else "fail"
    payload = {
        "status": status,
        "paper_id": dest.name,
        "format": fmt,
        "total": total,
        "duplicate_identifiers": duplicates,
        "duplicate_titles": title_dups,
    }
    if fmt == "keyed":
        payload["blocks"] = [{"key": k, "count": len(e)} for k, e in data["blocks"]]
    # GC-2026-1113-05: status=fail（发现重复）显式 exit 2，不再静默放行（PF-B12）。
    # 与上方解析失败的 exit 2 路径一致；JSON 结构不变，status 字段保持供闸门读取。
    return emit(payload, 0 if status == "pass" else 2)


def cmd_materials_debate(args):
    dest = Path(args.paper)
    if not dest.exists():
        return emit({"status": "error", "error": f"Paper directory not found: {dest}"}, 2)

    try:
        data = _load_materials(dest)
    except MaterialsFormatError as exc:
        return emit({"status": "error", "error": str(exc)}, 2)

    fmt = data["format"]
    materials = data["entries"]

    if not materials:
        return emit({"status": "error", "error": "No materials registered. Use 'materials add' first."}, 2)

    # Build context from materials
    context_lines = [f"Paper: {dest.name}", f"Total materials: {len(materials)}",
                     f"Format: {fmt}", ""]
    if fmt == "keyed":
        for key, entries in data["blocks"]:
            context_lines.append(f"## {key}（{len(entries)} 条）")
            for m in entries:
                context_lines.append(f"- {_entry_label(m)}")
            context_lines.append("")
    else:
        for m in materials:
            context_lines.append(f"- {_entry_label(m)}")
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


def _first_author_name(dest: Path, paper_cfg: dict):
    """PF-B7: the first author of the release (roles contains 'first').

    paper.yaml authors first, authors.yaml as the fallback. The build path and
    the package path call THIS helper, so the built artifact name and the
    package skeleton name can never diverge (GC-2026-1112-04, T9).
    Returns None when no first author is registered.
    """
    first_author = None
    for a in paper_cfg.get("authors") or []:
        if isinstance(a, dict) and "first" in (a.get("roles") or []):
            first_author = a.get("name")
            break
    if not first_author:
        for a in (_load_yaml_mapping(dest / "authors.yaml").get("authors") or []):
            if isinstance(a, dict) and "first" in (a.get("roles") or []):
                first_author = a.get("name")
                break
    return first_author


def _release_file_stem(title: str, first_author: str) -> str:
    """PF-B7 release file name: 标题（第一作者中文名）, POSIX-safe.

    One expression for both the build path and the package path — the built
    artifact and the package skeleton always carry the same name.
    """
    return _posix_safe_title(f"{title}（{first_author}）")


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write a JSON file atomically (temp file + os.replace).

    The release manifest IS the release record (PF-B7); a half-written file
    would destroy it, so the replacement is atomic.
    """
    import os
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=2))
            fh.flush()
            os.fsync(fh.fileno())
        # mkstemp creates 0600 — the replaced file keeps its own mode (or the
        # process default), so an atomic rewrite never narrows the access rights.
        try:
            mode = os.stat(path).st_mode & 0o777
        except FileNotFoundError:
            umask = os.umask(0)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


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
        check("normal_latin_font_hAnsi", latin, m_h.group(1) if m else None)

    # GC-2026-1116-03: table cells (header row + content rows) must carry the table
    # font size. pandoc renders every table cell with the Compact paragraph style,
    # so the size has to land there; before this change the profile declared a table
    # size that never reached the document (cells silently inherited the body size).
    tables_cfg = merged.get("tables", {}) or {}
    table_pt = tables_cfg.get("body_pt")
    if table_pt is None:
        table_pt = sizes.get("table_body")
    if table_pt:
        compact = _style_block(styles, "Compact")
        m = re.search(r'<w:sz w:val="(\d+)"', compact)
        check("compact_sz_halfpt", int(round(table_pt * 2)), int(m.group(1)) if m else None)

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

    # GC-2026-1112-06 follow-up fix (表单元格缩进归零): pandoc Compact (table cells
    # + tight lists) is basedOn BodyText -> Normaltime, and Normal carries the correct
    # 2-char body first-line indent. Compact itself has no w:ind, so every table-cell /
    # tight-list paragraph would inherit the body indent — against the template whose
    # table text sits flush. build_refdoc now writes Compact's effective indent
    # explicitly from tables.cell_first_line_indent_chars (default 0); this assertion
    # pins that the profile value actually landed in the produced artifact. Artifacts
    # built from the PRE-FIX refdoc carry no explicit Compact w:ind (they inherit the
    # body indent) — recorded as a stale note, not a build failure; a rebuilt artifact
    # whose explicit Compact indent no longer matches the profile fails the build (no
    # silent regression).
    compact_cfg = tables_cfg.get("cell_first_line_indent_chars", 0)
    compact_block = _style_block(styles, "Compact")
    _cm = re.search(r'w:firstLineChars="(\d+)"', compact_block)
    if _cm is None:
        notes.append({"check": "compact_first_line_chars",
                      "value": None,
                      "status": "stale_pre_fix_artifact_inherits_normal_indent",
                      "expected": int(round(compact_cfg * 100))})
    else:
        check("compact_first_line_chars", int(round(compact_cfg * 100)), int(_cm.group(1)))

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

    # Run-level DIRECT bold can override the style definition: e.g. markdown
    # `**关键词：**` inside an AbstractTitle div makes pandoc inject <w:b /> on
    # the runs, so the label still renders faux-bold while the style itself says
    # bold=off (GC-2026-1112-01 impl review P1-1, found on P6/P7).
    def _direct_bold_on(para: str) -> bool:
        for m in re.finditer(r"<w:b(?:\s[^>]*)?/>", para):
            if not re.search(r'w:val="(?:0|false)"', m.group(0)):
                return True
        return False

    if heading_bold is False or caption_bold is False:
        guarded = set()
        if heading_bold is False:
            guarded |= {"Heading1", "Heading2", "Heading3", "Heading4", "Heading5", "AbstractTitle"}
        if caption_bold is False:
            guarded |= {"Caption", "ImageCaption", "TableCaption"}
        offenders = []
        for pm in re.finditer(r"<w:p\b.*?</w:p>", docxml, re.S):
            para = pm.group(0)
            st = re.search(r'<w:pStyle w:val="([^"]+)"', para)
            if st and st.group(1) in guarded and _direct_bold_on(para):
                offenders.append(st.group(1))
        if offenders:
            failures.append({"check": "heiti_run_direct_bold_absent",
                             "expected": f"no direct <w:b/> in {sorted(guarded)} paragraphs",
                             "actual": sorted(set(offenders))})
        else:
            notes.append({"check": "heiti_run_direct_bold_absent", "value": 0})

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
    # The style each profile role is expected to land in. `affiliation` maps to
    # the dedicated Affiliation role (GC-2026-1112-06: the generated affiliation
    # list lands there via make_refdoc when the profile carries an authors domain),
    # `title_en` to Subtitle (Subtitle carries the English title).
    role_styles = {
        "abstract": "Abstract", "abstract_label": "AbstractTitle",
        "reference_entry": "Bibliography", "reference_heading": "Bibliography",
        "caption": "Caption", "table_caption": "TableCaption",
        "figure_caption": "ImageCaption", "author": "Author",
        "title_zh": "Title", "title_en": "Subtitle",
        # GC-2026-1112-06: the affiliation list now lands in the dedicated
        # Affiliation role (generated by make_refdoc when the profile carries the
        # authors domain) instead of falling back to BlockText.
        "affiliation": "Affiliation",
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

    A citation split across two runs is NOT re-joined: the coverage assertion
    only sees citations that are complete within one run, so a split citation
    passes the build silently and is caught post-hoc by the verify_layout
    count-parity check (H 组) — not, as PF-B12 first claimed, by the build
    itself (GC-2026-1112-01 impl review P2-1; run merging is an open item).
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
            # Only rebuild runs of the exact shape [rPr?][one w:t]; anything else
            # (multiple w:t, breaks, fields) is passed through untouched — the
            # rebuild would silently DROP everything after the first </w:t>
            # (GC-2026-1112-01 impl review P2-2).
            if not tm or len(re.findall(r"<w:t[\s>/]", run)) != 1 \
                    or any(marker in run for marker in _RUN_NON_TEXT_MARKERS) \
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


# ── SVG vector alternative: keep it, and guard the fallback ─────────────
# GC-2026-1113-02. pandoc embeds an SVG-referenced image as BOTH a raster
# <a:blip r:embed> fallback AND an <asvg:svgBlip> SVG alternative. Current
# LibreOffice renders the SVG, so the PDF figure becomes VECTOR (crisp
# text); the 96 DPI PNG fallback pandoc generates is what made the shipped
# PDF figures blurry (P1/P3/P6: measured 605 px @ 96 ppi on 2026-11-13).
#
# The 2026-11-12 ab0bdcc measure STRIPPED every svgBlip to work around an
# empty-figure-slot accident whose root cause was the OPPOSITE defect: an
# SVG-ONLY blip (no raster fallback), produced by the '../figures/' path
# form, which LibreOffice rendered as nothing. Stripping traded a
# render-host-dependent blank slot for guaranteed blur — both are defects.
# This change keeps the vector quality and turns the historical failure
# mode into a hard build failure instead: every blip carrying an svgBlip
# must also carry a raster r:embed fallback whose media part exists. The
# document itself is NOT modified.
RASTER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".emf", ".wmf", ".tif", ".tiff")

# PDF figure verification constants (GC-2026-1113-02, calibrated on P1
# v0.4.10 rebuilt with vector figures, 2026-11-13):
FIGURE_RASTER_MIN_PX = 64      # image objects at/below this on BOTH axes are
                                # SVG <pattern> fills LibreOffice rasterizes
                                # into tiles (probe-measured 28-49 px; the
                                # 2026-11-13 P1/P6 builds show 0 tiles — their
                                # patterns render as vectors); larger ones are
                                # figure-level rasters and must not appear for
                                # a vector-referenced figure
FIGURE_REGION_GAP_PT = 4.0     # slack added between the figure's bottom edge
                                # and the caption top when deriving the slot
                                # region (measured image-to-caption gaps on P1:
                                # 12-35 pt including SVG canvas padding)
FIGURE_REGION_MIN_INK = 0.01   # non-white ratio floor for a rendered figure
                                # slot (real P1 figures: 8.8%-37.9%; a blank
                                # slot measures 0.02% — ~50x below the floor)
FIGURE_INK_THRESHOLD = 250     # 8-bit gray below this counts as ink
FIGURE_RENDER_DPI = 150        # slot-region render resolution
CAPTION_MATCH_CHARS = 12       # normalized caption prefix used to locate the
                                # caption line in the PDF text layer
CAPTION_TOP_TOLERANCE_PT = 6.0  # page-top clearance a caption candidate must
                                # leave for the figure above it: a candidate
                                # whose implied figure top edge falls within
                                # this margin of the page top cannot be the
                                # real caption — the figure would not fit on
                                # the page above it (P2 fig4's in-image title
                                # matches the caption text ~254pt too high)


class FigureToolUnavailable(Exception):
    """A poppler tool a PDF figure assertion depends on could not be run.

    PF-B12: a check that cannot run is not a pass. Raised when the tool is
    missing from PATH, times out, exits non-zero or yields unmeasurable
    output. These states used to be conflated with legitimate negative
    results ("the PDF carries no text layer", "the slot carries no ink"),
    which let a build with unverified figure slots ship (P1 defect found by
    independent verification, 2026-11-13); the caller maps this to
    status=unavailable and fails the build instead.
    """


def _docx_relationship_targets(doc_parts: dict) -> dict:
    """Map relationship id -> target from word/_rels/document.xml.rels.

    Attribute order inside <Relationship> is not guaranteed, so each
    element's Id/Target are read independently.
    """
    rels_name = "word/_rels/document.xml.rels"
    if rels_name not in doc_parts:
        return {}
    mapping = {}
    for m in re.finditer(r"<Relationship\b[^>]*>", doc_parts[rels_name].decode("utf-8")):
        rid = re.search(r'Id="([^"]+)"', m.group(0))
        target = re.search(r'Target="([^"]+)"', m.group(0))
        if rid and target:
            mapping[rid.group(1)] = target.group(1)
    return mapping


def _validate_svg_alternatives(docx_path: Path) -> dict:
    """Assert every SVG-alternative blip keeps a raster fallback.

    Enumerates every <a:blip> in word/document.xml. For each blip carrying
    an <asvg:svgBlip> (the SVG alternative) it asserts:
      1. the blip's own r:embed points at a raster image relationship
         (.png/.jpg/.jpeg/.bmp/.gif/.emf/.wmf/.tif/.tiff),
      2. that relationship's target part exists inside the package,
      3. the svgBlip's own r:embed part exists inside the package.
    Any violation is a hard-failure defect: it is exactly the 2026-11-12
    ab0bdcc construction (an SVG-only blip from the '../figures/' path form
    rendered as an empty figure slot). The docx is NOT modified — the SVG
    alternative stays so the PDF figure renders as vector.

    Returns {"check": "svg_alternatives_preserved", "svg_blips": N,
    "raster_fallbacks": N, "blips_missing_raster": M, "missing": [...]}.
    """
    src = zipfile.ZipFile(docx_path)
    parts = {n: src.read(n) for n in src.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")
    rel_target = _docx_relationship_targets(parts)
    names = set(parts)

    svg_blips = 0
    raster_fallbacks = 0
    missing = []
    for idx, m in enumerate(re.finditer(r"<a:blip\b[^>]*?(?:/>|>.*?</a:blip>)", doc, re.S)):
        blk = m.group(0)
        open_tag = blk[: blk.index(">") + 1]
        primary = re.search(r'r:embed="([^"]+)"', open_tag)
        svg_rids = re.findall(r'<asvg:svgBlip[^>]*r:embed="([^"]+)"', blk)
        if not svg_rids:
            continue
        svg_blips += 1
        defects = []
        if not primary:
            defects.append("no raster r:embed on the blip (SVG-only blip)")
        else:
            rid = primary.group(1)
            target = rel_target.get(rid)
            if target is None:
                defects.append(f"raster r:embed={rid} has no relationship")
            elif not target.lower().endswith(RASTER_EXTENSIONS):
                defects.append(f"raster r:embed={rid} target {target} is not a raster image")
            elif "word/" + target.lstrip("/") not in names:
                defects.append(f"raster r:embed={rid} target {target} is absent from the package")
        for srid in svg_rids:
            starget = rel_target.get(srid)
            if starget is None or "word/" + starget.lstrip("/") not in names:
                defects.append(f"svgBlip r:embed={srid} media part is absent from the package")
        if defects:
            missing.append({"blip": idx, "primary_rid": primary.group(1) if primary else None,
                            "svg_rids": svg_rids, "defects": defects})
        else:
            raster_fallbacks += 1
    return {"check": "svg_alternatives_preserved", "svg_blips": svg_blips,
            "raster_fallbacks": raster_fallbacks, "blips_missing_raster": len(missing),
            "missing": missing}


def _docx_figure_geometry(docx_path: Path) -> list:
    """Per-figure geometry of the produced docx, in document order.

    For every drawing paragraph: the wp:extent (EMU -> pt), the caption text
    of the following caption-styled paragraph (pandoc's implicit-figure
    caption — the alt text), and whether the blip carries an SVG
    alternative. Front/back matter carry no figures, so document order
    matches the body figure reference order.
    """
    src = zipfile.ZipFile(docx_path)
    parts = {n: src.read(n) for n in src.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")
    paras = re.findall(r"<w:p\b.*?</w:p>", doc, re.S)
    figures = []
    for i, para in enumerate(paras):
        if "<w:drawing>" not in para or "a:blip" not in para:
            continue
        ext = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', para)
        blip = re.search(r"<a:blip\b[^>]*?(?:/>|>.*?</a:blip>)", para, re.S)
        blk_open = blip.group(0)[: blip.group(0).index(">") + 1] if blip else ""
        primary = re.search(r'r:embed="([^"]+)"', blk_open)
        caption = None
        if i + 1 < len(paras):
            nxt = paras[i + 1]
            style = re.search(r'<w:pStyle w:val="([^"]+)"', nxt)
            if style and re.search(r"caption", style.group(1), re.I):
                caption = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", nxt, re.S)) or None
        figures.append({
            "para": i,
            "width_pt": int(ext.group(1)) / 12700 if ext else None,
            "height_pt": int(ext.group(2)) / 12700 if ext else None,
            "caption": caption,
            "has_svg_blip": bool(blip and "svgBlip" in blip.group(0)),
            "primary_rid": primary.group(1) if primary else None,
        })
    return figures


def _pdf_text_lines(pdf_path: Path) -> list:
    """Every text line of the PDF with its bbox, in reading order.

    pdftotext -bbox-layout emits <line> elements inside <page> elements;
    lines are sorted by (page, y) so single-column documents read top-down.
    An empty list means the PDF genuinely carries no text layer; a tool that
    cannot be run raises FigureToolUnavailable (PF-B12: never a silent skip).
    """
    try:
        r = subprocess.run(["pdftotext", "-bbox-layout", str(pdf_path), "-"],
                           capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise FigureToolUnavailable(
            "pdftotext timed out; figure captions cannot be located in the PDF text layer, "
            "so the non-blank figure-slot assertion cannot run")
    except OSError as exc:  # includes FileNotFoundError — pdftotext not on PATH
        raise FigureToolUnavailable(
            f"pdftotext could not be run ({exc}); figure captions cannot be located in the "
            "PDF text layer, so the non-blank figure-slot assertion cannot run")
    if r.returncode != 0:
        raise FigureToolUnavailable(
            "pdftotext failed: " + r.stderr.decode("utf-8", "replace")[:120]
            + "; figure captions cannot be located in the PDF text layer, so the "
              "non-blank figure-slot assertion cannot run")
    html = r.stdout.decode("utf-8", "replace")
    lines = []
    page_no = 0
    for pm in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', html, re.S):
        page_no += 1
        for lm in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>',
                              pm.group(3), re.S):
            words = "".join(re.findall(r"<word[^>]*>(.*?)</word>", lm.group(5), re.S))
            lines.append({"page": page_no, "page_w": float(pm.group(1)), "page_h": float(pm.group(2)),
                          "x0": float(lm.group(1)), "y0": float(lm.group(2)),
                          "x1": float(lm.group(3)), "y1": float(lm.group(4)), "text": words})
    lines.sort(key=lambda ln: (ln["page"], ln["y0"], ln["x0"]))
    return lines


def _pgm_ink_ratio(path: Path) -> float | None:
    """Non-white pixel ratio of a binary PGM (P5) file — stdlib only.

    Pillow is not a declared toolchain dependency (and is invisible under
    python3 -I), so the trivial P5 container is parsed directly.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data.startswith(b"P5"):
        return None
    pos, fields = 2, []
    while len(fields) < 3:
        while pos < len(data) and data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b"#":                     # comment line
            while pos < len(data) and data[pos:pos + 1] != b"\n":
                pos += 1
            continue
        start = pos
        while pos < len(data) and not data[pos:pos + 1].isspace():
            pos += 1
        fields.append(data[start:pos])
    pos += 1                                                # single whitespace after maxval
    try:
        width, height, maxval = int(fields[0]), int(fields[1]), int(fields[2])
    except ValueError:
        return None
    if maxval > 255:                                        # 16-bit PGM: not produced here
        return None
    body = data[pos: pos + width * height]
    if width * height == 0 or len(body) < width * height:
        return None
    ink = sum(1 for b in body if b < FIGURE_INK_THRESHOLD)
    return ink / (width * height)


def _figure_source_candidates(figures_dir: Path, ref: str) -> list:
    """Resolve a body figure reference to candidate source paths.

    References are written relative to the paper root (figures/x.svg) or,
    historically, relative to the body directory (../figures/x.svg — the
    pandoc --resource-path second entry resolves it against <root>/body).
    """
    cands = [figures_dir / ref]
    if ref.startswith("../"):
        cands.append(figures_dir / ref[3:])
    cands.append(figures_dir / "body" / ref)
    cands.append(figures_dir / ref.lstrip("./"))
    return cands


def _classify_figure_refs(figure_refs: list, figures_dir: Path) -> dict:
    """Split body figure references by source kind (GC-2026-1113-02).

    - svg_refs: referenced as .svg — the PDF figure must be VECTOR.
    - bitmap_refs: referenced as .png/.jpg/... — the PDF legitimately
      embeds that bitmap.
      - raster_only_figures: no same-stem .svg exists (PF-B15 downgrade
        semantics: the figure IS the bitmap).
      - raster_ref_with_svg: a same-stem .svg exists but the body still
        references the bitmap — a MIGRATION state, recorded as a warning,
        never a build failure (P2 as of 2026-11-13).
    """
    bitmap_refs, raster_only, raster_with_svg, svg_refs = [], [], [], []
    for ref in figure_refs:
        if PurePosixPath(ref).suffix.lower() in RASTER_EXTENSIONS:
            bitmap_refs.append(ref)
            stem = ref.rsplit(".", 1)[0]
            if any(c.exists() for c in _figure_source_candidates(figures_dir, stem + ".svg")):
                raster_with_svg.append(ref)
            else:
                raster_only.append(ref)
        else:
            svg_refs.append(ref)
    return {"svg_refs": svg_refs, "bitmap_refs": bitmap_refs,
            "raster_only_figures": raster_only, "raster_ref_with_svg": raster_with_svg}


def _figure_text_intrusion_applicable(figures_dir: Path, ref: str) -> bool:
    """Whether the no-text-intrusion assertion applies to this figure.

    LibreOffice renders SVG-internal <text> as REAL, extractable PDF text
    (verified 2026-11-13 on P4/P6 figures), so a text-bearing SVG puts its
    own label lines INSIDE its figure region — counting those as intrusion
    would fail every healthy build (P2/P4/P5/P6/P7/P8 figures carry <text>).
    For those figures only the ink assertion applies. Path-only SVGs
    (P1/P3) and bitmap references contribute no text of their own, so the
    intrusion assertion applies to them.
    """
    if PurePosixPath(ref).suffix.lower() in RASTER_EXTENSIONS:
        return True
    for cand in _figure_source_candidates(figures_dir, ref):
        if cand.exists():
            if cand.suffix.lower() != ".svg":
                return False
            try:
                return b"<text" not in cand.read_bytes()
            except OSError:
                return False
    return False


def _locate_caption_line(lines: list, caption_text: str, used: set,
                         figure_height_pt: float | None = None,
                         page_height_pt: float | None = None) -> dict | None:
    """Find a figure's caption line in the PDF text layer.

    The caption text comes from the docx (pandoc's implicit-figure caption,
    which sits directly UNDER the figure). The scan stays FIRST-match in
    reading order, with one geometric admission test per candidate:

    Geometry rule — a real caption has the whole figure ABOVE it on the same
    page, so the figure's top edge (candidate y0 minus the docx figure
    height and the region gap) must clear the page top by at least
    CAPTION_TOP_TOLERANCE_PT. A candidate that fails this is skipped and the
    scan continues. If NO candidate passes (e.g. the caption opens a page
    with its figure on the previous one, or the figure is taller than the
    page), the first text-matching candidate is returned — the pre-geometry
    behavior — so the slot assertion still runs instead of silently
    disappearing.

    Why first-match-plus-geometry, and not last-match: a paper that repeats
    its caption as a body paragraph (P3 does) repeats it AFTER the pandoc
    caption, so a last-match rule would anchor P3's slot on body text. Why
    the geometric admission is needed at all: a figure whose SVG carries the
    caption wording as an in-image title (P2 fig4 does — "图4 主方案与消融在
    关键指标上的对照…" drawn at the top of its chart canvas) matches the
    caption prefix BEFORE the real caption in reading order. On P2 fig4 the
    in-image title sits at y≈203.9pt while the docx extent is 249.4pt tall:
    its implied figure top edge would be ≈ −50pt (off the page top), so it is
    skipped and the scan reaches the real caption at y≈457.8pt (implied top
    ≈ 204pt). P3's repeat is later in reading order, so its real caption
    remains the first candidate that passes geometry — both papers anchor
    correctly under the same rule.

    page_height_pt (when given, the caller passes the document's uniform page
    height) only guards the fit precondition: if the figure plus the region
    gap cannot fit on a single page at all, the top-edge test would reject
    every candidate, so it is disabled and the first text-matching candidate
    is returned. The top-edge comparison itself is against the page top
    (y=0 in the bbox), which needs no page height.
    """
    def norm(s: str) -> str:
        return re.sub(r"\s+", "", s)

    prefix = norm(caption_text)[:CAPTION_MATCH_CHARS]
    if len(prefix) < 2:
        return None
    geometry_live = (figure_height_pt is not None
                     and (page_height_pt is None
                          or figure_height_pt + FIGURE_REGION_GAP_PT < page_height_pt))
    first_idx = None
    for i, ln in enumerate(lines):
        if i in used:
            continue
        if not norm(ln["text"]).startswith(prefix):
            continue
        if first_idx is None:
            first_idx = i
        if geometry_live:
            top_edge = ln["y0"] - figure_height_pt - FIGURE_REGION_GAP_PT
            if top_edge < CAPTION_TOP_TOLERANCE_PT:
                continue  # the figure cannot fit above this candidate on its page
        used.add(i)
        return ln
    if first_idx is not None:
        used.add(first_idx)
        return lines[first_idx]
    return None


def _region_ink_ratio(pdf_path: Path, page: int, page_w: float,
                      top_pt: float, bottom_pt: float) -> float | None:
    """Non-white ratio of a PDF page region, rendered via pdftoppm -gray.

    None is returned only for a degenerate region (rounds to zero pixels at
    FIGURE_RENDER_DPI) — a document-geometry negative, not a tool fault.
    A tool that cannot be run, or output that cannot be measured, raises
    FigureToolUnavailable: the ink assertion would otherwise be skipped
    silently and an unverified slot would ship (PF-B12).
    """
    dpi = FIGURE_RENDER_DPI

    def px(v: float) -> int:
        return max(0, int(round(v * dpi / 72)))

    w_px, h_px = px(page_w), px(bottom_pt - top_pt)
    if w_px <= 0 or h_px <= 0:
        return None
    tmp = pdf_path.with_name(pdf_path.name + ".figregion.tmp")
    try:
        try:
            r = subprocess.run(["pdftoppm", "-gray", "-r", str(dpi), "-f", str(page), "-l", str(page),
                                "-x", "0", "-y", str(px(top_pt)), "-W", str(w_px), "-H", str(h_px),
                                "-singlefile", str(pdf_path), str(tmp)],
                               capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            raise FigureToolUnavailable(
                "pdftoppm timed out; the figure-slot region cannot be rendered, so the "
                "non-blank figure-slot assertion cannot run")
        except OSError as exc:  # includes FileNotFoundError — pdftoppm not on PATH
            raise FigureToolUnavailable(
                f"pdftoppm could not be run ({exc}); the figure-slot region cannot be "
                "rendered, so the non-blank figure-slot assertion cannot run")
        if r.returncode != 0:
            raise FigureToolUnavailable(
                "pdftoppm failed: " + r.stderr.decode("utf-8", "replace")[:120]
                + "; the figure-slot region cannot be rendered, so the non-blank "
                  "figure-slot assertion cannot run")
        ink = _pgm_ink_ratio(Path(str(tmp) + ".pgm"))
        if ink is None:
            raise FigureToolUnavailable(
                "pdftoppm produced no measurable PGM output; the figure-slot ink ratio "
                "cannot be determined, so the non-blank figure-slot assertion cannot run")
        return ink
    finally:
        try:
            Path(str(tmp) + ".pgm").unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - a leftover temp render is not fatal
            pass


def _pdf_figures_unavailable(error: str) -> dict:
    """Unavailable-result shape shared by every poppler tool gate (PF-B12).

    status=unavailable makes the caller record a pdf_figure_verification_failed
    limitation and fail the build; the failure entry keeps the manifest's
    failures list and the CLI error payload self-explanatory.
    """
    return {"check": "pdf_figures", "status": "unavailable",
            "failures": [{"kind": "figure_tool_unavailable", "detail": error}],
            "notes": [], "error": error}


def _verify_pdf_figures(pdf_path: Path, docx_path: Path, figure_refs: list, figures_dir: Path) -> dict:
    """PDF-level figure assertions (GC-2026-1113-02), run after conversion.

    A) Raster budget — pdfimages image objects wider OR taller than
       FIGURE_RASTER_MIN_PX (soft masks excluded) must not exceed the number
       of figures the body references as bitmaps: every vector-referenced
       figure must reach the PDF as vector. <=64px tiles are SVG <pattern>
       fills LibreOffice rasterizes — counted as pattern_tiles, never failed.

    B) Drawing inventory — the docx must hold one drawing per referenced
       figure; a reference without a drawing ships an empty slot.

    C) Non-blank figure slot — each figure's caption is located in the PDF
       text layer by its docx caption text; the region between the caption
       top and the figure height above it (wp:extent from the docx) must
       carry ink, and no body-text line may intrude into it (applied only
       where the figure cannot contribute text of its own — see
       _figure_text_intrusion_applicable). A blank or intruded slot fails
       the build: that is the 2026-11-12 empty-figure-slot regression.

    Failures are returned in the "failures" list; the caller records them in
    the manifest and fails the build (PF-B12: no silent pass). A poppler tool
    an assertion depends on that is missing or failing maps the whole check to
    status=unavailable via _pdf_figures_unavailable — the same contract as the
    pdfimages gate below — so an unverifiable figure never ships.
    """
    result = {"check": "pdf_figures", "status": "pass", "failures": [], "notes": []}

    # ── A. raster budget ──
    try:
        r = subprocess.run(["pdfimages", "-list", str(pdf_path)], capture_output=True, timeout=60)
    except FileNotFoundError:
        return _pdf_figures_unavailable(
            "pdfimages not found; the PDF's embedded rasters cannot be inventoried")
    except subprocess.TimeoutExpired:
        return _pdf_figures_unavailable("pdfimages timed out")
    if r.returncode != 0:
        return _pdf_figures_unavailable(
            "pdfimages failed: " + r.stderr.decode("utf-8", "replace")[:120])
    figure_rasters = pattern_tiles = 0
    for line in r.stdout.decode("utf-8", "replace").splitlines()[2:]:
        f = line.split()
        if len(f) < 5 or f[2] != "image":
            continue
        try:
            w, h = int(f[3]), int(f[4])
        except ValueError:
            continue
        if w > FIGURE_RASTER_MIN_PX or h > FIGURE_RASTER_MIN_PX:
            figure_rasters += 1
        else:
            pattern_tiles += 1

    classes = _classify_figure_refs(figure_refs, figures_dir)
    bitmap_refs = classes["bitmap_refs"]
    unexpected = figure_rasters - len(bitmap_refs)
    result.update({
        "figure_level_rasters": figure_rasters,
        "pattern_tiles": pattern_tiles,
        "svg_ref_figures": len(classes["svg_refs"]),
        "bitmap_ref_figures": len(bitmap_refs),
        "unexpected_rasters": unexpected,
        "raster_only_figures": classes["raster_only_figures"],
        "raster_ref_with_svg": classes["raster_ref_with_svg"],
    })
    if unexpected > 0:
        result["failures"].append({
            "kind": "figure_level_raster_present",
            "detail": (f"{unexpected} figure-level raster image(s) (>{FIGURE_RASTER_MIN_PX}px) beyond the "
                       f"{len(bitmap_refs)} bitmap-referenced figure(s): a vector-referenced figure reached "
                       "the PDF as a raster (svgBlip stripped?) or an extra raster was embedded"),
        })
    elif unexpected < 0:
        result["notes"].append(
            f"{len(bitmap_refs)} bitmap-referenced figure(s) but only {figure_rasters} figure-level "
            f"raster(s) in the PDF (a source bitmap embedded below the {FIGURE_RASTER_MIN_PX}px floor); "
            "recorded, not failed")
    if classes["raster_ref_with_svg"]:
        result["notes"].append(
            "body references a bitmap while a same-stem .svg exists (migration pending, not a build "
            f"failure): {', '.join(classes['raster_ref_with_svg'])}")

    # ── B. drawing inventory, C. non-blank figure slots ──
    geometry = _docx_figure_geometry(docx_path)
    try:
        lines = _pdf_text_lines(pdf_path)
    except FigureToolUnavailable as exc:
        return _pdf_figures_unavailable(str(exc))
    if not lines:
        result["notes"].append("pdftotext produced no text layer; figure-slot region check skipped")
    # The drawing inventory is re-checked here so the PDF-level verification
    # is self-contained: a referenced figure that lost its drawing ships an
    # empty slot no matter what the PDF shows (the docx step fails fast on the
    # same condition before the conversion runs).
    if len(geometry) < len(figure_refs):
        result["failures"].append({
            "kind": "figure_drawing_count_mismatch",
            "detail": (f"the docx holds {len(geometry)} figure drawing(s) for {len(figure_refs)} "
                       "referenced figure(s) — a referenced figure has no drawing in the document"),
        })
    elif len(geometry) > len(figure_refs):
        result["notes"].append(
            f"the docx holds {len(geometry)} figure drawing(s) for {len(figure_refs)} referenced "
            "figure(s) (front/back-matter or non-body figures); recorded, not failed")
    used_lines: set = set()
    pages_checked: list = []
    figure_regions: list = []
    blank_regions: list = []
    if len(geometry) != len(figure_refs):
        result["notes"].append(
            f"docx drawing count ({len(geometry)}) differs from body figure reference count "
            f"({len(figure_refs)}); figures are paired by document order")
    for idx, (fig, ref) in enumerate(zip(geometry, figure_refs)):
        entry = {"figure": idx + 1, "ref": ref, "has_svg_blip": fig["has_svg_blip"]}
        figure_regions.append(entry)
        if fig["height_pt"] is None:
            entry["status"] = "extent_missing"
            result["notes"].append(f"figure {idx + 1} ({ref}): no wp:extent in the docx; region check skipped")
            continue
        if not fig["caption"]:
            entry["status"] = "caption_absent"
            result["notes"].append(f"figure {idx + 1} ({ref}): no caption paragraph in the docx; region check skipped")
            continue
        # GC-2026-1113-02: the figure height and page height arm the geometry
        # admission in _locate_caption_line, so an in-image title that repeats
        # the caption wording (P2 fig4) cannot hijack the slot anchor.
        cap = (_locate_caption_line(lines, fig["caption"], used_lines,
                                    fig["height_pt"], lines[0]["page_h"])
               if lines else None)
        if cap is None:
            entry["status"] = "caption_unlocated"
            entry["detail"] = "caption text not found in the PDF text layer"
            result["notes"].append(
                f"figure {idx + 1} ({ref}): caption not located in the PDF text layer; region check skipped")
            continue
        cap_top = cap["y0"]
        top = max(0.0, cap_top - fig["height_pt"] - FIGURE_REGION_GAP_PT)
        entry.update({"page": cap["page"], "caption_top": round(cap_top, 1),
                      "region": [round(top, 1), round(cap_top, 1)],
                      "height_pt": round(fig["height_pt"], 1), "status": "pass"})
        if cap["page"] not in pages_checked:
            pages_checked.append(cap["page"])
        try:
            ink = _region_ink_ratio(pdf_path, cap["page"], cap["page_w"], top, cap_top)
        except FigureToolUnavailable as exc:
            return _pdf_figures_unavailable(str(exc))
        entry["ink_ratio"] = round(ink, 4) if ink is not None else None
        intruders = []
        if _figure_text_intrusion_applicable(figures_dir, ref):
            intruders = [ln for ln in lines if ln["page"] == cap["page"]
                         and ln["y1"] > top + 1.0 and ln["y0"] < cap_top - 1.0]
        entry["text_lines_in_region"] = len(intruders)
        problems = []
        if ink is None:
            entry["status"] = "ink_unavailable"
            result["notes"].append(f"figure {idx + 1} ({ref}): slot region rounds to zero pixels "
                                   f"at {FIGURE_RENDER_DPI} DPI; ink assertion skipped")
        else:
            if ink < FIGURE_REGION_MIN_INK:
                problems.append(f"slot ink ratio {ink:.4f} < {FIGURE_REGION_MIN_INK} (blank figure slot)")
            if intruders:
                problems.append(f"{len(intruders)} body-text line(s) intrude into the slot "
                                f"(first: {intruders[0]['text'][:30]!r})")
        if problems:
            entry["status"] = "blank_or_intruded"
            entry["detail"] = "; ".join(problems)
            blank_regions.append(entry)
            result["failures"].append({"kind": "blank_figure_region", "figure": idx + 1, "ref": ref,
                                       "page": cap["page"], "detail": "; ".join(problems)})
        elif entry["status"] != "ink_unavailable":
            entry["status"] = "pass"
    result["pages_checked"] = sorted(pages_checked)
    result["figure_regions"] = figure_regions
    result["blank_figure_regions"] = [
        {"figure": b["figure"], "ref": b["ref"], "page": b.get("page"), "detail": b.get("detail")}
        for b in blank_regions]
    if result["failures"]:
        result["status"] = "fail"
    return result


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
    # PF-B7 (GC-2026-1112-04): the release file name is 标题（第一作者中文名）. The first
    # author is resolved BEFORE any build work — the name is part of the release
    # record, so it is never guessed (missing → the build fails with the fix hint).
    try:
        first_author = _first_author_name(dest, paper_cfg)
    except Exception as exc:  # noqa: BLE001 - a broken authors.yaml is a naming failure
        return ({"status": "error",
                 "error": (f"the first author could not be read for the PF-B7 release file "
                           f"name: {exc}. Register the first author with roles: ['first'] "
                           f"in paper.yaml (or in authors.yaml)."),
                 "stage": "pre-build"}, 2)
    if not first_author:
        return ({"status": "error",
                 "error": ("no first author found — PF-B7 requires the release file name to be "
                           "标题（第一作者中文名）. Register the first author in paper.yaml "
                           "(authors: - name: <中文名>, roles: [first]) or in authors.yaml, "
                           "then rebuild."),
                 "stage": "pre-build"}, 2)
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
    # The release name uses the paper.yaml title verbatim (the package path uses
    # the same expression), so the built artifact and the package skeleton share
    # one stem even for a multi-line title.
    release_title = str(paper_cfg.get("title") or "").strip() or title
    title_en = paper_cfg.get("title_en")
    manuscript_kind = paper_cfg.get("manuscript_kind") or "research"

    body_source = dest / "body" / "paper.md"
    if not body_source.exists():
        return ({"status": "error", "error": f"single body source missing: body/paper.md (PF-B2)"}, 2)

    build_task_id = f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    temp_build_dir = dest / "temp" / f"{info['id']}-{build_task_id}"
    temp_build_dir.mkdir(parents=True, exist_ok=True)
    try:
        # GC-2026-1112-06: metadata-driven assembly. Front/back matter are generated
        # from paper.yaml + authors.yaml + abstract.md + funding.yaml; the body
        # (chapters + references + appendix after migration) is embedded between
        # them. assemble_document enforces the transitional hard gate — a
        # BARE-LIST authors.yaml fails the build, no legacy fallback.
        if metalayout is None:
            return ({"status": "error", "error": f"metalayout unavailable: {_metalayout_error}",
                     "stage": "pre-build"}, 2)
        # GC-2026-1112-06 终审返工（P3-5）：build 路径也跑语义硬闸 H3–H8
        # （validate_metadata）。load 级闸（H1 容器形态 / H2 jsonschema）在
        # assemble_document 内经 load_paper_metadata 生效；语义闸此前只在 check
        # 生效，新论文 init 骨架（元数据未填）可过 load 但必须在 build 也失败并
        # 给出可操作提示。
        try:
            meta = metalayout.load_paper_metadata(dest)
            meta_errors = metalayout.validate_metadata(meta)
        except metalayout.MetalayoutError as exc:
            return ({"status": "error", "error": f"metadata validation failed: {exc}",
                     "stage": "pre-build"}, 2)
        if meta_errors:
            return ({"status": "error",
                     "error": "metadata semantic checks failed (GC-2026-1112-06): "
                              + "; ".join(meta_errors),
                     "stage": "pre-build", "metadata_errors": meta_errors}, 2)
        assembly_path = temp_build_dir / "assembled.md"
        try:
            assembly_record = metalayout.assemble_document(
                dest, assembly_path, authors_profile=layout["merged"].get("authors"))
        except metalayout.MetalayoutError as exc:
            return ({"status": "error", "error": f"metadata assembly failed: {exc}",
                     "stage": "pre-build"}, 2)

        output_file = temp_build_dir / "paper.docx"
        cmd = [
            "pandoc", str(assembly_path),
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
        # GC-2026-1112-06: the English title is NOT injected via the subtitle
        # metadata — pandoc renders subtitle right after the title, which would
        # break the 范本 front-page order (funding block comes before the English
        # title). It is a Subtitle-styled div placed in the generated front matter
        # after the funding block instead (stie authors.front_order).
        # NOTE: author line is NOT injected either — the byline/affiliation list is
        # generated into the assembled front matter from the authors.yaml registry.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not output_file.exists():
            return ({"status": "error", "error": result.stderr.strip() or "pandoc failed", "stderr": result.stderr[:500]}, 1)
        # A figure that could not be resolved is only a pandoc WARNING — the build
        # used to succeed with an empty figure slot (found on P2/P3, 2026-11-12).
        # PF-B6 requires the actual rendering to be checked, so the produced package
        # must contain every figure the body references (front/back matter carry
        # none, so counting on the assembled input matches the body).
        src_text = assembly_path.read_text(encoding="utf-8")
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
        # GC-2026-1113-02: every referenced figure must reach the document as a
        # DRAWING, not merely as a media part — a package can carry the media
        # while the body lost the drawing, which would ship an empty figure
        # slot (the media-count check above cannot see that: pandoc embeds
        # BOTH the raster fallback and the SVG per figure).
        figure_geometry = _docx_figure_geometry(output_file)
        if len(figure_geometry) < len(refs):
            return ({"status": "error",
                     "error": (f"the produced document holds {len(figure_geometry)} figure drawing(s) "
                               f"for {len(refs)} referenced figures — shipping it would deliver the "
                               f"paper with missing figure slots (PF-B6/PF-B12)"),
                     "figure_refs": len(refs), "figure_drawings": len(figure_geometry),
                     "stage": "build", "stderr": result.stderr[:500]}, 1)

        _inject_paper_title_header(output_file, title)
        # pandoc copies the header/footer parts but not their relationships;
        # close the graph so the delivered docx is a valid package.
        hf_repair = _repair_header_footer_relationships(output_file)
        # GC-2026-1113-02: KEEP the SVG alternative so the PDF figure renders
        # as vector (crisp text); ASSERT every svgBlip still carries a raster
        # fallback. An SVG-only blip is the 2026-11-12 empty-figure-slot
        # regression ('../figures/' path form) and fails the build.
        svg_verified = _validate_svg_alternatives(output_file)
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
        layout_notes.append({"check": "svg_alternatives_preserved", "value": svg_verified})
        # GC-2026-1113-02: a body figure referenced as a bitmap while a
        # same-stem .svg exists is a MIGRATION state (its PDF embeds the
        # original bitmap — high resolution but not vector), recorded as a
        # warning; it is not a build failure (P2 as of 2026-11-13, with an
        # in-flight polish line on the same body).
        ref_classes = _classify_figure_refs(refs, dest)
        if ref_classes["raster_ref_with_svg"]:
            layout_notes.append({"check": "figure_raster_ref_with_svg",
                                 "value": ref_classes["raster_ref_with_svg"],
                                 "note": ("body references a bitmap whose same-stem .svg exists — the PDF "
                                          "embeds that bitmap (high resolution, not vector); migrating the "
                                          "reference to .svg yields a vector figure slot (PF-B15); "
                                          "recorded, not a build failure")})
        # GC-2026-1113-02: the SVG-alternative guard is a hard failure — a
        # blip carrying an svgBlip without a raster fallback is exactly the
        # 2026-11-12 empty-figure-slot construction.
        if svg_verified["blips_missing_raster"]:
            failures.append({
                "check": "svg_alternatives_preserved",
                "expected": "every <a:blip> carrying an <asvg:svgBlip> also carries a raster "
                            "r:embed fallback whose media part exists",
                "actual": svg_verified["missing"],
                "hint": ("an SVG-only blip renders as an EMPTY figure slot (ab0bdcc, 2026-11-12): "
                         "reference figures as 'figures/x.svg' (the pandoc --resource-path already "
                         "covers it) so pandoc emits the PNG fallback alongside the svgBlip; the "
                         "'../figures/' form produces an SVG-only blip"),
            })

        # ── content-compliance assertion: equations must be OMML, not images (S9) ──
        # GC-2026-1112-06 终审返工（P3-7）：公式计数只统计正文区间（body/paper.md），
        # 不把生成的前端/文末计入——摘要等元数据块若含行内公式（$…$）曾造成
        # `formulas_omml` 误失败（math_markers>0 而 omath_count 按全文档计）。
        body_text = body_source.read_text(encoding="utf-8")
        math_markers = len(re.findall(r'\$[^$\n]+\$', body_text)) + len(re.findall(r'\$\$.+?\$\$', body_text, re.S))
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
        safe_title = _release_file_stem(release_title, first_author)
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
        manifest_file = out_dir / "manifest.json"
        # T1 (GC-2026-1112-04): a rebuild must not silently reset the release state.
        # The review status is INHERITED from the manifest being replaced (a
        # published release stays published), and a prior package assembly is
        # marked stale — the assembly no longer describes the new release.
        prev_manifest: dict = {}
        if manifest_file.exists():
            try:
                loaded = json.loads(manifest_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    prev_manifest = loaded
            except Exception:  # noqa: BLE001 - an unreadable manifest counts as absent
                prev_manifest = {}
        prev_submission = prev_manifest.get("submission")
        if not isinstance(prev_submission, dict):
            prev_submission = {}
        review_status = prev_manifest.get("review_status") or "pending"
        # PF-B7: the release manifest carries the submission metadata set
        # (abstract, keywords, authors with biographies, conclusion, character
        # counts, submission direction). Every field is extracted on its own:
        # a failure nulls that field and records a gap — the build never dies
        # on a missing anchor (DD-2).
        submission, submission_warnings = _build_submission_block(dest, paper_cfg, release_title)
        if prev_submission.get("package_status") == "assembled":
            submission["package_status"] = "stale"
            submission["package_manifest_sha256"] = None
            submission["stale_note"] = "rebuild invalidated prior assembly; re-run package"
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
                # PF-B7: the manifest must record the rules version the PAPER is
                # bound to, not a constant baked into the tool (a hardcoded value
                # made the manifest claim a binding the papers did not have —
                # found 2026-11-12: manifest 0.3.0 vs paper.yaml 0.2.1).
                "rules_version": paper_cfg.get("rules_version") or "unbound",
                "merge_order": "L0(draft) -> L1(venue) -> L2(paper)",
                "override_log": layout["override_log"],
                "reference_doc": str(layout["refdoc_path"].relative_to(layoutlib.GOV_ROOT)),
                "reference_doc_sha256_16": refdoc_sha,
                "assertions": {"failed": 0, "notes": layout_notes},
                # GC-2026-1113-02: figure provenance — the body references, the
                # docx media parts, and the SVG-alternative guard result. The
                # PDF step adds the "pdf" sub-block (raster budget + slot
                # assertions) to this same block.
                "figures": {
                    "refs": refs,
                    "docx_media": len(embedded),
                    "docx_figures": len(figure_geometry),
                    "svg_blips_preserved": svg_verified["svg_blips"],
                    "raster_fallbacks": svg_verified["raster_fallbacks"],
                    "blips_missing_raster": svg_verified["blips_missing_raster"],
                    "raster_only_figures": ref_classes["raster_only_figures"],
                    "raster_ref_with_svg": ref_classes["raster_ref_with_svg"],
                },
                # Font families the profile requires; the PDF step checks each of them
                # against the embedded set and records any absence as a limitation.
                "profile_fonts": _profile_font_families(layout["role"]),
            },
            "body_source": "body/paper.md",
            # GC-2026-1112-06: assembly record — front/back matter are generated
            # from metadata (paper.yaml/authors.yaml/abstract.md/funding.yaml) and
            # body/paper.md embedded between them; the assembly is logged here so
            # the produced release is reproducible from the sources.
            "assembly": {
                "method": "metadata-driven (GC-2026-1112-06)",
                "front_matter_generated": assembly_record.get("front_matter_generated", False),
                "back_matter_generated": assembly_record.get("back_matter_generated", False),
                "path": str(assembly_path.relative_to(dest)),
            },
            "artifacts": [{"format": "docx", "path": str(docx_out.relative_to(dest)), "sha256": hashlib.sha256(docx_out.read_bytes()).hexdigest()[:16], "size": docx_out.stat().st_size}],
            "review_status": review_status,
            "submission": submission,
            "limitations": [n for n in layout_notes if n.get("check", "").endswith("_limitation")],
        }
        _atomic_write_json(manifest_file, manifest)
        current_json = dest / "build" / "current.json"
        current_json.write_text(json.dumps({"paper_version": version, "manifest_path": f"build/{version}/manifest.json"}, ensure_ascii=False), encoding="utf-8")
        # G-5: the naming switch leaves the old-named artifacts of a pending
        # version in the build directory. Nothing is deleted here (PF-B7: old
        # versions are preserved) — the leftovers are declared in the output.
        leftovers = sorted(p.name for p in out_dir.glob("*")
                           if p.is_file() and p.suffix in (".docx", ".pdf")
                           and p.stem != safe_title)
        notices = [f"{name} — the release file name is now '{safe_title}' (PF-B7); the old-named "
                   f"artifact of a pending version is kept, not deleted" for name in leftovers]
        return ({"status": "ok", "paper_id": info["id"], "paper_version": version, "layout_profile": layout["profile_name"],
                     "format": "docx", "output_path": str(docx_out), "manifest_path": str(manifest_file),
                     "artifact_stem": safe_title,
                     "review_status": review_status,
                     # GC-2026-1113-02: the figure data pipeline — the PDF step
                     # verifies the produced PDF's figure slots against these
                     # references and this source directory.
                     "figure_refs": refs,
                     "figures_dir": str(dest),
                     "stale_artifact_names": leftovers,
                     "artifact_name_notices": notices,
                     "submission_gaps": submission.get("submission_gaps") or [],
                     "submission_warnings": submission_warnings,
                     "layout_assertions": "pass", "override_log_entries": len(layout["override_log"])}, 0)
    except subprocess.TimeoutExpired:
        return ({"status": "error", "error": "pandoc timeout (120s)"}, 2)
    except Exception as exc:
        return ({"status": "error", "error": str(exc)}, 2)


def cmd_build_docx(args):
    payload, code = _cmd_build_docx_impl(args)
    return emit(payload, code)


# ── PDF determinism normalization ────────────────────────────────
# GC-2026-1113-01: LibreOffice overwrites three PDF fields on every export, so
# two exports of the same docx differ only in those bytes (verified 2026-11-13 on
# P1: a byte-diff of two exports shows exactly two regions — Info/CreationDate
# timestamp, and trailer /ID [ <h32> <h32> ] together with the /DocChecksum that
# LibreOffice derives from them). The XMP packet dates stay CONSTANT across
# exports because they come from the deterministic docx metadata, not the wall
# clock — so they need no normalization. The fix follows the same philosophy as
# the refdoc determinism (make_refdoc.py's fixed zip timestamps): replace the
# varying bytes with FIXED values of the SAME byte length, keeping the xref
# offsets valid. The normalized file is validated (pypdf parse + page count +
# pdftotext non-empty) before it may replace the export; any check failure keeps
# the original unnormalized PDF and records a limitation — never publish a
# possibly corrupt PDF.
PDF_NORM_FIXED_CREATION_TS = b"20260101000000"          # 14 digits; tz suffix kept
PDF_NORM_FIXED_ID = b"0102030405060708090A0B0C0D0E0F10"  # 32 hex
PDF_NORM_FIXED_DOCCHECKSUM = b"A1B2C3D4E5F60718293A4B5C6D7E8F90"  # 32 hex

_PYPDF_MODULE = None
_PYPDF_TRIED = False


def _import_pypdf():
    """Import pypdf even under `python3 -I` (isolation drops user site-packages).

    pypdf is used here as the corruption canary: count pages BEFORE replacement
    and re-parse the normalized bytes AFTER replacement. It is installed in the
    user's site-packages on this host (pypdf 6.20.1); -I hides that path, so it
    is re-added explicitly — the same explicit sys.path insertion already used
    for the sibling layoutlib module. A missing pypdf degrades the normalize path
    to a structural check and never blocks the build.
    """
    global _PYPDF_MODULE, _PYPDF_TRIED
    if _PYPDF_TRIED:
        return _PYPDF_MODULE
    _PYPDF_TRIED = True
    try:
        import pypdf as _mod
        _PYPDF_MODULE = _mod
        return _PYPDF_MODULE
    except Exception:  # noqa: BLE001 - fall through to the explicit-path retry
        pass
    try:
        import site as _site_mod
        cand = _site_mod.getusersitepackages()
        if cand and cand not in sys.path:
            sys.path.insert(0, cand)
        try:
            import pypdf as _mod2
            _PYPDF_MODULE = _mod2
        except Exception:  # noqa: BLE001 - pypdf genuinely unavailable
            _PYPDF_MODULE = None
    except Exception:  # noqa: BLE001 - site module quirks are not fatal
        _PYPDF_MODULE = None
    return _PYPDF_MODULE


def _pdf_normalize_deterministic(pdf_path: Path) -> dict:
    """Same-length metadata normalization for a LibreOffice-exported PDF.

    Replaces the three wall-clock/random fields with fixed same-length values:
      - Info/CreationDate  (timestamp only; the timezone suffix is kept as-is,
        so the replacement matches the source length on any LO output)
      - trailer /ID pair
      - trailer /DocChecksum
    Validates before publishing: pypdf parse + page-count equality with the
    pre-normalization file + a non-empty pdftotext sample. Any failure restores
    the ORIGINAL bytes and returns status='fallback' (the caller records a
    limitation; the unnormalized PDF ships, never a possibly corrupt one).
    Returns dict: {status, fields, reason?, page_count?}.
    """
    try:
        original = pdf_path.read_bytes()
    except OSError as exc:
        return {"status": "noop", "reason": f"cannot read pdf: {exc}", "fields": {}}
    data = original
    replaced = {"CreationDate": False, "ID": False, "DocChecksum": False}

    # 1. Info dict /CreationDate(D:YYYYMMDDHHMMSS<tz>) -> fixed timestamp
    m_cre = re.search(rb"/CreationDate\((D:[0-9]{14})([^)\r\n]*)\)", data)
    if m_cre:
        fixed = b"/CreationDate(D:" + PDF_NORM_FIXED_CREATION_TS + m_cre.group(2) + b")"
        if len(fixed) == len(m_cre.group(0)):
            data = data[: m_cre.start()] + fixed + data[m_cre.end():]
            replaced["CreationDate"] = True

    # 2. trailer /ID [ <h32><sep><h32> ] -> both halves fixed (sep preserved)
    m_id = re.search(rb"/ID \[ <([0-9A-Fa-f]{32})>([\r\n ]+)<([0-9A-Fa-f]{32})> \]", data)
    if m_id:
        fixed = (b"/ID [ <" + PDF_NORM_FIXED_ID + b">" + m_id.group(2)
                 + b"<" + PDF_NORM_FIXED_ID + b"> ]")
        if len(fixed) == len(m_id.group(0)):
            data = data[: m_id.start()] + fixed + data[m_id.end():]
            replaced["ID"] = True

    # 3. trailer /DocChecksum /<h32> -> fixed 32 hex
    data, n_dc = re.subn(rb"/DocChecksum /[0-9A-Fa-f]{32}",
                         lambda _m: b"/DocChecksum /" + PDF_NORM_FIXED_DOCCHECKSUM, data)
    replaced["DocChecksum"] = n_dc > 0

    if len(data) != len(original):
        # A same-length invariant was broken somewhere — never ship that.
        return {"status": "fallback",
                "reason": "normalization changed the total byte length; original kept",
                "fields": replaced, "page_count": None}

    # ── corruption canary / validation (any failure -> fallback) ──
    reasons = []
    pypdf_lib = _import_pypdf()
    page_before = page_after = None
    if pypdf_lib is None:
        reasons.append("pypdf not importable; the normalized file got a structural "
                       "(length/sample) check only")
    else:
        try:
            page_before = len(pypdf_lib.PdfReader(io.BytesIO(original)).pages)
        except Exception as exc:  # noqa: BLE001
            reasons.append(f"pypdf could not parse the pre-normalization file: {str(exc)[:100]}")
        try:
            page_after = len(pypdf_lib.PdfReader(io.BytesIO(data)).pages)
        except Exception as exc:  # noqa: BLE001
            reasons.append(f"pypdf could not parse the normalized file: {str(exc)[:100]}")
            page_after = None
        if page_before is not None and page_after is not None and page_after != page_before:
            reasons.append(f"page count changed after normalization: {page_before} -> {page_after}")

    sample_ok = False
    tmp = pdf_path.with_name(pdf_path.name + ".detnorm.tmp")
    txt = tmp.with_suffix(".txt")
    try:
        tmp.write_bytes(data)
        r = subprocess.run(["pdftotext", str(tmp), str(txt)], capture_output=True, text=True, timeout=30)
        text = ""
        if r.returncode == 0 and txt.exists():
            text = txt.read_text(encoding="utf-8", errors="replace")
        sample_ok = r.returncode == 0 and text.strip() != ""
        if not sample_ok:
            reasons.append("pdftotext on the normalized bytes returned empty/err output")
    except (subprocess.TimeoutExpired, OSError) as exc:
        sample_ok = False
        reasons.append(f"pdftotext could not run: {str(exc)[:100]}")
    finally:
        for _p in (tmp, txt):
            try:
                _p.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass

    if reasons:
        # Keep the unnormalized original; the caller records the limitation.
        try:
            pdf_path.write_bytes(original)
        except OSError as exc:
            return {"status": "fallback",
                    "reason": "; ".join(reasons) + f"; could not restore original: {exc}",
                    "fields": replaced, "page_count": None}
        return {"status": "fallback", "reason": "; ".join(reasons),
                "fields": replaced, "page_count": page_after}

    pdf_path.write_bytes(data)
    return {"status": "normalized", "fields": replaced, "page_count": page_after}


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
            # GC-2026-1113-01: PDF determinism — normalize the LibreOffice
            # wall-clock/random metadata fields BEFORE the sha is recorded, so the
            # shipped PDF (and hence its sha) is deterministic across rebuilds,
            # exactly as the docx already is. Any failure keeps the unnormalized
            # original and records a limitation (never publish a corrupt PDF).
            pdf_norm = _pdf_normalize_deterministic(pdf_path)
            manifest_path = Path(docx_result["manifest_path"])
            pdf_fonts: list[str] = []
            fig_check: dict | None = None
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["formats"].append("pdf")
                manifest["artifacts"].append({"format": "pdf", "path": str(pdf_path.relative_to(dest)), "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16], "size": pdf_path.stat().st_size})
                determinism_block = {
                    "kind": "creationdate_id_docchecksum_same_length",
                    "status": pdf_norm["status"],
                    "fields": pdf_norm.get("fields", {}),
                    "page_count": pdf_norm.get("page_count"),
                    "note": ("same-length byte normalization of CreationDate / /ID / "
                             "/DocChecksum; the normalized PDF sha256 is deterministic "
                             "across rebuilds of the same docx (GC-2026-1113-01)"),
                }
                if pdf_norm.get("reason"):
                    determinism_block["reason"] = pdf_norm["reason"]
                manifest.setdefault("layout", {})["pdf_determinism"] = determinism_block
                if pdf_norm["status"] == "fallback":
                    manifest.setdefault("limitations", []).append(
                        {"kind": "pdf_deterministic_normalization_fallback",
                         "detail": "PDF shipped unnormalized: " + (pdf_norm.get("reason") or "validation failed")})
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
                    _atomic_write_json(manifest_path, manifest)
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
                # The whole manifest is written back — the PF-B7 submission block
                # written by the docx step is preserved as it stands.
                _atomic_write_json(manifest_path, manifest)
                # GC-2026-1113-02: PDF-level figure verification — the raster
                # budget and the non-blank figure slots. A failure is recorded
                # in the manifest BEFORE the build fails (PF-B12: an
                # unverified figure slot must not ship silently), following the
                # font-inventory pattern above.
                fig_refs = docx_result.get("figure_refs") or []
                fig_dir = Path(docx_result.get("figures_dir") or dest)
                fig_check = _verify_pdf_figures(pdf_path, docx_path, fig_refs, fig_dir)
                manifest["layout"].setdefault("figures", {})["pdf"] = fig_check
                if fig_check.get("status") != "pass":
                    manifest.setdefault("limitations", []).append(
                        {"kind": "pdf_figure_verification_failed",
                         "detail": (fig_check.get("error")
                                    or "; ".join(f.get("detail", "") for f in fig_check.get("failures", []))
                                    or "figure verification reported a non-pass status")})
                    _atomic_write_json(manifest_path, manifest)
                    return emit({"status": "error",
                                 "error": ("PDF figure verification failed (PF-B12): "
                                           + (fig_check.get("error")
                                              or "; ".join(f.get("detail", "") for f in fig_check.get("failures", []))
                                              or "see manifest layout.figures.pdf")),
                                 "stage": "pdf-verify", "failures": fig_check.get("failures", []),
                                 "pdf_path": str(pdf_path)}, 1)
                _atomic_write_json(manifest_path, manifest)
            return emit({"status": "ok", "paper_id": dest.name, "format": "pdf", "output_path": str(pdf_path), "manifest_path": str(manifest_path), "pdf_fonts": sorted(set(pdf_fonts)) if pdf_fonts else [], "pdf_determinism": pdf_norm, "figure_assertions": fig_check.get("status") if fig_check else None})
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


# ── package (PF-B15/PF-B16 submission package, GC-2026-1112-03) ─────────

class PackageFailure(Exception):
    """A package failure: reported with a non-zero exit code and details.

    exit_code 1 = a build/assertion failure (the paper or the package is at
    fault); exit_code 2 = a usage or environment failure (the caller is at
    fault) — the same split cmd_check / cmd_build_docx use.
    """
    def __init__(self, error: str, exit_code: int = 1, **details):
        super().__init__(error)
        self.payload = {"status": "error", "error": error}
        self.payload.update(details)
        self.exit_code = exit_code


# Figure types that qualify for the PF-B15 bitmap downgrade. The downgrade is
# limited to photograph-like figures; every other bitmap (or an undecidable
# source) stays redraw_pending, because PF-B15 makes the SVG redraw a hard duty.
PHOTO_TYPES = {"photo", "photos", "photograph", "photographs", "photography",
               "photographic", "照片", "摄影", "写真"}

FIG_STATUS_SVG = "svg_source_registered"
FIG_STATUS_DOWNGRADE = "downgraded_bitmap"
FIG_STATUS_REDRAW = "redraw_pending"

# The counting method of record (G5/T1): a TRUE non-whitespace character
# count, matching the P5 ruling (len(re.sub(r'\s','',text))). The older
# _count_chinese_chars (CJK characters + whitespace-split words) is NOT used
# here; it is kept as a sidecar reference value only.
CHAR_COUNT_METHOD = "非空白字符（len(re.sub(r'\\s','',text))，含标点/数字/字母），与 P5 既有裁定口径一致"


def _resolve_paper_dir(spec: str) -> Path:
    """Resolve --paper to a paper workspace directory.

    Accepts a path, a bare repository directory name, or a bare paper id
    ('P4'). Paper workspaces live outside this repo (papers/ is gitignored).
    """
    if not spec:
        raise PackageFailure("--paper required", exit_code=2)
    cand = Path(spec).expanduser()
    if cand.is_dir():
        return cand.resolve()
    papers_root = PROJECT_ROOT / "papers"
    named = papers_root / spec
    if named.is_dir():
        return named.resolve()
    if papers_root.is_dir():
        hits = [d for d in sorted(papers_root.iterdir())
                if d.is_dir() and (d.name == spec or d.name.startswith(spec + "-"))]
        if len(hits) == 1:
            return hits[0].resolve()
        if len(hits) > 1:
            raise PackageFailure(f"--paper {spec} is ambiguous: {[d.name for d in hits]}", exit_code=2)
    raise PackageFailure(f"Paper directory not found: {spec}", exit_code=2)


def _resolve_package_version(dest: Path, args) -> tuple[str, str]:
    """Return (version, source) with source in {'cli', 'current'}."""
    if getattr(args, "version", None) and getattr(args, "current", False):
        raise PackageFailure("--version and --current are mutually exclusive", exit_code=2)
    if getattr(args, "version", None):
        return _norm_version(args.version), "cli"
    current_file = dest / "build" / "current.json"
    if not current_file.exists():
        raise PackageFailure(f"build/current.json not found: {current_file} (use --version)", exit_code=2)
    try:
        current = json.loads(current_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PackageFailure(f"build/current.json is unreadable: {exc}", exit_code=2)
    version = current.get("paper_version")
    if not version:
        raise PackageFailure("build/current.json carries no paper_version (use --version)", exit_code=2)
    return _norm_version(str(version)), "current"


def _count_nonwhitespace_chars(text: str) -> int:
    """True non-whitespace character count (P5 ruling; PF-RV8 band check)."""
    return len(re.sub(r'\s', '', text or ''))


def _load_yaml_file(path: Path) -> object:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PackageFailure(f"{path} is not valid YAML: {exc}")


def _load_yaml_mapping(path: Path) -> dict:
    """Load a YAML file that must hold a mapping (authors.yaml, writing-spec.yaml)."""
    data = _load_yaml_file(path)
    return data if isinstance(data, dict) else {}


def _markdown_sections(text: str, level: int = 1) -> tuple[list, list]:
    """Return (sections, lines); a section is {'line': idx, 'title': str}."""
    lines = text.splitlines()
    pattern = re.compile(r"^" + "#" * level + r"\s+(\S.*?)\s*$")
    sections = []
    for idx, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            sections.append({"line": idx, "title": m.group(1)})
    return sections, lines


def _strip_pandoc_fences(text: str) -> str:
    """Drop pandoc div fences (':::' / '::: {custom-style=...}')."""
    kept = []
    for line in text.splitlines():
        s = line.strip()
        if s == ":::" or s.startswith("::: {"):
            continue
        kept.append(line)
    return "\n".join(kept)


def _split_md_row(line: str) -> list:
    """Split a markdown table row into cells (honours \\| escapes)."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, buf, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append("".join(buf))
    return [c.strip() for c in cells]


def _is_md_separator(line: str) -> bool:
    s = line.strip()
    if not s.startswith("|"):
        return False
    cells = _split_md_row(s)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells)


def _strip_markdown_bold(text: str) -> str:
    """Remove markdown bold wrappers — formatting marker, not table data."""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


def _package_figures(dest: Path) -> list:
    """Figure delivery plan from figures/index.yaml.

    Only the `filename_svg` field decides the delivery state (T6/G6):
    a registered SVG is packaged as-is (no redraw diff duty — PF-B15 attaches
    the diff duty to a redraw), a photograph-like bitmap may be downgraded
    honestly, every other bitmap or an undecidable source stays
    redraw_pending (PF-B15 redraw duty stays human until O6).
    """
    index_file = dest / "figures" / "index.yaml"
    if not index_file.exists():
        raise PackageFailure(f"figures/index.yaml not found: {index_file}")
    data = _load_yaml_file(index_file)
    entries = None
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        for key in ("figures", "figs", "items"):
            if isinstance(data.get(key), list):
                entries = data[key]
                break
    if entries is None:
        raise PackageFailure(f"figures/index.yaml carries no figure list: {index_file}")
    plans = []
    for i, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        fig_id = str(entry.get("id") or f"fig{i}")
        svg_name = str(entry.get("filename_svg") or "").strip()
        bitmap_name = str(entry.get("filename") or entry.get("filename_png") or "").strip()
        declared_type = entry.get("type") or entry.get("source_type")
        plan = {"index": i, "id": fig_id, "status": None, "packaged_as": None,
                "source": None, "reason": None, "declared_type": declared_type}
        if svg_name:
            svg_path = dest / "figures" / svg_name
            if not svg_path.exists():
                raise PackageFailure(
                    f"figures/index.yaml registers filename_svg for {fig_id} but the file is missing: {svg_path}",
                    figure=fig_id, filename_svg=svg_name)
            plan["status"] = FIG_STATUS_SVG
            plan["packaged_as"] = f"figures/fig{i}.svg"
            plan["source"] = svg_path
            plan["reason"] = "SVG source registered — packaged as-is (same source, no redraw diff duty)"
        elif str(declared_type or "").strip().lower() in PHOTO_TYPES:
            if not bitmap_name:
                raise PackageFailure(
                    f"figures/index.yaml marks {fig_id} as photograph-like but registers no bitmap file name",
                    figure=fig_id)
            bmp_path = dest / "figures" / bitmap_name
            if not bmp_path.exists():
                raise PackageFailure(
                    f"figures/index.yaml marks {fig_id} as photograph-like but the bitmap file is missing: {bmp_path}",
                    figure=fig_id, filename=bitmap_name)
            plan["status"] = FIG_STATUS_DOWNGRADE
            plan["packaged_as"] = f"figures/fig{i}.png"
            plan["source"] = bmp_path
            plan["reason"] = (f"photograph-like figure (type={declared_type}) — PF-B15 allows an honest "
                              f"bitmap downgrade with the reason recorded")
        else:
            plan["status"] = FIG_STATUS_REDRAW
            plan["reason"] = (f"no filename_svg registered; source type '{declared_type or 'undeclared'}' is not "
                              f"photograph-like — PF-B15 requires an SVG redraw (human duty until O6)")
        plans.append(plan)
    return plans


def _package_tables(dest: Path) -> list:
    """Table plan from body/paper.md (the single authoritative body source).

    Pipe tables are enumerated in document order; each block is paired with
    the nearest preceding caption '表 N' (a caption div wins over a plain
    short line, an in-text reference such as '表 3 报告了…' is not a caption).
    A block without a caption is numbered by sequence (PF-B2 / PF-B15).
    """
    body_file = dest / "body" / "paper.md"
    if not body_file.exists():
        raise PackageFailure("single body source missing: body/paper.md (PF-B2)")
    lines = body_file.read_text(encoding="utf-8").splitlines()

    blocks = []
    i = 0
    n = len(lines)
    while i < n - 1:
        s = lines[i].strip()
        if s.startswith("|") and _is_md_separator(lines[i + 1]):
            # form 1: header row opens with a pipe (existing behaviour — unchanged)
            j = i + 2
            while j < n and lines[j].strip().startswith("|"):
                j += 1
            blocks.append({"start": i, "end": j})
            i = j
            continue
        if (not s.startswith("|")) and _is_md_separator(lines[i + 1]):
            # form 2 (pandoc pipe-table semantics): the header row does not open
            # with '|' but the next line is a valid separator row and the header
            # splits into the same number of columns — pandoc renders this as a
            # real <w:tbl> (verified on P3: '分区 | 定位 | 功能说明' / '|---|---|---|').
            header_cells = _split_md_row(s)
            sep_cells = _split_md_row(lines[i + 1])
            if len(header_cells) == len(sep_cells) and len(header_cells) >= 2:
                j = i + 2
                while j < n:
                    row = lines[j].strip()
                    if not row or "|" not in row:
                        break
                    if len(_split_md_row(row)) != len(header_cells):
                        break
                    j += 1
                blocks.append({"start": i, "end": j})
                i = j
                continue
        i += 1

    captions = []
    in_caption_div = False
    for idx, line in enumerate(lines):
        m = re.match(r"^:::\s*\{([^}]*)\}\s*$", line)
        if m:
            in_caption_div = "table caption" in m.group(1).lower()
            continue
        if line.strip() == ":::":
            in_caption_div = False
            continue
        cm = re.match(r"^\s*表\s*(\d+)\s*(.*)$", line)
        if cm:
            stripped = line.strip()
            captions.append({
                "line": idx,
                "number": int(cm.group(1)),
                "text": stripped,
                "strong": in_caption_div,
                "weak": (not stripped.endswith("。")) and len(stripped) <= 60,
            })

    tables = []
    for bi, block in enumerate(blocks):
        floor = blocks[bi - 1]["start"] if bi else 0
        limit = max(floor, block["start"] - 40)
        in_window = [c for c in captions if limit <= c["line"] < block["start"]]
        strong = [c for c in in_window if c["strong"]]
        weak = [c for c in in_window if c["weak"]]
        picked = None
        if strong:
            picked = max(strong, key=lambda c: c["line"])
        elif weak:
            picked = max(weak, key=lambda c: c["line"])
        header = _split_md_row(lines[block["start"]])
        rows = []
        for r in range(block["start"] + 2, block["end"]):
            cells = _split_md_row(lines[r])
            if len(cells) != len(header):
                raise PackageFailure(
                    f"markdown table parse failed at body/paper.md:{r + 1} — "
                    f"{len(cells)} cells against a {len(header)}-column header",
                    line=r + 1, table_start_line=block["start"] + 1)
            rows.append(cells)
        tables.append({
            "number": picked["number"] if picked else None,
            "caption": picked["text"] if picked else None,
            "header": header,
            "rows": rows,
            "source_line": block["start"] + 1,
        })

    used = set()
    for t in tables:
        if t["number"] is not None:
            if t["number"] in used:
                raise PackageFailure(
                    f"duplicate table number 表 {t['number']} in body/paper.md "
                    f"(captions must be unique)", line=t["source_line"])
            used.add(t["number"])
    nxt = 1
    for t in tables:
        if t["number"] is not None:
            continue
        while nxt in used:
            nxt += 1
        t["number"] = nxt
        used.add(nxt)
    for t in tables:
        t["packaged_as"] = f"tables/tab{t['number']}.csv"
    return tables


def _package_body(dest: Path, spec: dict) -> dict:
    """Body ranges and the conclusion text of body/paper.md."""
    body_file = dest / "body" / "paper.md"
    if not body_file.exists():
        raise PackageFailure("single body source missing: body/paper.md (PF-B2)")
    text = body_file.read_text(encoding="utf-8")
    sections, lines = _markdown_sections(text, 1)
    heading = str(spec.get("conclusion_heading") or "").strip()
    if not heading:
        raise PackageFailure(
            "writing-spec.yaml carries no conclusion_heading — the conclusion anchor is required (S12)",
            conclusion_heading=None)
    hit = next((s for s in sections if heading in s["title"]), None)
    if hit is None:
        raise PackageFailure(
            f"conclusion heading not found in body/paper.md: "
            f"writing-spec.conclusion_heading='{heading}' (S12 — the body conclusion heading must align "
            f"with the writing spec; the review line adjudicates the content level)",
            conclusion_heading=heading,
            h1_titles=[s["title"] for s in sections])
    conclusion_end = len(lines)
    for s in sections:
        if s["line"] > hit["line"]:
            conclusion_end = s["line"]
            break
    conclusion = _strip_pandoc_fences("\n".join(lines[hit["line"]:conclusion_end])).strip()
    start = None
    for s in sections:
        if re.match(r"^\d+[\s.、]", s["title"]):
            start = s["line"]
            break
    if start is None:
        raise PackageFailure(
            "body/paper.md carries no numbered chapter heading ('# 1 …') — the body range cannot be located")
    body_text = "\n".join(lines[start:conclusion_end])
    ref_start = ref_end = None
    for s in sections:
        if "参考文献" in s["title"]:
            ref_start = s["line"]
            for t in sections:
                if t["line"] > ref_start:
                    ref_end = t["line"]
                    break
            break
    ref_text = ""
    if ref_start is not None:
        ref_text = "\n".join(lines[ref_start:(ref_end if ref_end is not None else len(lines))])
    return {
        "body_text": body_text,
        "conclusion": conclusion,
        "references_text": ref_text,
        "body_range": [start + 1, conclusion_end],
        "conclusion_range": [hit["line"] + 1, conclusion_end],
        "references_range": [ref_start + 1, ref_end] if ref_start is not None else None,
    }


def _extract_abstract(dest: Path, spec: dict) -> tuple[str, list, str, list, bool, list]:
    """(zh abstract text, zh keywords, en abstract text, en keywords,
    english abstract present, field errors)."""
    path = dest / "abstract.md"
    if not path.exists():
        raise PackageFailure(f"abstract.md not found: {path}")
    text = path.read_text(encoding="utf-8")
    sections, lines = _markdown_sections(text, 2)
    zh = next((s for s in sections if "中文摘要" in s["title"]), None)
    if zh is None:
        zh = next((s for s in sections if "摘要" in s["title"]), None)
    errors = []
    abstract_text = ""
    keywords = []
    if zh is None:
        errors.append("abstract_zh: no '## 中文摘要' section in abstract.md")
    else:
        end = len(lines)
        for s in sections:
            if s["line"] > zh["line"]:
                end = s["line"]
                break
        body_lines = lines[zh["line"] + 1:end]
        sep = str(spec.get("keywords_separator") or "；")
        kw_line = None
        keep = []
        for line in body_lines:
            if re.match(r"^\s*\**\s*(关键词|Keywords)\s*\**\s*[：:]", line):
                kw_line = line
                continue
            keep.append(line)
        abstract_text = "\n".join(keep).strip()
        if kw_line is None:
            errors.append("keywords_zh: no '关键词：' line in the Chinese abstract section")
        else:
            raw = re.sub(r"^\s*\**\s*(关键词|Keywords)\s*\**\s*[：:]\s*", "", kw_line).strip()
            parts = [p.strip() for p in raw.split(sep)] if sep in raw else [p.strip() for p in raw.split("；")]
            keywords = [p for p in parts if p]
            if not keywords:
                errors.append("keywords_zh: the keyword line parsed to an empty list")
    en_present = bool(re.search(r"^#{1,6}\s+.*english.*abstract", text, re.IGNORECASE | re.MULTILINE)) \
        or bool(re.search(r"\*{0,2}Keywords\*{0,2}\s*[：:]", text))
    # English abstract full text + English keyword list. Consumed from the
    # canonical renderer (metalayout._parse_abstract — the same function that
    # feeds the docx front matter), so the manifest's abstract_en/keywords_en
    # match what is actually rendered. Its keyword regex is the P2-2 hardened
    # form: case-insensitive and tolerant of the `Key words` variant
    # (metalayout._EN_KW_FULL). A missing/empty English section returns empty
    # and records a gap (DD-2 per-field boundary) — never breaks the build.
    abstract_en_text = ""
    keywords_en: list = []
    try:
        eng = metalayout._parse_abstract(dest) if metalayout is not None else {}
    except Exception as exc:  # noqa: BLE001 - a broken en section is a gap, not a crash
        errors.append(f"abstract_en: English abstract could not be extracted ({exc})")
        eng = {}
    if isinstance(eng, dict):
        abstract_en_text = (eng.get("en") or "").strip()
        keywords_en = [k for k in (eng.get("keywords_en") or []) if k]
        if not eng.get("en_section_present"):
            errors.append("abstract_en: no '## English Abstract' section in abstract.md")
        else:
            if not abstract_en_text:
                errors.append("abstract_en: the English Abstract section is empty")
            if not keywords_en:
                errors.append("keywords_en: no English keyword list parsed in the English Abstract section")
    return abstract_text, keywords, abstract_en_text, keywords_en, en_present, errors


def _label_value(text: str, *labels: str):
    for lab in labels:
        m = re.search(re.escape(lab) + r"\s*[：:]\s*([^。；;\n]+)", text)
        if m:
            return m.group(1).strip()
    return None


def _parse_bio_paragraph(text: str) -> dict:
    """Best-effort parse of one author biography paragraph (ten fields)."""
    head = re.match(
        r"^\s*([^\s，,（(]{2,12})\s*[，,]\s*(\d{4})\s*[—\-–~至]*\s*[，,]\s*([男女])\s*[，,]\s*"
        r"([^，,]{2,15}?人)\s*[，,]\s*([^，,。]{2,12}?)\s*[，,]\s*([^，,。]{2,14})", text)
    alt = re.match(r"^\s*([^\s，,（(]{2,12})\s*[（(]\s*(\d{4})\s*[—\-–~至]*\s*[）)]", text)
    if head:
        name, birth, gender, origin, degree, title = head.groups()
    elif alt:
        name, birth = alt.group(1), alt.group(2)
        gender = origin = degree = title = None
    else:
        return {}
    fields = {
        "出生年": birth,
        "性别": gender,
        "籍贯": origin[:-1] if origin else None,
        "学位": degree,
        "职称": title,
        "研究方向": _label_value(text, "研究方向"),
        "通信地址": _label_value(text, "通信地址"),
        "邮政编码": _label_value(text, "邮编", "邮政编码"),
        "电子邮箱": _label_value(text, "电子邮箱"),
        "电话": _label_value(text, "电话"),
    }
    missing = [k for k, v in fields.items() if not v]
    return {"name": name, "fields": fields, "missing": missing}


def _parse_author_bios(dest: Path) -> dict:
    """Structured biographies parsed from body/paper.md#作者简介 (O4 source)."""
    body_file = dest / "body" / "paper.md"
    if not body_file.exists():
        return {}
    text = body_file.read_text(encoding="utf-8")
    sections, lines = _markdown_sections(text, 1)
    sec = next((s for s in sections if "作者简介" in s["title"]), None)
    if sec is None:
        return {}
    end = len(lines)
    for s in sections:
        if s["line"] > sec["line"]:
            end = s["line"]
            break
    raw = _strip_pandoc_fences("\n".join(lines[sec["line"]:end]))
    bios = {}
    for para in re.split(r"\n\s*\n", raw):
        para = para.strip()
        if not para:
            continue
        bio = _parse_bio_paragraph(para)
        if bio:
            bios[bio["name"]] = bio
    return bios


def _package_authors(dest: Path, paper_cfg: dict) -> tuple[list, dict, list]:
    """Authors (name/affiliations/roles/email/corresponding/bio) + bio source.

    GC-2026-1112-06: the bio now comes from the authors.yaml document-level bio
    block (joined by author_id) — the body/paper.md「作者简介」section is gone in
    the metadata-driven build. name/roles/corresponding field semantics are
    unchanged; bio values stay strings (birth_year is cast) so the A3 comparison
    and the manifest shape are unchanged.
    """
    authors = paper_cfg.get("authors") or []
    if not authors:
        authors = _load_yaml_mapping(dest / "authors.yaml").get("authors") or []
    try:
        reg_doc = _load_yaml_file(dest / "authors.yaml")
    except Exception:  # noqa: BLE001 - a broken authors.yaml is a gap, not a crash
        reg_doc = {}
    reg_by_id: dict = {}
    if isinstance(reg_doc, dict):
        for e in reg_doc.get("authors") or []:
            if isinstance(e, dict) and e.get("id"):
                reg_by_id[e["id"]] = e
    _BIO_KEYMAP = {
        "birth_year": "出生年", "gender": "性别", "hometown": "籍贯",
        "degree": "学位", "title": "职称", "research_direction": "研究方向",
        "address": "通信地址", "postcode": "邮政编码", "email": "电子邮箱",
        "phone": "电话",
    }
    entries = []
    gaps = []
    for a in authors:
        if not isinstance(a, dict):
            continue
        roles = list(a.get("roles") or [])
        name = a.get("name")
        reg = reg_by_id.get(a.get("author_id") or a.get("id")) or {}
        raw_bio = reg.get("bio") if isinstance(reg.get("bio"), dict) else {}
        bio_fields = {}
        for key, value in raw_bio.items():
            if key not in _BIO_KEYMAP or value in (None, ""):
                continue
            field = _BIO_KEYMAP[key]
            bio_fields[field] = str(value) if key == "birth_year" else value
        missing = [f for f in _BIO_KEYMAP.values() if f not in bio_fields]
        if not raw_bio:
            gaps.append({
                "kind": "author_bio_missing",
                "author": name,
                "detail": "no bio block for this author (authors.yaml has no bio)",
                "open_item": "O4",
            })
        elif missing:
            gaps.append({
                "kind": "author_bio_incomplete",
                "author": name,
                "missing_fields": missing,
                "detail": "authors.yaml bio lacks some of the ten S17 fields",
                "open_item": "O4",
            })
        entries.append({
            "name": name,
            "affiliations": list(a.get("affiliations") or reg.get("affiliations") or []),
            "roles": roles,
            "email": a.get("email"),
            "corresponding": bool(a.get("corresponding")) or ("corresponding" in roles),
            "bio": bio_fields or None,
        })
    bios = {e["name"]: {"fields": e["bio"], "missing": []} for e in entries if e.get("bio")}
    return entries, bios, gaps


def _package_direction(spec: dict) -> tuple[str | None, dict, list, list]:
    """Submission direction + the verbatim-list membership check."""
    gaps, notes = [], []
    raw = spec.get("submission_direction")
    direction = raw.strip() if isinstance(raw, str) and raw.strip() else None
    cfp = spec.get("cfp_directions")
    candidates = []
    if isinstance(cfp, dict):
        for key in ("columns", "special_issue_directions", "long_term_scope"):
            value = cfp.get(key)
            if isinstance(value, list):
                candidates += [str(x).strip() for x in value if str(x).strip()]
        if cfp.get("special_issue_theme"):
            candidates.append(str(cfp["special_issue_theme"]).strip())
    elif isinstance(cfp, list):
        candidates += [str(x).strip() for x in cfp if str(x).strip()]
    check = {"registered_items": len(candidates), "matched_item": None, "exact": False}
    if direction is None:
        gaps.append({
            "kind": "submission_direction_missing",
            "detail": "writing-spec.yaml carries no submission_direction (PF-B16 allows null + a logged gap)",
        })
        return None, check, gaps, notes
    matched = next((c for c in candidates if c and (direction == c or c in direction)), None)
    if matched is None:
        gaps.append({
            "kind": "submission_direction_not_verbatim_item",
            "detail": "submission_direction quotes no verbatim item of writing-spec.cfp_directions "
                      "(PF-B16 forbids self-invented directions)",
            "value": direction,
        })
    else:
        check["matched_item"] = matched
        check["exact"] = (direction == matched)
        if not check["exact"]:
            notes.append({
                "kind": "submission_direction_carries_annotation",
                "detail": "the registered direction quotes a verbatim list item plus a pending annotation",
                "matched_item": matched,
            })
    return direction, check, gaps, notes


def _build_submission_block(dest: Path, paper_cfg: dict, release_title: str) -> tuple[dict, list[str]]:
    """PF-B7 release manifest submission metadata set (GC-2026-1112-04).

    Every field is extracted on its own: an extraction failure nulls THAT field,
    records a gap and emits a warning line — the build is never interrupted
    (DD-2). The package path is the strict twin of this block (A3 compares them
    field by field), so both read the same sources the same way.
    """
    gaps: list[dict] = []
    warnings: list[str] = []

    def note(kind: str, field: str, detail: str, **extra):
        gaps.append({"kind": kind, "field": field, "detail": detail, **extra})
        warnings.append(f"submission.{field}: {detail}")

    # ── the writing spec carries the anchors (conclusion heading, direction) ──
    spec: dict = {}
    try:
        spec = _load_yaml_mapping(dest / "writing-spec.yaml")
    except Exception as exc:  # noqa: BLE001 - a broken spec is a gap, not a build failure
        note("writing_spec_unreadable", "writing_spec",
             f"writing-spec.yaml could not be loaded ({exc}); the conclusion anchor and the "
             f"submission direction are unavailable")

    # ── abstract / keywords / English-abstract presence ──
    abstract_zh = None
    keywords_zh = None
    abstract_en = None
    keywords_en = None
    abstract_en_present = None
    try:
        text, keywords, en_text, en_keywords, en_present, field_errors = _extract_abstract(dest, spec)
        abstract_zh = text or None
        keywords_zh = keywords or None
        abstract_en = en_text or None
        keywords_en = en_keywords or None
        abstract_en_present = bool(en_present)
        if abstract_zh is None:
            note("abstract_zh_missing", "abstract_zh", "the Chinese abstract is empty")
        if keywords_zh is None:
            note("keywords_zh_missing", "keywords_zh", "no keyword list was parsed")
        if abstract_en is None:
            note("abstract_en_missing", "abstract_en", "the English abstract is empty")
        if keywords_en is None:
            note("keywords_en_missing", "keywords_en", "no English keyword list was parsed")
        for err in field_errors:
            err_field, _, err_detail = str(err).partition(": ")
            note("abstract_field_error", err_field or "abstract_zh", err_detail or str(err))
    except Exception as exc:  # noqa: BLE001
        note("abstract_extraction_failed", "abstract_zh",
             f"the Chinese abstract could not be extracted ({exc})")

    # ── authors (name/affiliations/roles/email/corresponding/bio) ──
    authors = None
    bio_gaps: list[dict] = []
    try:
        entries, _bios, bio_gaps = _package_authors(dest, paper_cfg)
        authors = entries or None
        if authors is None:
            note("authors_missing", "authors", "no author is registered")
        for g in bio_gaps:
            gap = dict(g)
            gap.setdefault("field", "authors")
            gaps.append(gap)
            warnings.append(f"submission.authors: {gap.get('kind')} — {gap.get('detail')}")
    except Exception as exc:  # noqa: BLE001
        note("authors_extraction_failed", "authors",
             f"the author list could not be extracted ({exc})")

    # ── body range, conclusion and the character counts ──
    conclusion = None
    body_chars_value = None
    total_chars_value = None
    components = {"abstract_zh": None, "body": None, "references": None, "total": None}
    try:
        body = _package_body(dest, spec)
        conclusion = body["conclusion"] or None
        if conclusion is None:
            note("conclusion_missing", "conclusion", "the conclusion range is empty")
        body_chars_value = _count_nonwhitespace_chars(body["body_text"])
        refs_chars = _count_nonwhitespace_chars(body["references_text"])
        abstract_chars = _count_nonwhitespace_chars(abstract_zh or "")
        total_chars_value = abstract_chars + body_chars_value + refs_chars
        components = {"abstract_zh": abstract_chars, "body": body_chars_value,
                      "references": refs_chars, "total": total_chars_value}
    except Exception as exc:  # noqa: BLE001
        note("body_extraction_failed", "conclusion",
             f"the body range / conclusion could not be extracted ({exc})")

    # ── submission direction (PF-B16: a verbatim item of the registered list) ──
    direction = None
    direction_check = None
    try:
        direction, direction_check, dir_gaps, _dir_notes = _package_direction(spec)
        for g in dir_gaps:
            gap = dict(g)
            gap.setdefault("field", "submission_direction")
            gaps.append(gap)
            warnings.append(f"submission.submission_direction: {gap.get('detail')}")
    except Exception as exc:  # noqa: BLE001
        note("direction_extraction_failed", "submission_direction",
             f"the submission direction could not be extracted ({exc})")

    # ── the character-count band (writing-spec min/max; INFO level, PF-RV8) ──
    min_chars = spec.get("min_chars")
    max_chars = spec.get("max_chars")
    band = {"min_chars": min_chars, "max_chars": max_chars, "level": "INFO", "status": "unknown"}
    if isinstance(min_chars, int) and isinstance(max_chars, int) and body_chars_value is not None:
        if body_chars_value < min_chars:
            band["status"] = "below_min"
        elif body_chars_value > max_chars:
            band["status"] = "above_max"
        else:
            band["status"] = "in_band"
    counting_note = (f"{CHAR_COUNT_METHOD}；total = 摘要 + 正文 + 参考文献；"
                     f"正文带宽 {min_chars}–{max_chars} 字（writing-spec；INFO 级，裁定权在 PF-RV8）")

    block = {
        "title": release_title,
        "title_en": paper_cfg.get("title_en"),
        "abstract_zh": abstract_zh,
        "abstract_en": abstract_en,
        "abstract_en_present": abstract_en_present,
        "keywords_zh": keywords_zh,
        "keywords_en": keywords_en,
        "authors": authors,
        "bio_gaps": bio_gaps,
        "conclusion": conclusion,
        "body_chars": {"value": body_chars_value, "methodology": CHAR_COUNT_METHOD,
                       "components": dict(components), "band": band},
        "total_chars": {"value": total_chars_value, "methodology": CHAR_COUNT_METHOD,
                        "components": dict(components)},
        "submission_direction": direction,
        "submission_direction_check": direction_check,
        "counting_note": counting_note,
        "submission_gaps": gaps,
        "package_manifest_sha256": None,
        "package_status": "not_assembled",
    }
    return block, warnings


def _find_release_artifact(build_dir: Path, suffix: str, preferred_stem: str) -> Path:
    candidates = sorted(p for p in build_dir.glob(f"*{suffix}") if p.is_file())
    if not candidates:
        raise PackageFailure(f"no {suffix} artifact in {build_dir} (build the release first)")
    if f"{preferred_stem}{suffix}" in [c.name for c in candidates]:
        return build_dir / f"{preferred_stem}{suffix}"
    if len(candidates) == 1:
        return candidates[0]
    raise PackageFailure(f"ambiguous {suffix} artifacts in {build_dir}: {[c.name for c in candidates]}")


def _package_plan(dest: Path, version: str) -> dict:
    """Compute the whole package plan (expected skeleton + manifest content)."""
    try:
        paper_cfg = _load_paper_yaml(dest)
    except Exception as exc:
        raise PackageFailure(f"paper.yaml is unreadable: {exc}")
    if not paper_cfg:
        raise PackageFailure(f"paper.yaml not found or empty: {dest / 'paper.yaml'}")
    spec = _load_yaml_mapping(dest / "writing-spec.yaml")

    title = str(paper_cfg.get("title") or "").strip()
    if not title:
        raise PackageFailure("paper.yaml carries no title")
    first_author = _first_author_name(dest, paper_cfg)
    if not first_author:
        raise PackageFailure("no first author found — paper.yaml/authors.yaml must register roles containing 'first'")
    stem = _release_file_stem(title, first_author)

    build_dir = dest / "build" / version
    if not build_dir.is_dir():
        raise PackageFailure(f"build directory not found: {build_dir}")
    docx_source = _find_release_artifact(build_dir, ".docx", stem)
    pdf_source = _find_release_artifact(build_dir, ".pdf", stem)

    release_manifest_path = build_dir / "manifest.json"
    if not release_manifest_path.exists():
        raise PackageFailure(f"release manifest not found: {release_manifest_path}")
    try:
        release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PackageFailure(f"release manifest is unreadable: {exc}")

    body = _package_body(dest, spec)
    (abstract_zh, keywords, abstract_en, keywords_en,
     abstract_en_present, field_errors) = _extract_abstract(dest, spec)
    authors, bios, bio_gaps = _package_authors(dest, paper_cfg)
    direction, direction_check, direction_gaps, direction_notes = _package_direction(spec)
    figures = _package_figures(dest)
    tables = _package_tables(dest)

    body_chars = _count_nonwhitespace_chars(body["body_text"])
    refs_chars = _count_nonwhitespace_chars(body["references_text"])
    abstract_chars = _count_nonwhitespace_chars(abstract_zh)
    total_chars = abstract_chars + body_chars + refs_chars

    gaps = list(bio_gaps) + list(direction_gaps)
    notes = list(direction_notes)
    if not authors:
        field_errors.append("authors: no author registered")
    if not abstract_zh:
        field_errors.append("abstract_zh: empty Chinese abstract")
    if body_chars <= 0:
        field_errors.append("body_chars: the body range is empty")
    if total_chars <= 0:
        field_errors.append("total_chars: the counted text is empty")

    downgrades = []
    redraw_pending = []
    for f in figures:
        if f["status"] == FIG_STATUS_DOWNGRADE:
            downgrades.append({
                "figure": f["id"],
                "packaged_as": f["packaged_as"],
                "reason_category": "photograph_like",
                "reason": f["reason"],
                "source": str(f["source"].relative_to(dest)) if f["source"] else None,
                "source_sha256": hashlib.sha256(f["source"].read_bytes()).hexdigest() if f["source"] else None,
            })
        elif f["status"] == FIG_STATUS_REDRAW:
            redraw_pending.append({
                "figure": f["id"],
                "packaged_as": None,
                "reason": f["reason"],
                "declared_type": f["declared_type"],
                "source": str(f["source"].relative_to(dest)) if f["source"] else None,
            })
            gaps.append({
                "kind": "figure_redraw_pending",
                "figure": f["id"],
                "detail": f["reason"],
                "open_item": "O6",
            })

    min_chars = spec.get("min_chars")
    max_chars = spec.get("max_chars")
    bandwidth = {"min_chars": min_chars, "max_chars": max_chars, "body_chars": body_chars, "level": "INFO"}
    if isinstance(min_chars, int) and body_chars < min_chars:
        bandwidth["status"] = "below_min"
    elif isinstance(max_chars, int) and body_chars > max_chars:
        bandwidth["status"] = "above_max"
    else:
        bandwidth["status"] = "in_band"

    manifest = {
        "package_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "title_en": paper_cfg.get("title_en"),
        "abstract_zh": abstract_zh,
        "abstract_en": abstract_en or None,
        "abstract_en_present": abstract_en_present,
        "keywords_zh": keywords,
        "keywords_en": keywords_en or None,
        "authors": authors,
        "conclusion": body["conclusion"],
        "total_chars": total_chars,
        "body_chars": body_chars,
        "submission_direction": direction,
        "char_count_methodology": CHAR_COUNT_METHOD,
        "char_count_components": {
            "abstract_zh": abstract_chars,
            "body": body_chars,
            "references": refs_chars,
            "total": total_chars,
        },
        "figures": {
            "count": len(figures),
            "items": [{"id": f["id"], "packaged_as": f["packaged_as"], "status": f["status"]} for f in figures],
        },
        "tables": {
            "count": len(tables),
            "items": [{"number": t["number"], "packaged_as": t["packaged_as"], "caption": t["caption"]} for t in tables],
        },
        "downgrades": [
            {"figure": d["figure"], "packaged_as": d["packaged_as"],
             "reason_category": d["reason_category"], "reason": d["reason"]}
            for d in downgrades
        ],
    }

    sidecar = {
        "paper_id": dest.name,
        "paper_version": version,
        "generated_at": manifest["generated_at"],
        "gaps": gaps,
        "downgrades": downgrades,
        "redraw_pending": redraw_pending,
        "notes": notes,
        "field_errors": field_errors,
        "char_count_bandwidth": bandwidth,
        "char_count_reference": {
            "method": "_count_chinese_chars (CJK characters + whitespace-split words) — writing-status legacy metric",
            "body": _count_chinese_chars(body["body_text"]),
            "references": _count_chinese_chars(body["references_text"]),
            "abstract_zh": _count_chinese_chars(abstract_zh),
            "total": _count_chinese_chars(body["body_text"]) + _count_chinese_chars(body["references_text"])
                     + _count_chinese_chars(abstract_zh),
        },
        "char_count_methodology": CHAR_COUNT_METHOD,
        "source_manifest": {
            "path": str(release_manifest_path.relative_to(dest)),
            "release_id": release_manifest.get("release_id"),
            "paper_title": release_manifest.get("paper_title"),
            "paper_version": release_manifest.get("paper_version"),
        },
        "author_bio_source": "authors.yaml#authors[].bio (GC-2026-1112-06)" if bios else None,
        "tables_source": [
            {"number": t["number"], "caption": t["caption"], "source_location": f"body/paper.md:{t['source_line']}"}
            for t in tables
        ],
    }

    return {
        "version": version,
        "stem": stem,
        "docx_name": f"{stem}.docx",
        "pdf_name": f"{stem}.pdf",
        "docx_source": docx_source,
        "pdf_source": pdf_source,
        "build_dir": build_dir,
        "package_dir": build_dir / "package",
        "sidecar_path": build_dir / "package-gaps.json",
        "release_manifest": release_manifest,
        "figures": figures,
        "tables": tables,
        "manifest": manifest,
        "sidecar": sidecar,
        "gaps": gaps,
        "notes": notes,
        "field_errors": field_errors,
        "downgrades": downgrades,
        "redraw_pending": redraw_pending,
        "bandwidth": bandwidth,
        "char_counts": {
            "total_chars": total_chars,
            "body_chars": body_chars,
            "abstract_zh_chars": abstract_chars,
            "references_chars": refs_chars,
        },
        "body_ranges": {
            "body": body["body_range"],
            "conclusion": body["conclusion_range"],
            "references": body["references_range"],
        },
    }


def _norm_cmp_text(value):
    """Comparison normalisation: a text field compares after strip()."""
    return value.strip() if isinstance(value, str) else value


def _norm_cmp_list(value):
    """Comparison normalisation: a list of strings compares after strip() each."""
    if not isinstance(value, list):
        return value
    return [v.strip() if isinstance(v, str) else v for v in value]


def _norm_cmp_bio(value):
    """Comparison normalisation: a biography field map compares after strip()."""
    if not isinstance(value, dict):
        return value
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in value.items()}


def _norm_cmp_authors(authors):
    """The A3 author comparison sub-domain (G-7): name + roles + corresponding + bio.

    The affiliation and the e-mail are recorded but not compared — they belong
    to the author registration, not to the release/package shared set.
    """
    if not isinstance(authors, list):
        return authors
    out = []
    for a in authors:
        if not isinstance(a, dict):
            out.append(a)
            continue
        out.append({
            "name": _norm_cmp_text(a.get("name")),
            "roles": _norm_cmp_list(a.get("roles")),
            "corresponding": bool(a.get("corresponding")),
            "bio": _norm_cmp_bio(a.get("bio")),
        })
    return out


def _norm_cmp_chars(value):
    """The A3 character-count comparison value (the submission block nests it)."""
    if isinstance(value, dict):
        return value.get("value")
    return value


def _compare_submission_block(submission: dict, manifest: dict) -> list[dict]:
    """PF-B7 shared-field equality between the release submission block and the
    package manifest (A3 extension, GC-2026-1112-04).

    The compared set is fixed: title, title_en, abstract_zh, abstract_en,
    keywords_zh, keywords_en, the authors sub-domain, conclusion, body_chars.value,
    total_chars.value and submission_direction. Every comparison is made on the
    normalised value.
    """
    diffs: list[dict] = []

    def cmp(field, left, right):
        if left != right:
            diffs.append({"field": field, "release_manifest": left, "package_manifest": right})

    cmp("title", _norm_cmp_text(submission.get("title")), _norm_cmp_text(manifest.get("title")))
    cmp("title_en", _norm_cmp_text(submission.get("title_en")), _norm_cmp_text(manifest.get("title_en")))
    cmp("abstract_zh", _norm_cmp_text(submission.get("abstract_zh")),
        _norm_cmp_text(manifest.get("abstract_zh")))
    cmp("abstract_en", _norm_cmp_text(submission.get("abstract_en")),
        _norm_cmp_text(manifest.get("abstract_en")))
    cmp("keywords_zh", _norm_cmp_list(submission.get("keywords_zh")),
        _norm_cmp_list(manifest.get("keywords_zh")))
    cmp("keywords_en", _norm_cmp_list(submission.get("keywords_en")),
        _norm_cmp_list(manifest.get("keywords_en")))
    cmp("authors", _norm_cmp_authors(submission.get("authors")),
        _norm_cmp_authors(manifest.get("authors")))
    cmp("conclusion", _norm_cmp_text(submission.get("conclusion")),
        _norm_cmp_text(manifest.get("conclusion")))
    cmp("body_chars", _norm_cmp_chars(submission.get("body_chars")), manifest.get("body_chars"))
    cmp("total_chars", _norm_cmp_chars(submission.get("total_chars")), manifest.get("total_chars"))
    cmp("submission_direction", _norm_cmp_text(submission.get("submission_direction")),
        _norm_cmp_text(manifest.get("submission_direction")))
    return diffs


def _materialize_package(plan: dict) -> None:
    """Rebuild the package root from scratch (PF-B16 skeleton)."""
    import shutil
    package_dir = plan["package_dir"]
    resolved = package_dir.resolve()
    if resolved.name != "package" or resolved.parent != plan["build_dir"].resolve():
        raise PackageFailure(f"refusing to clear a non-package path: {resolved}")
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True)
    (package_dir / "figures").mkdir()
    (package_dir / "tables").mkdir()
    shutil.copy2(plan["docx_source"], package_dir / plan["docx_name"])
    shutil.copy2(plan["pdf_source"], package_dir / plan["pdf_name"])
    for f in plan["figures"]:
        if f["status"] == FIG_STATUS_REDRAW or not f["source"]:
            continue
        suffix = ".png" if f["status"] == FIG_STATUS_DOWNGRADE else ".svg"
        shutil.copy2(f["source"], package_dir / "figures" / f"fig{f['index']}{suffix}")
    import csv
    for t in plan["tables"]:
        out = package_dir / "tables" / f"tab{t['number']}.csv"
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow([_strip_markdown_bold(c) for c in t["header"]])
            for row in t["rows"]:
                writer.writerow([_strip_markdown_bold(c) for c in row])
    (package_dir / "manifest.json").write_text(
        json.dumps(plan["manifest"], ensure_ascii=False, indent=2), encoding="utf-8")
    plan["sidecar_path"].write_text(
        json.dumps(plan["sidecar"], ensure_ascii=False, indent=2), encoding="utf-8")


def _count_docx_tables(docx_path: Path) -> int:
    """Ground-truth table count from a docx: the number of <w:tbl> in the body.

    A docx is a zip. The count is taken from the DECOMPRESSED 'word/document.xml'
    (a raw byte search on the still-compressed archive can silently miss or
    under-count — the same trap verify_layout.py documents at its line ~293).
    Start tags are matched with a delimiter look-ahead so that the 'tbl' prefixed
    non-container elements (<w:tblPr>, <w:tblGrid>, <w:tblBorders>) are excluded.
    Raises PackageFailure when the file or the main document part is unreadable.
    """
    try:
        with zipfile.ZipFile(docx_path) as zf:
            raw = zf.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        raise PackageFailure(f"cannot read word/document.xml from {docx_path}: {exc}") from exc
    xml_text = raw.decode("utf-8", errors="replace")
    return len(re.findall(r"<w:tbl(?=[\s/>])", xml_text))


def _package_assertions(plan: dict, manifest: dict) -> list:
    """A1-A5 — the PF-B16/PF-B7 cross-checks (PF-B15/B16 enforcement point)."""
    package_dir = plan["package_dir"]
    results = []

    missing = []
    for rel in (plan["docx_name"], plan["pdf_name"], "manifest.json"):
        if not (package_dir / rel).exists():
            missing.append(rel)
    for sub in ("figures", "tables"):
        if not (package_dir / sub).is_dir():
            missing.append(sub + "/")
    results.append({"id": "A1", "name": "package skeleton complete (5 items)",
                    "status": "pass" if not missing else "fail", "missing": missing})

    empty = []
    if not manifest.get("title"):
        empty.append("title")
    if not manifest.get("authors"):
        empty.append("authors")
    if not manifest.get("abstract_zh"):
        empty.append("abstract_zh")
    if not manifest.get("keywords_zh"):
        empty.append("keywords_zh")
    if not manifest.get("conclusion"):
        empty.append("conclusion")
    if not (manifest.get("body_chars") or 0) > 0:
        empty.append("body_chars")
    if not (manifest.get("total_chars") or 0) > 0:
        empty.append("total_chars")
    results.append({"id": "A2", "name": "structural manifest fields non-empty",
                    "status": "pass" if not empty else "fail", "empty_fields": empty,
                    "field_errors": plan.get("field_errors") or []})

    release = plan["release_manifest"]
    diffs = []
    if str(release.get("paper_title", "")).strip() != str(manifest.get("title", "")).strip():
        diffs.append({"field": "title", "release_manifest": release.get("paper_title"),
                      "package_manifest": manifest.get("title")})
    if _norm_version(str(release.get("paper_version", ""))) != _norm_version(str(manifest.get("package_version", ""))):
        diffs.append({"field": "package_version", "release_manifest": release.get("paper_version"),
                      "package_manifest": manifest.get("package_version")})
    # PF-B7 (GC-2026-1112-04): the release manifest's submission metadata set and
    # the package manifest must agree field by field — a source drift between the
    # release and the package is caught here, not in the sender's mailbox.
    submission = release.get("submission")
    submission_diffs: list[dict] = []
    if isinstance(submission, dict):
        submission_diffs = _compare_submission_block(submission, manifest)
        diffs = diffs + submission_diffs
    results.append({"id": "A3", "name": "shared fields identical to the release manifest",
                    "status": "pass" if not diffs else "fail", "differences": diffs,
                    "submission_compared": isinstance(submission, dict),
                    "submission_differences": submission_diffs})

    tables_dir = package_dir / "tables"
    actual_csv = {p.name for p in tables_dir.glob("*.csv")} if tables_dir.is_dir() else set()
    expected_csv = {Path(t["packaged_as"]).name for t in plan["tables"]}
    manifest_csv = {Path(i.get("packaged_as", "")).name for i in (manifest.get("tables", {}).get("items") or [])
                    if i.get("packaged_as")}
    table_missing = sorted(expected_csv - actual_csv)
    table_extra = sorted(actual_csv - expected_csv)
    manifest_missing = sorted(expected_csv - manifest_csv)
    # ── ground-truth leg (GC-2026-1112-07): the self-consistency comparison above
    # is NOT a correctness check — a detection miss leaves both sides empty and the
    # old leg passes vacuously (P3 shipped 3 tables whose header rows had no leading
    # '|', _package_tables missed them and the old check still passed). The packaged
    # docx is the same file shipped with the package (sha256 already compared at
    # package time); count its real <w:tbl>s and require N_tbl == N_csv, where
    # N_csv is the manifest's tables count (i.e. the number actually exported).
    N_csv = (manifest.get("tables") or {}).get("count")
    docx_name = plan.get("docx_name")
    docx_gt = {"docx_name": docx_name, "N_tbl": None, "N_csv": N_csv,
               "source": "word/document.xml <w:tbl> count", "matched": False, "error": None}
    if not docx_name:
        docx_gt["error"] = "no docx_name in package plan"
    else:
        docx_file = package_dir / docx_name
        if not docx_file.exists():
            docx_gt["error"] = f"packaged docx missing: {docx_name}"
        else:
            try:
                docx_gt["N_tbl"] = _count_docx_tables(docx_file)
                docx_gt["matched"] = (docx_gt["N_tbl"] == N_csv)
            except PackageFailure as exc:
                docx_gt["error"] = str(exc)
    table_ok = not (table_missing or table_extra or manifest_missing) and docx_gt["matched"]
    _n_tbl = docx_gt["N_tbl"]
    _n_csv = docx_gt["N_csv"]
    detail = None
    if not docx_gt["matched"] and _n_tbl is not None:
        if _n_tbl > (_n_csv or 0):
            detail = (f"docx 含 {_n_tbl} 个 <w:tbl> 表格但只导出 {_n_csv or 0} 个 CSV——"
                      f"存在漏检（{_n_tbl - (_n_csv or 0)} 个表格未导出）")
        elif _n_tbl < (_n_csv or 0):
            detail = (f"docx 含 {_n_tbl} 个 <w:tbl> 表格却导出/登记了 {_n_csv} 个 CSV——"
                      f"存在幻影（{(_n_csv or 0) - _n_tbl} 个 CSV 在 docx 中无对应表格）")
        else:
            detail = f"docx 含 {_n_tbl} 个 <w:tbl> 表格但导出/检测到 {_n_csv} 个 CSV——存在漏检或幻影"
    results.append({"id": "A4", "name": "CSV set matches body/paper.md AND the packaged docx table count (bidirectional + ground-truth)",
                    "status": "pass" if table_ok else "fail",
                    "expected": sorted(expected_csv), "packaged": sorted(actual_csv),
                    "missing": table_missing, "extra": table_extra, "manifest_missing": manifest_missing,
                    "docx_ground_truth": docx_gt, "detail": detail})

    figures_dir = package_dir / "figures"
    actual_fig = {p.name for p in figures_dir.iterdir() if p.is_file()} if figures_dir.is_dir() else set()
    expected_fig = {Path(f["packaged_as"]).name for f in plan["figures"] if f["packaged_as"]}
    manifest_fig = {Path(i.get("packaged_as", "")).name for i in (manifest.get("figures", {}).get("items") or [])
                    if i.get("packaged_as")}
    fig_missing = sorted(expected_fig - actual_fig)
    fig_extra = sorted(actual_fig - expected_fig)
    manifest_fig_missing = sorted(expected_fig - manifest_fig)
    registered_missing = [f["id"] for f in plan["figures"] if f["packaged_as"]
                          and not (plan["package_dir"] / f["packaged_as"]).exists()]
    fig_ok = not (fig_missing or fig_extra or manifest_fig_missing or registered_missing)
    results.append({"id": "A5", "name": "figure set identical to figures/index.yaml (bidirectional)",
                    "status": "pass" if fig_ok else "fail",
                    "expected": sorted(expected_fig), "packaged": sorted(actual_fig),
                    "missing": fig_missing, "extra": fig_extra,
                    "manifest_missing": manifest_fig_missing, "registered_but_absent": registered_missing})
    return results


def _package_writeback(dest: Path, version: str, package_manifest_path: Path) -> dict:
    """Write the package manifest sha256 back into the release manifest (PF-B7).

    Guard (GC-2026-1112-04): the release manifest may take the sha256 only when
    it is the version build/current.json points at AND its review_status is
    exactly 'pending' — a superseded version keeps its assembly record in the
    sidecar, and a published version is never modified in place (PF-B7).
    The word list is closed: 'pending' only (G-2).
    """
    result = {"written": False, "reason": None, "sha256": None,
              "release_manifest": str(dest / "build" / version / "manifest.json")}
    manifest_path = dest / "build" / version / "manifest.json"
    if not manifest_path.exists():
        result["reason"] = "release_manifest_missing"
        return result
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        result["reason"] = "release_manifest_unreadable"
        result["error"] = str(exc)
        return result
    if not isinstance(data, dict):
        result["reason"] = "release_manifest_malformed"
        return result

    # ── guard 1: the version must be the one build/current.json points at ──
    current_file = dest / "build" / "current.json"
    current_version = None
    if current_file.exists():
        try:
            current_version = json.loads(current_file.read_text(encoding="utf-8")).get("paper_version")
        except Exception:  # noqa: BLE001
            current_version = None
    current_version = _norm_version(str(current_version)) if current_version else None
    if current_version != _norm_version(version):
        result["reason"] = "superseded_version"
        result["current_version"] = current_version
        result["detail"] = (
            f"build/current.json points at {current_version or 'nothing'} — {version} is a "
            f"superseded version and its release manifest is not modified (PF-B7: old versions "
            f"are preserved). The assembly record stays in build/{version}/package-gaps.json "
            f"(sidecar); bump paper_version (PF-V3) and rebuild if this version is to be published.")
        return result

    # ── guard 2: only a 'pending' release may take the sha256 ──
    review_status = data.get("review_status")
    if review_status != "pending":
        result["reason"] = "review_status_not_pending"
        result["review_status"] = review_status
        result["detail"] = (
            f"the release manifest of {version} carries review_status={review_status!r} — only a "
            f"'pending' release may take the package sha256 (a published version is never modified "
            f"in place, PF-B7).")
        return result

    submission = data.get("submission")
    if not isinstance(submission, dict):
        result["reason"] = "submission_block_absent"
        result["detail"] = (
            f"the release manifest of {version} carries no submission block — the PF-B7 submission "
            f"metadata set is written by the build; rebuild the release and re-run the package.")
        return result

    try:
        digest = hashlib.sha256(package_manifest_path.read_bytes()).hexdigest()
    except Exception as exc:  # noqa: BLE001
        result["reason"] = "package_manifest_unreadable"
        result["error"] = str(exc)
        return result

    submission["package_manifest_sha256"] = digest
    submission["package_status"] = "assembled"
    submission.pop("stale_note", None)
    data["submission"] = submission
    try:
        _atomic_write_json(manifest_path, data)
    except Exception as exc:  # noqa: BLE001 - a failed write must not report 'assembled'
        result["reason"] = "writeback_failed"
        result["error"] = str(exc)
        return result
    result.update({"written": True, "reason": "assembled", "sha256": digest})
    return result


def _append_build_record(dest: Path, payload: dict, plan: dict | None) -> None:
    """Append the build-record section (PF-B7 ledger; append-only)."""
    record = dest / "build-record.md"
    version = payload.get("paper_version") or (plan or {}).get("version") or "?"
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines = [f"## PKG-{version} · 投稿交付包组装（{stamp}）", ""]
    lines.append(f"- 运行：`python3 -I tools/paper.py package --paper {payload.get('paper_dir', dest.name)}`"
                 f"{' --verify-only' if payload.get('mode') == 'verify' else ''}"
                 f"{' --strict' if payload.get('strict') else ''}")
    lines.append(f"- 模式：{'校验（--verify-only，不重建）' if payload.get('mode') == 'verify' else '组装（清空重建）'}")
    lines.append(f"- 版本：{version}；包根：`build/{version}/package/`；缺口 sidecar：`build/{version}/package-gaps.json`")
    lines.append("")
    status = payload.get("status")
    lines.append("### 骨架清单")
    lines.append("")
    lines.append("| 项 | 文件 | 结果 |")
    lines.append("|---|---|---|")
    if plan:
        lines.append(f"| docx | {plan['docx_name']} | {'ok' if (plan['package_dir'] / plan['docx_name']).exists() else '缺失'} |")
        lines.append(f"| pdf | {plan['pdf_name']} | {'ok' if (plan['package_dir'] / plan['pdf_name']).exists() else '缺失'} |")
        for f in plan["figures"]:
            name = Path(f["packaged_as"]).name if f["packaged_as"] else "—"
            lines.append(f"| 图 {f['id']} | figures/{name} | {f['status']} |")
        for t in plan["tables"]:
            lines.append(f"| 表 {t['number']} | {t['packaged_as']} | {t['caption'] or '（无题注，按序补配）'} |")
    lines.append("")
    lines.append("### 字数")
    lines.append("")
    lines.append("| 口径 | 值 |")
    lines.append("|---|---|")
    counts = payload.get("char_counts") or {}
    if counts:
        lines.append(f"| total_chars（非空白字符） | {counts.get('total_chars')} |")
        lines.append(f"| body_chars（非空白字符） | {counts.get('body_chars')} |")
        lines.append(f"| 摘要 / 参考文献（非空白字符） | {counts.get('abstract_zh_chars')} / {counts.get('references_chars')} |")
        ref = (payload.get("char_count_reference") or {})
        lines.append(f"| 旧口径参考（_count_chinese_chars） | total {ref.get('total')} / body {ref.get('body')} |")
    bandwidth = payload.get("bandwidth") or {}
    if bandwidth:
        lines.append(f"| 带宽（writing-spec min/max） | {bandwidth.get('min_chars')}/{bandwidth.get('max_chars')} "
                     f"→ {bandwidth.get('status')}（INFO 级，裁定权在 PF-RV8 审稿线） |")
    lines.append("")
    lines.append("### 缺口摘要")
    lines.append("")
    gaps = payload.get("gaps") or []
    if gaps:
        for g in gaps:
            lines.append(f"- {g.get('kind')}：{g.get('detail') or g.get('figure') or ''}")
    else:
        lines.append("- 无缺口。")
    downgrades = payload.get("downgrades") or []
    for d in downgrades:
        lines.append(f"- 降级（摄影类）：{d.get('figure')} → {d.get('packaged_as')}；{d.get('reason')}")
    lines.append("")
    lines.append("### 断言结论")
    lines.append("")
    for a in payload.get("assertions") or []:
        detail = ""
        if a["status"] == "fail":
            detail = f" — {json.dumps({k: v for k, v in a.items() if k not in ('id', 'name', 'status')}, ensure_ascii=False)}"
        lines.append(f"- {a['id']} {a['name']}：{a['status']}{detail}")
    lines.append(f"- 结论：{'pass' if payload.get('assertions_status') == 'pass' else 'fail'}"
                 f"；--strict：{payload.get('strict_status', 'n/a')}")
    if payload.get("error"):
        lines.append(f"- 失败原因：{payload['error']}")
    if payload.get("failed_assertions"):
        lines.append(f"- 失败断言：{', '.join(payload['failed_assertions'])}")
    if payload.get("strict_reasons"):
        lines.append(f"- strict 原因：{'；'.join(payload['strict_reasons'])}")
    writeback = payload.get("writeback") or {}
    if writeback:
        detail = writeback.get("detail") or writeback.get("error") or ""
        lines.append(f"- 发布 manifest 回写：{writeback.get('reason')}"
                     + (f"；sha256 {writeback.get('sha256')}" if writeback.get("sha256") else "")
                     + (f"；{detail}" if detail else ""))
    lines.append(f"- 本次运行：{status}（退出码 {payload.get('exit_code')}）")
    lines.append("")
    try:
        if not record.exists():
            record.write_text("# 构建记录（build-record）\n\n", encoding="utf-8")
        with record.open("a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(lines) + "\n")
    except Exception as exc:  # noqa: BLE001 - a ledger failure must not mask the result
        payload["build_record_error"] = str(exc)


def cmd_package(args):
    """Assemble or verify the PF-B16 submission package (GC-2026-1112-03)."""
    mode = "verify" if getattr(args, "verify_only", False) else "build"
    payload = {"status": "error", "command": "package", "mode": mode,
               "strict": bool(getattr(args, "strict", False))}
    dest = None
    plan = None
    code = 2
    try:
        if getattr(args, "version", None) and getattr(args, "current", False):
            raise PackageFailure("--version and --current are mutually exclusive")
        dest = _resolve_paper_dir(args.paper)
        version, version_source = _resolve_package_version(dest, args)
        payload.update({"paper_id": dest.name, "paper_version": version, "version_source": version_source,
                        "paper_dir": str(dest)})
        plan = _package_plan(dest, version)
        package_dir = plan["package_dir"]
        if mode == "build":
            _materialize_package(plan)
            manifest = plan["manifest"]
        else:
            manifest_file = package_dir / "manifest.json"
            if not manifest_file.exists():
                raise PackageFailure(f"no package manifest to verify: {manifest_file}")
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception as exc:
                raise PackageFailure(f"package manifest is unreadable: {exc}")
        assertions = _package_assertions(plan, manifest)
        failed = [a for a in assertions if a["status"] == "fail"]
        payload.update({
            "status": "ok" if not failed else "fail",
            "package_dir": str(package_dir),
            "gaps_sidecar": str(plan["sidecar_path"]),
            "assertions": assertions,
            "assertions_status": "pass" if not failed else "fail",
            "failed_assertions": [a["id"] for a in failed],
            "gaps": plan["gaps"],
            "notes": plan["notes"],
            "downgrades": plan["downgrades"],
            "redraw_pending": plan["redraw_pending"],
            "char_counts": plan["char_counts"],
            "char_count_reference": plan["sidecar"]["char_count_reference"],
            "bandwidth": plan["bandwidth"],
            "figures": [{"id": f["id"], "packaged_as": f["packaged_as"], "status": f["status"]} for f in plan["figures"]],
            "tables": [{"number": t["number"], "packaged_as": t["packaged_as"], "caption": t["caption"]}
                       for t in plan["tables"]],
            "manifest_fields": {
                "title": manifest.get("title"),
                "title_en": manifest.get("title_en"),
                "abstract_zh_chars": plan["char_counts"]["abstract_zh_chars"],
                "abstract_en_present": manifest.get("abstract_en_present"),
                "keywords_zh": manifest.get("keywords_zh"),
                "authors": len(manifest.get("authors") or []),
                "corresponding_authors": [a["name"] for a in (manifest.get("authors") or []) if a.get("corresponding")],
                "bio_parsed": [a["name"] for a in (manifest.get("authors") or []) if a.get("bio")],
                "conclusion_chars": _count_nonwhitespace_chars(manifest.get("conclusion") or ""),
                "total_chars": manifest.get("total_chars"),
                "body_chars": manifest.get("body_chars"),
                "submission_direction": manifest.get("submission_direction"),
                "char_count_methodology": manifest.get("char_count_methodology"),
                "figures": manifest.get("figures", {}).get("count"),
                "tables": manifest.get("tables", {}).get("count"),
                "downgrades": len(manifest.get("downgrades") or []),
            },
        })
        code = 0 if not failed else 1
        if getattr(args, "strict", False):
            strict_reasons = []
            if plan["gaps"]:
                strict_reasons.append(f"{len(plan['gaps'])} gap(s) recorded in {plan['sidecar_path'].name}")
            if plan["redraw_pending"]:
                strict_reasons.append(f"{len(plan['redraw_pending'])} figure(s) pending SVG redraw")
            payload["strict_reasons"] = strict_reasons
            payload["strict_status"] = "pass" if not strict_reasons else "fail"
            if strict_reasons:
                payload["status"] = "fail"
                code = 1
        else:
            payload["strict_status"] = "n/a"
        # ── PF-B7: write the package manifest sha256 back into the release manifest ──
        # '--verify-only' writes nothing at all; a failed assertion or a failed
        # --strict run writes nothing either (T6).
        writeback = {"attempted": False, "written": False, "reason": None, "sha256": None}
        if mode == "verify":
            writeback["reason"] = "verify_only_zero_write"
        elif failed:
            writeback["reason"] = "assertions_failed_no_writeback"
        elif payload.get("strict_status") == "fail":
            writeback["reason"] = "strict_failed_no_writeback"
        else:
            writeback["attempted"] = True
            writeback.update(_package_writeback(dest, version, package_dir / "manifest.json"))
        payload["writeback"] = writeback
        if writeback["attempted"] and not writeback["written"]:
            payload["status"] = "fail"
            code = 1
            payload["error"] = (writeback.get("detail") or writeback.get("error")
                                or "the package sha256 could not be written into the release manifest")
    except PackageFailure as exc:
        payload.update(exc.payload)
        payload.setdefault("stage", "package")
        code = exc.exit_code
    except Exception as exc:  # noqa: BLE001
        payload.update({"status": "error", "error": str(exc), "stage": "package"})
        code = 2
    payload["exit_code"] = code
    if dest is not None:
        _append_build_record(dest, payload, plan)
    return emit(payload, code)


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

    p_package = sub.add_parser("package", help="Assemble or verify the PF-B16 submission package")
    p_package.add_argument("--paper", required=True, help="Path to paper workspace (directory name or paper id accepted)")
    p_package.add_argument("--version", default=None, help="Paper version to package, e.g. v0.3.2 (default: build/current.json)")
    p_package.add_argument("--current", action="store_true", help="Use the version in build/current.json (default)")
    p_package.add_argument("--verify-only", action="store_true", help="Verify an existing package without rebuilding it")
    p_package.add_argument("--strict", action="store_true", help="Fail when the gaps sidecar is non-empty or a figure is redraw_pending")

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
        "package": cmd_package,
    }
    code = cmds[args.command](args)
    raise SystemExit(code)

if __name__ == "__main__":
    main()
