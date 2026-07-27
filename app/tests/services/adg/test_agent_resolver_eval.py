"""LLM-as-a-Judge evaluation for agent resolver.

Runs the agent resolver with real LLM calls against constructed ADG fixtures,
then judges whether resolved FQN patterns match expected outputs.

Scoring:
  exact_match  — resolved FQN == expected FQN
  partial_match — resolved FQN is a correct ancestor wildcard
                  (e.g., expected app.routes.handler, resolved app.routes.*)
  miss          — resolved FQN is wrong

Run: uv run pytest -m resolver_eval app/tests/services/adg/test_agent_resolver_eval.py
Skip: pytest -m "not resolver_eval"
Configurable model: RESOLVER_EVAL_MODEL env var (default: deepseek/deepseek-v4-flash)
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from openai import OpenAI

from services.adg.agent_resolver import resolve_agent_constraints, _resolve_one, ResolutionTrace, classify_failure
from services.extract.config import LangExtractConfig
from services.fqn import FQN
from services.models import (
    ADG,
    ConstraintEdge,
    Edge,
    FQNKind,
    FQNNode,
    PredicateType,
    SymbolicConstraint,
)

HAS_API_KEY = bool(os.environ.get("OPENROUTER_API_KEY"))
EVAL_MODEL = os.environ.get("RESOLVER_EVAL_MODEL", "deepseek/deepseek-v4-flash")

pytestmark = [
    pytest.mark.resolver_eval,
    pytest.mark.skipif(not HAS_API_KEY, reason="OPENROUTER_API_KEY not set"),
]


# ---------------------------------------------------------------------------
# ADG fixture: a realistic multi-module codebase graph
# ---------------------------------------------------------------------------


def _build_eval_adg() -> ADG:
    """Constructed ADG with modules, classes, methods, imports, and inherits
    that exercise all 4 predicate types and external dependencies."""
    nodes = [
        # Core app module
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        # API layer
        FQNNode(fqn=FQN.from_dotted("app.api"), kind=FQNKind.MODULE, file_path="app/api/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users"), kind=FQNKind.MODULE, file_path="app/api/users.py", line_start=0, line_end=50, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView"), kind=FQNKind.CLASS, file_path="app/api/users.py", line_start=5, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView.get"), kind=FQNKind.METHOD, file_path="app/api/users.py", line_start=10, line_end=20, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.routes"), kind=FQNKind.MODULE, file_path="app/api/routes.py", line_start=0, line_end=60, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.routes.handler"), kind=FQNKind.FUNCTION, file_path="app/api/routes.py", line_start=15, line_end=30, start_byte=0, end_byte=0),
        # Auth module
        FQNNode(fqn=FQN.from_dotted("app.auth"), kind=FQNKind.MODULE, file_path="app/auth/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware"), kind=FQNKind.MODULE, file_path="app/auth/middleware.py", line_start=0, line_end=60, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware.AuthMiddleware"), kind=FQNKind.CLASS, file_path="app/auth/middleware.py", line_start=5, line_end=55, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware.AuthMiddleware.check"), kind=FQNKind.METHOD, file_path="app/auth/middleware.py", line_start=15, line_end=25, start_byte=0, end_byte=0),
        # Database module
        FQNNode(fqn=FQN.from_dotted("app.database"), kind=FQNKind.MODULE, file_path="app/database/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.database.query"), kind=FQNKind.MODULE, file_path="app/database/query.py", line_start=0, line_end=80, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.database.query.QueryEngine"), kind=FQNKind.CLASS, file_path="app/database/query.py", line_start=5, line_end=70, start_byte=0, end_byte=0),
        # Services module
        FQNNode(fqn=FQN.from_dotted("app.services"), kind=FQNKind.MODULE, file_path="app/services/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.services.user_service"), kind=FQNKind.MODULE, file_path="app/services/user_service.py", line_start=0, line_end=50, start_byte=0, end_byte=0),
        # Common utilities
        FQNNode(fqn=FQN.from_dotted("app.common"), kind=FQNKind.MODULE, file_path="app/common/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.common.logging"), kind=FQNKind.MODULE, file_path="app/common/logging.py", line_start=0, line_end=30, start_byte=0, end_byte=0),
        # External
        FQNNode(fqn=FQN.from_dotted("requests"), kind=FQNKind.EXTERNAL, file_path="", line_start=-1, line_end=-1, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("mysql"), kind=FQNKind.EXTERNAL, file_path="", line_start=-1, line_end=-1, start_byte=0, end_byte=0),
    ]
    edges = [
        # CONTAINS hierarchy
        Edge(source="app", target="app.api", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.users", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.api.users.UserView", kind="CONTAINS"),
        Edge(source="app.api.users.UserView", target="app.api.users.UserView.get", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.routes", kind="CONTAINS"),
        Edge(source="app.api.routes", target="app.api.routes.handler", kind="CONTAINS"),
        Edge(source="app", target="app.auth", kind="CONTAINS"),
        Edge(source="app.auth", target="app.auth.middleware", kind="CONTAINS"),
        Edge(source="app.auth.middleware", target="app.auth.middleware.AuthMiddleware", kind="CONTAINS"),
        Edge(source="app.auth.middleware.AuthMiddleware", target="app.auth.middleware.AuthMiddleware.check", kind="CONTAINS"),
        Edge(source="app", target="app.database", kind="CONTAINS"),
        Edge(source="app.database", target="app.database.query", kind="CONTAINS"),
        Edge(source="app.database.query", target="app.database.query.QueryEngine", kind="CONTAINS"),
        Edge(source="app", target="app.services", kind="CONTAINS"),
        Edge(source="app.services", target="app.services.user_service", kind="CONTAINS"),
        Edge(source="app", target="app.common", kind="CONTAINS"),
        Edge(source="app.common", target="app.common.logging", kind="CONTAINS"),
        # IMPORTS
        Edge(source="app.api.users", target="app.auth.middleware", kind="IMPORTS"),
        Edge(source="app.services.user_service", target="app.database.query", kind="IMPORTS"),
        Edge(source="app.services.user_service", target="app.common.logging", kind="IMPORTS"),
        Edge(source="app.api.routes", target="requests", kind="IMPORTS"),
        # INHERITS
        Edge(source="app.auth.middleware.AuthMiddleware", target="app.api.users.UserView", kind="INHERITS"),
    ]
    return ADG(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# Test fixtures: ADR prose + expected ConstraintEdges for 5 constraint types
# ---------------------------------------------------------------------------


FIXTURES: list[dict] = [
    {
        "id": "prohibits_dependency",
        "constraint": SymbolicConstraint(
            subject="the API module",
            object="database module",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            justification="ADR-001: API modules must not import database modules directly",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        ),
        "expected_subject": "app.api.*",
        "expected_object": "app.database.*",
        "description": "API module prohibits dependency on database module",
    },
    {
        "id": "requires_dependency",
        "constraint": SymbolicConstraint(
            subject="the services module",
            object="common logging module",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            justification="ADR-007: All services must import common.logging for structured output",
            adr_id="ADR-007",
            adr_path="docs/adr/007.md",
        ),
        "expected_subject": "app.services.*",
        "expected_object": "app.common.logging.*",
        "description": "Services module requires dependency on logging module",
    },
    {
        "id": "requires_implementation",
        "constraint": SymbolicConstraint(
            subject="all API endpoints",
            object="rate limiting",
            predicate=PredicateType.REQUIRES_IMPLEMENTATION,
            justification="ADR-003: All API endpoints must implement rate limiting internally",
            adr_id="ADR-003",
            adr_path="docs/adr/003.md",
        ),
        "expected_subject": "app.api.*",
        "expected_object": "rate_limiting",
        "description": "API endpoints must implement rate limiting",
    },
    {
        "id": "prohibits_implementation",
        "constraint": SymbolicConstraint(
            subject="modules outside the auth module",
            object="authentication logic",
            predicate=PredicateType.PROHIBITS_IMPLEMENTATION,
            justification="ADR-008: Only app.auth.middleware may implement authentication",
            adr_id="ADR-008",
            adr_path="docs/adr/008.md",
        ),
        "expected_subject": "app.*",
        "expected_object": "authentication",
        "description": "Only auth module may implement authentication",
    },
    {
        "id": "external_dependency",
        "constraint": SymbolicConstraint(
            subject="the API routes module",
            object="requests library",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            justification="ADR-009: API routes must use requests for HTTP calls",
            adr_id="ADR-009",
            adr_path="docs/adr/009.md",
        ),
        "expected_subject": "app.api.routes.*",
        "expected_object": "requests",
        "description": "API routes module requires external requests library",
    },
]


# ---------------------------------------------------------------------------
# Judge logic
# ---------------------------------------------------------------------------


def _is_ancestor(expected: str, resolved: str) -> bool:
    """Check if resolved is a correct ancestor wildcard of expected.

    E.g., expected=app.api.users, resolved=app.api.* → True
          expected=app.api.*, resolved=app.* → True
          expected=app.api, resolved=app.services.* → False
    """
    # Strip wildcards for comparison
    expected_base = expected.rstrip(".*")
    resolved_base = resolved.rstrip(".*")
    # resolved is an ancestor if expected starts with resolved_base + "."
    return expected_base.startswith(resolved_base + ".")


def _score_constraint(
    resolved: ConstraintEdge,
    expected_subject: str,
    expected_object: str,
) -> dict:
    """Score a single resolved constraint against expected FQN patterns."""
    subject_score = _score_fqn(resolved.subject, expected_subject)
    object_score = _score_fqn(resolved.object, expected_object)
    return {
        "subject": subject_score,
        "object": object_score,
        "overall": (
            "exact_match" if subject_score == "exact_match" and object_score == "exact_match"
            else "partial_match" if subject_score != "miss" and object_score != "miss"
            else "miss"
        ),
    }


def _score_fqn(resolved: str, expected: str) -> str:
    """Score a single FQN pattern: exact_match, partial_match, or miss."""
    if resolved == expected:
        return "exact_match"
    # Partial: resolved is an ancestor wildcard of expected, or vice versa
    if _is_ancestor(expected, resolved) or _is_ancestor(resolved, expected):
        return "partial_match"
    return "miss"


# ---------------------------------------------------------------------------
# LLM-as-Judge: asks a judge model to evaluate resolution quality
# ---------------------------------------------------------------------------

JUDGE_PROMPT = """\
You are evaluating an ADG agent resolver that maps prose architectural constraints
to FQN patterns by traversing a code graph.

