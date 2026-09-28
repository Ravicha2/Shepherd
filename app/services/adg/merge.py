"""Merge Layer: unify AST ADG with resolved ConstraintEdges.

Adds EXTERNAL nodes for orphan FQNs and merges constraint edges into the ADG.
"""
from __future__ import annotations

import configparser
import logging
import re
from pathlib import Path

from services.models import (
    ADG,
    ConstraintEdge,
    DependencyRole,
    FQNNode,
)

log = logging.getLogger(__name__)

PYTHON_DEV_TOOLS: frozenset[str] = frozenset({
    "pytest", "py", "nose", "nose2", "unittest",
    "black", "autopep8", "yapf",
    "mypy", "pyre", "pytype",
    "flake8", "pylint", "pyflakes", "pydocstyle", "ruff",
    "isort", "bandit",
    "tox", "nox",
    "coverage", "pytest_cov",
    "sphinx", "mkdocs",
    "setuptools", "wheel", "pip", "build",
    "twine", "pre_commit",
})

_DEV_EXTRA_NAMES: frozenset[str] = frozenset({
    "dev", "development", "dev-dependencies",
    "test", "tests", "testing",
    "lint", "linting",
    "typing", "types",
    "docs", "documentation",
})

_PACKAGE_NAME_RE = re.compile(r"^([a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?)")


def _extract_package_name(dep_spec: str) -> str:
    """Extract normalized package name from a PEP 508 dependency spec.

    "pytest>=8.2" -> "pytest", "python-dateutil" -> "python_dateutil"
    """
    dep_spec = dep_spec.strip()
    if not dep_spec:
        return ""
    match = _PACKAGE_NAME_RE.match(dep_spec)
    if not match:
        return ""
    return match.group(1).lower().replace("-", "_").replace(".", "_")


def _load_dev_packages_from_config(project_root: Path | None) -> frozenset[str]:
    """Parse pyproject.toml or setup.cfg for dev/test/lint dependency extras.

    Best-effort: missing or malformed files return an empty frozenset.
    pyproject.toml takes priority; setup.cfg is only consulted if
    pyproject.toml has no dev extras.
    """
    if project_root is None:
        return frozenset()

    packages: set[str] = set()

    # Try pyproject.toml first (Python 3.11+ has tomllib)
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            extras = data.get("project", {}).get("optional-dependencies", {})
            for group_name, deps in extras.items():
                if group_name in _DEV_EXTRA_NAMES:
                    for dep in deps:
                        name = _extract_package_name(dep)
                        if name:
                            packages.add(name)
        except Exception:
            pass  # best-effort

    if packages:
        return frozenset(packages)

    # Fallback to setup.cfg
    setup_cfg_path = project_root / "setup.cfg"
    if setup_cfg_path.exists():
        try:
            config = configparser.ConfigParser()
            config.read(setup_cfg_path)
            if config.has_section("options.extras_require"):
                for group_name in config["options.extras_require"]:
                    if group_name in _DEV_EXTRA_NAMES:
                        for line in config["options.extras_require"][group_name].splitlines():
                            name = _extract_package_name(line)
                            if name:
                                packages.add(name)
        except Exception:
            pass  # best-effort

    return frozenset(packages)


def _classify_external_role(
    fqn_str: str,
    extra_dev_packages: frozenset[str] = frozenset(),
) -> DependencyRole:
    """Classify an external FQN by its root package name.

    Hardcoded registry takes priority over project config.
    """
    root_package = fqn_str.split(".")[0]
    if root_package in PYTHON_DEV_TOOLS:
        return DependencyRole.DEV_TOOL
    if root_package in extra_dev_packages:
        return DependencyRole.DEV_TOOL
    return DependencyRole.UNKNOWN


def with_external_nodes(adg: ADG, project_root: Path | None = None) -> ADG:
    """The one externalizer: a placeholder for every FQN the graph does not define.

    Both reference sources are read here — import targets from structural edges
    and the endpoints of constraint edges — so the two merge paths cannot
    disagree about which EXTERNAL nodes exist (#174).

    A wildcard pattern (app.api.*) is not a concrete FQN: resolve it to its base
    namespace (app.api) before the membership test, so the pattern itself never
    becomes a node. The base might still be an orphan, and then it does.

    project_root: optional path to repo root for dev-tool classification
                  via pyproject.toml / setup.cfg extras.
    """
    extra_dev_packages = _load_dev_packages_from_config(project_root)

    referenced = {edge.target for edge in adg.edges if edge.kind == "IMPORTS"}
    for edge in adg.constraint_edges:
        referenced.add(edge.subject)
        referenced.add(edge.object)

    known_fqns = adg.fqn_set
    external_fqns = sorted(
        base
        for base in (fqn.removesuffix(".*") for fqn in referenced)
        if base and base not in known_fqns
    )
    if external_fqns:
        log.info("with_external_nodes: creating %d EXTERNAL nodes for unresolved FQNs: %s", len(external_fqns), external_fqns)
    else:
        log.debug("with_external_nodes: no unresolved FQNs")

    return adg.with_nodes(*(
        FQNNode.external(fqn, role=_classify_external_role(fqn, extra_dev_packages))
        for fqn in external_fqns
    ))


def add_external_nodes(adg: ADG, project_root: Path | None = None) -> ADG:
    """One-line delegate to the externalizer, kept for existing callers.

    NOT imports-only, despite the name. Since #174 this reads constraint-edge
    endpoints as well as IMPORTS targets, so a hand-built graph can gain an
    EXTERNAL node for an endpoint it never had — grounding a constraint that
    used to be an orphan. That widening is the point of the one-externalizer
    decision; `run_prepared` is the production caller, and in the CLI path
    `build_seed` already externalized those endpoints, so it is a no-op there.
    Pinned by test_delegate_covers_constraint_endpoints_not_just_imports.
    """
    return with_external_nodes(adg, project_root)


def merge_constraint_edges(adg: ADG, constraint_edges: list[ConstraintEdge], project_root: Path | None = None) -> ADG:
    """Attach resolved constraints, then externalize — the single merge order.

    `build_seed`, `build_gold_seed` and `commit_update` all route through here,
    so externalize-then-merge cannot come back as a second idiom (#174).
    """
    return with_external_nodes(adg.with_constraints(*constraint_edges), project_root)
