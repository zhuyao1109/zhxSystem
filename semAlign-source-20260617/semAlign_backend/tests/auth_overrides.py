"""
测试用 FastAPI 依赖覆盖，供多个测试模块复用。

用法::

    from core.deps import get_current_user
    from tests.auth_overrides import override_get_current_user

    app.dependency_overrides[get_current_user] = override_get_current_user(user)
"""

from collections.abc import Callable

from models.user import User


def override_get_current_user(user: User) -> Callable[[], User]:
    """
    构造可赋值给 ``app.dependency_overrides[get_current_user]`` 的函数，
    在测试中固定返回给定用户，不校验 JWT。
    """
    def _impl() -> User:
        return user

    return _impl
