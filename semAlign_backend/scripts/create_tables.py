#!/usr/bin/env python3
"""创建数据库表"""

import sys
from pathlib import Path
import argparse

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import engine, Base
from models import user, standard, alignment_task, term_conflict, conflict_dialogue


def create_tables(rebuild: bool = False):
    """创建数据库表，rebuild=True时强制重建"""
    print("=" * 60)
    print("创建数据库表")
    print("=" * 60)
    
    try:
        if rebuild:
            print("⚠️  警告: 强制重建模式")
            print("   这将删除所有现有数据！")
            
            # 确认操作
            confirm = input("\n确认要继续吗？: ")
            if confirm.lower() != 'yes':
                print("操作已取消")
                sys.exit(0)
            
            # 删除所有表
            print("\n正在删除现有表...")
            Base.metadata.drop_all(bind=engine)
            print("✅ 现有表已删除")
        
        # 创建所有表
        print("\n正在创建表...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ 数据库表创建成功")
        print("=" * 60)
        print("已创建的表:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
        print("=" * 60)
        
        if rebuild:
            print("\n💡 提示:")
            print("   数据已清空，请运行 init_user.py 创建管理员用户")
            print("=" * 60)
        
    except Exception as e:
        print(f"❌ 创建数据库表失败: {e}")
        sys.exit(1)


def list_tables():
    """列出数据库中所有表"""
    print("=" * 60)
    print("数据库表列表")
    print("=" * 60)
    
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("数据库中没有表")
        else:
            for table_name in tables:
                print(f"  - {table_name}")
                
        print("=" * 60)
        print(f"共 {len(tables)} 个表")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 列出表失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='创建数据库表')
    parser.add_argument('--rebuild', action='store_true', help='强制重建表（会删除现有数据）')
    parser.add_argument('--list', action='store_true', help='列出所有已存在的表')
    
    args = parser.parse_args()
    
    if args.list:
        list_tables()
    else:
        create_tables(rebuild=args.rebuild)


if __name__ == "__main__":
    main()
