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

import ast
from pathlib import Path
from textwrap import dedent

import pytest

from services.adg import parse_repo
from services.adg.object_scope import (
    ImportedDefinitions,
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


def test_a_callee_parameter_bound_to_the_requester_object_scopes_through_its_id() -> None:
    source = dedent(
        """
        def _read_flow(session, flow_id, user):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user.id)
            return stmt

        def read_flow(session, flow_id, current_user):
            return _read_flow(session, flow_id, current_user)
        """
    )

    assert _single_guard(source, "read_flow", ("flow_id",)) == Guard(
        symbol="_read_flow",
        predicate="select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user.id)",
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


def test_a_requester_bound_through_two_helpers_still_scopes() -> None:
    source = dedent(
        """
        async def _read_flow(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return (await session.exec(stmt)).first()

        async def _scoped_read(session, flow_id, uid):
            return await _read_flow(session, flow_id, uid)

        async def read_flow(session, flow_id, current_user):
            return await _scoped_read(session, flow_id, current_user.id)
        """
    )

    assert _single_guard(source, "read_flow", ("flow_id",)) == Guard(
        symbol="_read_flow",
        predicate="select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)",
        scopes_object=True,
        covers=("flow_id",),
    )


def test_one_unscoped_call_site_keeps_the_callee_unscoped() -> None:
    source = dedent(
        """
        async def _read_flow(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return (await session.exec(stmt)).first()

        async def read_flow(session, flow_id, current_user):
            await _read_flow(session, flow_id, None)
            return await _read_flow(session, flow_id, current_user.id)
        """
    )

    assert extract_guards(source, "read_flow", ("flow_id",)) == ()


def test_a_callee_parameter_bound_to_a_requester_derived_value_does_not_scope() -> None:
    source = dedent(
        """
        async def _read_flow(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return (await session.exec(stmt)).first()

        async def read_flow(session, flow_id, current_user):
            return await _read_flow(session, flow_id, current_user.teammate_ids)
        """
    )

    assert extract_guards(source, "read_flow", ("flow_id",)) == ()


@pytest.mark.parametrize("statement", [
    pytest.param(
        "stmt = select(Flow).where(Flow.id == flow_id)"
        ".exclude(own.user_id == request.user.id)",
        id="exclude"),
    pytest.param(
        "stmt = select(Flow).where("
        "(Flow.id == flow_id) | (own.user_id == request.user.id))",
        id="or"),
])
def test_a_comparison_in_a_non_scoping_chain_keeps_the_chain_verdict(
        statement: str) -> None:
    source = dedent(
        f"""
        def detail(request, flow_id):
            own = get_object_or_404(Other, pk=flow_id)
            {statement}
            return stmt
        """
    )

    guards = extract_guards(source, "detail", ("flow_id",))

    assert not any(guard.scopes_object for guard in guards)


def test_an_identically_named_column_of_another_object_is_not_the_requester() -> None:
    source = dedent(
        """
        def _load(session, flow_id, user_id):
            other = get_object_or_404(Other, pk=flow_id)
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == other.user_id)
            return stmt

        def read(session, flow_id, current_user):
            return _load(session, flow_id, current_user.id)
        """
    )

    assert extract_guards(source, "read", ("flow_id",)) == ()


def test_a_root_handler_parameter_is_not_bound_by_an_internal_caller() -> None:
    source = dedent(
        """
        def handler(request, user_id):
            item = get_object_or_404(Item, pk=user_id)
            if item.owner_id != user_id:
                raise Http404()
            _retry(request, user_id)
            return item

        def _retry(request, uid):
            return handler(request, request.user.id)
        """
    )

    assert extract_guards(source, "handler", ("user_id",)) == ()


def test_a_call_site_inside_the_last_linked_helper_still_counts() -> None:
    source = dedent(
        """
        def _load(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return stmt

        def _a(session, flow_id, uid):
            _c(session, flow_id)
            return _load(session, flow_id, uid)

        def _c(session, flow_id):
            return _load(session, flow_id, flow_id)

        def read(session, flow_id, current_user):
            return _a(session, flow_id, current_user.id)
        """
    )

    assert extract_guards(source, "read", ("flow_id",)) == ()


def _imported(mapping: dict[str, str]):
    """Module name -> parsed tree, the lookup an imported helper resolves through."""
    def source(module_name: str) -> ast.Module | None:
        text = mapping.get(module_name)
        return ast.parse(dedent(text)) if text is not None else None
    return source


def _helper_resolver(handler: str, **modules: str) -> ImportedDefinitions:
    return ImportedDefinitions(
        ast.parse(dedent(handler)), "app.routes", _imported(modules))


def test_an_imported_helper_whose_every_grant_path_names_the_requester_scopes() -> None:
    handler = """
        from app.access import has_access

        def get_file(item_id, user=Depends(get_verified_user)):
            if has_access(item_id, user):
                return user
    """
    helper = """
        def has_access(item_id, user):
            file = load_file(item_id)
            if file.user_id == user.id:
                return True
            shared = shared_with(file)
            if shared:
                accessible = accessible_for(user.id, shared)
                if accessible:
                    return True
            return False
    """
    resolver = _helper_resolver(handler, **{"app.access": helper})

    guards = extract_guards(
        dedent(handler), "get_file", ("item_id",),
        resolve_callees=resolver.resolve)

    assert Guard(
        symbol="has_access",
        predicate="has_access(item_id, user)",
        scopes_object=True,
    ) in guards


def test_one_requester_less_grant_path_makes_the_imported_helper_unscoped() -> None:
    """The ownership comparison at the top does not redeem a later grant that
    never names the requester. The helper's own guards are not emitted, so the
    handler cannot be cleared by the comparison alone."""
    handler = """
        from app.access import has_access

        def get_file(item_id, user=Depends(get_verified_user)):
            if has_access(item_id, user):
                return user
    """
    helper = """
        def has_access(item_id, user):
            file = load_file(item_id)
            if file.user_id == user.id:
                return True
            chats = shared_chats(file)
            if chats:
                return True
            return False
    """
    resolver = _helper_resolver(handler, **{"app.access": helper})

    guards = extract_guards(
        dedent(handler), "get_file", ("item_id",),
        resolve_callees=resolver.resolve)

    assert guards == (
        Guard(
            symbol="has_access",
            predicate="has_access(item_id, user)",
            scopes_object=False,
        ),
    )


def test_an_or_branch_that_grants_without_the_requester_makes_the_helper_unscoped() -> None:
    handler = """
        from app.access import has_access

        def get_file(item_id, user=Depends(get_verified_user)):
            if has_access(item_id, user):
                return user
    """
    helper = """
        def has_access(item_id, user):
            if shared_with(item_id) or owner_of(item_id) == user.id:
                return True
            return False
    """
    resolver = _helper_resolver(handler, **{"app.access": helper})

    guards = extract_guards(
        dedent(handler), "get_file", ("item_id",),
        resolve_callees=resolver.resolve)

    assert guards == (
        Guard(symbol="has_access", predicate="has_access(item_id, user)",
              scopes_object=False),
    )


def test_an_unresolved_helper_is_never_a_silently_scoping_guard() -> None:
    source = dedent(
        """
        def get_file(item_id, user=Depends(get_verified_user)):
            if has_access(item_id, user):
                return user
        """
    )
    resolver = _helper_resolver(source)

    assert extract_guards(
        source, "get_file", ("item_id",),
        resolve_callees=resolver.resolve) == (
        Guard(
            symbol="has_access",
            predicate="has_access(item_id, user)",
            scopes_object=False,
        ),
    )


def test_an_imported_but_missing_symbol_is_unverified_not_scoping() -> None:
    handler = """
        from app.access import has_access

        def get_file(item_id, user=Depends(get_verified_user)):
            if has_access(item_id, user):
                return user
    """
    module = """
        def other_helper(item_id, user):
            return owner_of(item_id) == user.id
    """
    resolver = _helper_resolver(handler, **{"app.access": module})

    (guard,) = extract_guards(
        dedent(handler), "get_file", ("item_id",),
        resolve_callees=resolver.resolve)

    assert guard.symbol == "has_access"
    assert not guard.scopes_object


def _imported_helper_scopes(helper_body: str,
                            call: str = "has_access(item_id, user)",
                            params: str = "user=Depends(get_verified_user)",
                            ) -> bool:
    handler = f"""
        from app.access import has_access

        def get_file(item_id, {params}):
            if {call}:
                return {params.split('=')[0]}
    """
    resolver = _helper_resolver(handler, **{"app.access": dedent(helper_body)})
    guards = extract_guards(
        dedent(handler), "get_file", ("item_id",),
        resolve_callees=resolver.resolve)
    return any(guard.symbol == "has_access" and guard.scopes_object
               for guard in guards)


def test_a_grant_in_the_else_of_an_ownership_test_does_not_scope() -> None:
    """The return sits where the ownership test is false: granting there is
    the requester-less path. `!=` flips the polarity and does scope."""
    assert not _imported_helper_scopes("""
        def has_access(item_id, user):
            file = load_file(item_id)
            if file.user_id == user.id:
                return False
            else:
                return True
    """)
    assert _imported_helper_scopes("""
        def has_access(item_id, user):
            file = load_file(item_id)
            if file.user_id != user.id:
                return False
            else:
                return True
    """)


def test_a_returned_or_with_a_requester_less_side_does_not_scope() -> None:
    assert not _imported_helper_scopes("""
        def has_access(item_id, user):
            file = load_file(item_id)
            return shared_with(file) or file.user_id == user.id
    """)


def test_a_ternary_grant_that_can_take_the_requester_less_branch_does_not_scope() -> None:
    assert not _imported_helper_scopes("""
        def has_access(item_id, user):
            file = load_file(item_id)
            return True if shared_with(file) else file.user_id == user.id
    """)


def test_a_fail_open_except_return_is_a_grant_path() -> None:
    assert not _imported_helper_scopes("""
        def has_access(item_id, user):
            try:
                return owner_of(item_id) == user.id
            except Exception:
                return True
    """)


def test_an_augmented_or_conditional_rebinding_of_a_traced_local_does_not_scope() -> None:
    assert not _imported_helper_scopes("""
        def has_access(item_id, user):
            allowed = count_for(user.id)
            allowed |= shared_with(item_id)
            if allowed:
                return True
            return False
    """)
    assert not _imported_helper_scopes("""
        def has_access(item_id, user):
            if needs_lookup(item_id):
                allowed = allowed_for(user.id)
            if allowed:
                return True
            return False
    """)


def test_only_a_requester_returning_dependency_binds_a_requester() -> None:
    """`Depends(get_user_settings)` returns settings, not the user; treating it
    as the requester would clear a handler on a non-identity value."""
    assert not _imported_helper_scopes(
        """
        def has_access(item_id, settings):
            if settings.owner_id == settings.id:
                return True
            return False
        """,
        call="has_access(item_id, settings)",
        params="settings=Depends(get_user_settings)")


def test_a_falsy_container_return_is_not_a_grant_path() -> None:
    assert _imported_helper_scopes("""
        def has_access(item_id, user):
            if owner_of(item_id) == user.id:
                return True
            return []
    """)


def test_an_ownership_column_of_another_model_does_not_scope() -> None:
    source = dedent(
        """
        def detail(request, flow_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Other.user_id == request.user.id)
            return stmt
        """
    )

    guards = extract_guards(source, "detail", ("flow_id",))

    assert not any(guard.scopes_object for guard in guards)


@pytest.mark.parametrize("select,prefix", [
    pytest.param("select(Flow.id)", "Flow", id="column"),
    pytest.param("select(models.Flow)", "models.Flow", id="module-qualified"),
])
def test_a_column_or_module_qualified_query_still_scopes(
        select: str, prefix: str) -> None:
    source = dedent(
        f"""
        def _load(session, flow_id, user_id):
            stmt = {select}.where({prefix}.id == flow_id).where({prefix}.user_id == user_id)
            return stmt

        def read(session, flow_id, current_user):
            return _load(session, flow_id, current_user.id)
        """
    )

    guards = extract_guards(source, "read", ("flow_id",))

    assert any(guard.symbol == "_load" and guard.scopes_object
               for guard in guards)


def test_a_starred_argument_at_the_call_site_binds_nothing() -> None:
    source = dedent(
        """
        def _load(session, flow_id, user_id):
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return stmt

        def read(session, flow_id, current_user):
            rest = ()
            return _load(*rest, current_user.id)
        """
    )

    assert extract_guards(source, "read", ("flow_id",)) == ()


def test_a_parameter_reassigned_inside_the_callee_is_not_the_requester() -> None:
    source = dedent(
        """
        def _load(session, flow_id, user_id):
            user_id = flow_id
            stmt = select(Flow).where(Flow.id == flow_id).where(Flow.user_id == user_id)
            return stmt

        def read(session, flow_id, current_user):
            return _load(session, flow_id, current_user.id)
        """
    )

    assert extract_guards(source, "read", ("flow_id",)) == ()


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

    def test_open_webui_imported_helper_grant_path_flips_across_the_fix(self) -> None:
        # The guard is an imported helper. Its body's ownership comparison is
        # not enough: the vulnerable body has a grant path that never names the
        # requester, so the helper does not scope and the handler fires.
        handler = "backend.open_webui.routers.files.get_file_by_id"
        vulnerable = _guards_at(
            "open-webui", "4d2f18981051205016bd24d39521e25a33581225", handler)
        fixed = _guards_at(
            "open-webui", "2e52ad8ff2f8d9ed9f38f76e9bc19c8f92d91fc3", handler)

        assert any(guard.symbol == "has_access_to_file"
                   and not guard.scopes_object for guard in vulnerable)
        assert not any(guard.scopes_object for guard in vulnerable)
        assert any(guard.symbol == "has_access_to_file" and guard.scopes_object
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
