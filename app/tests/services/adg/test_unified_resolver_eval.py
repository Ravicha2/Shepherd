"""Unified resolver eval: score resolve_adr_constraints against openlobby ground truth.

Deterministic FQN pattern scoring (no LLM-as-judge). Runs the real unified resolver
against all 13 openlobby ADRs and scores resolved ConstraintEdges against human-curated
ground truth at tests/ground_truth/openlobby_ground_truth.json.

CLI: uv run --extra dev python -m tests.services.adg.test_unified_resolver_eval  (from app/)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

from services.adg.search import build_search_backend
from services.adg.treesitter import parse_repo
from services.adg.unified_resolver import resolve_adr_constraints
from services.extract.config import LangExtractConfig
from services.models import ConstraintEdge, ConstraintScope, PredicateType
from tests.eval_paths import report_path, write_report


REPO_ROOT = Path(__file__).resolve().parents[4]
REPOS_YAML_PATH = REPO_ROOT / "repos" / "repos.yaml"
GROUND_TRUTH_DIR = REPO_ROOT / "tests" / "ground_truth"


def _eval_repos() -> list[str]:
    """Eval set: smoke + eval group repos from repos.yaml that have a ground truth file.
    Ground-truth existence keeps not-yet-curated eval repos (e.g. tamr-client) out."""
    with open(REPOS_YAML_PATH) as f:
        repos = yaml.safe_load(f)
    return [
        r["id"] for r in repos["repos"]
        if r.get("group", "smoke") in ("eval", "smoke")
        and (GROUND_TRUTH_DIR / f"{r['id'].replace('-', '_')}_ground_truth.json").exists()
    ]


EVAL_REPOS = _eval_repos()

HAS_API_KEY = bool(os.environ.get("OPENROUTER_API_KEY"))

pytestmark = [
    pytest.mark.resolver_eval,
    pytest.mark.skipif(not HAS_API_KEY, reason="OPENROUTER_API_KEY not set"),
]


# -- FQN pattern scoring ----------------------------------------------------

def _is_ancestor(expected: str, resolved: str) -> bool:
    """True if resolved is a correct ancestor wildcard of expected.

    expected=app.api.users, resolved=app.api.* → True
    expected=app.api.*, resolved=app.*       → True
    expected=app.api, resolved=app.services.* → False
    """
    expected_base = expected.rstrip(".*")
    resolved_base = resolved.rstrip(".*")
    return expected_base.startswith(resolved_base + ".")


def _score_fqn(resolved: str, expected: str) -> str:
    if resolved == expected:
        return "exact_match"
    if _is_ancestor(expected, resolved) or _is_ancestor(resolved, expected):
        return "partial_match"
    if resolved.rstrip(".*") == expected.rstrip(".*"):
        # X.* vs X: same base, wildcard-granularity difference. On the object side
        # this mirrors the cpt engine's requires tolerance (a dependency anywhere
        # under X satisfies requires-on-X, engine.py target.startswith(object + ".")).
        return "partial_match"
    return "miss"


def _is_credited_fragment(edge: ConstraintEdge, expected_constraints: list[dict]) -> bool:
    """Many-to-one consolidation (issue #134): a resolved edge whose subject sits
    under an expected row's subject prefix (same predicate, object not a miss) is
    that row's mandate fragmented per-module, so it credits the row instead of
    counting a false positive, no double counting (the row keeps its own score). Known
    boundary: the gold prefix is kind-blind, so this also credits modules the
    ADR's mandate would exclude; a different predicate or an object miss never
    credits."""
    for expected in expected_constraints:
        try:
            expected_pred = PredicateType(expected["predicate"])
        except ValueError:
            continue
        if edge.predicate != expected_pred:
            continue
        if not _is_ancestor(edge.subject, expected["subject"]):
            continue
        if _score_fqn(edge.object, expected["object"]) != "miss":
            return True
    return False


_SCORE_RANK = {"exact_match": 2, "partial_match": 1, "miss": 0}


def _score_constraint(
    expected: dict, resolved_edges: list[ConstraintEdge]
) -> tuple[str, ConstraintEdge | None]:
    """Best score for one expected constraint against all resolved edges.

    Predicate must match. overall = min(subject_score, object_score).
    Records the best-effort edge on any predicate match, even if FQN score is miss,
    so the report shows what the resolver actually produced.
    """
    try:
        expected_pred = PredicateType(expected["predicate"])
    except ValueError:
        return "miss", None

    best: str | None = None
    best_edge: ConstraintEdge | None = None
    for edge in resolved_edges:
        if edge.predicate != expected_pred:
            continue
        subject_score = _score_fqn(edge.subject, expected["subject"])
        object_score = _score_fqn(edge.object, expected["object"])
        overall = min(subject_score, object_score, key=lambda s: _SCORE_RANK[s])
        if best is None or _SCORE_RANK[overall] > _SCORE_RANK[best]:
            best = overall
            best_edge = edge
    if best is None:
        return "miss", None
    return best, best_edge


# -- Eval result aggregation ------------------------------------------------

@dataclass
class EvalResult:
    results: list[dict] = field(default_factory=list)
    exact: int = 0
    partial: int = 0
    miss: int = 0
    total: int = 0
    false_positives: int = 0
    # ponytail: identities, not just the count — LLM runs don't reproduce, so
    # unmatched edges must be captured in the report to be triageable later
    false_positive_edges: list[dict] = field(default_factory=list)
    # #134 consolidation credits, itemized for the same reason: their absence
    # from false_positive_edges must be explainable from the report alone
    credited_fragments: list[dict] = field(default_factory=list)
    # #136 tooling-scope exclusions: edges held out of the FP count by declared
    # scope (tooling deps live in pyproject/setup.cfg/noxfile, not the import
    # graph), itemized so the exclusion stays reversible and auditable
    excluded_tooling_edges: list[dict] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return (self.exact + 0.5 * self.partial) / self.total if self.total else 0.0

    def to_report(self) -> dict:
        return {
            "exact": self.exact,
            "partial": self.partial,
            "miss": self.miss,
            "total": self.total,
            "false_positives": self.false_positives,
            "false_positive_edges": self.false_positive_edges,
            "credited_fragments": self.credited_fragments,
            "excluded_tooling_edges": self.excluded_tooling_edges,
            "accuracy": round(self.accuracy, 4),
            "per_constraint": self.results,
        }


# -- Ablation toggles (issue #131 search_off; #137 children_off/dependencies_off) --

def _flag_on(name: str) -> bool:
    return os.environ.get(name, "") not in ("", "0")


def _empty_search_backend(query: str, top_k: int = 10) -> list[dict]:
    """search_off arm: the tool stays declared and callable, the recall is gone."""
    return []


def _select_search_backend(repo_root: Path, adg):
    """The one branch run_eval executes, factored out so tests can pin it."""
    if _flag_on("ABLATION_SEARCH_OFF"):
        return _empty_search_backend
    return build_search_backend(repo_root, adg)


# -- #137 neighborhood-tool arms: five-surface scrubs (the #131 dependents_off
# lesson: removing only _TOOLS contaminates the arm, because a hallucinated call
# still hits _TOOL_FUNCTIONS and returns REAL data; the handler must go too, so a
# hallucination lands on the unknown-tool error branch instead).

from unittest.mock import patch
from contextlib import contextmanager

import services.adg.unified_resolver as unified_resolver

_NEIGHBORHOOD_SENTENCE_FULL = (
    "then inspect the neighborhood with list_children "
    "and list_dependencies to confirm the exact FQNs before writing a constraint."
)
_NEIGHBORHOOD_SENTENCE_WITHOUT_CHILDREN = (
    "then inspect the neighborhood with list_dependencies to confirm the exact FQNs before writing a constraint."
)
_NEIGHBORHOOD_SENTENCE_WITHOUT_DEPENDENCIES = (
    "then inspect the neighborhood with list_children "
    "to confirm the exact FQNs before writing a constraint."
)
_SEARCH_DESCRIPTION_FULL = "then inspect the hits with list_children / list_dependencies."
_SEARCH_DESCRIPTION_WITHOUT_CHILDREN = "then inspect the hits with list_dependencies."
_SEARCH_DESCRIPTION_WITHOUT_DEPENDENCIES = "then inspect the hits with list_children."
_EXAMPLE_ONE_STEP_THREE = 'Step 3: list_children("app.routes") \u2192 confirm the handler population'
_EXAMPLE_THREE_STEP_TWO = 'Step 2: list_children("app.services") \u2192 see the service classes that must inherit it'


def _scrubbed_tool_surface(removed_tool: str) -> tuple[list[dict], dict, str]:
    """Build the children_off/dependencies_off tool surface: scrub the removed
    tool's schema entry, dispatch handler, search_code description sentence,
    Required-exploration sentence, and (children only) both example steps.
    Returns (tools, handlers, prompt_template). Drift-asserts on every old string
    (#131 lesson: a silent no-op str.replace runs a contaminated arm)."""
    prompt_template = unified_resolver._SYSTEM_PROMPT_TEMPLATE

    if removed_tool == "list_children":
        replacements = [
            (_NEIGHBORHOOD_SENTENCE_FULL, _NEIGHBORHOOD_SENTENCE_WITHOUT_CHILDREN),
            (_EXAMPLE_ONE_STEP_THREE, ""),
            (_EXAMPLE_THREE_STEP_TWO, ""),
        ]
        search_description_pair = (_SEARCH_DESCRIPTION_FULL, _SEARCH_DESCRIPTION_WITHOUT_CHILDREN)
        example_step_deleted = True
    elif removed_tool == "list_dependencies":
        replacements = [(_NEIGHBORHOOD_SENTENCE_FULL, _NEIGHBORHOOD_SENTENCE_WITHOUT_DEPENDENCIES)]
        search_description_pair = (_SEARCH_DESCRIPTION_FULL, _SEARCH_DESCRIPTION_WITHOUT_DEPENDENCIES)
        example_step_deleted = False
    else:
        raise ValueError(f"unknown removed tool: {removed_tool}")

    for old_text, new_text in replacements:
        assert old_text in prompt_template, f"prompt drift, scrub no longer matches: {old_text!r}"
        prompt_template = prompt_template.replace(old_text, new_text)
    assert removed_tool not in prompt_template, "prompt scrub incomplete"

    tools = []
    for tool in unified_resolver._TOOLS:
        name = tool["function"]["name"]
        if name == removed_tool:
            continue
        description = tool["function"]["description"]
        if search_description_pair[0] in description:
            assert name == "search_code", "description scrub target is not search_code"
            description = description.replace(*search_description_pair)
        assert removed_tool not in description, "tool description scrub incomplete"
        tools.append({**tool, "function": {**tool["function"], "description": description}})
    assert len(tools) == 2, f"expected 2 tools after scrub, got {len(tools)}"

    handlers = {
        handler_name: handler
        for handler_name, handler in unified_resolver._TOOL_FUNCTIONS.items()
        if handler_name != removed_tool
    }
    assert removed_tool not in handlers, "handler scrub incomplete"
    assert example_step_deleted or removed_tool != "list_children"
    return tools, handlers, prompt_template


@contextmanager
def _neighborhood_tool_surface(removed_tool: str):
    """Apply the arm's five-surface edits for the duration of the eval loop only."""
    if not (_flag_on("ABLATION_CHILDREN_OFF") or _flag_on("ABLATION_DEPENDENCIES_OFF")):
        yield
        return
    if _flag_on("ABLATION_CHILDREN_OFF") and _flag_on("ABLATION_DEPENDENCIES_OFF"):
        raise RuntimeError("combined children_off+dependencies_off arm is out of scope (#137: one variable per arm)")
    removed_tool = "list_children" if _flag_on("ABLATION_CHILDREN_OFF") else "list_dependencies"
    tools, handlers, prompt_template = _scrubbed_tool_surface(removed_tool)
    with patch.object(unified_resolver, "_TOOLS", tools), \
         patch.object(unified_resolver, "_TOOL_FUNCTIONS", handlers), \
         patch.object(unified_resolver, "_SYSTEM_PROMPT_TEMPLATE", prompt_template):
        yield


# -- Fixtures ---------------------------------------------------------------

def _repo_root(repo_id: str) -> Path:
    with open(REPOS_YAML_PATH) as f:
        repos = yaml.safe_load(f)
    repo = next(r for r in repos["repos"] if r["id"] == repo_id)
    repo_path = Path(repo["url"])
    if not repo_path.is_absolute():
        repo_path = REPO_ROOT / "repos" / repo_path
    return repo_path


def _ground_truth_path(repo_id: str) -> Path:
    # ponytail: naming convention <repo_id>_ground_truth.json; "-" -> "_" for python-tuf
    return GROUND_TRUTH_DIR / f"{repo_id.replace('-', '_')}_ground_truth.json"


@pytest.fixture(scope="module", params=EVAL_REPOS, ids=lambda r: r)
def repo_id(request) -> str:
    return request.param


@pytest.fixture(scope="module")
def adg(repo_id) -> "object":
    return parse_repo(_repo_root(repo_id))


@pytest.fixture(scope="module")
def ground_truth(repo_id) -> list[dict]:
    with open(_ground_truth_path(repo_id)) as f:
        return json.load(f)


# -- Eval runner ------------------------------------------------------------

def run_eval(
    ground_truth: list[dict],
    adg,
    repo_id: str,
    report_to_disk: bool = False,
) -> EvalResult:
    """Run the unified resolver on every ADR fixture and score against ground truth."""
    repo_root = _repo_root(repo_id)
    search_backend = _select_search_backend(repo_root, adg)
    result = EvalResult()

    with _neighborhood_tool_surface(
        removed_tool="list_children" if _flag_on("ABLATION_CHILDREN_OFF") else "list_dependencies"
    ):
        for fixture in ground_truth:
            adr_text = (repo_root / fixture["adr_path"]).read_text()

            resolved_edges = resolve_adr_constraints(
                adr_text=adr_text,
                adr_id=fixture["adr_id"],
                adr_path=fixture["adr_path"],
                adg=adg,
                config=LangExtractConfig(),
                search_backend=search_backend,
            )

            expected_constraints = fixture.get("constraints", [])
            matched_edge_ids: set[int] = set()

            for expected in expected_constraints:
                score, matched = _score_constraint(expected, resolved_edges)
                if matched is not None:
                    matched_edge_ids.add(id(matched))
                result.results.append({
                    "adr_id": fixture["adr_id"],
                    "expected": expected,
                    "score": score,
                    "resolved_subject": matched.subject if matched else None,
                    "resolved_object": matched.object if matched else None,
                })
                result.total += 1
                if score == "exact_match":
                    result.exact += 1
                elif score == "partial_match":
                    result.partial += 1
                else:
                    result.miss += 1

            for edge in resolved_edges:
                if id(edge) in matched_edge_ids:
                    continue
                entry = {
                    "adr_id": fixture["adr_id"],
                    "subject": edge.subject,
                    "predicate": edge.predicate.value,
                    "object": edge.object,
                }
                if _is_credited_fragment(edge, expected_constraints):
                    result.credited_fragments.append(entry)
                elif edge.scope is ConstraintScope.TOOLING:
                    result.excluded_tooling_edges.append(entry)
                else:
                    result.false_positives += 1
                    result.false_positive_edges.append(entry)

    if report_to_disk:
        write_report(report_path(repo_id), result.to_report())
    return result


# -- Test -------------------------------------------------------------------

def test_unified_resolver_eval(adg, ground_truth, repo_id) -> None:
    """End-to-end eval harness. Verifies scoring runs and tallies are consistent.
    Accuracy is reported, not gated — resolver quality is a separate concern."""
    result = run_eval(ground_truth, adg, repo_id, report_to_disk=True)
    print(f"\n[resolver_eval:{repo_id}] exact={result.exact} partial={result.partial} miss={result.miss} "
          f"total={result.total} false_positives={result.false_positives} "
          f"accuracy={result.accuracy:.3f}")
    assert result.total > 0
    assert result.exact + result.partial + result.miss == result.total


# -- CLI --------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    rid = sys.argv[1] if len(sys.argv) > 1 else "openlobby"
    with open(_ground_truth_path(rid)) as f:
        gt = json.load(f)
    adg_obj = parse_repo(_repo_root(rid))
    result = run_eval(gt, adg_obj, rid, report_to_disk=True)
    print(json.dumps(result.to_report(), indent=2))