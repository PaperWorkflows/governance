# Git Safety Rules

## Scope

This file defines the execution rules for Git operations across all subagents and all repositories of this project (per-paper repositories, the governance repository, and any repository a subagent is dispatched to touch). It is the executable detail layer of AGENTS.md F7 (Safety and Constraints) and F10 (Git Safety).

## Rules

### PF-G1 仓库边界

- Every Git write operation (add / commit / reset / branch / remote / repository config) executes inside the target repository: the working directory is the repository root, or the command carries an explicit repository selector (`-C <repo>` / `--git-dir`).
- Before every commit, run `git rev-parse --show-toplevel` and verify the output equals the target repository directory (physical path; symbolic links resolve to their target). If it does not match, stop and report — do not commit.
- The toplevel verification output is part of the execution report (PF-G5).

### PF-G2 禁建仓库

- `git init` (or `git clone` into a new location) without an explicit main-session instruction or an explicit user instruction is prohibited. User instructions take precedence over project files.
- A `fatal: not a git repository` error means the invocation is wrong — wrong directory, wrong selector, or the repository does not exist. Stop and report; never create a repository to make a failing command succeed.
- The workspace root is not a repository by design. A repository found there is an accident to be reported to the main session, never a base to build on.

### PF-G3 .git 保护

- `.git` directories are repository identity (history, refs, config, hooks). Deleting, moving, renaming, or overwriting any `.git` is prohibited.
- Embedded-repository / submodule errors (e.g. "pathspec ... in submodule") mean: stop and report. Never bypass them by removing the nested `.git`, by `git rm --cached`, or by re-initializing an outer repository.
- Per-paper repositories are independent by design (F1, PF-V4); nesting is the intended structure, not a defect.

### PF-G4 破坏性命令

- The following require explicit per-invocation authorization from the main session or the user, quoted verbatim in the execution report: `git reset --hard`, `git clean -fd`, forced checkout (`checkout -f` / `--force`), `git push --force`, history rewriting (`filter-branch`, `filter-repo`), `git reflog expire`, `git gc --prune=now`.
- If such a command was executed in error, recovery goes through dangling objects (`git fsck --lost-found`, reflog) and must be verified byte-level before being reported as recovered.
- `rm -rf` on any path that contains `.git` falls under F7 unauthorized permanent deletion.

### PF-G5 逐字报告

- Execution reports list Git operations verbatim: command, working directory, and the toplevel verification output.
- The main session does not accept summaries ("committed to each repo") in place of the verbatim record, and verifies independently.

### PF-G6 派单契约

- Any main-session dispatch that touches paper repositories or the governance repository includes this clause: repository boundary and toplevel verification (PF-G1), no repository creation (PF-G2), .git protection (PF-G3), destructive-command prohibition (PF-G4), verbatim reporting (PF-G5).
- A main-session dispatch prompt without this clause is defective; the subagent may refuse it and must report the omission. A user-direct dispatch is authoritative — proceed under the user's instruction and report the omission.
