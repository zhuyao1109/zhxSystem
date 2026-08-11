import os
import tempfile
import uuid
from pathlib import Path
import shutil

def save_uploaded_file(uploaded_file, prefix="upload"):
    """保存上传的文件到临时目录"""
    temp_dir = tempfile.mkdtemp()
    file_ext = Path(uploaded_file.name).suffix
    file_name = f"{prefix}_{uuid.uuid4().hex}{file_ext}"
    file_path = Path(temp_dir) / file_name
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)

def cleanup_temp_files():
    """清理临时文件"""
    temp_dir = tempfile.gettempdir()
    for item in os.listdir(temp_dir):
        if item.startswith("upload_") or item.endswith(".tmp"):
            try:
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except OSError:
                pass

def get_file_extension(file_path):
    """获取文件扩展名"""
    return Path(file_path).suffix.lower()

def is_supported_format(file_path):
    """检查文件格式是否支持"""
    supported = ['.pdf', '.docx', '.doc', '.md', '.txt']
    return get_file_extension(file_path) in supported