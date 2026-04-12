from app.api.system import health, roles, users
from app.authz.codes import PermissionCode
from app.authz.policy import build_default_policy_resolver, endpoint_key


def test_policy_resolver_supports_function_level_mapping_for_post_routes():
    resolver = build_default_policy_resolver()

    create_role_policy = resolver.resolve(roles.create_role)
    delete_role_policy = resolver.resolve(roles.delete_role)

    assert create_role_policy.public is False
    assert create_role_policy.permissions == (PermissionCode.ROLE_CREATE,)

    assert delete_role_policy.public is False
    assert delete_role_policy.permissions == (PermissionCode.ROLE_DELETE,)


def test_policy_resolver_can_mark_health_endpoint_public():
    resolver = build_default_policy_resolver()

    health_policy = resolver.resolve(health.health_check)

    assert health_policy.public is True
    assert health_policy.permissions == ()


def test_endpoint_key_uses_module_and_qualname_for_stable_mapping():
    key = endpoint_key(users.list_users)
    assert key == "app.api.system.users:list_users"
