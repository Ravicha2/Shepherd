"""Tests for guard extraction (#246 slice 2).

Public interface under test:
    extract_guards(source: str, handler_fqn: str, object_parameters=())
        -> tuple[Guard, ...]

A guard record names the guard's symbol, its predicate text, and whether that
predicate scopes the loaded object to the requester, plus the two soundness
checks (always-false dead guard, deny-branch re-invoke). Everything is
framework idiom — no case, repo, route or advisory names.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from services.adg import parse_repo
from services.adg.object_scope import (
    backfill_handler_facts,
    extract_guards,
    object_parameters,
)
from services.adg.route_inventory import repo_at_sha
from services.models import Guard

SECURITY_REPOS = (
    Path(__file__).resolve().parents[5] / "research-exp-setup" / "security" / "data" / "repos"
)


def test_django_re_path_named_group_yields_the_parameter_name() -> None:
    assert object_parameters([r"/avatar/list/(?P<user_id>\d+)/"]) == ("user_id",)


def test_requester_object_comparison_is_a_scoping_guard() -> None:
    source = dedent(
        """
        def download(request, item_id):
            item = get_object_or_404(Item, pk=item_id)
            if item.owner_id != request.user.id:
                raise Http404()
            return item
        """
    )

    guards = extract_guards(source, "download", ("item_id",))

    assert guards == (
        Guard(
            symbol="download",
            predicate="item.owner_id != request.user.id",
            scopes_object=True,
        ),
    )


def test_predicate_only_applied_when_an_object_field_is_truthy_does_not_scope() -> None:
    source = dedent(
        """
        def object(self):
            o = get_object_or_404(CachedFile, id=self.kwargs['id'])
            if o.session_key:
                if o.session_key != self.request.session.session_key:
                    raise Http404()
            return o
        """
    )

    guards = extract_guards(source, "object")

    assert guards == (
        Guard(
            symbol="object",
            predicate="o.session_key != self.request.session.session_key",
            scopes_object=False,
            conditional=True,
        ),
    )


def test_scoping_call_with_the_requester_is_a_guard() -> None:
    source = dedent(
        """
        def object(self):
            o = get_object_or_404(CachedFile, id=self.kwargs['id'])
            if not o.allowed_for_session(self.request):
                raise Http404()
            return o
        """
    )

    guards = extract_guards(source, "object")

    assert guards == (
        Guard(
            symbol="o.allowed_for_session",
            predicate="o.allowed_for_session(self.request)",
            scopes_object=True,
        ),
    )


def test_dead_guard_and_deny_branch_reinvoke_are_recorded() -> None:
    source = dedent(
        """
        def admin_or_owner_required(func):
            def wrapped(request, user_id=None):
                if request.user.is_authenticated:
                    if request.user.is_administrator() or request.user.id == user_id:
                        return func(request, user_id)
                return login_required(func)(request, user_id)
            return wrapped

        @admin_or_owner_required
        def show_list(request, user_id=None):
            user = get_object_or_404(User, pk=user_id)
            return user
        """
    )

    guards = extract_guards(source, "show_list", ("user_id",))

    assert set(guards) == {
        Guard(
            symbol="admin_or_owner_required",
            predicate="request.user.id == user_id",
            scopes_object=False,
            conditional=True,
            dead=True,
        ),
        Guard(
            symbol="login_required",
            predicate="login_required(func)(request, user_id)",
            scopes_object=False,
            bypass=True,
        ),
    }


def test_converted_path_parameter_clears_the_dead_guard() -> None:
    source = dedent(
        """
        def admin_or_owner_required(func):
            def wrapped(request, user_id=None):
                if not request.user.is_authenticated:
                    return login_required(func)(request, user_id)
                user_id_int = int(user_id) if user_id is not None else None
                if request.user.is_administrator() or request.user.id == user_id_int:
                    return func(request, user_id)
            return wrapped

        @admin_or_owner_required
        def show_list(request, user_id=None):
            user = get_object_or_404(User, pk=user_id)
            return user
        """
    )

    guards = extract_guards(source, "show_list", ("user_id",))

    assert guards == (
        Guard(
            symbol="admin_or_owner_required",
            predicate="request.user.id == user_id_int",
            scopes_object=True,
        ),
    )


def test_back_fill_populates_object_parameters_and_guards(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "__init__.py").write_text("")
    (repo / "app" / "views.py").write_text(dedent(
        """
        from fastapi import APIRouter

        router = APIRouter()

        @router.get("/users/{user_id}")
        def get_user(user_id: str, request):
            user = db.get(User, user_id)
            if request.user.id != user.owner_id:
                raise PermissionError
            return user
        """
    ))
    adg = parse_repo(repo)

    filled = backfill_handler_facts(adg, repo)

    handler = filled.node_of["app.views.get_user"]
    assert handler.object_parameters == ("user_id",)
    assert handler.guards == (
        Guard(
            symbol="get_user",
            predicate="request.user.id != user.owner_id",
            scopes_object=True,
        ),
    )
    assert filled.node_of["app.views"].guards == ()
    assert len(filled.nodes) == len(adg.nodes)
    assert adg.node_of["app.views.get_user"].guards == ()


def _guards_at(repo: str, sha: str, handler_fqn: str) -> tuple[Guard, ...]:
    root = SECURITY_REPOS / repo
    if not root.exists():
        pytest.skip(f"{root} is not present")
    with repo_at_sha(root, sha) as tree:
        filled = backfill_handler_facts(parse_repo(tree), tree)
    return filled.node_of[handler_fqn].guards


class TestPinnedGuardFixtures:
    """The pre-gate's five checks, at the real vulnerable and fixing commits."""

    def test_askbot_dead_guard_and_bypass_flip_across_the_fix(self) -> None:
        vulnerable = _guards_at(
            "askbot-devel", "ffae1aee7db8d4c909a412aa763d41f08853a8fa",
            "askbot.views.avatar_views.show_list")
        fixed = _guards_at(
            "askbot-devel", "3da3d75f35204aa71633c7a315327ba39cb6295d",
            "askbot.views.avatar_views.show_list")

        assert any(guard.dead for guard in vulnerable)
        assert any(guard.bypass for guard in vulnerable)
        assert not any(guard.scopes_object for guard in vulnerable)
        assert not any(guard.dead or guard.bypass for guard in fixed)
        assert any(guard.scopes_object for guard in fixed)

    def test_pretix_conditional_session_key_predicate_flips_across_the_fix(self) -> None:
        vulnerable = _guards_at(
            "pretix", "703be2ebb82c0d1cacb41fc76e55ba30561414d6",
            "src.pretix.base.views.cachedfiles.DownloadView")
        fixed = _guards_at(
            "pretix", "4b5651862c57c6e384822d1d23292342126c479a",
            "src.pretix.base.views.cachedfiles.DownloadView")

        assert any("session_key" in guard.predicate and guard.conditional
                   and not guard.scopes_object for guard in vulnerable)
        assert not any(guard.scopes_object for guard in vulnerable)
        assert any(guard.symbol == "o.allowed_for_session" and guard.scopes_object
                   for guard in fixed)

    def test_weblate_object_identifier_route_flips_across_the_fix(self) -> None:
        vulnerable = _guards_at(
            "weblate", "a63a2fd3aa40be591d47741b685cc42c9e7ca6ee",
            "weblate.api.views.UserViewSet.notifications_details")
        fixed = _guards_at(
            "weblate", "84e56f496989d08269b1496fc5e4d97dedb74b36",
            "weblate.api.views.UserViewSet.notifications_details")

        assert not any(guard.scopes_object for guard in vulnerable)
        assert any(guard.symbol == "self.perm_check" and guard.scopes_object
                   for guard in fixed)
