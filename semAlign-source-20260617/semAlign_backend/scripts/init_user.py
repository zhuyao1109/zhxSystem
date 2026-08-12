
#!/usr/bin/env python3
"""初始化管理员用户"""


import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import SessionLocal
from core.security import get_password_hash
from models.user import User, UserRole


def create_admin_user():
    """创建管理员用户（默认：admin/admin123）"""
    print("=" * 60)
    print("初始化管理员用户")
    print("=" * 60)
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 检查是否已存在 admin 用户
        admin = db.query(User).filter(User.username == "admin").first()
        
        if admin:
            print("⚠️  管理员用户已存在")
            print(f"   用户名: {admin.username}")
            print(f"   角色: {admin.role}")
            print(f"   状态: {'激活' if admin.is_active else '禁用'}")
            print("\n如需重置密码，请运行: python scripts/update_password.py")
            return
        
        # 创建管理员用户
        admin = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            email="admin@example.com",
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        
        print("✅ 管理员用户创建成功")
        print("=" * 60)
        print("登录信息:")
        print("   用户名: admin")
        print("   密码: admin123")
        print("   角色: 管理员")
        print("=" * 60)
        print("\n💡 提示:")
        print("   1. 请在生产环境中立即修改默认密码")
        print("   2. 使用 update_password.py 脚本修改密码")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        db.rollback()
        sys.exit(1)
        
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()