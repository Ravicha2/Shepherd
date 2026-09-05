"""Semble-backed code search backend for ADR resolution (ADR 017, decisions 1, 5, 6).

Implements the recall half of the search-first tool surface: build a semble
index once per repo, lift its file-level hits to ADG FQN handles via
FQNNode.file_path, and return a bounded payload for the resolver agent.

ADR: docs/adr/017-search-first-resolution-tools.md
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from semble import SembleIndex

from services.models import ADG, FQNKind, FQNNode

SearchCallable = Callable[..., list[dict]]


def _normalize_hit_path(hit_path: str, repo_root: Path) -> str:
    """Canonical repo-relative posix form; FQNNode.file_path is repo-relative."""
    path = Path(hit_path)
    if path.is_absolute():
        try:
            path = path.relative_to(repo_root)
        except ValueError:
            pass  # outside the repo; the file lookup misses and the hit drops out
    return path.as_posix().removeprefix("./")


def build_search_backend(repo_path: Path, adg: ADG, index: SembleIndex | None = None) -> SearchCallable:
    """Build the semble index once and return a search(query, top_k=10) callable.

    Hits lift to FQN handles for ADG nodes whose line span overlaps the hit's
    chunk lines; hits with no ADG node drop out naturally.
    """
    if index is None:
        try:
            index = SembleIndex.from_path(repo_path)
        except Exception as error:
            # ADR 017 decision 5: loud failure, no silent degradation of retrieval.
            raise RuntimeError(
                f"semble search backend unavailable ({error!r}). "
                "Remedy: run once with network access to cache the embedding model, "
                "or set SEMBLE_MODEL_NAME to a local Model2Vec model directory."
            ) from error

    nodes_by_file: dict[str, list[FQNNode]] = defaultdict(list)
    for node in adg.nodes:
        nodes_by_file[node.file_path].append(node)

    def search(query: str, top_k: int = 10) -> list[dict]:
        hits = index.search(query, top_k=top_k)
        results: list[dict] = []
        for hit in hits:
            chunk = hit.chunk
            file_path = _normalize_hit_path(chunk.file_path, repo_path)
            overlapping = [
                node for node in nodes_by_file.get(file_path, [])
                if node.line_start <= chunk.end_line and node.line_end >= chunk.start_line
            ]
            for node in sorted(overlapping, key=lambda node: node.line_start):
                results.append({
                    "fqn": str(node.fqn),
                    "kind": node.kind.value,
                    "file": file_path,
                    "snippet": chunk.content[:500],
                })
        return results[:top_k]

    return search


if __name__ == "__main__":  # ponytail: assert-based self-check, no pytest/network needed
    from dataclasses import dataclass

    from services.fqn import FQN

    @dataclass
    class _Chunk:
        content: str
        file_path: str
        start_line: int
        end_line: int

    @dataclass
    class _Hit:
        chunk: _Chunk

    class _StubIndex:
        def search(self, query: str, top_k: int = 10) -> list[_Hit]:
            return [_Hit(_Chunk(content="y" * 600, file_path="/repo/app/api/users.py", start_line=10, end_line=20))]

    stub_adg = ADG(nodes=[FQNNode(fqn=FQN.from_dotted("app.api.users.UserView"), kind=FQNKind.CLASS, file_path="app/api/users.py", line_start=5, line_end=40, start_byte=0, end_byte=0)])
    backend = build_search_backend(Path("/repo"), stub_adg, index=_StubIndex())
    results = backend("user view")
    assert len(results) == 1
    assert results[0] == {
        "fqn": "app.api.users.UserView",
        "kind": "class",
        "file": "app/api/users.py",
        "snippet": "y" * 500,
    }
    print("search backend self-check ok")
