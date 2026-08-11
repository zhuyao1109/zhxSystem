import pdfplumber
from docx import Document
import re
from typing import Dict, List, Any, Tuple
import fitz
import markdown

_PARSE_ERRORS = (OSError, ValueError, RuntimeError, KeyError, AttributeError)


class DocumentParser:
    """类：DocumentParser。"""
    def __init__(self):
        """函数内部辅助：init  。"""
        self.supported_formats = ['.pdf', '.docx', '.doc', '.md', '.txt']
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """函数：parse。"""
        file_ext = self._get_extension(file_path)
        
        if file_ext == '.pdf':
            return self._parse_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return self._parse_docx(file_path)
        elif file_ext == '.md':
            return self._parse_markdown(file_path)
        elif file_ext == '.txt':
            return self._parse_text(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
    
    def _get_extension(self, file_path: str) -> str:
        """函数内部辅助：get extension。"""
        return '.' + file_path.split('.')[-1].lower()
    
    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """函数内部辅助：parse pdf。"""
        content = {
            "sections": [],
            "full_text": "",
            "metadata": {},
            "pages": []
        }
        
        try:
            # 尝试使用pdfplumber
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n"
                    content["pages"].append({
                        "page_number": i + 1,
                        "text": page_text
                    })
                
                content["full_text"] = full_text
                
                # 提取元数据
                if hasattr(pdf, 'metadata') and pdf.metadata:
                    content["metadata"] = dict(pdf.metadata)
                
                return content
        except _PARSE_ERRORS as e1:
            try:
                # 回退到PyMuPDF
                doc = fitz.open(file_path)
                full_text = ""
                for i, page in enumerate(doc):
                    page_text = page.get_text()
                    full_text += page_text + "\n"
                    content["pages"].append({
                        "page_number": i + 1,
                        "text": page_text
                    })
                
                content["full_text"] = full_text
                doc.close()
                return content
            except _PARSE_ERRORS as e2:
                raise RuntimeError(f"PDF解析失败: {e1}, {e2}") from e2
    
    def _build_docx_paragraphs(self, doc) -> Tuple[List[Dict[str, Any]], str]:
        """函数内部辅助：build docx paragraphs。"""
        paragraphs = []
        full_text = ""
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                text = para.text.strip()
                paragraphs.append({
                    "index": i,
                    "text": text,
                    "style": para.style.name if para.style else "Normal"
                })
                full_text += text + "\n"
        return paragraphs, full_text

    def _extract_docx_metadata(self, doc) -> Dict[str, Any]:
        """函数内部辅助：extract docx metadata。"""
        props = doc.core_properties
        if not props:
            return {}
        return {
            "title": props.title or "",
            "author": props.author or "",
            "subject": props.subject or "",
            "keywords": props.keywords or "",
            "created": str(props.created) if props.created else "",
            "modified": str(props.modified) if props.modified else ""
        }

    def _parse_docx(self, file_path: str) -> Dict[str, Any]:
        """函数内部辅助：parse docx。"""
        content = {
            "sections": [],
            "full_text": "",
            "metadata": {},
            "paragraphs": []
        }
        
        try:
            doc = Document(file_path)
            paragraphs, full_text = self._build_docx_paragraphs(doc)
            content["full_text"] = full_text
            content["paragraphs"] = paragraphs
            content["metadata"] = self._extract_docx_metadata(doc)
            return content
        except _PARSE_ERRORS as e:
            raise RuntimeError(f"Word文档解析失败: {e}") from e
    
    def _parse_markdown_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        """函数内部辅助：parse markdown sections。"""
        sections = []
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                level = len(re.match(r'^#+', line).group())
                title = line.strip('#').strip()
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "level": level,
                    "title": title,
                    "content": ""
                }
            elif current_section:
                current_section["content"] += line + "\n"
        if current_section:
            sections.append(current_section)
        return sections

    def _extract_yaml_front_matter(self, lines: List[str]) -> Dict[str, Any]:
        """函数内部辅助：extract yaml front matter。"""
        metadata = {}
        if not lines or lines[0].strip() != '---':
            return metadata
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                for yaml_line in lines[1:i]:
                    if ':' in yaml_line:
                        key, value = yaml_line.split(':', 1)
                        metadata[key.strip()] = value.strip()
                break
        return metadata

    def _parse_markdown(self, file_path: str) -> Dict[str, Any]:
        """函数内部辅助：parse markdown。"""
        content = {
            "sections": [],
            "full_text": "",
            "metadata": {},
            "structure": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
            
            content["full_text"] = md_text
            lines = md_text.split('\n')
            content["sections"] = self._parse_markdown_sections(lines)
            content["metadata"] = self._extract_yaml_front_matter(lines)
            return content
        except _PARSE_ERRORS as e:
            raise RuntimeError(f"Markdown解析失败: {e}") from e
    
    def _parse_text(self, file_path: str) -> Dict[str, Any]:
        """函数内部辅助：parse text。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return {
                "sections": self._extract_sections(text),
                "full_text": text,
                "metadata": {}
            }
        except _PARSE_ERRORS as e:
            raise RuntimeError(f"文本文件解析失败: {e}") from e
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """函数内部辅助：extract sections。"""
        sections = []
        lines = text.split('\n')
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 常见的中文章节模式
            patterns = [
                r'^第[一二三四五六七八九十\d]+章\s+',
                r'^第[一二三四五六七八九十\d]+节\s+',
                r'^\d+\.\d+(\.\d+)*\s+',
                r'^[一二三四五六七八九十]+、\s*'
            ]
            
            is_section = any(re.match(pattern, line) for pattern in patterns)
            
            if is_section:
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "title": line,
                    "content": "",
                    "line_start": i
                }
            elif current_section:
                current_section["content"] += line + "\n"
        
        if current_section:
            sections.append(current_section)
        
        return sections