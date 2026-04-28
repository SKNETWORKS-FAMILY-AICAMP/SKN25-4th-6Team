#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카드 JSON -> 청크(JSONL) 생성기

출력 파일:
- vector_store/chunks.jsonl
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"[0-9a-zA-Z가-힣&]+", text))


def safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def split_text_by_size(text: str, max_chars: int, overlap_chars: int) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(0, end - overlap_chars)
    return chunks


def build_chunk_rows(data: Dict[str, Any], file_name: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    card_name = safe_get(data, ["card", "name"], "")
    bank = safe_get(data, ["card", "bank"], "")
    brands = safe_get(data, ["card", "brandType"], [])
    if not isinstance(brands, list):
        brands = []

    annual_fee = safe_get(data, ["annual_fee", "primary_card", "amount"], 0) or safe_get(
        data, ["annual_fee", "primary_card", "total"], 0
    )
    if not isinstance(annual_fee, int):
        annual_fee = 0

    usage_scope = safe_get(data, ["card", "features", "usage_scope"], "")

    # 카드별 핵심 요약 청크(짧은 질의에 대한 매칭 강화)
    summary_lines = [
        f"카드명: {card_name}",
        f"카드사: {bank}",
        f"브랜드: {', '.join(brands) if brands else '-'}",
        f"사용범위: {usage_scope}",
        f"연회비: {annual_fee}",
    ]
    summary_text = "\n".join(summary_lines)
    rows.append(
        {
            "chunk_id": f"{file_name}::summary::0",
            "source_file": file_name,
            "card_name": card_name,
            "bank": bank,
            "section_title": "summary",
            "chunk_index": 0,
            "text": summary_text,
            "token_count": estimate_tokens(summary_text),
            "annual_fee": annual_fee,
            "usage_scope": usage_scope,
            "brands": brands,
        }
    )

    section_map = safe_get(data, ["document_understanding", "section_map"], {})
    if isinstance(section_map, dict):
        for title, content in section_map.items():
            section_text = f"[{title}]\n{str(content)}".strip()
            for i, piece in enumerate(split_text_by_size(section_text, max_chars=1200, overlap_chars=120)):
                rows.append(
                    {
                        "chunk_id": f"{file_name}::section::{title}::{i}",
                        "source_file": file_name,
                        "card_name": card_name,
                        "bank": bank,
                        "section_title": str(title),
                        "chunk_index": i,
                        "text": piece,
                        "token_count": estimate_tokens(piece),
                        "annual_fee": annual_fee,
                        "usage_scope": usage_scope,
                        "brands": brands,
                    }
                )

    excluded_items = safe_get(data, ["exclusions", "excluded_items"], [])
    if isinstance(excluded_items, list) and excluded_items:
        exclusion_text = "제외항목: " + ", ".join([str(x) for x in excluded_items])
        rows.append(
            {
                "chunk_id": f"{file_name}::exclusions::0",
                "source_file": file_name,
                "card_name": card_name,
                "bank": bank,
                "section_title": "exclusions",
                "chunk_index": 0,
                "text": exclusion_text,
                "token_count": estimate_tokens(exclusion_text),
                "annual_fee": annual_fee,
                "usage_scope": usage_scope,
                "brands": brands,
            }
        )

    return rows


def load_cards(data_dir: Path) -> List[Tuple[str, Dict[str, Any]]]:
    cards: List[Tuple[str, Dict[str, Any]]] = []
    for path in sorted(data_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cards.append((path.name, data))
        except Exception as exc:
            print(f"[WARN] JSON 로드 실패: {path.name} ({exc})")
    return cards


def main() -> None:
    parser = argparse.ArgumentParser(description="카드 JSON 청크 생성")
    parser.add_argument("--data-dir", default="data", help="입력 카드 JSON 디렉토리")
    parser.add_argument("--out", default="vector_store/chunks.jsonl", help="출력 청크 JSONL 파일")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    data_dir = (project_root / args.data_dir).resolve()
    out_path = (project_root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cards = load_cards(data_dir)
    all_rows: List[Dict[str, Any]] = []

    for file_name, data in cards:
        all_rows.extend(build_chunk_rows(data, file_name))

    with open(out_path, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("=" * 70)
    print(f"[OK] cards={len(cards)} chunks={len(all_rows)}")
    print(f"[OK] saved: {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