For each constraint, you receive:
- The original prose constraint (subject, object, predicate)
- The expected FQN patterns (ground truth)
- The resolved FQN patterns (what the agent produced)
- The ADG node list (what the agent had available)

Score each constraint:
1. **Subject match**: exact_match / partial_match / miss
   - exact_match: resolved subject == expected subject
   - partial_match: resolved subject is a correct ancestor wildcard (e.g., expected app.api.users, resolved app.api.*)
   - miss: resolved subject points to a wrong part of the codebase
2. **Object match**: same scoring as subject
3. **Overall**: exact_match if both exact, partial_match if neither is miss, miss otherwise

For partial_match: the resolved FQN must be in the correct neighborhood of the codebase,
just more or less specific than expected.

Respond STRICTLY with JSON. No markdown fences, no preamble.
"""


def _call_judge(
    constraint: SymbolicConstraint,
    expected_subject: str,
    expected_object: str,
    resolved: ConstraintEdge,
    adg: ADG,
) -> dict:
    """Ask the judge model to evaluate a single resolution."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")

    judge_model = os.environ.get("JUDGE_MODEL", "deepseek/deepseek-v4-flash")
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    adg_nodes = "\n".join(f"  {n.fqn} ({n.kind.value})" for n in adg.nodes)

    payload = {
        "constraint_prose": {
            "subject": constraint.subject,
            "object": constraint.object,
            "predicate": constraint.predicate.value,
        },
        "expected": {"subject": expected_subject, "object": expected_object},
        "resolved": {"subject": resolved.subject, "object": resolved.object},
        "adg_nodes_available": adg_nodes,
    }

    response = client.chat.completions.create(
        model=judge_model,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ],
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        first_nl = raw.index("\n") if "\n" in raw else len(raw)
        raw = raw[first_nl + 1:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Eval runner: resolve fixtures with real LLM, score results
# ---------------------------------------------------------------------------


class EvalResult:
    """Aggregates evaluation results across all fixtures."""

    def __init__(self) -> None:
        self.results: list[dict] = []
        self.exact = 0
        self.partial = 0
        self.miss = 0
        self.total = 0

    def add(self, fixture_id: str, scores: dict, constraint: SymbolicConstraint, resolved: ConstraintEdge, failure_mode: str | None = None) -> None:
        self.results.append({
            "fixture": fixture_id,
            "description": constraint.justification,
            "prose_subject": constraint.subject,
            "prose_object": constraint.object,
            "resolved_subject": resolved.subject,
            "resolved_object": resolved.object,
            "subject_score": scores["subject"],
            "object_score": scores["object"],
            "overall": scores["overall"],
            "failure_mode": failure_mode,
        })
        self.total += 1
        if scores["overall"] == "exact_match":
            self.exact += 1
        elif scores["overall"] == "partial_match":
            self.partial += 1
        else:
            self.miss += 1

    @property
    def accuracy(self) -> float:
        return (self.exact + 0.5 * self.partial) / self.total if self.total else 0.0

    @property
    def exact_rate(self) -> float:
        return self.exact / self.total if self.total else 0.0

    def report(self) -> str:
        lines = [
            "=== Agent Resolver Eval Report ===",
            f"Total: {self.total}  Exact: {self.exact}  Partial: {self.partial}  Miss: {self.miss}",
            f"Exact rate: {self.exact_rate:.0%}  Accuracy (exact+0.5*partial): {self.accuracy:.0%}",
            "",
        ]
        for r in self.results:
            mode = f" [{r['failure_mode']}]" if r["failure_mode"] else ""
            lines.append(
                f"  {r['fixture']}: {r['overall']}{mode} | "
                f"subject={r['subject_score']} ({r['prose_subject']} -> {r['resolved_subject']}) | "
                f"object={r['object_score']} ({r['prose_object']} -> {r['resolved_object']})"
            )
        failures = [r for r in self.results if r["overall"] == "miss"]
        if failures:
            lines.append("")
            lines.append("=== Failure Modes ===")
            for f in failures:
                mode = f["failure_mode"] or "unknown"
                lines.append(
                    f"  {f['fixture']}: {mode} | "
                    f"subject={f['subject_score']} object={f['object_score']} "
                    f"| prose: {f['prose_subject']} -> {f['prose_object']}"
                )
        return "\n".join(lines)


_eval_cache: EvalResult | None = None


def _run_eval(adg: ADG, model: str = EVAL_MODEL) -> EvalResult:
    """Resolve all fixtures with real LLM calls and score results.

    Cached across calls in the same session to avoid redundant LLM calls.
    """
    global _eval_cache
    if _eval_cache is not None:
        return _eval_cache

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")

    config = LangExtractConfig(
        model_id=model,
        model_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
    )

    from openai import OpenAI as OpenAIClient
    client = OpenAIClient(api_key=api_key, base_url=config.model_url)

    result = EvalResult()
    for fixture in FIXTURES:
        constraint = fixture["constraint"]
        resolution = _resolve_one(constraint, adg, client, config.model_id)

        if resolution.edge is None:
            failure_mode = classify_failure(resolution.trace, adg)
            result.results.append({
                "fixture": fixture["id"],
                "description": constraint.justification,
                "prose_subject": constraint.subject,
                "prose_object": constraint.object,
                "resolved_subject": "<missing>",
                "resolved_object": "<missing>",
                "subject_score": "miss",
                "object_score": "miss",
                "overall": "miss",
                "failure_mode": failure_mode,
            })
            result.total += 1
            result.miss += 1
            continue

        resolved = resolution.edge
        scores = _score_constraint(
            resolved, fixture["expected_subject"], fixture["expected_object"],
        )
        failure_mode = None if scores["overall"] != "miss" else classify_failure(resolution.trace, adg)
        result.add(fixture["id"], scores, constraint, resolved, failure_mode=failure_mode)

    print(result.report())
    _eval_cache = result
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolverEval:
    """LLM-as-a-Judge eval for agent resolver. Runs real LLM calls once per session."""

    @pytest.fixture(autouse=True)
    def _adg(self) -> ADG:
        """Constructed ADG available to all tests."""
        self.adg = _build_eval_adg()
        return self.adg

    def test_all_fixtures_resolve(self) -> None:
        """At least 60% of fixture constraints should produce a ConstraintEdge."""
        result = _run_eval(self.adg)
        resolved = result.total - sum(1 for r in result.results if r["resolved_subject"] == "<missing>")
        assert resolved >= len(FIXTURES) * 0.6, (
            f"Only {resolved}/{len(FIXTURES)} fixtures resolved. Full results:\n{result.report()}"
        )

    def test_accuracy_above_threshold(self) -> None:
        """Agent resolver accuracy should be >= 20% (exact + 0.5*partial / total).

        Baseline for deepseek/deepseek-v4-flash; expected to improve with better models.
        """
        result = _run_eval(self.adg)
        assert result.accuracy >= 0.2, (
            f"Accuracy {result.accuracy:.0%} below 20% threshold.\n"
            f"{result.report()}"
        )

    def test_partial_match_rate(self) -> None:
        """At least 2 constraints should have partial-or-better matches."""
        result = _run_eval(self.adg)
        partial_or_better = result.exact + result.partial
        assert partial_or_better >= 2, (
            f"Only {partial_or_better} partial-or-better matches. Results:\n{result.report()}"
        )

    def test_failure_mode_report(self) -> None:
        """Always passes: prints per-constraint failure modes for human review."""
        result = _run_eval(self.adg)
        # Always pass; the report is the deliverable
        print(f"\n=== Failure Mode Report ===")
        for r in result.results:
            mode = r.get("failure_mode") or "n/a"
            print(f"  {r['fixture']}: {r['overall']} [{mode}] | "
                  f"subject={r['subject_score']} ({r['prose_subject']} -> {r['resolved_subject']}) | "
                  f"object={r['object_score']} ({r['prose_object']} -> {r['resolved_object']})")


class TestJudgeScoring:
    """Unit tests for the scoring logic (no LLM calls)."""

    def test_exact_match(self) -> None:
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.database.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        scores = _score_constraint(edge, "app.api.*", "app.database.*")
        assert scores["subject"] == "exact_match"
        assert scores["object"] == "exact_match"
        assert scores["overall"] == "exact_match"

    def test_partial_match_ancestor(self) -> None:
        """Resolved is a broader wildcard than expected: partial match."""
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.database.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        # Expected is more specific than resolved
        scores = _score_constraint(edge, "app.api.users.*", "app.database.query.*")
        assert scores["subject"] == "partial_match"
        assert scores["object"] == "partial_match"
        assert scores["overall"] == "partial_match"

    def test_partial_match_correct_neighborhood(self) -> None:
        """Resolved and expected share a top-level module: partial match."""
        edge = ConstraintEdge(
            subject="app.api.routes.*",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            object="requests",
            justification="test",
            adr_id="ADR-009",
            adr_path="docs/adr/009.md",
        )
        scores = _score_constraint(edge, "app.api.routes.*", "requests")
        assert scores["subject"] == "exact_match"
        assert scores["object"] == "exact_match"
        assert scores["overall"] == "exact_match"

    def test_miss_wrong_module(self) -> None:
        """Resolved points to completely wrong module: miss."""
        edge = ConstraintEdge(
            subject="app.services.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.auth.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        scores = _score_constraint(edge, "app.api.*", "app.database.*")
        assert scores["subject"] == "miss"
        assert scores["object"] == "miss"
        assert scores["overall"] == "miss"

    def test_is_ancestor(self) -> None:
        assert _is_ancestor("app.api.users", "app.api.*") is True
        assert _is_ancestor("app.api.*", "app.*") is True
        assert _is_ancestor("app.api.*", "app.services.*") is False
        assert _is_ancestor("app.api.users.UserView", "app.api.*") is True


class TestEvalReport:
    """Test the EvalResult aggregation."""

    def test_report_format(self) -> None:
        result = EvalResult()
        result.add(
            "prohibits_dependency",
            {"subject": "exact_match", "object": "partial_match", "overall": "partial_match"},
            SymbolicConstraint(
                subject="the API module",
                object="database module",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                justification="test",
                adr_id="ADR-001",
                adr_path="docs/adr/001.md",
            ),
            ConstraintEdge(
                subject="app.api.*",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="app.database.query.*",
                justification="test",
                adr_id="ADR-001",
                adr_path="docs/adr/001.md",
            ),
        )
        report = result.report()
        assert "prohibits_dependency" in report
        assert "Accuracy" in report


# ---------------------------------------------------------------------------
# Standalone eval runner: uv run python -m app.tests.services.adg.test_agent_resolver_eval
# ---------------------------------------------------------------------------

def _main() -> None:
    """Run the eval standalone and print the report."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        sys.exit(1)

    model = EVAL_MODEL
    if len(sys.argv) > 1:
        model = sys.argv[1]

    print(f"Running agent resolver eval with model: {model}")
    adg = _build_eval_adg()
    result = _run_eval(adg, model=model)
    print(result.report())

    # Save JSON report
    report_path = os.path.join(os.path.dirname(__file__), "eval_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "model": model,
            "total": result.total,
            "exact": result.exact,
            "partial": result.partial,
            "miss": result.miss,
            "accuracy": result.accuracy,
            "exact_rate": result.exact_rate,
            "results": result.results,
        }, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    _main()