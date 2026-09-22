"""Jev resolver spike: can Jev pick an ADR's FQN locus, at the right grain?

One POST to /v1/systemone per ADR, three typed questions:
  - `states_constraint` (noul): the none-verdict gate, also scored on the gold's
    zero-constraint ADRs, where the right answer is "no constraint".
  - `locus` (choice): sibling modules at one level, "which place".
  - `grain` (choice): the specificity ladder for that path, "how wide". This is
    the mistake gemini actually made: `openlobby.*` where the gold wants
    `openlobby.core.search.*`.

The ladder is derived from the gold subject, so a coarse-gold ADR gets finer
rungs appended and over-narrowing is visible too.

Ponytail: a spike, not the resolver. No ADG, no semble, no agent loop. If Jev
cannot beat the coarse reading where the gold is narrow, the System One
decomposition buys nothing and this file is deleted.

Run: uv run python app/tests/services/adg/run_jev_spike.py [adr_id ...]
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

ROOT = Path(__file__).resolve().parents[5]
REPO = ROOT / "dataset-Shepherd" / "small" / "openlobby-server"
ADR_DIR = REPO / "docs" / "architecture" / "decisions"
GOLD = ROOT / "Shepherd" / "tests" / "ground_truth" / "openlobby_ground_truth.json"
# What the gemini resolver emitted, from the #134 trace (logs/issue-134/run1).
TRACE = ROOT / "Shepherd" / "logs" / "issue-134" / "run1" / "resolver_traces.jsonl"


def _api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        return key
    # ponytail: .env is gitignored and not on the process env; walk up for it
    for parent in Path(__file__).resolve().parents:
        env_file = parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TYPESAFE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("TYPESAFE_API_KEY not found in environment or any parent .env")


def _gold_subjects() -> dict[str, str | None]:
    """adr number -> first gold subject, or None for a zero-constraint ADR."""
    out: dict[str, str | None] = {}
    for entry in json.loads(GOLD.read_text()):
        number = entry["adr_id"].removeprefix("ADR-")
        constraints = entry.get("constraints", [])
        out[number] = constraints[0]["subject"] if constraints else None
    return out


def _gemini_emitted() -> dict[str, str]:
    """adr number -> the subject gemini's resolver emitted in the #134 trace."""
    out: dict[str, str] = {}
    if not TRACE.exists():
        return out
    for line in TRACE.read_text().splitlines():
        record = json.loads(line)
        if not record["adr_path"].startswith("docs/architecture/decisions/"):
            continue
        number = record["adr_id"].removeprefix("ADR-")
        if record["edges"]:
            out[number] = record["edges"][0]["subject"]
    return out


def _prefixes(subject: str) -> list[str]:
    parts = subject.split(".")
    if parts[-1] == "*":
        parts = parts[:-1]
    return [".".join(parts[:i]) for i in range(1, len(parts) + 1)]


def _members(directory: Path, prefix: str) -> dict[str, str]:
    """Modules and subpackages directly under `directory`, as dotted names.

    Directories count: `openlobby.core.api` is a package, and a *.py-only glob
    drops it from the field, which silently removes the right answer.
    """
    if not directory.is_dir():
        return {}
    return {f"{prefix}.{path.stem}": f"the module named {path.stem}"
            for path in sorted(directory.iterdir())
            if path.stem != "__init__" and path.stem != "__pycache__"
            and (path.is_dir() or path.suffix == ".py")}


def _siblings(subject: str) -> dict[str, str]:
    """Modules beside the subject's leaf, from the real repo tree."""
    bare = _prefixes(subject)[-1]
    parent = ".".join(bare.split(".")[:-1])
    if not parent:
        return {}  # a top-level subject has no sibling field; locus is moot
    return _members(REPO / Path(*parent.split(".")), parent)


def _finer_rungs(bare: str) -> dict[str, str]:
    """Levels below the gold subject, so over-narrowing shows up too."""
    return {name: f"the namespace `{name}`"
            for name in _members(REPO / Path(*bare.split(".")), bare)}


def _questions(subject: str | None) -> dict:
    questions: dict = {
        "states_constraint": {
            "type": "noul",
            "instructions": (
                "Does this ADR state a constraint on which code may depend on what, "
                "or on where a piece of technology must live?"
            ),
            "criteria": {
                "true": "It mandates or forbids a dependency or a code locus",
                "false": "It is process, style, or history only",
            },
        },
    }
    if subject is None:
        return questions
    siblings = _siblings(subject)
    if siblings:
        questions["locus"] = {
            "type": "choice",
            "instructions": (
                "The ADR settles a technology choice. Which single module of "
                "`candidates` is the code locus where that choice is carried out?"
            ),
            "criteria": siblings,
        }
    bare = _prefixes(subject)[-1]
    ladder = {name: f"the namespace `{name}`" for name in _prefixes(subject)}
    ladder.update(_finer_rungs(bare))
    if len(ladder) > 1:
        questions["grain"] = {
            "type": "choice",
            "instructions": (
                "At which level of specificity does this ADR's decision apply? "
                "Pick the tightest namespace that still covers every place the "
                "decision must hold."
            ),
            "criteria": ladder,
        }
    return questions


def _ask(adr_text: str, questions: dict) -> dict:
    body = {"state": adr_text, "model": MODEL, "questions": questions}
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise SystemExit(f"HTTP {error.code}: {error.read().decode()[:500]}") from error


def _cell(answer: dict, key: str, gold_bare: str | None) -> str:
    """One table cell: the pick, its confidence, and whether it matches gold."""
    if key not in answer.get("answers", {}):
        return "n/a"
    picked = answer["answers"][key]["choice"]
    confidence = answer["answers"][key]["confidence"]
    mark = "" if gold_bare is None else (" =gold" if picked == gold_bare else " X")
    return f"{picked} ({confidence:.2f}){mark}"


def main() -> None:
    subjects = _gold_subjects()
    emitted = _gemini_emitted()
    wanted = sys.argv[1:] or sorted(subjects)
    rows = []
    for number in wanted:
        subject = subjects.get(number)
        adr_file = next(ADR_DIR.glob(f"{number}-*.md"))
        answer = _ask(adr_file.read_text(), _questions(subject))
        gold_bare = _prefixes(subject)[-1] if subject else None
        stated = answer["answers"]["states_constraint"]
        rows.append((
            number,
            gold_bare or "(none)",
            emitted.get(number, "?"),
            f"{stated['noul']:.2f}",
            _cell(answer, "locus", gold_bare),
            _cell(answer, "grain", gold_bare),
        ))
        print(f"  ... ADR-{number} done", file=sys.stderr)

    widths = [max(len(row[i]) for row in [("ADR", "gold", "gemini", "noul", "locus", "grain")] + rows)
              for i in range(6)]
    header = ("ADR", "gold", "gemini", "noul", "locus", "grain")
    print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))


if __name__ == "__main__":
    main()
