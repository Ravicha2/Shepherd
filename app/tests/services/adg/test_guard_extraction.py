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


def _single_guard(source: str, handler: str,
                  params: tuple[str, ...] = ()) -> Guard:
    (guard,) = extract_guards(dedent(source), handler, params)
    return guard


@pytest.mark.parametrize("handler,params,source,expected", [
    pytest.param(
        "download", ("item_id",),
        """
        def download(request, item_id):
            item = get_object_or_404(Item, pk=item_id)
            if item.owner_id != request.user.id:
                raise Http404()
            return item
        """,
        Guard(
            symbol="download",
            predicate="item.owner_id != request.user.id",
            scopes_object=True,
        ),
        id="requester-object-comparison",
    ),
    pytest.param(
        "show_list", ("user_id",),
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
        """,
        Guard(
            symbol="admin_or_owner_required",
            predicate="request.user.id == user_id_int",
            scopes_object=True,
        ),
        id="converted-path-parameter",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            item = get_object_or_404(Item, pk=item_id)
            if request.user.is_authenticated:
                if item.owner_id != request.user.id:
                    raise Http404()
            return item
        """,
        Guard(
            symbol="detail",
            predicate="item.owner_id != request.user.id",
            scopes_object=True,
        ),
        id="auth-gate",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(self, request, item_id):
            if self.restricted:
                item = Item.objects.filter(pk=item_id, owner=request.user).first()
            return item
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(pk=item_id, owner=request.user).first()",
            scopes_object=False,
            conditional=True,
        ),
        id="conditional-fetch-chain",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            return Item.objects.filter(Q(pk=item_id) | Q(owner=request.user)).first()
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(Q(pk=item_id) | Q(owner=request.user)).first()",
            scopes_object=False,
        ),
        id="or-branch-bypasses-ownership",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            return Item.objects.filter(pk=item_id).exclude(owner=request.user).first()
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(pk=item_id).exclude(owner=request.user).first()",
            scopes_object=False,
        ),
        id="exclude-negates-ownership",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            return Item.objects.filter(pk=item_id, user__tenant=request.user.tenant).first()
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(pk=item_id, user__tenant=request.user.tenant).first()",
            scopes_object=False,
        ),
        id="tenant-bound-field-does-not-scope",
    ),
    pytest.param(
        "detail", ("id",),
        """
        def detail(self, request, id):
            return get_object_or_404(StaffSession, pk=self.kwargs['id'], user=self.request.user)
        """,
        Guard(
            symbol="detail",
            predicate="get_object_or_404(StaffSession, pk=self.kwargs['id'], user=self.request.user)",
            scopes_object=True,
            covers=("id",),
        ),
        id="kwarg-subscript-ties-to-route-param",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            oid = int(item_id)
            return Item.objects.filter(pk=oid, owner=request.user).first()
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(pk=oid, owner=request.user).first()",
            scopes_object=True,
            covers=("item_id",),
        ),
        id="local-alias-ties-to-route-param",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            return get_object_or_404(Item.objects.filter(owner=request.user), pk=item_id)
        """,
        Guard(
            symbol="detail",
            predicate="get_object_or_404(Item.objects.filter(owner=request.user), pk=item_id)",
            scopes_object=True,
            covers=("item_id",),
        ),
        id="inline-queryset-carries-the-requester-filter",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            return Item.objects.filter(owner=request.user).exclude(pk=item_id).first()
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(owner=request.user).exclude(pk=item_id).first()",
            scopes_object=True,
            covers=("item_id",),
        ),
        id="exclude-narrowing-a-scoped-queryset-still-scopes",
    ),
    pytest.param(
        "detail", ("id",),
        """
        def detail(request, id):
            return Item.objects.filter(pk=other.id, owner=request.user).first()
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(pk=other.id, owner=request.user).first()",
            scopes_object=False,
        ),
        id="param-name-inside-another-name-does-not-tie",
    ),
    pytest.param(
        "detail", ("item_id",),
        """
        def detail(request, item_id):
            return Item.objects.filter(pk=item_id, owner__in=request.user.teammate_ids).first()
        """,
        Guard(
            symbol="detail",
            predicate="Item.objects.filter(pk=item_id, owner__in=request.user.teammate_ids).first()",
            scopes_object=False,
        ),
        id="requester-derived-value-is-not-the-requester",
    ),
])
def test_a_scoping_guard_is_judged_by_where_and_how_it_runs(
        handler: str, params: tuple[str, ...], source: str, expected: Guard) -> None:
    assert _single_guard(source, handler, params) == expected


