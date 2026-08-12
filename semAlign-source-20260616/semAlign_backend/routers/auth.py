"""认证路由 - 处理用户登录和认证相关操作"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.deps import get_db, get_current_user
from core.security import create_access_token, get_password_hash, verify_password
from models.user import User
from schemas.user import ForgotPasswordRequest, LoginRequest, LoginResponse, UserResponse
from schemas.base import APIResponse

router = APIRouter(prefix="/auth", tags=["认证模块"])


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录接口
    
    业务逻辑：
        1. 根据用户名查询用户
        2. 验证密码是否正确
        3. 检查用户账户状态
        4. 生成 JWT 访问令牌
        5. 返回令牌和用户信息
    
    请求参数：
        - username: 用户名
        - password: 密码
    
    返回数据：
        - token: JWT 访问令牌
        - user: 用户信息
    
    前端使用示例：
        const response = await api.login({ username, password });
        const { token, user } = response.data;
        localStorage.setItem('token', token);
        // 后续请求会自动携带 token
    
    错误处理：
        - 401: 用户名或密码错误
        - 403: 用户账户已被禁用
    
    Args:
        request: 登录请求（包含用户名和密码）
        db: 数据库会话
    
    Returns:
        APIResponse[LoginResponse]: 登录响应（包含 token 和用户信息）
    """
    # 查询用户
    user = db.query(User).filter(User.username == request.username).first()
    
    # 验证用户名和密码
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查用户账户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用，请联系管理员"
        )
    
    # 生成 JWT 访问令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # 返回登录响应
    return APIResponse(
        data=LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        ),
        message="登录成功"
    )


@router.post("/forgot-password", response_model=APIResponse[dict])
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    """忘记密码闭环：通过用户名或邮箱直接重置密码。

    当前系统为内网演示/管理系统，暂未接入邮件验证码；因此采用账号信息 + 新密码的闭环重置方式。
    生产环境应替换为验证码或管理员审批重置流程。
    """
    value = request.username_or_email.strip()
    user = db.query(User).filter(
        (User.username == value) | (User.email == value)
    ).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在，请检查用户名或邮箱",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    user.password_hash = get_password_hash(request.new_password)
    db.commit()
    return APIResponse(
        data={"reset": True},
        message="密码已重置，请使用新密码登录",
    )


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息接口
    
    业务逻辑：
        1. 从请求头中提取 JWT Token
        2. 验证 Token 有效性
        3. 从 Token 中解析用户 ID
        4. 查询用户信息
        5. 返回用户信息
    
    请求头：
        Authorization: Bearer {token}
    
    返回数据：
        - id: 用户 ID
        - username: 用户名
        - email: 邮箱
        - role: 用户角色
        - is_active: 账户状态
        - avatar: 头像
        - created_at: 创建时间
    
    前端使用示例：
        const response = await api.getCurrentUser();
        const user = response.data;
        console.log(user.username);
    
    错误处理：
        - 401: Token 无效或已过期
        - 403: 用户账户已被禁用
    
    Args:
        current_user: 当前认证用户（通过依赖注入获取）
    
    Returns:
        APIResponse[UserResponse]: 用户信息响应
    """
    return APIResponse(data=UserResponse.model_validate(current_user))