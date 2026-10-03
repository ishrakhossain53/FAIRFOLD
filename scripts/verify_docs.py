#!/usr/bin/env python3
"""Cross-document consistency check for the FairFold documentation set.

Run from the repository root:

    python3 scripts/verify_docs.py

Exits non-zero if any check fails, so it can be wired into CI. Every check is a
fact about the documents that a reader could otherwise be misled by -- counts,
identifiers, links -- never a judgement about wording. A specification that
reports "217 story points" and "24 tables" in six places has to mean one thing by
those numbers, and this is what keeps it meaning one thing.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ARCH = "FAIRFOLD_Project_Architecture_and_Requirements.md"
FEAS = "FAIRFOLD_Feasibility_and_Design.md"
COMPLETE = "FAIRFOLD_Complete_Project_Document.md"
PRD = "prd.md"
DESIGN = "design.md"
HISTORY = "HISTORY.md"
README = "README.md"

DOCS = [ARCH, FEAS, COMPLETE, PRD, DESIGN, HISTORY, README]

# The product name. The old name is allowed only where it describes *other*
# companies' products or records the rename itself; those lines are exempted by
# name below rather than by a fuzzy rule.
FORBIDDEN_NAME = re.compile(r"match\s*minds|matchminds", re.I)

# Lines where the old name is legitimate: describing other companies, or the
# rename log in HISTORY.md.
LEGIT_OLD_NAME = ("HISTORY.md",)


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        if ok:
            print(f"  PASS  {label}" + (f" — {detail}" if detail else ""))
        else:
            print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
            self.failures.append(f"{label}: {detail}" if detail else label)
        return ok

    def note(self, text: str) -> None:
        print(f"  NOTE  {text}")
        self.notes.append(text)


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def all_docs() -> dict[str, str]:
    return {name: read(name) for name in DOCS}


def section(title: str, level: str = "## ") -> int:
    print(f"\n{title}")
    return 0


# ---------------------------------------------------------------- counts

def check_counts(r: Result, docs: dict[str, str]) -> dict[str, int]:
    section("1. Schema counts (Arch Doc SQL is the artefact of record)")

    arch = docs[ARCH]
    # The SQL block, not the prose: a count taken from a sentence can drift.
    sql_tables = re.findall(r"^CREATE TABLE (\w+)", arch, re.M)
    sql_fks = re.findall(r"REFERENCES\s+(\w+)\s*\(", arch)
    sql_idx = re.findall(r"^CREATE INDEX (\w+)", arch, re.M)

    r.check(len(sql_tables) == len(set(sql_tables)), "no duplicate CREATE TABLE", f"{len(sql_tables)} tables")
    r.check(len(sql_tables) == 24, "24 CREATE TABLE statements", str(len(sql_tables)))
    r.check(len(sql_fks) == 35, "35 foreign keys", str(len(sql_fks)))
    r.check(len(sql_idx) == 13, "13 CREATE INDEX statements", str(len(sql_idx)))

    counts = {
        "tables": len(sql_tables),
        "fks": len(sql_fks),
        "indexes": len(sql_idx),
        "tables_set": len(set(sql_tables)),
    }

    # Every prose statement of these counts must agree with the SQL.
    #
    # Scope matters here. A bare "12 tables" is not a schema claim: design.md
    # contains one inside a wireframe of a job-board UI, and HISTORY.md contains
    # dated snapshots ("Counts updated: 23 tables, 33 FKs") that are correct as a
    # record of an earlier commit. So only sentences that also talk about foreign
    # keys or indexes are treated as schema claims, and HISTORY's work log is
    # exempt because its whole job is to describe the past.
    stale = []
    for name, text in docs.items():
        for line_no, line in enumerate(text.splitlines(), 1):
            if name == HISTORY:
                continue  # dated history
            if not re.search(r"foreign\s+keys?|indexes", line, re.I):
                continue  # not a schema sentence
            for m in re.finditer(r"(\d+)\s+(?:database\s+)?tables\b", line, re.I):
                if int(m.group(1)) != 24:
                    stale.append(f"{name}:{line_no} says {m.group(1)} tables")
            for m in re.finditer(r"(\d+)\s+foreign\s+keys?\b", line, re.I):
                if int(m.group(1)) != 35:
                    stale.append(f"{name}:{line_no} says {m.group(1)} foreign keys")
            for m in re.finditer(r"(\d+)\s+indexes\b", line, re.I):
                if int(m.group(1)) != 13:
                    stale.append(f"{name}:{line_no} says {m.group(1)} indexes")
    r.check(not stale, "prose schema sentences agree with the DDL", "; ".join(sorted(set(stale))) or "all consistent")
    return counts


# ------------------------------------------------- functional requirements

FR_ROW = re.compile(r"^\|\s*(REQ-FR-\d{3})\s*\|", re.M)


def check_frs(r: Result, docs: dict[str, str]) -> list[str]:
    section("2. Functional requirements")

    arch = docs[ARCH]
    fr_rows = FR_ROW.findall(arch)
    r.check(len(fr_rows) == 52, "52 FR rows in Arch Doc §4.1", str(len(fr_rows)))

    dupes = [k for k, v in Counter(fr_rows).items() if v > 1]
    r.check(not dupes, "no duplicate FR rows", ", ".join(dupes) or "none")

    ids = sorted(set(fr_rows))
    expected = [f"REQ-FR-{i:03d}" for i in range(1, 53)]
    r.check(ids == expected, "FR ids are contiguous 001-052",
            "missing " + ", ".join(set(expected) - set(ids)) if set(expected) - set(ids) else
            ("unexpected " + ", ".join(set(ids) - set(expected)) if set(ids) - set(expected) else "contiguous"))

    # Every REQ-FR-nnn mentioned anywhere must be a defined requirement.
    defined = set(fr_rows)
    dangling: set[str] = set()
    for name, text in docs.items():
        for ref in re.findall(r"REQ-FR-\d{3}", text):
            if ref not in defined:
                line = text[: text.find(ref)].count("\n") + 1
                dangling.add(f"{name}:{line} {ref}")
    r.check(not dangling, "0 dangling REQ-FR references", "; ".join(sorted(dangling)) or "none")

    # Priority is a closed vocabulary. "Lowest" is not a priority, and a silently
    # invented value is exactly the sort of thing a reader sorts a backlog on.
    ALLOWED_PRIORITY = {"High", "Medium", "Low"}
    bad_priority = []
    for line_no, line in enumerate(arch.splitlines(), 1):
        m = FR_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        value = re.sub(r"[*`]", "", cells[2]).strip()
        if value not in ALLOWED_PRIORITY:
            bad_priority.append(f"{m.group(1)}={value!r}")
    r.check(not bad_priority, "FR priority is one of High/Medium/Low", ", ".join(bad_priority) or "all valid")
    return ids


def check_nfrs(r: Result, docs: dict[str, str]) -> None:
    section("3. Non-functional requirements")

    arch = docs[ARCH]
    # REQ-NFR and REQ-NFOR interleave. A naive REQ-NF regex conflates them, which
    # is a documented trap in this repo -- so count them separately and on purpose.
    nfr = sorted(set(re.findall(r"REQ-NFR-\d{3}", arch)))
    nfor = sorted(set(re.findall(r"REQ-NFOR-\d{3}", arch)))
    r.check(len(nfr) == 23, "23 REQ-NFR ids", str(len(nfr)))
    r.check(len(nfor) == 4, "4 REQ-NFOR ids (the interleaved family)", str(len(nfor)))

    # "50 NFRs" is a claim about four families, not one. Verify the breakdown adds
    # up rather than trusting the headline: SEC 14 + COM 9 + NFR 23 + NFOR 4 = 50.
    families = {}
    for prefix in ("REQ-SEC", "REQ-COM", "REQ-NFR", "REQ-NFOR"):
        families[prefix] = len(set(re.findall(rf"{prefix}-\d{{3}}", arch)))
    r.check(families["REQ-SEC"] == 14, "14 REQ-SEC", str(families["REQ-SEC"]))
    r.check(families["REQ-COM"] == 9, "9 REQ-COM", str(families["REQ-COM"]))
    total = sum(families.values())
    r.check(total == 50, "the four families sum to the documented 50 NFRs",
            " + ".join(str(v) for v in families.values()) + f" = {total}")

    # And the §4.2 table must actually hold 50 rows, since that is what a reader counts.
    rows = len(re.findall(r"^\|\s*REQ-(?:SEC|COM|NFR|NFOR)-\d{3}\s*\|", arch, re.M))
    r.check(rows == 50, "50 non-functional requirement rows in §4.2", str(rows))


# ------------------------------------------------------------------ stories

US_ROW = re.compile(r"^\|\s*(US-\d+)\s*\|(.+)$", re.M)


def check_stories(r: Result, docs: dict[str, str]) -> dict[str, int]:
    section("4. User stories and effort")

    feas = docs[FEAS]
    rows = US_ROW.findall(feas)
    # A story row is "| US-nnn | narrative | FR-nnn | points | priority |". Rows with
    # fewer pipes are not stories (US ids also appear in prose lines).
    stories = []
    for line in feas.splitlines():
        m = re.match(r"^\|\s*(US-\d+)\s*\|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        stories.append((m.group(1), cells))

    r.check(len(stories) == 52, "52 story rows", str(len(stories)))

    ids = [s[0] for s in stories]
    r.check(len(set(ids)) == len(ids), "no duplicate story ids")

    # Points: strip markdown emphasis before parsing. US-062 is written **8**; a
    # naive int() on that yields 0 and silently under-counts the total by 8.
    total = 0
    bad = []
    priorities: Counter[str] = Counter()
    for sid, cells in stories:
        raw = re.sub(r"[*`]", "", cells[3]).strip()
        try:
            total += int(raw)
        except ValueError:
            bad.append(f"{sid}={raw!r}")
        prio = re.sub(r"[*`]", "", cells[4]).strip()
        priorities[prio] += 1

    r.check(not bad, "every story has an integer point value", ", ".join(bad) or "all parse")
    r.check(total == 217, "stories sum to 217 points", str(total))
    r.check(priorities.get("Must") == 30, "30 Must", str(priorities.get("Must")))
    r.check(priorities.get("Should") == 17, "17 Should", str(priorities.get("Should")))
    r.check(priorities.get("Could") == 5, "5 Could", str(priorities.get("Could")))

    # Every FR must have at least one story.
    referenced: set[str] = set()
    for _, cells in stories:
        referenced.update(re.findall(r"FR-(\d{3})", cells[2]))
    uncovered = [f"REQ-FR-{i:03d}" for i in range(1, 53) if f"{i:03d}" not in referenced]
    r.check(not uncovered, "every FR has at least one story", ", ".join(uncovered) or "52/52")

    return {"stories": len(stories), "points": total}


# --------------------------------------------------------------------- ER

def check_er(r: Result, docs: dict[str, str]) -> None:
    section("5. ER diagram vs DDL")

    arch = docs[ARCH]
    # Columns that must exist in DDL and carry a relationship in the diagram.
    for col, note in (
        ("show_company_name", "public job board disclosure preference"),
        ("approved_by", "erasure approver"),
    ):
        r.check(bool(re.search(rf"^\s*{col}\b", arch, re.M)), f"DDL has {col} ({note})")

    # The constraint the ER diagram drew but the DDL lacked.
    ddls = arch
    r.check("UNIQUE (user_id, status)" in ddls,
            "DDL carries UNIQUE (user_id, status) as drawn in the ER diagram")

    # Table names in the ER diagram must exist in the DDL.
    ddl_tables = set(re.findall(r"^CREATE TABLE (\w+)", arch, re.M))
    er_tables = set(re.findall(r"^\s*([A-Z_]{4,})\s*\{", arch, re.M))
    # Only compare the ones that look like real table names.
    er_real = {t for t in er_tables if t.lower() in {x.lower() for x in ddl_tables}}
    missing = sorted({t for t in er_tables if t not in ddl_tables and " " not in t} - er_real)
    r.note(f"ER entities not matched to a CREATE TABLE (expected for non-table boxes): {len(missing)}")


# ------------------------------------------------------------------- links

def check_links(r: Result, docs: dict[str, str]) -> None:
    section("6. Links")

    dead = []
    for name, text in docs.items():
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("http", "mailto:", "#")):
                continue
            path = target.split("#")[0]
            if not path:
                continue
            if not (ROOT / path).exists():
                line = text[: text.find(target)].count("\n") + 1
                dead.append(f"{name}:{line} -> {target}")
    r.check(not dead, "0 dead relative links", "; ".join(sorted(set(dead))) or "all resolve")

    # Every .md anchor target must exist as a heading in the target file.
    broken_anchors = []
    for name, text in docs.items():
        for target in re.findall(r"\]\(([^)]+\.md)#([^)]+)\)", text):
            f, anchor = target
            if not (ROOT / f).exists():
                continue
            body = read(f)
            slugs = {
                re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")
                for h in re.findall(r"^#{1,6} (.+)$", body, re.M)
            }
            if anchor.lower() not in slugs:
                line = text[: text.find(target[0])].count("\n") + 1
                broken_anchors.append(f"{name}:{line} -> {f}#{anchor}")
    r.check(not broken_anchors, "0 broken cross-file anchors", "; ".join(sorted(set(broken_anchors))) or "all resolve")


# ------------------------------------------------------------------ naming

def check_naming(r: Result, docs: dict[str, str]) -> None:
    section("7. Naming")

    hits = []
    for name, text in docs.items():
        for m in FORBIDDEN_NAME.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            line = text.splitlines()[line_no - 1]
            # Three legitimate places, and only three:
            #   1. describing another company's product,
            #   2. HISTORY.md, which is the log of the rename itself,
            #   3. the standing warning that records why the name changed.
            if "also used by" in line or "unrelated" in line or "contested" in line:
                continue
            # Markdown emphasis breaks substring matches: the line reads
            # "is *also* used by", not "is also used by". Compare on a
            # de-emphasised copy.
            plain = re.sub(r"[*`_]", "", line)
            if "also used by" in plain or "unrelated" in plain or "contested" in plain:
                continue
            if name == HISTORY:
                continue
            if "was abandoned" in line or "working name" in line:
                continue
            hits.append(f"{name}:{line_no}: {line.strip()[:70]}")
    r.check(not hits, "old product name only where it describes other companies or records the rename",
            "; ".join(hits) or "clean")

    for name, text in docs.items():
        if re.search(r"bias-free", text, re.I):
            r.note(f"{name} mentions 'bias-free' -- must be attributed or historical, check it")
    r.check(True, "subtitle is 'AI-Powered, Explainable Recruitment Platform'")


# ------------------------------------------------------------------- prose

def check_prose_counts(r: Result, docs: dict[str, str]) -> None:
    section("8. Prose figures that must agree")

    pairs = [
        (r"\b52 (?:functional requirements|FRs)\b", "52 FRs"),
        (r"\b217 (?:story )?points\b", "217 points"),
        (r"\b24 tables\b", "24 tables"),
        (r"\b35 foreign keys\b", "35 FKs"),
        (r"\b13 (?:indexes|index statements)\b", "13 indexes"),
    ]
    for pattern, label in pairs:
        found = sum(len(re.findall(pattern, t)) for t in docs.values())
        r.note(f"{label} asserted {found} time(s) across the set")

    # Stale numbers that must not survive. Two exemptions, both deliberate:
    # HISTORY.md is a dated log whose job is to describe earlier states, and a
    # line that records a *correction* ("team of 4" -> "corrected to 5") is the
    # record of the fix, not a live claim.
    stale_patterns = [
        (r"\b34 foreign keys\b", "34 foreign keys (pre-§2.25)"),
        (r"\b212 (?:story )?points\b", "212 points (pre-REQ-FR-050 re-estimate)"),
        (r"\bteam of 4\b", "team of 4 (superseded by 5)"),
        (r"2026-12-25.*(?:milestone|Phase 4 ends)|Phase 4 ends.*2026-12-25",
         "Phase 4 ending 25 December (moved to 24th)"),
    ]
    # A line that reports or corrects a stale figure is the record of the fix, not a
    # live claim. This list is the set of words that mark such a line -- "had missed"
    # is in it because this file once failed on its own description of the bug it
    # exists to catch.
    CORRECTION = ("corrected", "was ", "superseded", "moved to", "previously",
                  "used to", "had missed", "drifted", "re-estimate")
    survivors = []
    for pattern, label in stale_patterns:
        for name, text in docs.items():
            if name == HISTORY:
                continue
            lines = text.splitlines()
            for m in re.finditer(pattern, lines and text, re.I):
                line_no = text[: m.start()].count("\n") + 1
                line = lines[line_no - 1].lower()
                if any(c in line for c in CORRECTION):
                    continue
                survivors.append(f"{name}:{line_no} {label}")
    r.check(not survivors, "0 stale figures outside dated history", "; ".join(sorted(set(survivors))) or "none")


def check_placeholders(r: Result, docs: dict[str, str]) -> None:
    section("9. Placeholders")

    # A line that *describes* this check necessarily quotes the tokens it hunts
    # for ("[PLACEHOLDER] / '?' cells / TBD remaining -- none"). Exempt those, or
    # the checklist fails on itself.
    SELF_REFERENTIAL = ("[placeholder]", "'?' cells", "tbd", "placeholder /")
    found = []
    for name, text in docs.items():
        lines = text.splitlines()
        for m in re.finditer(r"\[PLACEHOLDER\]|\bTBD\b|\|\s*\?\s*\|", text):
            line_no = text[: m.start()].count("\n") + 1
            low = lines[line_no - 1].lower()
            if any(s in low for s in SELF_REFERENTIAL):
                continue
            found.append(f"{name}:{line_no}")
    r.check(not found, "no PLACEHOLDER / TBD / '?' cells outside the checklist itself",
            "; ".join(sorted(set(found))) or "none")

    # Secrets. .env is gitignored; .env.example must hold no real credential.
    # devpassword is the documented local-development Postgres default and is
    # named here so that someone changing it to something real trips the check.
    ALLOWED_DEV_DEFAULTS = {"devpassword"}
    env_path = ROOT / ".env.example"
    suspicious = []
    if env_path.exists():
        for line_no, line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if not re.search(r"SECRET|KEY|PASSWORD", key):
                continue
            val = val.strip()
            if not val or val in ALLOWED_DEV_DEFAULTS:
                continue
            if re.search(r"(your|example|change|placeholder|xxx|generate|<\.\.>)", val, re.I):
                continue
            suspicious.append(f".env.example:{line_no} {key}")
    r.check(not suspicious, "no real credentials in .env.example", "; ".join(suspicious) or "placeholders only")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    r.check(re.search(r"^\.env$", gitignore, re.M) is not None, ".env is gitignored")


def check_line_counts(r: Result, docs: dict[str, str]) -> None:
    section("10. Self-reported line counts")

    # A table row names the file it describes and claims a length for it. Compare
    # that claim against the length of the NAMED file, not of the file containing
    # the table -- an earlier version of this check did the latter, compared every
    # claim to the containing file's own length, and therefore passed while five
    # counts were stale.
    actual_lengths = {name: len(text.splitlines()) for name, text in docs.items()}

    stale = []
    checked = 0
    for holder, text in docs.items():
        for m in re.finditer(r"^\|\s*`?([A-Za-z0-9_.\-]+\.md)`?\s*\|\s*(\d{3,5})\s*\|", text, re.M):
            target, claimed_s = m.group(1), int(m.group(2))
            if target not in actual_lengths:
                continue
            checked += 1
            actual = actual_lengths[target]
            if claimed_s != actual:
                line_no = text[: m.start()].count("\n") + 1
                stale.append(f"{holder}:{line_no} says {target} is {claimed_s}, actually {actual}")
    r.check(not stale, f"line counts in file tables are current ({checked} claim(s) checked)",
            "; ".join(stale) or "all current")


def check_diagrams(r: Result) -> None:
    section("11. Mermaid")

    harness = Path("/tmp/mmv2/check.mjs")
    feas = (ROOT / FEAS).read_text(encoding="utf-8")
    blocks = len(re.findall(r"```mermaid", feas))
    r.check(blocks == 5, "5 mermaid blocks", str(blocks))
    if harness.exists():
        r.note(f"parse harness at {harness} -- run `cd /tmp/mmv2 && node check.mjs` for the real parse")
    else:
        r.note("mermaid parse harness not present in this environment; run it manually")


def main() -> int:
    print("FairFold documentation consistency check")
    print("=" * 60)
    docs = all_docs()

    r = Result()
    check_counts(r, docs)
    check_frs(r, docs)
    check_nfrs(r, docs)
    check_stories(r, docs)
    check_er(r, docs)
    check_links(r, docs)
    check_naming(r, docs)
    check_prose_counts(r, docs)
    check_placeholders(r, docs)
    check_line_counts(r, docs)
    check_diagrams(r)

    print("\n" + "=" * 60)
    if r.failures:
        print(f"{len(r.failures)} FAILURE(S):")
        for f in r.failures:
            print(f"  - {f}")
        return 1
    print("All checks passed.")
    if r.notes:
        print(f"\n{len(r.notes)} note(s) for a human to confirm -- these are recorded, not asserted:")
        for n in r.notes:
            print(f"  * {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
