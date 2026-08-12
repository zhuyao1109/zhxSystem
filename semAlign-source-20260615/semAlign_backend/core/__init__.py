"""Core module for SemAlign backend."""

from .config import settings
from .database import engine, SessionLocal, Base, get_db

try:
    from .security import (
        get_password_hash,
        verify_password,
        create_access_token,
        decode_access_token,
    )
except Exception:  # pragma: no cover - 允许精简环境下仅使用数据库能力
    get_password_hash = None
    verify_password = None
    create_access_token = None
    decode_access_token = None

try:
    from .deps import (
        get_current_user,
        get_current_active_user,
        get_current_admin_user,
    )
except Exception:  # pragma: no cover - 允许精简环境下仅使用数据库能力
    get_current_user = None
    get_current_active_user = None
    get_current_admin_user = None

__all__ = [
    "settings",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
]
