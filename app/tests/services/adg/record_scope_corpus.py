"""#157 scope-corpus recorder: capture ONE real resolver session per benchmark ADR.

Runs the production `resolve_adr_constraints` (real LLM, real tools) over every
benchmark-gold ADR and commits the raw final assistant response per ADR. The
committed fixtures are then replayed zero-LLM by `test_scope_corpus.py`, which
pins the per-edge scope plumbing (ADR 019) with recorded real outputs.

The recorder wraps the OpenAI client: every real response passes through
untouched, and the final no-tool-call assistant content is captured. Nothing
about the resolver is stubbed or altered.

Usage (from app/, needs OPENROUTER_API_KEY):
  uv run --extra dev python -m tests.services.adg.record_scope_corpus
  uv run --extra dev python -m tests.services.adg.record_scope_corpus flowkit

Writes: ../benchmark/scope_fixtures/<repo>.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import services.adg.unified_resolver as unified_resolver
from services.adg.search import build_search_backend
from services.adg.treesitter import parse_repo
from services.extract.config import LangExtractConfig

from tests.services.adg.test_benchmark_arms_eval import _load_gold, _repo_roots
from tests.services.adg.test_unified_resolver_eval import _repo_root

REPO_ROOT = Path(__file__).resolve().parents[4]  # Shepherd/
FIXTURE_DIR = REPO_ROOT / "benchmark" / "scope_fixtures"

# ADR 019 supersedes a whole-ADR regex; the benchmark gold set is its corpus.
BENCHMARK_REPOS = ["python-tuf", "flowkit", "experimenter", "structurizr-python"]


class _RecordingClient:
    """Transparent proxy: forwards to the real client, records final contents."""

    def __init__(self, real_client):
        self._real = real_client
        self.contents: list[str] = []
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        response = self._real.chat.completions.create(**kwargs)
        message = response.choices[0].message
        if not getattr(message, "tool_calls", None) and getattr(message, "content", None):
            self.contents.append(message.content)
        return response


def record_repo(repo_id: str) -> dict:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")

    gold, instances = _load_gold(repo_id)
    repo_root = _repo_root(repo_id)
    adg = parse_repo(repo_root)
    roots = _repo_roots(adg)
    search_backend = build_search_backend(repo_root, adg)
    config = LangExtractConfig()

    real_openai = unified_resolver.OpenAI

    entries: list[dict] = []
    for fixture in gold:
        recorder = _RecordingClient(real_openai(api_key=config.api_key, base_url=config.model_url))
        unified_resolver.OpenAI = lambda **kwargs: recorder
        try:
            unified_resolver.resolve_adr_constraints(
                adr_text=(repo_root / fixture["adr_path"]).read_text(),
                adr_id=fixture["adr_id"],
                adr_path=fixture["adr_path"],
                adg=adg,
                config=config,
                search_backend=search_backend,
            )
        finally:
            unified_resolver.OpenAI = real_openai

        entries.append({
            "adr_id": fixture["adr_id"],
            "adr_path": fixture["adr_path"],
            "raw_response": recorder.contents[-1] if recorder.contents else "",
        })
        print(f"  {repo_id} {fixture['adr_id']}: captured {len(recorder.contents)} final response(s)")

    return {
        "repo_id": repo_id,
        "roots": sorted(roots),
        "pin_commit": instances.get("pin_commit"),
        "model_id": config.model_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "adrs": entries,
    }


def write_triage_report() -> Path:
    """Zero-LLM: summarize the committed fixtures' triage quality as data.

    Layer 1 pins plumbing + recall-safety (`test_scope_corpus.py`); the triage
    quality gate is #158's k>=2 confusion matrix. This artifact records what the
    one committed run produced against the #157 named expectations so the gap is
    visible and diffable, not silent."""
    from tests.services.adg.test_scope_corpus import NAMED_EXPECTATIONS, _triage_rows

    rows = _triage_rows()
    report = {
        "note": (
            "One recorded run per benchmark ADR (benchmark/scope_fixtures). "
            "Quality is reported, gated in #158 (k>=2). Layer 1 (#157) pins plumbing "
            "and recall-safety only (ADR 019)."
        ),
        "n_adrs": len(rows),
        "named_expectation_matches": sum(1 for r in rows if r["named_match"] is True),
        "named_expectation_checked": sum(1 for r in rows if r["named_expected"]),
        "rows": rows,
    }
    out = FIXTURE_DIR / "TRIAGE_REPORT.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return out


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--report"]:
        out = write_triage_report()
        print(f"wrote {out}")
        return 0
    repos = argv[1:] or BENCHMARK_REPOS
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for repo_id in repos:
        print(f"recording {repo_id} ...")
        payload = record_repo(repo_id)
        out = FIXTURE_DIR / f"{repo_id.replace('-', '_')}.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {out} ({len(payload['adrs'])} ADRs)")
    write_triage_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
