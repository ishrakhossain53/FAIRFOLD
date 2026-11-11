#!/usr/bin/env python3
"""Slim the batch spec files for phases 2-5 in docs/prompts/paste-ready/.

Why: every spec repeated a ~1.3 KB "# RULES" block that told the agent it cannot see the
repo (CLAUDE.md says the opposite), plus Process / "What I will paste" / "Progress snippets"
boilerplate that CLAUDE.md already defines. Only the batch-specific parts are kept:
Phase/Type/Requirement/prerequisite lines, In scope, Out of scope, Done when, Watch out.

Phase 0 and Phase 1 files are never touched. Decision batches keep their Process section
because it holds the STOP gate. Idempotent: a file that already has the header is skipped.

Usage:  python scripts/slim_prompts.py            # rewrite files
        python scripts/slim_prompts.py --dry-run  # report only
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "docs" / "prompts" / "paste-ready"
HEADER = (
    "> Spec only. Run it through its group prompt in `docs/prompts/PHASE_{n}.md` "
    "(CLAUDE.md has the run rules). Check the prerequisite is `[x]` in `docs/PROGRESS.md`; "
    "if not, stop.\n\n"
)
DROP = ("process", "progress snippets", "what i will paste for you")
REQUIRED = ("## In scope", "## Out of scope", "## Done when")


def slim(text: str, phase: str) -> str:
    m = re.search(r"^# Batch ", text, re.M)
    if not m:
        raise ValueError("no '# Batch' heading")
    body = text[m.start() :]
    # split into sections at '## ' headings; first chunk is the title block
    parts = re.split(r"(?m)^(?=## )", body)
    kept = [parts[0]]
    for sec in parts[1:]:
        title = sec.splitlines()[0][3:].strip().lower()
        is_gate = title == "process" and "**Gate:**" in sec
        if any(title.startswith(d) for d in DROP) and not is_gate:
            continue
        kept.append(sec)
    out = HEADER.format(n=phase) + "".join(kept).rstrip() + "\n"
    # decision batches keep their Process gate; drop the stale "paste" wording inside it
    out = out.replace("Using only what I paste, write", "Write")
    for r in REQUIRED:
        if r not in out:
            raise ValueError(f"lost required section {r}")
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = sorted(p for p in DIR.glob("*.md") if p.name[0] in "2345")
    before = after = changed = 0
    for p in files:
        t = p.read_text(encoding="utf-8")
        before += len(t.encode())
        if t.startswith("> Spec only."):
            after += len(t.encode())
            continue
        new = slim(t, p.name[0])
        after += len(new.encode())
        changed += 1
        if not dry:
            p.write_text(new, encoding="utf-8")
    print(
        f"{len(files)} phase 2-5 specs, {changed} {'would change' if dry else 'rewritten'}"
    )
    print(f"bytes before {before}, after {after}, saved {before - after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
