"""Jev pre-reviewer gate spike: can Jev judge a finding before the reviewer sees it?

Replays the 221 already-annotated findings in research-exp-setup/annotations
through POST /v1/systemone. One request per case sheet, one `noul` per finding,
two questions each because they are different bets:
  - `real`:     does this finding identify a violation that must be fixed? This is
                the truth question, and on the dominant FP class (pre-existing at
                the pin) the answer is genuinely yes.
  - `definite`: is it stated as a definite, checkable violation of concrete code,
                rather than hedged, speculative, secondary, or documentation-level?
                This is the text-reachable proxy.

The label in the sheets is not "is this true" but "is this in this commit's known
violation set", so raw agreement is not the metric. The metric is: at the highest
threshold that drops no confirmed finding, how many dismissed ones fall, and are
they the text-reachable class or the provenance class.

Ponytail: a spike. It replays labels, it does not run an arm, and it writes nothing.

Run: uv run python benchmark/run_jev_pregate_spike.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import yaml

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

SHEPHERD = Path(__file__).resolve().parents[1]
RESEARCH = SHEPHERD.parent
ANNOTATIONS = RESEARCH / "research-exp-setup" / "annotations"
REPOS_YAML = SHEPHERD / "repos" / "repos.yaml"

QUESTION_KEYS = ("real", "definite")


def _api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        return key
    for parent in Path(__file__).resolve().parents:
        env_file = parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TYPESAFE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("TYPESAFE_API_KEY not found in environment or any parent .env")


def _repo_paths() -> dict[str, Path]:
    """repo id -> local repo root, from repos.yaml (urls are repos/ relative)."""
    config = yaml.safe_load(REPOS_YAML.read_text())
    base = SHEPHERD / "repos"
    return {entry["id"]: (base / entry["url"]).resolve() for entry in config["repos"]}


class AdrReader:
    def __init__(self) -> None:
        config = yaml.safe_load(REPOS_YAML.read_text())
        self._adr_dir = {entry["id"]: entry.get("adr_dir") for entry in config["repos"]}
        self._paths = _repo_paths()
        self._cache: dict[tuple[str, str], str] = {}

    def read(self, repo: str, adr_id: str) -> str:
        key = (repo, adr_id)
        if key in self._cache:
            return self._cache[key]
        adr_dir = self._adr_dir.get(repo)
        root = self._paths.get(repo)
        text = ""
        if adr_dir and root and root.is_dir():
            matches = sorted((root / adr_dir).glob(f"{adr_id}-*.md"))
            if matches:
                text = matches[0].read_text()
        self._cache[key] = text
        return text


def _ask(questions: dict, state: dict, attempt: int = 0) -> dict:
    body = {"state": state, "model": MODEL, "questions": questions}
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code in (429, 529) and attempt < 3:
            time.sleep(2 ** attempt)
            return _ask(questions, state, attempt + 1)
        raise SystemExit(f"HTTP {error.code}: {error.read().decode()[:400]}") from error


def _bucket(row: dict) -> str:
    """Why the annotator dismissed it, for reading the result only. The gate
    never sees this; it comes from the label file, not the finding."""
    why = (row.get("justification") or "").lower()
    if "pre-existing" in why or "preexisting" in why:
        return "pre-existing"
    if "not a known violation" in why or "known violation set" in why:
        return "not-in-known-set"
    if str(row.get("case_type")) in ("compliant_probe", "clean_merged_commit"):
        return "case-metadata"
    return "other"


def _questions_for(findings: list[dict], reader: AdrReader, repo: str) -> dict:
    """One question per finding per bet; each carries its own ADR text."""
    questions: dict = {}
    for index, row in enumerate(findings):
        adr_text = reader.read(repo, row["adr_id"]) or "(ADR text unavailable)"
        claim = " ".join(row["claim"].split())
        for key in QUESTION_KEYS:
            asked = (
                "Does the finding identify a violation of the ADR that concrete code "
                "in this repository must fix?"
                if key == "real" else
                "Is the finding stated as a definite, checkable violation of concrete "
                "code, rather than a hedged, speculative, secondary, or "
                "documentation-level observation?"
            )
            questions[f"{index}:{key}"] = {
                "type": "noul",
                "instructions": {
                    "adr": adr_text,
                    "finding": claim,
                    "question": f"{asked} Answer about `finding` against `adr`.",
                },
                "criteria": {
                    "true": "It does",
                    "false": "It does not",
                },
            }
    return questions


def _auc(rows: list[dict], key: str) -> float:
    """Rank-based AUC: probability a confirmed finding scores above a dismissed one."""
    confirmed = [r[key] for r in rows if r["verdict"] == "confirmed"]
    dismissed = [r[key] for r in rows if r["verdict"] == "dismissed"]
    if not confirmed or not dismissed:
        return float("nan")
    wins = sum(1.0 if c > d else 0.5 if c == d else 0.0
               for c in confirmed for d in dismissed)
    return wins / (len(confirmed) * len(dismissed))


def _gate_report(rows: list[dict], key: str) -> None:
    """The honest metric: the highest threshold that drops no confirmed finding."""
    confirmed = sorted((r[key] for r in rows if r["verdict"] == "confirmed"))
    if not confirmed:
        return
    floor = confirmed[0]
    kept = [r for r in rows if r[key] >= floor]
    dropped = [r for r in rows if r[key] < floor]
    dropped_dismissed = [r for r in dropped if r["verdict"] == "dismissed"]
    lost_confirmed = [r for r in dropped if r["verdict"] == "confirmed"]
    print(f"  {key:<9} AUC={_auc(rows, key):.3f}   "
          f"threshold={floor:.2f} keeps {len(kept)}/{len(rows)}")
    print(f"            dropped {len(dropped_dismissed)} dismissed, "
          f"lost {len(lost_confirmed)} confirmed")
    by_bucket: dict[str, int] = defaultdict(int)
    for row in dropped_dismissed:
        by_bucket[row["_bucket"]] += 1
    if dropped_dismissed:
        print("            dropped FP by cause: " + "  ".join(
            f"{name}={count}" for name, count in sorted(by_bucket.items())))
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["verdict"] == "dismissed":
            totals[row["_bucket"]] += 1
    print("            FP available by cause: " + "  ".join(
        f"{name}={count}" for name, count in sorted(totals.items())))


def _sweep(rows: list[dict], key: str) -> None:
    """Recall/precision tradeoff, so 'drops 0 confirmed' is not read as free."""
    print(f"  {key} threshold sweep (confirmed kept / dismissed dropped):")
    for step in range(1, 20):
        threshold = step * 0.05
        kept_confirmed = sum(1 for r in rows
                             if r["verdict"] == "confirmed" and r[key] >= threshold)
        dropped_dismissed = sum(1 for r in rows
                                if r["verdict"] == "dismissed" and r[key] < threshold)
        confirmed_total = sum(1 for r in rows if r["verdict"] == "confirmed")
        kept = kept_confirmed + (sum(1 for r in rows if r["verdict"] == "dismissed")
                                 - dropped_dismissed)
        precision = kept_confirmed / kept if kept else 0.0
        print(f"    >={threshold:.2f}  confirmed {kept_confirmed:>3}/{confirmed_total}"
              f"  FP dropped {dropped_dismissed:>3}  precision {precision:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="only the first N sheets")
    parser.add_argument("--save", type=Path, help="write the scored rows here")
    args = parser.parse_args()

    reader = AdrReader()
    sheets = sorted(ANNOTATIONS.glob("**/*.yml"))
    if args.limit:
        sheets = sheets[:args.limit]

    rows: list[dict] = []
    for position, sheet_file in enumerate(sheets, 1):
        sheet = yaml.safe_load(sheet_file.read_text()) or {}
        findings = sheet.get("findings") or []
        if not findings:
            continue
        answer = _ask(_questions_for(findings, reader, sheet["repo"]),
                      {"repo": sheet["repo"], "commit": sheet.get("commit")})
        for index, row in enumerate(findings):
            scored = {"verdict": row["verdict"], "arm": row["arm"],
                      "_bucket": _bucket({**row, "case_type": sheet.get("case_type")})}
            for key in QUESTION_KEYS:
                entry = answer["answers"].get(f"{index}:{key}")
                if entry:
                    scored[key] = entry["noul"]
            rows.append(scored)
        print(f"  [{position}/{len(sheets)}] {sheet['repo']} "
              f"{sheet_file.stem} ({len(findings)} findings)", flush=True)

    scored_rows = [r for r in rows if all(k in r for k in QUESTION_KEYS)]
    print(f"\nscored {len(scored_rows)}/{len(rows)} findings "
          f"({sum(1 for r in scored_rows if r['verdict'] == 'confirmed')} confirmed, "
          f"{sum(1 for r in scored_rows if r['verdict'] == 'dismissed')} dismissed)")
    for key in QUESTION_KEYS:
        _gate_report(scored_rows, key)
        _sweep(scored_rows, key)

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json.dumps(scored_rows, indent=1))
        print(f"  saved {len(scored_rows)} scored rows to {args.save}")

    spread: dict[str, list[float]] = defaultdict(list)
    for row in scored_rows:
        spread[row["verdict"]].append(row["definite"])
    for verdict, values in sorted(spread.items()):
        print(f"  definite scores on {verdict}: "
              f"min={min(values):.2f} med={sorted(values)[len(values) // 2]:.2f} "
              f"max={max(values):.2f}")


if __name__ == "__main__":
    main()
