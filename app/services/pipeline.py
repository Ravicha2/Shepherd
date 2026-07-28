"""ADG Pipeline: orchestrates constraint merge, specificity computation, augmentation, and detection.

Usage (production):
    pipeline = ADGPipeline()
    result = pipeline.run(repo_path, adr_dir, config, commit=sha)

Usage (tests, pure data):
    inputs = PipelineInputs(adg=adg, diff_result=diff)
    result = pipeline.run_prepared(inputs)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from services.adg.merge import add_external_nodes, merge_constraint_edges
from services.cpt.dismissal import Dismissal, filter_dismissed
from services.cpt.diff_processor import augment_adg
from services.cpt.engine import detect as cpt_detect
from services.models import ADG, ConstraintEdge, Diff, DiffResult
from services.resolver import MatchStatus

log = logging.getLogger(__name__)


def pattern_specificity(pattern: str) -> float:
    """Compute specificity for a constraint pattern string.

    Wildcard patterns (ending .*) get depth only.
    Exact patterns get depth + 1.0.

    Strips the .* wildcard suffix before counting depth so
    'app.routes.*' has depth 2 (not 3).
    """
    is_wildcard = pattern.endswith(".*")
    clean = pattern[:-2] if is_wildcard else pattern
    depth = len(clean.rstrip(".").split("."))
    return float(depth) + (0.0 if is_wildcard else 1.0)


def adg_with_specificity(adg: ADG) -> ADG:
    """Return a NEW ADG where every ConstraintEdge has specificity set.

    ConstraintEdges start with specificity=0.0 from the unified resolver;
    this computes pattern depth + exact bonus for each edge.
    """
    new_edges: list[ConstraintEdge] = []
    for edge in adg.constraint_edges:
        new_edges.append(ConstraintEdge(
            subject=edge.subject,
            predicate=edge.predicate,
            object=edge.object,
            justification=edge.justification,
            adr_id=edge.adr_id,
            adr_path=edge.adr_path,
            specificity=pattern_specificity(edge.subject),
        ))
    return ADG(
        nodes=list(adg.nodes),
        edges=list(adg.edges),
        constraint_edges=new_edges,
    )


# ---------------------------------------------------------------------------
# Mutation normalization
# ---------------------------------------------------------------------------

def augment_immutable(adg: ADG, diff: Diff) -> ADG:
    """Wrap the in-place augment_adg so it returns a fresh ADG.

    Callers never see their input ADG mutated.
    """
    clone = ADG(
        nodes=list(adg.nodes),
        edges=list(adg.edges),
        constraint_edges=list(adg.constraint_edges),
    )
    augment_adg(clone, diff)
    return clone


# ---------------------------------------------------------------------------
# Pure-data test input
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineInputs:
    """Everything needed to run detection without touching git/filesystem/LLM."""
    adg: ADG
    diff_result: DiffResult
    diff: Diff | None = None
    project_root: Path | None = None


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

class ADGPipeline:
    """Orchestrates the full ADG -> CPT detection pipeline."""

    def run_prepared(self, inputs: PipelineInputs) -> "CPTResult":
        """Pure pipeline: no io, no mutation surprises.

        Add external nodes, compute specificity, optionally augment, then detect.
        """
        from services.cpt.engine import CPTResult

        merged = add_external_nodes(inputs.adg, project_root=inputs.project_root)
        merged = adg_with_specificity(merged)

        if inputs.diff is not None:
            merged = augment_immutable(merged, inputs.diff)

        return cpt_detect(inputs.diff_result, merged)

    def run_with_dismissals(self, inputs: PipelineInputs, dismissals: list[Dismissal]) -> "CPTResult":
        """Run detect pipeline, then filter out dismissed violations.

        Pure function: no io, dismissals passed in by caller.
        """
        from services.cpt.engine import CPTResult

        result = self.run_prepared(inputs)
        filtered = filter_dismissed(result.violations, dismissals)
        return CPTResult(
            violations=filtered,
            orphans=result.orphans,
            self_loop_constraints=result.self_loop_constraints,
        )

    @staticmethod
    def build_seed(adg: ADG, adr_dir: Path, project_root: Path | None = None, config: "LangExtractConfig | None" = None) -> ADG:
        """Resolve ADRs via unified agent, merge constraints, compute specificity.

        Discovers ADR markdown files in adr_dir, resolves each to ConstraintEdges,
        merges them into the ADG, and computes specificity.

        For cli/main.py:seed_build().
        """
        from services.adg.unified_resolver import resolve_adr_constraints
        from services.extract.config import LangExtractConfig

        if config is None:
            raise ValueError("config is required for unified resolver")

        adr_path = Path(adr_dir)
        adr_files = sorted(adr_path.glob("*.md"))
        if not adr_files:
            log.warning("build_seed: no ADR files found in %s", adr_path)
            merged = add_external_nodes(adg, project_root=project_root)
            return adg_with_specificity(merged)

        log.info("build_seed: resolving %d ADR files from %s", len(adr_files), adr_path)

        all_edges: list[ConstraintEdge] = []
        for adr_file in adr_files:
            adr_text = adr_file.read_text(encoding="utf-8")
            adr_id = adr_file.stem
            edges = resolve_adr_constraints(adr_text, adr_id, str(adr_file), adg, config)
            log.info("build_seed: %s produced %d constraint edges", adr_id, len(edges))
            all_edges.extend(edges)

        merged = merge_constraint_edges(adg, all_edges, project_root=project_root)
        merged = add_external_nodes(merged, project_root=project_root)
        return adg_with_specificity(merged)