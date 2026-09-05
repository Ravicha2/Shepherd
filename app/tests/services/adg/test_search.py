"""Tests for the semble-backed search backend (ADR 017).

All tests go through the build_search_backend seam with a stub index and a
synthetic ADG: no network, no HF model, no filesystem indexing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from services.adg.search import build_search_backend
from services.fqn import FQN
from services.models import ADG, FQNKind, FQNNode


# -- Stubs --------------------------------------------------------------------

@dataclass
class StubChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str = "python"


@dataclass
class StubHit:
    chunk: StubChunk
    score: float = 0.0


class StubIndex:
    """Duck-typed SembleIndex: returns preloaded hits for any query."""

    def __init__(self, hits: list[StubHit]) -> None:
        self._hits = hits

    def search(self, query: str, top_k: int = 10) -> list[StubHit]:
        return self._hits[:top_k]


# -- Fixtures -----------------------------------------------------------------

def make_adg() -> ADG:
    """app/api/users.py: module 0-50, class 5-40, method 10-20, function 45-50."""
    nodes = [
        FQNNode(fqn=FQN.from_dotted("app.api.users"), kind=FQNKind.MODULE, file_path="app/api/users.py", line_start=0, line_end=50, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView"), kind=FQNKind.CLASS, file_path="app/api/users.py", line_start=5, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView.get"), kind=FQNKind.METHOD, file_path="app/api/users.py", line_start=10, line_end=20, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.list_users"), kind=FQNKind.FUNCTION, file_path="app/api/users.py", line_start=45, line_end=50, start_byte=0, end_byte=0),
    ]
    return ADG(nodes=nodes, edges=[])


# -- Lift happy path ----------------------------------------------------------

class TestLift:
    def test_hit_lifts_to_overlapping_nodes(self) -> None:
        hit = StubHit(StubChunk(content="def get(self): ...", file_path="app/api/users.py", start_line=10, end_line=20))
        backend = build_search_backend(Path("/repo"), make_adg(), index=StubIndex([hit]))

        results = backend("user view get")

        assert [(entry["fqn"], entry["kind"]) for entry in results] == [
            ("app.api.users", "module"),
            ("app.api.users.UserView", "class"),
            ("app.api.users.UserView.get", "method"),
        ]
        assert all(entry["file"] == "app/api/users.py" for entry in results)
        assert all(entry["snippet"] == "def get(self): ..." for entry in results)

    def test_snippet_truncated_to_500_chars(self) -> None:
        long_content = "x" * 600
        hit = StubHit(StubChunk(content=long_content, file_path="app/api/users.py", start_line=10, end_line=20))
        backend = build_search_backend(Path("/repo"), make_adg(), index=StubIndex([hit]))

        results = backend("user view get")

        assert results and all(len(entry["snippet"]) == 500 for entry in results)

    def test_payload_capped_at_top_k(self) -> None:
        hit_one = StubHit(StubChunk(content="def get(self): ...", file_path="app/api/users.py", start_line=10, end_line=20))
        hit_two = StubHit(StubChunk(content="def check(self): ...", file_path="app/api/users.py", start_line=45, end_line=50))
        backend = build_search_backend(Path("/repo"), make_adg(), index=StubIndex([hit_one, hit_two]))

        results = backend("users", top_k=4)

        assert len(results) == 4

    def test_hit_with_no_adg_node_drops_out(self) -> None:
        """Files skipped by the parse-error policy (#121 problem 1) lift to nothing."""
        hit = StubHit(StubChunk(content="unparseable", file_path="app/broken.py", start_line=1, end_line=5))
        backend = build_search_backend(Path("/repo"), make_adg(), index=StubIndex([hit]))

        assert backend("broken thing") == []


# -- Path normalization -------------------------------------------------------

class TestPathNormalization:
    def test_absolute_hit_path_lifts_to_relative_nodes(self) -> None:
        hit = StubHit(StubChunk(content="def get(self): ...", file_path="/repo/app/api/users.py", start_line=10, end_line=20))
        backend = build_search_backend(Path("/repo"), make_adg(), index=StubIndex([hit]))

        results = backend("user view get")

        assert [entry["fqn"] for entry in results] == [
            "app.api.users",
            "app.api.users.UserView",
            "app.api.users.UserView.get",
        ]
        assert all(entry["file"] == "app/api/users.py" for entry in results)


# -- Loud failure (ADR 017 decision 5) ----------------------------------------

class TestLoudFailure:
    def test_index_build_failure_raises_with_remedy(self, monkeypatch) -> None:
        class UnavailableIndex:
            @staticmethod
            def from_path(path) -> "UnavailableIndex":
                raise OSError("no network, model not cached")

        monkeypatch.setattr("services.adg.search.SembleIndex", UnavailableIndex)

        with pytest.raises(RuntimeError, match="SEMBLE_MODEL_NAME"):
            build_search_backend(Path("/repo"), make_adg())