def test_an_unrelated_ownership_fetch_does_not_clear_the_handler() -> None:
    guards = extract_guards(
        dedent(
            """
            def detail(request, item_id):
                if AuditLog.objects.filter(id=log_id, user=request.user).exists():
                    return Item.objects.get(pk=item_id)
            """
        ),
        "detail", ("item_id",))

    assert guards
    assert not any(guard.scopes_object for guard in guards)


def test_a_chain_guard_names_the_route_parameters_it_covers() -> None:
    guards = extract_guards(
        dedent(
            """
            def detail(request, item_id, owner_id):
                return Item.objects.filter(pk=item_id, owner=request.user).first()
            """
        ),
        "detail", ("item_id", "owner_id"))

    assert [guard.covers for guard in guards if guard.scopes_object] == [("item_id",)]


def test_django_re_path_named_group_yields_the_parameter_name() -> None:
    assert object_parameters([r"/avatar/list/(?P<user_id>\d+)/"]) == ("user_id",)


def test_predicate_only_applied_when_an_object_field_is_truthy_does_not_scope() -> None:
    guard = _single_guard(
        """
        def object(self):
            o = get_object_or_404(CachedFile, id=self.kwargs['id'])
            if o.session_key:
                if o.session_key != self.request.session.session_key:
                    raise Http404()
            return o
        """,
        "object")

    assert guard == Guard(
        symbol="object",
        predicate="o.session_key != self.request.session.session_key",
        scopes_object=False,
        conditional=True,
    )


def test_scoping_call_with_the_requester_is_a_guard() -> None:
    guard = _single_guard(
        """
        def object(self):
            o = get_object_or_404(CachedFile, id=self.kwargs['id'])
            if not o.allowed_for_session(self.request):
                raise Http404()
            return o
        """,
        "object")

    assert guard == Guard(
        symbol="o.allowed_for_session",
        predicate="o.allowed_for_session(self.request)",
        scopes_object=True,
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
            dead=True,
        ),
        Guard(
            symbol="login_required",
            predicate="login_required(func)(request, user_id)",
            scopes_object=False,
            bypass=True,
        ),
    }


def test_a_local_named_user_is_not_the_requester() -> None:
    source = dedent(
        """
        def detail(request, item_id, other_id):
            user = get_object_or_404(User, pk=item_id)
            if user.id != other_id:
                raise Http404()
            return user
        """
    )

    assert extract_guards(source, "detail", ("item_id", "other_id")) == ()


def test_a_callee_parameter_bound_to_the_requester_positionally_scopes() -> None:
    source = dedent(
        """
        async def _read_flow(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return (await session.exec(stmt)).first()

        async def read_flow(session, flow_id, current_user):
            return await _read_flow(session, flow_id, current_user.id)
        """
    )

    assert _single_guard(source, "read_flow", ("flow_id",)) == Guard(
        symbol="_read_flow",
        predicate="select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)",
        scopes_object=True,
        covers=("flow_id",),
    )


def test_a_callee_parameter_bound_to_the_requester_by_keyword_scopes() -> None:
    source = dedent(
        """
        async def _read_flow(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return (await session.exec(stmt)).first()

        async def read_flow(session, flow_id, current_user):
            return await _read_flow(session=session, flow_id=flow_id, user_id=current_user.id)
        """
    )

    assert _single_guard(source, "read_flow", ("flow_id",)) == Guard(
        symbol="_read_flow",
        predicate="select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)",
        scopes_object=True,
        covers=("flow_id",),
    )


def test_a_callee_parameter_only_named_for_the_requester_does_not_scope() -> None:
    source = dedent(
        """
        async def _read_flow(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return (await session.exec(stmt)).first()

        async def read_flow(session, flow_id, user_id):
            return await _read_flow(session, flow_id, user_id)
        """
    )

    assert extract_guards(source, "read_flow", ("flow_id",)) == ()


