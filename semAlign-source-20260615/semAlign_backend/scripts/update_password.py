
#!/usr/bin/env python3
"""更新用户密码"""


import sys
import getpass
from pathlib import Path
import argparse

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import SessionLocal
from core.security import get_password_hash
from models.user import User


def update_password(username: str, new_password: str):
    """更新指定用户的密码"""
    print("=" * 60)
    print("更新用户密码")
    print("=" * 60)
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 查询用户
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            print("\n可用的用户列表:")
            users = db.query(User).all()
            for u in users:
                print(f"  - {u.username} ({u.role})")
            db.close()
            sys.exit(1)
        
        # 验证新密码
        if len(new_password) < 6:
            print("❌ 密码长度不能少于 6 个字符")
            db.close()
            sys.exit(1)
        
        # 更新密码
        user.password_hash = get_password_hash(new_password)
        db.commit()
        
        print("✅ 密码更新成功")
        print("=" * 60)
        print(f"用户名: {username}")
        print(f"角色: {user.role}")
        print(f"状态: {'激活' if user.is_active else '禁用'}")
        print("=" * 60)
        print("\n💡 提示:")
        print("   请妥善保管新密码")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 更新密码失败: {e}")
        db.rollback()
        sys.exit(1)
        
    finally:
        db.close()





def main():
    """主函数"""


    parser = argparse.ArgumentParser(description='更新用户密码')
    parser.add_argument('--username', help='用户名（默认: admin）', default='admin')
    parser.add_argument('--password', help='新密码（如未提供则交互式输入）')
    
    args = parser.parse_args()
    
    # 如果没有提供密码，则交互式输入
    if not args.password:
        print("请输入新密码:")
        new_password = getpass.getpass("密码: ")
        
        print("请确认新密码:")
        confirm_password = getpass.getpass("确认密码: ")
        
        if new_password != confirm_password:
            print("❌ 两次输入的密码不一致")
            sys.exit(1)
        
        args.password = new_password
    
    # 更新密码
    update_password(args.username, args.password)


if __name__ == "__main__":
    main()