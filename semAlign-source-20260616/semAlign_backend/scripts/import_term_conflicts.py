#!/usr/bin/env python3
"""导入术语冲突 CSV 到数据库。"""

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import Base, SessionLocal, engine
from models import ImportBatch, Term, TermConflict


def file_sha256(path: Path) -> str:
    """计算文件 SHA256。"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def clean_text(value: Optional[str]) -> str:
    """清洗字符串，统一空白。"""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_term(value: str) -> str:
    """术语规范化，用于唯一性比较。"""
    return clean_text(value).lower()


def normalize_standard_no(value: str) -> str:
    """标准号规范化，减小格式差异影响。"""
    text = clean_text(value).upper()
    text = text.replace("／", "/")
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*-\s*", "-", text)
    return text


def ordered_pair(a: str, b: str) -> tuple[str, str]:
    """生成有序标准号对，保证 A/B 与 B/A 视为同一对。"""
    x = normalize_standard_no(a)
    y = normalize_standard_no(b)
    if x <= y:
        return x, y
    return y, x


def normalize_headers(row: Dict[str, str]) -> Dict[str, str]:
    """清洗表头（处理 BOM）。"""
    fixed = {}
    for k, v in row.items():
        key = k.lstrip("\ufeff").strip() if isinstance(k, str) else k
        fixed[key] = v
    return fixed


def upsert_term(db, cache: Dict[str, Term], term_name: str) -> Term:
    """获取或创建术语。"""
    term_norm = normalize_term(term_name)
    if term_norm in cache:
        return cache[term_norm]

    term = db.query(Term).filter(Term.name_norm == term_norm).first()
    if term is None:
        term = Term(name=clean_text(term_name), name_norm=term_norm)
        db.add(term)
        db.flush()
    cache[term_norm] = term
    return term


def import_csv(csv_path: Path, dry_run: bool = False) -> None:
    """导入 CSV。"""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        file_hash = file_sha256(csv_path)
        batch = ImportBatch(
            file_name=csv_path.name,
            file_hash=file_hash,
            status="processing",
            source_type="terminology_conflict_csv",
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        term_cache: Dict[str, Term] = {}
        seen_in_file = set()
        total_rows = 0
        success_rows = 0
        failed_rows = 0
        failed_examples = []

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_rows += 1
                raw = normalize_headers(row)

                term_name = clean_text(raw.get("术语名", ""))
                std1_raw = clean_text(raw.get("定义1来源标准", ""))
                std2_raw = clean_text(raw.get("定义2来源标准", ""))
                conflict_type = clean_text(raw.get("冲突类型", ""))
                conflict_desc = clean_text(raw.get("冲突描述", ""))

                if not term_name or not std1_raw or not std2_raw or not conflict_type:
                    failed_rows += 1
                    if len(failed_examples) < 20:
                        failed_examples.append(f"第 {total_rows} 行缺少必要字段")
                    continue

                std1, std2 = ordered_pair(std1_raw, std2_raw)
                pair_key = f"{std1}||{std2}"

                term = upsert_term(db, term_cache, term_name)

                dedup_key = (term.id, pair_key, conflict_type, conflict_desc)
                if dedup_key in seen_in_file:
                    continue

                exists = (
                    db.query(TermConflict.id)
                    .filter(TermConflict.term_id == term.id)
                    .filter(TermConflict.pair_key == pair_key)
                    .filter(TermConflict.conflict_type == conflict_type)
                    .filter(TermConflict.conflict_desc == conflict_desc)
                    .first()
                )
                if exists:
                    seen_in_file.add(dedup_key)
                    continue

                db.add(
                    TermConflict(
                        term_id=term.id,
                        standard_no_1=std1,
                        standard_no_2=std2,
                        pair_key=pair_key,
                        conflict_type=conflict_type,
                        conflict_desc=conflict_desc or "未提供描述",
                        source_file=csv_path.name,
                        batch_id=batch.id,
                    )
                )
                seen_in_file.add(dedup_key)
                success_rows += 1

                if total_rows % 500 == 0:
                    db.flush()

        batch.total_rows = total_rows
        batch.success_rows = success_rows
        batch.failed_rows = failed_rows
        batch.status = "completed" if failed_rows == 0 else "partial_success"
        batch.error_log = "\n".join(failed_examples) if failed_examples else None

        if dry_run:
            db.rollback()
            print("DRY RUN 完成，未写入数据库。")
        else:
            db.commit()

        print("=" * 60)
        print("术语冲突导入完成")
        print("=" * 60)
        print(f"文件: {csv_path}")
        print(f"批次 ID: {batch.id}")
        print(f"总行数: {total_rows}")
        print(f"成功写入: {success_rows}")
        print(f"失败行数: {failed_rows}")
        print(f"状态: {batch.status}")
        if failed_examples:
            print("失败示例:")
            for item in failed_examples[:5]:
                print(f"  - {item}")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="导入术语冲突 CSV")
    parser.add_argument(
        "--csv",
        default=str(project_root.parent / "术语冲突类型标注.csv"),
        help="CSV 文件路径",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅校验，不写入数据库",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    import_csv(csv_path=csv_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
