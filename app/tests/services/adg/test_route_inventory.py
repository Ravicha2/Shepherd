"""Tests for the route inventory derived view (ADR 021).

Public interface under test:
    canonical_path(raw_path: str) -> str
    structural_match(path_a: str, path_b: str) -> bool
    build_route_inventory(repo_path: Path, adg: ADG | None = None) -> RouteInventory

The inventory is a deterministic enumeration of the HTTP request surface:
route -> handler -> module. It extracts no guards by design.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from services.adg import parse_repo
from services.adg.route_inventory import (
    build_route_inventory,
    canonical_path,
    repo_at_sha,
    structural_match,
)


# BAC-BENCH pinned clones (#221), a sibling of the Shepherd checkout.
BACBENCH_REPOS = (
    Path(__file__).resolve().parents[5]
    / "research-exp-setup" / "security" / "data" / "repos"
)


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """Write a Python package tree and return its root."""
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(source))
    return tmp_path


class TestCanonicalPath:
    """Converter types and parameter names collapse to one param segment."""

    def test_flask_converter_and_param_name_are_stripped(self) -> None:
        assert canonical_path("/users/<int:user_id>") == "/users/{}"

    def test_flask_path_converter_is_stripped(self) -> None:
        assert canonical_path("/files/<path:filename>") == "/files/{}"

    def test_fastapi_param_and_converter_are_stripped(self) -> None:
        assert canonical_path("/files/{file_path:path}") == "/files/{}"

    def test_flask_and_fastapi_spellings_canonicalize_the_same(self) -> None:
        assert canonical_path("/users/<int:id>") == canonical_path("/users/{user_id}")

    def test_literal_segments_and_trailing_slash_are_preserved(self) -> None:
        assert canonical_path("/api/v1/users/") == "/api/v1/users/"

    def test_structural_match_ignores_param_spelling_and_position_names(self) -> None:
        assert structural_match("/users/<int:id>", "/users/{user_id}")

    def test_structural_match_rejects_different_literal_segments(self) -> None:
        assert not structural_match("/users/{id}", "/groups/{id}")

    def test_structural_match_rejects_different_segment_counts(self) -> None:
        assert not structural_match("/users/{id}", "/users/{id}/posts")


class TestFastApiDecorators:
    """FastAPI verb decorators emit one record per decorator."""

    def test_route_handler_module_methods_and_evidence(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/routes.py": """
                from fastapi import APIRouter

                router = APIRouter()

                @router.get("/users/{user_id}")
                def get_user(user_id: int):
                    return {}

                class Users:
                    @router.post("/users")
                    def create(self):
                        return {}
            """,
        })

        inventory = build_route_inventory(repo)
        by_handler = {route.handler_fqn: route for route in inventory.routes}

        get_user = by_handler["app.routes.get_user"]
        assert get_user.methods == ("GET",)
        assert get_user.raw_path == "/users/{user_id}"
        assert get_user.canonical_path == "/users/{}"
        assert get_user.module == "app.routes"
        assert get_user.registration_kind == "decorator"
        assert get_user.evidence.file_path == "app/routes.py"
        assert get_user.evidence.line == 6

        create = by_handler["app.routes.Users.create"]
        assert create.methods == ("POST",)
        assert create.module == "app.routes"

    def test_handler_fqns_resolve_against_the_adg(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/routes.py": """
                from fastapi import APIRouter

                router = APIRouter()

                @router.get("/health")
                def health():
                    return {}
            """,
        })

        inventory = build_route_inventory(repo)
        adg = parse_repo(repo)

        assert inventory.routes
        assert all(route.handler_fqn in adg.fqn_set for route in inventory.routes)
        assert all(route.module in adg.fqn_set for route in inventory.routes)

    def test_explicit_methods_list_is_extracted_and_normalized(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/routes.py": """
                from fastapi import APIRouter

                router = APIRouter()

                @router.api_route("/items/{item_id}", methods=["put", "GET"])
                def item(item_id: int):
                    return {}
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes[0].methods == ("GET", "PUT")

    def test_keyword_path_is_extracted(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/routes.py": """
                from fastapi import APIRouter

                router = APIRouter()

                @router.get(path="/health")
                def health():
                    return {}
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert inventory.routes[0].raw_path == "/health"

    def test_keyword_rule_is_extracted(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Flask

                app = Flask(__name__)

                @app.route(rule="/health")
                def health():
                    return ""
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert inventory.routes[0].raw_path == "/health"

    def test_stacked_decorators_keep_their_own_evidence_lines(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/routes.py": """
                from fastapi import APIRouter

                router = APIRouter()

                @router.get("/a")
                @router.post("/b")
                def handler():
                    return {}
            """,
        })

        inventory = build_route_inventory(repo)

        assert {(r.methods, r.raw_path, r.evidence.line) for r in inventory.routes} == {
            (("GET",), "/a", 6),
            (("POST",), "/b", 7),
        }

    def test_methods_keyword_is_read_for_flask_route(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Blueprint

                bp = Blueprint("views", __name__)

                @bp.route("/items", methods=["post", "GET"])
                def items():
                    return ""
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes[0].methods == ("GET", "POST")
        assert inventory.routes[0].canonical_path == "/items"

    def test_flask_route_defaults_to_get(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Flask

                app = Flask(__name__)

                @app.route("/health")
                def health():
                    return ""
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes[0].methods == ("GET",)

    def test_flask_two_style_verb_decorator(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Blueprint

                bp = Blueprint("views", __name__)

                @bp.delete("/items/<int:item_id>")
                def delete_item(item_id):
                    return ""
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes[0].methods == ("DELETE",)
        assert inventory.routes[0].canonical_path == "/items/{}"


class TestCallFormRegistrations:
    """Non-decorator registrations are reported, never silently dropped."""

    def test_add_url_rule_is_reported_as_a_gap(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Blueprint

                bp = Blueprint("views", __name__)

                bp.add_url_rule("/search/", "user_search", object)
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes == ()
        assert len(inventory.gaps) == 1
        gap = inventory.gaps[0]
        assert gap.reason == "non_decorator_registration"
        assert gap.registration == "add_url_rule"
        assert gap.raw_path == "/search/"
        assert gap.handler_fqn == "app.views"
        assert gap.file_path == "app/views.py"

    def test_call_form_gap_uses_the_enclosing_function_fqn(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/routes.py": """
                from fastapi import APIRouter

                router = APIRouter()

                def register():
                    router.add_api_route("/health", object, methods=["GET"])
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes == ()
        assert inventory.gaps[0].reason == "non_decorator_registration"
        assert inventory.gaps[0].registration == "add_api_route"
        assert inventory.gaps[0].raw_path == "/health"
        assert inventory.gaps[0].handler_fqn == "app.routes.register"


class TestInventoryShape:
    """The record schema and deterministic ordering are the contract."""

    def test_no_guard_fields_are_extracted(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Blueprint

                bp = Blueprint("views", __name__)

                @bp.route("/admin")
                @login_required
                def admin():
                    return ""
            """,
        })

        payload = build_route_inventory(repo).to_dict()

        assert "guards" not in payload
        assert set(payload["routes"][0]) == {
            "methods", "raw_path", "canonical_path", "handler_fqn",
            "module", "registration_kind", "evidence",
        }

    def test_rerun_is_byte_identical(self, tmp_path: Path) -> None:
        import json

        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/z.py": """
                from flask import Blueprint

                bp = Blueprint("z", __name__)

                @bp.route("/z")
                def z():
                    return ""
            """,
            "app/a.py": """
                from fastapi import APIRouter

                router = APIRouter()

                @router.get("/a/{id}")
                def a(id: int):
                    return {}
            """,
        })

        first = json.dumps(build_route_inventory(repo).to_dict(), sort_keys=True)
        second = json.dumps(build_route_inventory(repo).to_dict(), sort_keys=True)

        assert first == second
        assert [r["evidence"]["file_path"] for r in json.loads(first)["routes"]] == [
            "app/a.py", "app/z.py",
        ]

    def test_non_literal_methods_is_reported_as_a_gap(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Blueprint

                ALLOWED = ["GET", "POST"]
                bp = Blueprint("views", __name__)

                @bp.route("/items", methods=ALLOWED)
                def items():
                    return ""
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes == ()
        assert inventory.gaps[0].reason == "non_literal_methods"

    def test_non_literal_path_is_reported_as_a_gap(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/routes.py": """
                from fastapi import APIRouter

                PREFIX = "/api"
                router = APIRouter()

                @router.get(PREFIX + "/health")
                def health():
                    return {}
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.routes == ()
        assert len(inventory.gaps) == 1
        assert inventory.gaps[0].handler_fqn == "app.routes.health"
        assert inventory.gaps[0].reason == "non_literal_path"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("repo_id", "sha", "expected_routes"),
    [
        (
            "aegra",
            "d7d80c850010a9c5a3d2be59254c19b9eb0e25dd",
            (
                ("POST", "/threads/{thread_id}/runs",
                 "libs.aegra-api.src.aegra_api.api.runs.create_run"),
                ("POST", "/threads/{thread_id}/runs/stream",
                 "libs.aegra-api.src.aegra_api.api.runs.create_and_stream_run"),
                ("POST", "/threads/{thread_id}/runs/wait",
                 "libs.aegra-api.src.aegra_api.api.runs.wait_for_run"),
            ),
        ),
        (
            "khoj",
            "b8eeefa0b1e8795e21ded99f2ffb7b34c6ab063c",
            (("GET", "/auth/callback",
              "src.khoj.routers.notion.notion_auth_callback"),),
        ),
        (
            "indico",
            "17ba9730a713b0be704a0670f7016b8bcb59a390",
            (("GET", "/booking/<int:booking_id>",
              "indico.modules.rb.blueprint.booking_link"),),
        ),
        (
            "mlflow",
            "990c8a780aa111f69842b0f42ce74af467fe9f57",
            (("POST", "/v1/chat/completions",
              "mlflow.gateway.app.create_app_from_config.openai_chat_handler"),),
        ),
    ],
)
def test_pinned_clone_enumeration(
    repo_id: str,
    sha: str,
    expected_routes: tuple[tuple[str, str, str], ...],
) -> None:
    """The decorator enumerator runs on the real BAC-BENCH pinned trees.

    Runs with `uv run pytest -m integration`. The clones are `--no-checkout`
    mirrors outside the Shepherd repo, so the test skips when they are absent.
    """
    clone = BACBENCH_REPOS / repo_id
    if not clone.exists():
        pytest.skip(f"{clone} is not present (run #221's mirror)")

    with repo_at_sha(clone, sha) as work_tree:
        inventory = build_route_inventory(work_tree)

    assert inventory.routes
    assert not any(gap.reason == "handler_not_in_adg" for gap in inventory.gaps)
    for method, path, handler in expected_routes:
        matches = [r for r in inventory.routes if r.handler_fqn == handler]
        assert matches, f"{handler} missing from {repo_id}"
        assert method in matches[0].methods
        assert structural_match(matches[0].raw_path, path)

    if repo_id == "indico":
        # The affected /search/ route is add_url_rule + a class-based view, so
        # it must surface as a gap, not disappear from the inventory.
        assert any(
            gap.reason == "non_decorator_registration"
            and gap.raw_path == "/search/"
            and gap.file_path == "indico/modules/users/blueprint.py"
            for gap in inventory.gaps
        )

    if repo_id == "mlflow":
        # The AJAX artifact routes are built by _add_static_prefix(...), so the
        # decorator enumerator reports them as gaps rather than guessing.
        assert any(gap.reason == "non_literal_path" for gap in inventory.gaps)
