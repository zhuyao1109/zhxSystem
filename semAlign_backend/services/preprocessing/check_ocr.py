import sys
import os

print("="*40)
print("🔍 环境诊断工具")
print("="*40)
print(f"当前 Python 解释器路径:\n{sys.executable}")
print("-" * 40)

print("1. 正在尝试导入 paddle (飞桨核心)...")
try:
    import paddle
    print(f"✅ Paddle 导入成功! 版本: {paddle.__version__}")
    # 检查是否能运行简单的计算，确保 dll 正常
    paddle.utils.run_check()
    print("✅ Paddle 运行检查通过")
except Exception as e:
    print(f"❌ Paddle 导入或运行失败:\n{e}")
    # 如果是 DLL 错误，通常在这里

print("-" * 40)
print("2. 正在尝试导入 paddleocr...")
try:
    # 打印一下 sys.path 确认包路径在里面
    # print(sys.path) 
    from paddleocr import PaddleOCR
    print("✅ PaddleOCR 导入成功!")
except Exception as e:
    print(f"❌ PaddleOCR 导入失败 (这就是真实原因):\n{e}")
    import traceback
    traceback.print_exc()

print("="*40)
input("按回车键退出...")
