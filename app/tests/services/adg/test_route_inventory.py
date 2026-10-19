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

    def test_django_re_path_groups_become_param_segments(self) -> None:
        assert canonical_path(r"^download/(?P<id>[^/]+)/$") == "/download/{}/"
        assert canonical_path(r"^api/v1/users/(?P<user_id>\d+)/$") == "/api/v1/users/{}/"

    def test_django_re_path_unnamed_and_alternative_groups(self) -> None:
        assert canonical_path(
            r"^admin/pages/(?P<page_id>\d+)/revisions/compare/(live|earliest|\d+)\.\.\.(live|latest)/$"
        ) == "/admin/pages/{}/revisions/compare/{}...{}/"

    def test_re_path_matches_path_syntax_structurally(self) -> None:
        assert structural_match(
            r"^admin/pages/(?P<page_id>\d+)/edit/preview/$",
            "/admin/pages/<int:page_id>/edit/preview/",
        )


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


class TestDjangoUrlconf:
    """Django urlpatterns are enumerated by traversing path/re_path entries."""

    def test_path_function_view_is_enumerated(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None
            """,
            "app/urls.py": """
                from django.urls import path
                from app import views

                urlpatterns = [
                    path("health/", views.health, name="health"),
                ]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        route = inventory.routes[0]
        assert route.raw_path == "/health/"
        assert route.canonical_path == "/health/"
        assert route.handler_fqn == "app.views.health"
        assert route.module == "app.urls"
        assert route.registration_kind == "urlconf"
        assert route.evidence.file_path == "app/urls.py"
        assert route.evidence.line == 6

    def test_nested_include_prefixes_cbv_and_re_path(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/api/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None

                class ReportView:
                    def post(self, request, pk):
                        return None
            """,
            "app/api/urls.py": """
                from django.urls import path
                from app import views

                urlpatterns = [
                    path("health/", views.health, name="health"),
                ]
            """,
            "app/urls.py": """
                from django.urls import include, path, re_path
                from app.api import urls as api_urls
                from app import views

                urlpatterns = [
                    path("api/v1/", include((api_urls, "api"), namespace="api")),
                    path("admin/", include([
                        path("reports/<int:pk>/", views.ReportView.as_view()),
                    ])),
                    re_path(r"^legacy/(?P<id>\\d+)/$", views.health),
                ]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        by_path = {route.canonical_path: route for route in inventory.routes}
        assert set(by_path) == {
            "/api/v1/health/", "/admin/reports/{}/", "/legacy/{}/",
        }
        assert by_path["/api/v1/health/"].handler_fqn == "app.views.health"
        assert by_path["/admin/reports/{}/"].handler_fqn == "app.views.ReportView"
        assert by_path["/admin/reports/{}/"].methods == ("POST",)
        assert by_path["/legacy/{}/"].handler_fqn == "app.views.health"


class TestDjangoUrlconfConstruction:
    """Urlconf lists are built in the many ways real repos build them."""

    def test_append_and_extend_are_traversed(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None

                def about(request):
                    return None
            """,
            "app/extra_urls.py": """
                from django.urls import path
                from app import views

                urlpatterns = [
                    path("extra/", views.about),
                ]
            """,
            "app/urls.py": """
                from django.urls import include, path
                from app import views

                urlpatterns = [path("health/", views.health)]
                urlpatterns.append(path("about/", views.about))
                urlpatterns.extend([path("", include("app.extra_urls"))])
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert {
            route.canonical_path for route in inventory.routes
        } == {"/health/", "/about/", "/extra/"}

    def test_reassignment_from_the_previous_list_keeps_prior_entries(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None

                def about(request):
                    return None
            """,
            "app/urls.py": """
                from django.urls import path
                from app import views

                urlpatterns = [path("health/", views.health)]
                urlpatterns = urlpatterns + [path("about/", views.about)]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert {
            route.canonical_path for route in inventory.routes
        } == {"/health/", "/about/"}

    def test_branch_assignments_are_all_enumerated(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None
            """,
            "app/urls.py": """
                from django.conf import settings
                from django.urls import include, path
                from app import views

                base = [path("health/", views.health)]
                if settings.PREFIXED:
                    urlpatterns = [path("prefixed/", include(base))]
                else:
                    urlpatterns = base
            """,
        })

        inventory = build_route_inventory(repo)

        assert {
            route.canonical_path for route in inventory.routes
        } == {"/health/", "/prefixed/health/"}

    def test_imported_urlpatterns_are_expanded_not_treated_as_a_root(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/api/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None
            """,
            "app/api/asset.py": """
                from django.urls import path
                from app import views

                urlpatterns = [path("asset/", views.health)]
            """,
            "app/api/aggregate.py": """
                from django.urls import path

                from app.api.asset import urlpatterns as asset_patterns
                from app import views

                urlpatterns = [*asset_patterns, path("extra/", views.health)]
            """,
            "app/urls.py": """
                from django.urls import include, path

                urlpatterns = [path("api/", include("app.api.aggregate"))]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert {
            route.canonical_path for route in inventory.routes
        } == {"/api/asset/", "/api/extra/"}

    def test_import_rooted_names_resolve_to_repo_rooted_fqns(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "apps/api/plane/__init__.py": "",
            "apps/api/plane/api/__init__.py": "",
            "apps/api/plane/views.py": """
                def health(request):
                    return None
            """,
            "apps/api/plane/api/other_urls.py": """
                from django.urls import path
                from plane.views import health

                urlpatterns = [path("health/", health)]
            """,
            "apps/api/plane/urls.py": """
                from django.urls import include, path

                urlpatterns = [path("api/", include("plane.api.other_urls"))]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        route = inventory.routes[0]
        assert route.canonical_path == "/api/health/"
        assert route.handler_fqn == "apps.api.plane.views.health"


class TestDjangoUrlconfWrappers:
    """Django's url-list helpers and dynamic mounts keep routes visible."""

    def test_imported_pattern_list_variable_is_expanded(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None

                def about(request):
                    return None
            """,
            "app/shared.py": """
                from django.urls import path
                from app import views

                common_patterns = [path("health/", views.health)]
            """,
            "app/urls.py": """
                from django.urls import path
                from app import views
                from app.shared import common_patterns

                urlpatterns = common_patterns + [path("about/", views.about)]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert {
            route.canonical_path for route in inventory.routes
        } == {"/health/", "/about/"}

    def test_shared_pattern_list_keeps_its_defining_module_for_handler_resolution(
        self, tmp_path: Path,
    ) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/handlers.py": """
                def health(request):
                    return None
            """,
            "app/shared.py": """
                from django.urls import path
                from app.handlers import health

                common_patterns = [path("health/", health)]
            """,
            "app/urls.py": """
                from app.shared import common_patterns

                urlpatterns = common_patterns
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert inventory.routes[0].handler_fqn == "app.handlers.health"

    def test_package_reexports_resolve_to_the_defining_module(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views/__init__.py": """
                from app.views.impl import HealthView
            """,
            "app/views/impl.py": """
                class HealthView:
                    def get(self, request):
                        return None
            """,
            "app/urls.py": """
                from django.urls import path
                from app.views import HealthView

                urlpatterns = [path("health/", HealthView.as_view())]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert inventory.routes[0].handler_fqn == "app.views.impl.HealthView"

    def test_pattern_decorator_wrapper_keeps_the_wrapped_entries(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None
            """,
            "app/urls.py": """
                from django.urls import path
                from app import views
                from app.decorators import decorate_urlpatterns, never_cache

                urlpatterns = [path("health/", views.health)]
                urlpatterns = decorate_urlpatterns(urlpatterns, never_cache)
            """,
            "app/decorators.py": """
                def never_cache(view):
                    return view

                def decorate_urlpatterns(patterns, decorator):
                    return patterns
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert [route.canonical_path for route in inventory.routes] == ["/health/"]

    def test_dynamic_prefix_still_traverses_the_included_module(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None
            """,
            "app/inner_urls.py": """
                from django.urls import path
                from app import views

                urlpatterns = [path("health/", views.health)]
            """,
            "app/urls.py": """
                from django.conf import settings
                from django.urls import include, url

                urlpatterns = [url(r"%s" % settings.PREFIX, include("app.inner_urls"))]
            """,
        })

        inventory = build_route_inventory(repo)

        assert [route.canonical_path for route in inventory.routes] == ["/health/"]
        assert [gap.reason for gap in inventory.gaps] == ["non_literal_path"]

    def test_instance_as_view_resolves_to_the_class(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                class ThreadsList:
                    def get(self, request):
                        return None
            """,
            "app/urls.py": """
                from django.urls import url
                from app import views

                urlpatterns = [url(r"^threads/$", views.ThreadsList().as_view())]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert inventory.routes[0].handler_fqn == "app.views.ThreadsList"

    def test_reassigning_with_the_previous_list_on_the_right_keeps_entries(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None

                def debug(request):
                    return None
            """,
            "app/urls.py": """
                from django.conf import settings
                from django.urls import path
                from app import views

                urlpatterns = [path("health/", views.health)]
                if settings.DEBUG:
                    urlpatterns = [path("debug/", views.debug)] + urlpatterns
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert {
            route.canonical_path for route in inventory.routes
        } == {"/health/", "/debug/"}


class TestDrfRouters:
    """router.register resolves to ViewSet action FQNs and @action routes."""

    def test_register_and_actions_are_enumerated(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                from rest_framework import viewsets
                from rest_framework.decorators import action

                class NoteViewSet(viewsets.ModelViewSet):
                    @action(detail=True)
                    def archive(self, request, pk):
                        return None

                    @action(detail=False, methods=["post"], url_path="bulk-create")
                    def bulk_create(self, request):
                        return None
            """,
            "app/urls.py": """
                from django.urls import include, path
                from rest_framework import routers
                from app import views

                router = routers.DefaultRouter()
                router.register(r"notes", views.NoteViewSet, basename="note")

                urlpatterns = [
                    path("api/", include(router.urls)),
                ]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        by_route = {
            (route.raw_path, route.methods): route for route in inventory.routes
        }
        assert set(by_route) == {
            ("/api/notes/", ("GET",)),
            ("/api/notes/", ("POST",)),
            ("/api/notes/{pk}/", ("GET",)),
            ("/api/notes/{pk}/", ("PUT",)),
            ("/api/notes/{pk}/", ("PATCH",)),
            ("/api/notes/{pk}/", ("DELETE",)),
            ("/api/notes/{pk}/archive/", ("GET",)),
            ("/api/notes/bulk-create/", ("POST",)),
        }
        assert by_route[("/api/notes/", ("POST",))].handler_fqn == (
            "app.views.NoteViewSet.create"
        )
        assert by_route[("/api/notes/{pk}/archive/", ("GET",))].handler_fqn == (
            "app.views.NoteViewSet.archive"
        )
        assert by_route[("/api/notes/bulk-create/", ("POST",))].handler_fqn == (
            "app.views.NoteViewSet.bulk_create"
        )
        assert {
            route.registration_kind for route in inventory.routes
        } == {"router"}

    def test_i18n_patterns_and_extended_urlpatterns(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "app/__init__.py": "",
            "app/views.py": """
                def health(request):
                    return None
            """,
            "app/urls.py": """
                from django.conf.urls.i18n import i18n_patterns
                from django.urls import include, path, re_path
                from app import views

                shared = [path("a/", views.health)]
                urlpatterns = i18n_patterns(path("i18n/", include((shared, "x"))))
                urlpatterns += [re_path(r"^b/$", views.health)]
            """,
        })

        inventory = build_route_inventory(repo)

        assert inventory.gaps == ()
        assert {
            route.canonical_path for route in inventory.routes
        } == {"/i18n/a/", "/b/"}


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
