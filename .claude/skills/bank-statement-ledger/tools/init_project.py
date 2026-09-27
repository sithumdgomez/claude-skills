"""Create a bookkeeping project folder from this skill's templates.

  python <skill>/tools/init_project.py ~/bookkeeping
  python <skill>/tools/init_project.py ~/bookkeeping --update-scripts   # refresh scripts after a skill update

Creates the folder layout, copies the pipeline scripts into scripts/, and the templates
(CLAUDE.md, PROGRESS.md, DECISIONS.md, notes_for_claude.md, config/*, .claude/settings.json,
.claude/agents/*, .gitignore). Never overwrites a file that already exists (except
scripts/*.py with --update-scripts; bank parsers you wrote are never touched).

Refuses to create the project inside a git repository that has a remote: bank statements
must never be pushed to GitHub or any other host.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
DIRS = ["00_raw", "01_statements", "02_extracted", "03_data", "config", "review", "output",
        "scripts/parsers", ".claude/agents"]


def git_remote(target: Path) -> str | None:
    for d in [target, *target.parents]:
        if (d / ".git").exists():
            try:
                out = subprocess.run(["git", "-C", str(d), "remote", "-v"], capture_output=True, text=True).stdout
            except FileNotFoundError:
                return None
            return out.strip() or None
    return None


def copy(src: Path, dst: Path, overwrite: bool, report: dict) -> None:
    if dst.exists() and not overwrite:
        report["kept"].append(dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    report["written"].append(dst)


def init(target: Path, update_scripts: bool = False, allow_remote: bool = False) -> dict:
    target = target.expanduser().resolve()
    remote = git_remote(target)
    if remote and not allow_remote:
        print(f"REFUSED: {target} is inside a git repository with a remote:\n{remote}\n"
              "Bank statements must stay on this machine. Choose a folder outside any repo.")
        sys.exit(1)
    for d in DIRS:
        (target / d).mkdir(parents=True, exist_ok=True)
    report = {"written": [], "kept": []}
    for f in sorted((SKILL / "pipeline").glob("*.py")):
        copy(f, target / "scripts" / f.name, update_scripts, report)
    for f in sorted((SKILL / "pipeline" / "parsers").glob("_*.py")):
        copy(f, target / "scripts" / "parsers" / f.name, update_scripts, report)
    t = SKILL / "templates"
    for name in ["CLAUDE.md", "PROGRESS.md", "DECISIONS.md", "notes_for_claude.md", "income_not_in_bank.csv"]:
        copy(t / name, target / name, False, report)
    for f in sorted((t / "config").iterdir()):
        copy(f, target / "config" / f.name, False, report)
    copy(t / "settings.json", target / ".claude" / "settings.json", False, report)
    copy(t / "gitignore", target / ".gitignore", False, report)
    for f in sorted((t / "agents").glob("*.md")):
        copy(f, target / ".claude" / "agents" / f.name, False, report)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--update-scripts", action="store_true")
    ap.add_argument("--allow-git-remote", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    target = Path(a.target)
    rep = init(target, a.update_scripts, a.allow_git_remote)
    print(f"Project: {target.expanduser().resolve()}")
    print(f"  files written: {len(rep['written'])}, already there (kept): {len(rep['kept'])}")
    print("Next:")
    print("  1. Copy statements into 00_raw/<bank>/<account>/ and make 00_raw read-only")
    print("  2. Fill config/accounts.csv, own_names in config/project.json, and notes_for_claude.md")
    print("  3. cd into the folder, start Claude Code, and say: Read PROGRESS.md and do the next step")


if __name__ == "__main__":
    main()