def test_route_converter_clears_the_dead_guard(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "__init__.py").write_text("")
    (repo / "app" / "views.py").write_text(dedent(
        """
        from flask import Blueprint

        bp = Blueprint("views", __name__)

        @bp.route("/users/<int:user_id>/")
        def get_user(user_id):
            user = db.get(User, user_id)
            if request.user.id != user_id:
                raise PermissionError
            return user
        """
    ))

    filled = backfill_handler_facts(parse_repo(repo), repo)

    (guard,) = filled.node_of["app.views.get_user"].guards
    assert guard.dead is False
    assert guard.scopes_object is True


def test_a_byte_order_mark_does_not_hide_the_guards(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "__init__.py").write_text("")
    source = dedent(
        """
        from flask import Blueprint

        bp = Blueprint("views", __name__)

        @bp.route("/users/<user_id>/")
        def get_user(user_id):
            user = db.get(User, user_id)
            if request.user.id != user.owner_id:
                raise PermissionError
            return user
        """
    )
    (repo / "app" / "views.py").write_bytes(b"\xef\xbb\xbf" + source.encode())

    filled = backfill_handler_facts(parse_repo(repo), repo)

    assert filled.node_of["app.views.get_user"].guards


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


def _filled_at(repo: str, sha: str):
    root = SECURITY_REPOS / repo
    if not root.exists():
        pytest.skip(f"{root} is not present")
    with repo_at_sha(root, sha) as tree:
        return backfill_handler_facts(parse_repo(tree), tree)


def _guards_at(repo: str, sha: str, handler_fqn: str) -> tuple[Guard, ...]:
    return _filled_at(repo, sha).node_of[handler_fqn].guards


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

    def test_pretix_inherited_handler_gets_facts_and_flips_across_the_fix(self) -> None:
        vulnerable = _filled_at("pretix", "703be2ebb82c0d1cacb41fc76e55ba30561414d6")
        mixin_fqn = "src.pretix.api.views.exporters.ExportersMixin.download"

        node = vulnerable.node_of[mixin_fqn]
        assert "cfid" in node.object_parameters
        assert "src.pretix.api.views.exporters.EventExportersViewSet.download" \
            not in vulnerable.node_of
        assert not any(guard.scopes_object for guard in node.guards)

        fixed = _filled_at("pretix", "4b5651862c57c6e384822d1d23292342126c479a")
        assert any(guard.symbol == "cf.allowed_for_session" and guard.scopes_object
                   for guard in fixed.node_of[mixin_fqn].guards)

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

    def test_tandoor_tenant_filter_does_not_scope_but_ownership_filter_does(self) -> None:
        handler = "cookbook.views.api.RecipeViewSet.batch_update"
        vulnerable = _guards_at(
            "recipes", "0b363fb6100e0c5d0044f60f64c0c285f86c786b", handler)
        fixed = _guards_at(
            "recipes", "84fa837c5412d50758ce32965b49a041517ce28d", handler)

        assert any("space=self.request.space" in guard.predicate
                   and not guard.scopes_object for guard in vulnerable)
        assert not any(guard.scopes_object for guard in vulnerable)
        assert any("created_by=self.request.user" in guard.predicate
                   and guard.scopes_object for guard in fixed)

    def test_langflow_callee_parameter_binding_flips_across_the_fix(self) -> None:
        # The requester reaches the query as a plain callee parameter
        # (`user_id=current_user.id`), so the scope lives inside `_read_flow`.
        handlers = (
            "src.backend.base.langflow.api.v1.flows.read_flow",
            "src.backend.base.langflow.api.v1.flows.update_flow",
            "src.backend.base.langflow.api.v1.flows.delete_flow",
        )
        for handler in handlers:
            vulnerable = _guards_at(
                "langflow", "73c1f203b0205d00928a0af7fa0e0fc93170f03e", handler)
            fixed = _guards_at(
                "langflow", "d437d018ceba95242fcf4c1279df214d96314f2e", handler)

            assert not any(guard.scopes_object for guard in vulnerable), handler
            assert any(guard.symbol == "_read_flow" and guard.scopes_object
                       for guard in fixed), handler
