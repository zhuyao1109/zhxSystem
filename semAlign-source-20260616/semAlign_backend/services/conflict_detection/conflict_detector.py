"""
冲突检测器 - 智能解析 + 适配同步LLM
"""

import os
import re
import json
import warnings
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# 忽略警告
warnings.filterwarnings("ignore")

# --- 导入大模型检测器 ---
try:
    # 尝试同一目录导入
    from llm_conflict_detector import LLMConflictDetector
    LLM_AVAILABLE = True
except ImportError:
    try:
        # 尝试包路径导入
        from src.conflict_detection.llm_conflict_detector import LLMConflictDetector
        LLM_AVAILABLE = True
    except ImportError:
        LLM_AVAILABLE = False
        print("⚠️ 无法导入 llm_conflict_detector，大模型功能禁用")

@dataclass
class DataItem:
    """数据项实体"""
    id: str
    name: str = ""
    text: str = ""
    section: str = "正文"
    source: str = ""
    def to_dict(self): return asdict(self)

class UniversalParser:
    """通用解析器 (支持 txt/md 智能分块)"""
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """函数：parse file。"""
        filename = os.path.basename(file_path)
        print(f"\n🔍 解析文件: {filename}")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"❌ 读取文件失败: {e}")
            return {"clauses": [], "metadata": {}}

        # 预清洗
        content = self._preprocess_clean(content)
        # 智能分块
        items = self._parse_structured_text(content, filename)
        print(f"✅ 提取到 {len(items)} 个数据项")
        
        clauses = []
        for i, item in enumerate(items):
            clauses.append({
                "id": item.id,
                "text": item.text,
                "section": item.section,
                "data_item": item.to_dict(),
                "document_metadata": {"filename": filename, "file_path": file_path}
            })
            
        return {
            "clauses": clauses,
            "metadata": {
                "document_name": filename,
                "file_path": file_path,
                "total_items": len(items)
            }
        }

    def _preprocess_clean(self, content: str) -> str:
        # 去除页眉页脚页码
        """函数内部辅助：preprocess clean。"""
        content = re.sub(r'GB/T\s*\d+[—\-一]\d{4}', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^\s*\d+\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'…{2,}', '', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content

    def _parse_structured_text(self, content: str, source: str) -> List[DataItem]:
        """函数内部辅助：parse structured text。"""
        items = []
        # 模糊匹配头部 (兼容 OCR 产生的空格/标点错误)
        start_markers = [r'数\s*据\s*项\s*名\s*称', r'中\s*文\s*名\s*称', r'字\s*段\s*名']
        pattern = f"({'|'.join(start_markers)})"
        
        parts = re.split(pattern, content)
        current_block = ""
        
        # 智能跳过前言
        start_idx = 0
        for i, p in enumerate(parts):
            if any(re.search(m, p) for m in start_markers):
                current_block = p; start_idx = i + 1; break
        
        for i in range(start_idx, len(parts)):
            p = parts[i]
            if not p.strip(): continue
            if any(re.search(m, p) for m in start_markers):
                if current_block: self._add_item(items, current_block, source)
                current_block = p
            else:
                current_block += p
        
        if current_block: self._add_item(items, current_block, source)
        
        if not items: return self._fallback_parse(content, source)
        return items

    def _add_item(self, items, text, source):
        """函数内部辅助：add item。"""
        text = text.strip()
        if len(text) < 10: return
        # 提取名字
        name = "未知项"
        m = re.match(r'.*?[:：\s]\s*(.+)', text.split('\n')[0])
        if m: name = m.group(1).strip()
        if len(name) > 50: return # 名字太长可能是解析错位
        
        items.append(DataItem(id=f"{source}_{len(items)}", name=name, text=text, source=source))

    def _fallback_parse(self, content, source):
        # 兜底：按段落分
        """函数内部辅助：fallback parse。"""
        items = []
        for i, p in enumerate(re.split(r'\n\s*\n', content)):
            if len(p.strip()) > 20:
                items.append(DataItem(id=f"{source}_para_{i}", name=f"条款{i}", text=p.strip(), source=source))
        return items

class EnhancedConflictDetector:
    """增强版冲突检测器"""
    def __init__(self, use_llm: bool = False, llm_api_key: str = None):
        """函数内部辅助：init  。"""
        self.use_llm = use_llm and LLM_AVAILABLE
        self.parser = UniversalParser()
        self.llm = None
        if self.use_llm:
            try:
                self.llm = LLMConflictDetector(api_key=llm_api_key)
            except (ValueError, RuntimeError, OSError) as e:
                print(f"❌ LLM 初始化失败: {e}")

    def detect_conflicts(self, file_a: str, file_b: str) -> List[Dict]:
        """函数：detect conflicts。"""
        print("="*60)
        print(f"🚀 启动检测: {os.path.basename(file_a)} vs {os.path.basename(file_b)}")
        
        doc_a = self.parser.parse_file(file_a)
        doc_b = self.parser.parse_file(file_b)
        
        conflicts = []
        if self.llm:
            print("\n🤖 调用大模型分析...")
            conflicts = self.llm.detect_conflicts(
                doc_a['clauses'], doc_b['clauses'],
                doc_a['metadata'], doc_b['metadata']
            )
            print(f"✅ 发现 {len(conflicts)} 个冲突")
            
        self._save_report(file_a, file_b, conflicts)
        return conflicts

    def _save_report(self, fa, fb, conflicts):
        """函数内部辅助：save report。"""
        name = f"report_{os.path.basename(fa)}_vs_{os.path.basename(fb)}.json"
        try:
            with open(name, 'w', encoding='utf-8') as f:
                json.dump(conflicts, f, ensure_ascii=False, indent=2, default=str)
            print(f"💾 报告已保存: {name}")
        except OSError:
            pass

if __name__ == "__main__":
    # 测试代码
    folder = r"D:\zhx_model_sft\mvp\data"
    key = "sk-284a6a8d7787428b86044a35c57aa3b0"
    if os.path.exists(folder):
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('txt')]
        if len(files) >= 2:
            detector = EnhancedConflictDetector(use_llm=True, llm_api_key=key)
            detector.detect_conflicts(files[0], files[1])
