#!/usr/bin/env python3
"""导入冲突问答 CSV，并映射到术语冲突表。"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, Optional

from sqlalchemy import and_

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import Base, SessionLocal, engine
from models import ConflictDialogue, ConflictDialogueMapping, TermConflict


STD_NO_PATTERN = re.compile(
    r"(?:GB|MH)\s*/\s*T\s*\d+(?:\.\d+)*\s*[-—]\s*\d{4}|"
    r"ISO\s*\d+(?:\.\d+)*\s*[:：]\s*\d{4}|"
    r"(?:GB|MH)\s*T\s*\d+(?:\.\d+)*\s*[-—]\s*\d{4}",
    re.IGNORECASE,
)


def clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_standard_no(value: str) -> str:
    text = clean_text(value).upper()
    text = text.replace("／", "/").replace("：", ":").replace("—", "-")
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s*:\s*", ":", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("GBT", "GB/T").replace("MHT", "MH/T")
    return text


def normalize_headers(row: Dict[str, str]) -> Dict[str, str]:
    fixed: Dict[str, str] = {}
    for key, value in row.items():
        k = key.lstrip("\ufeff").strip() if isinstance(key, str) else str(key)
        fixed[k] = value
    return fixed


def extract_standard_nos(texts: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for text in texts:
        for hit in STD_NO_PATTERN.findall(text or ""):
            result.add(normalize_standard_no(hit))
    return result


def extract_standard_core(value: str) -> Optional[str]:
    text = normalize_standard_no(value)
    match = re.search(r"(\d+(?:\.\d+)*-\d{4}|\d+(?:\.\d+)*:\d{4})", text)
    if match:
        return match.group(1)
    return None


def normalize_title(value: str) -> str:
    text = clean_text(value)
    text = text.replace("《", "").replace("》", "")
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("／", "/").replace("—", "-").replace("－", "-")
    text = text.replace("：", ":").replace("，", ",").replace("；", ";")
    text = re.sub(r"\.md$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "", text).strip().lower()
    return text


def extract_source_titles(texts: Iterable[str]) -> set[str]:
    titles: set[str] = set()
    for text in texts:
        raw = clean_text(text)
        if not raw:
            continue

        in_brackets = re.findall(r"《([^》]+)》", raw)
        for item in in_brackets:
            normalized = normalize_title(item)
            if normalized:
                titles.add(normalized)

        for piece in re.split(r"[,，;；]+", raw):
            normalized = normalize_title(piece)
            if len(normalized) >= 4:
                titles.add(normalized)
    return titles


def guess_conflict_type_hint(value: str) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    if "格式" in text:
        return "格式冲突"
    if "范围" in text:
        return "范围冲突"
    if "时效" in text or "日期" in text or "时间" in text:
        return "时效冲突"
    if "命名" in text or "编码" in text or "标识符" in text or "代码" in text:
        return "命名冲突"
    if "逻辑" in text:
        return "逻辑冲突"
    if "数值" in text:
        return "数值冲突"
    if "领域" in text or "设施" in text:
        return "领域冲突"
    if "标准" in text or "依据" in text:
        return "引用冲突"
    if "层级" in text:
        return "层级冲突"
    return None


def import_dialogues(
    csv_path: Path,
    dry_run: bool = False,
    remap: bool = True,
) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        total_rows = 0
        inserted_rows = 0
        updated_rows = 0
        failed_rows = 0

        # original_conflict_id -> 聚合信息，用于后续映射
        groups: dict[str, dict[str, object]] = defaultdict(
            lambda: {"conflict_type": "", "texts": [], "dialogue_db_ids": []}
        )

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for raw_row in reader:
                total_rows += 1
                row = normalize_headers(raw_row)

                dialogue_id = clean_text(row.get("dialogue_id"))
                original_conflict_id = clean_text(row.get("original_conflict_id"))
                question = clean_text(row.get("question"))
                answer = clean_text(row.get("answer"))
                conflict_type = clean_text(row.get("conflict_type"))

                if not dialogue_id or not original_conflict_id or not question or not answer:
                    failed_rows += 1
                    continue

                answer_clean = clean_text(row.get("answer_clean"))
                source_document = clean_text(row.get("source_document"))
                source_paragraph = clean_text(row.get("source_paragraph"))
                dialogue_type = clean_text(row.get("type")) or "unknown"
                style = clean_text(row.get("style")) or "unknown"
                cluster = clean_text(row.get("cluster")) or "unknown"
                if not conflict_type:
                    conflict_type = "未分类"

                existing = db.query(ConflictDialogue).filter(
                    ConflictDialogue.dialogue_id == dialogue_id
                ).first()

                if existing is None:
                    existing = ConflictDialogue(
                        dialogue_id=dialogue_id,
                        original_conflict_id=original_conflict_id,
                        question=question,
                        answer=answer,
                        answer_clean=answer_clean or None,
                        source_document=source_document,
                        source_paragraph=source_paragraph,
                        dialogue_type=dialogue_type,
                        style=style,
                        cluster=cluster,
                        conflict_type=conflict_type,
                        source_file=csv_path.name,
                    )
                    db.add(existing)
                    db.flush()
                    inserted_rows += 1
                else:
                    existing.original_conflict_id = original_conflict_id
                    existing.question = question
                    existing.answer = answer
                    existing.answer_clean = answer_clean or None
                    existing.source_document = source_document
                    existing.source_paragraph = source_paragraph
                    existing.dialogue_type = dialogue_type
                    existing.style = style
                    existing.cluster = cluster
                    existing.conflict_type = conflict_type
                    existing.source_file = csv_path.name
                    db.add(existing)
                    db.flush()
                    updated_rows += 1

                group = groups[original_conflict_id]
                if not group["conflict_type"]:
                    group["conflict_type"] = conflict_type
                group["texts"].extend([source_document, source_paragraph, question, answer])
                group["dialogue_db_ids"].append(existing.id)

                if total_rows % 500 == 0:
                    db.flush()

        mapping_inserted = 0
        mapping_deleted = 0
        mapped_conflicts = 0
        all_term_conflicts = db.query(TermConflict).all()
        term_conflict_by_core: dict[str, list[TermConflict]] = defaultdict(list)
        term_conflict_by_title: dict[str, list[TermConflict]] = defaultdict(list)
        term_conflict_by_title_pair: dict[tuple[str, str], list[TermConflict]] = defaultdict(list)
        term_conflict_titles: dict[int, tuple[str, str]] = {}
        for item in all_term_conflicts:
            left_title = normalize_title(item.standard_no_1)
            right_title = normalize_title(item.standard_no_2)
            term_conflict_titles[item.id] = (left_title, right_title)

            if left_title:
                term_conflict_by_title[left_title].append(item)
            if right_title:
                term_conflict_by_title[right_title].append(item)
            if left_title and right_title:
                pair_key = tuple(sorted((left_title, right_title)))
                term_conflict_by_title_pair[pair_key].append(item)

            for std in (item.standard_no_1, item.standard_no_2):
                core = extract_standard_core(std)
                if core:
                    term_conflict_by_core[core].append(item)

        for original_conflict_id, payload in groups.items():
            dialogue_db_ids = payload["dialogue_db_ids"]
            if not isinstance(dialogue_db_ids, list) or not dialogue_db_ids:
                continue

            if remap:
                deleted = db.query(ConflictDialogueMapping).filter(
                    ConflictDialogueMapping.original_conflict_id == original_conflict_id
                ).delete(synchronize_session=False)
                mapping_deleted += int(deleted or 0)

            conflict_type = clean_text(str(payload.get("conflict_type", "")))
            texts = payload.get("texts", [])
            if not isinstance(texts, list):
                texts = []
            title_tokens = extract_source_titles(t for t in texts if isinstance(t, str))
            conflict_type_hint = guess_conflict_type_hint(conflict_type)

            standard_nos = extract_standard_nos(t for t in texts if isinstance(t, str))
            cores: set[str] = set()
            for std in standard_nos:
                core = extract_standard_core(std)
                if core:
                    cores.add(core)

            candidate_map: dict[int, TermConflict] = {}
            candidate_reason: dict[int, str] = {}
            for core in cores:
                for candidate in term_conflict_by_core.get(core, []):
                    candidate_map[candidate.id] = candidate
                    candidate_reason[candidate.id] = "standard_core"

            if not candidate_map and len(title_tokens) >= 2:
                for left_title, right_title in combinations(sorted(title_tokens), 2):
                    key = tuple(sorted((left_title, right_title)))
                    for candidate in term_conflict_by_title_pair.get(key, []):
                        candidate_map[candidate.id] = candidate
                        candidate_reason[candidate.id] = "title_pair"

            if not candidate_map and title_tokens:
                for token in title_tokens:
                    for candidate in term_conflict_by_title.get(token, []):
                        candidate_map[candidate.id] = candidate
                        candidate_reason[candidate.id] = "title_single"

            candidates = list(candidate_map.values())
            if not candidates:
                continue

            ranked: list[tuple[float, TermConflict, str]] = []
            for candidate in candidates:
                score = 0.0
                matched_by: list[str] = []
                reason = candidate_reason.get(candidate.id, "rule_based")
                std_hits = 0
                if normalize_standard_no(candidate.standard_no_1) in standard_nos:
                    std_hits += 1
                if normalize_standard_no(candidate.standard_no_2) in standard_nos:
                    std_hits += 1

                if reason == "standard_core":
                    if std_hits == 0:
                        continue
                    score += 0.45 * std_hits
                    matched_by.append("standard_no")
                elif reason == "title_pair":
                    score += 0.82
                    matched_by.append("title_pair")
                elif reason == "title_single":
                    left_title, right_title = term_conflict_titles.get(candidate.id, ("", ""))
                    title_hits = int(left_title in title_tokens) + int(right_title in title_tokens)
                    if title_hits == 0:
                        continue
                    score += 0.55 if title_hits == 1 else 0.70
                    matched_by.append("title_single")

                if conflict_type and candidate.conflict_type == conflict_type:
                    score += 0.20
                    matched_by.append("conflict_type_exact")
                elif conflict_type_hint and candidate.conflict_type == conflict_type_hint:
                    score += 0.15
                    matched_by.append("conflict_type_hint")

                if conflict_type and candidate.conflict_type and conflict_type != candidate.conflict_type:
                    ct_tokens = set(re.findall(r"[\w\u4e00-\u9fff]+", conflict_type))
                    cand_tokens = set(re.findall(r"[\w\u4e00-\u9fff]+", candidate.conflict_type))
                    if ct_tokens and cand_tokens:
                        overlap = len(ct_tokens & cand_tokens) / len(ct_tokens | cand_tokens)
                        score += 0.10 * overlap
                        if overlap > 0:
                            matched_by.append("conflict_type_overlap")

                if score >= 0.45:
                    ranked.append((score, candidate, "+".join(matched_by) or "rule_based"))

            ranked.sort(key=lambda item: item[0], reverse=True)
            top = ranked[:3]
            if not top:
                continue

            mapped_conflicts += 1
            for dialogue_db_id in dialogue_db_ids:
                for score, term_conflict, matched_by in top:
                    exists = db.query(ConflictDialogueMapping.id).filter(
                        and_(
                            ConflictDialogueMapping.dialogue_id == dialogue_db_id,
                            ConflictDialogueMapping.term_conflict_id == term_conflict.id,
                        )
                    ).first()
                    if exists:
                        continue
                    db.add(
                        ConflictDialogueMapping(
                            dialogue_id=dialogue_db_id,
                            original_conflict_id=original_conflict_id,
                            term_conflict_id=term_conflict.id,
                            matched_by=matched_by,
                            confidence=round(score, 4),
                            note=(
                                f"standards={','.join(sorted(standard_nos))};"
                                f"titles={','.join(sorted(title_tokens))}"
                            ),
                        )
                    )
                    mapping_inserted += 1

        if dry_run:
            db.rollback()
            print("DRY RUN 完成，未写入数据库。")
        else:
            db.commit()

        print("=" * 60)
        print("冲突问答导入与映射完成")
        print("=" * 60)
        print(f"文件: {csv_path}")
        print(f"总行数: {total_rows}")
        print(f"新增问答: {inserted_rows}")
        print(f"更新问答: {updated_rows}")
        print(f"失败行数: {failed_rows}")
        print(f"映射删除: {mapping_deleted}")
        print(f"映射新增: {mapping_inserted}")
        print(f"成功映射冲突组数: {mapped_conflicts}/{len(groups)}")
        print("=" * 60)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="导入冲突问答CSV并映射术语冲突")
    parser.add_argument(
        "--csv",
        default=str(project_root.parent.parent / "订单10_10_冲突问答对生成_20251223_V2.0_with_clusters.csv"),
        help="CSV 文件路径",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅校验，不写入数据库")
    parser.add_argument(
        "--no-remap",
        action="store_true",
        help="不删除同 original_conflict_id 的旧映射，采用增量写入",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    import_dialogues(csv_path=csv_path, dry_run=args.dry_run, remap=not args.no_remap)


if __name__ == "__main__":
    main()
