"""用户资料路由 — GET/PUT /api/user/profile（与 mvp 及前端 Endpoints.USER_PROFILE 一致）。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.deps import get_current_admin_user, get_current_user, get_db
from core.security import verify_password, get_password_hash
from models.user import User
from schemas.base import APIResponse
from schemas.user import AdminUserUpdate, UserResponse, UserUpdate, ChangePasswordRequest

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.get("/permissions", response_model=APIResponse[dict])
async def get_permissions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIResponse[dict]:
    """获取当前用户权限配置。"""
    is_admin = current_user.role == "admin"
    return APIResponse(
        data={
            "role": current_user.role,
            "permissions": {
                "search": True,
                "view_reviewed_alignment": True,
                "import_standards": is_admin,
                "manage_alignment_tasks": is_admin,
                "manage_users": is_admin,
            },
        }
    )


@router.get("/admin/users", response_model=APIResponse[list[UserResponse]])
async def list_users(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_admin_user)],
) -> APIResponse[list[UserResponse]]:
    """管理员查看用户列表。"""
    users = db.query(User).order_by(User.id.asc()).all()
    return APIResponse(data=[UserResponse.model_validate(user) for user in users])


@router.put("/admin/users/{user_id}", response_model=APIResponse[UserResponse])
async def update_user_by_admin(
    user_id: int,
    body: AdminUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_admin_user)],
) -> APIResponse[UserResponse]:
    """管理员更新用户角色和启用状态。"""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if body.role is not None:
        if body.role not in {"admin", "user"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色只能是 admin 或 user")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return APIResponse(data=UserResponse.model_validate(user), message="用户权限已更新")


@router.get("/profile", response_model=APIResponse[UserResponse])
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIResponse[UserResponse]:
    """获取当前用户信息。"""
    return APIResponse(data=UserResponse.model_validate(current_user))


@router.put("/profile", response_model=APIResponse[UserResponse])
async def update_profile(
    body: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIResponse[UserResponse]:
    """更新用户邮箱、头像等。"""
    if body.email is not None:
        current_user.email = body.email
    if body.avatar is not None:
        current_user.avatar = body.avatar
    db.commit()
    db.refresh(current_user)
    return APIResponse(data=UserResponse.model_validate(current_user), message="更新成功")


@router.post("/change-password", response_model=APIResponse[dict])
async def change_password(
    body: ChangePasswordRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIResponse[dict]:
    """修改当前用户密码。"""
    # 验证旧密码
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )

    # 检查新密码不能与旧密码相同
    if body.old_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与当前密码相同"
        )

    # 更新密码
    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()

    return APIResponse(data={"success": True}, message="密码修改成功")
