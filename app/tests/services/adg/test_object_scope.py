"""Tests for the object-scope extractor (#245 slice 1).

Public interface under test:
    object_parameters(raw_paths: Iterable[str]) -> tuple[str, ...]

The extractor names the object parameters a handler loads from its routes.
Everything is framework idiom — no case, repo, route or advisory names.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from services.adg import parse_repo
from services.adg.object_scope import backfill_object_parameters, object_parameters
from services.adg.route_inventory import repo_at_sha
from services.models import FQNNode

DJANGO_FIXTURE = Path(__file__).resolve().parents[4] / "repos" / "django"
DJANGO_PIN = "f35a463d714f261baddf04bc43cc8b5910fe084e"


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(source))
    return tmp_path


class TestObjectParameters:
    """Route-path idioms resolve to the object parameter names."""

    def test_flask_converter_yields_the_parameter_name(self) -> None:
        assert object_parameters(["/users/<int:user_id>/"]) == ("user_id",)

    def test_fastapi_braces_yield_the_parameter_name(self) -> None:
        assert object_parameters(["/threads/{thread_id}/runs"]) == ("thread_id",)

    def test_django_path_converter_yields_the_parameter_name(self) -> None:
        assert object_parameters(["/users/<uuid:pk>/"]) == ("pk",)

    def test_non_object_parameters_are_dropped(self) -> None:
        """Pagination and filter slots name no object, so they are not facts."""
        assert object_parameters(["/items/?page=<int:page>&limit={limit}"]) == ()


class TestNodeField:
    """The optional field defaults to empty, including on the EXTERNAL sentinel."""

    def test_synthetic_external_nodes_are_untouched(self) -> None:
        assert FQNNode.external("django").object_parameters == ()


class TestBackfill:
    """The post-parse pass populates handler nodes from the route inventory."""

    def test_handlers_get_the_object_parameters_their_routes_name(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from flask import Blueprint
                from django.http import JsonResponse

                bp = Blueprint("views", __name__)

                @bp.route("/items/<int:item_id>/", methods=["GET"])
                def item(item_id):
                    return ""

                def detail(request, thing_id):
                    return JsonResponse({})
            """,
            "app/urls.py": """
                from django.urls import path

                from app.views import detail

                urlpatterns = [path("things/<int:thing_id>/", detail)]
            """,
        })
        adg = parse_repo(repo)

        filled = backfill_object_parameters(adg, repo)

        assert filled.node_of["app.views.item"].object_parameters == ("item_id",)
        assert filled.node_of["app.views.detail"].object_parameters == ("thing_id",)
        assert filled.node_of["app.views"].object_parameters == ()
        assert len(filled.nodes) == len(adg.nodes)
        assert adg.node_of["app.views.item"].object_parameters == ()


class TestPinnedDjangoFixture:
    """The URLconf join works on the real pinned Django fixture."""

    def test_urlconf_parameter_reaches_the_handler_node(self) -> None:
        if not DJANGO_FIXTURE.exists():
            pytest.skip(f"{DJANGO_FIXTURE} is not present")

        with repo_at_sha(DJANGO_FIXTURE, DJANGO_PIN) as work_tree:
            filled = backfill_object_parameters(parse_repo(work_tree), work_tree)

        assert filled.node_of["users.views.user_detail"].object_parameters == ("user_id",)
        assert filled.node_of["users.views.user_list"].object_parameters == ()
