#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
임베딩(JSONL) -> 벡터 인덱스(NPZ + 메타 JSONL) 생성기

출력 파일:
- vector_store/vector_index.npz
- vector_store/vector_meta.jsonl
- vector_store/index_info.json
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


def load_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def main() -> None:
    parser = argparse.ArgumentParser(description="카드 벡터 인덱스 생성")
    parser.add_argument("--embeddings", default="vector_store/embeddings.jsonl", help="입력 임베딩 JSONL")
    parser.add_argument("--out-dir", default="vector_store", help="출력 디렉토리")
    parser.add_argument("--normalize", action="store_true", help="L2 정규화 적용")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    emb_path = (project_root / args.embeddings).resolve()
    out_dir = (project_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "vector_index.npz"
    meta_path = out_dir / "vector_meta.jsonl"
    info_path = out_dir / "index_info.json"

    rows = load_rows(emb_path)
    if not rows:
        raise SystemExit(f"[ERROR] 임베딩 입력이 비어 있습니다: {emb_path}")

    vectors: List[List[float]] = []
    meta_rows: List[Dict[str, Any]] = []
    for row in rows:
        embedding = row.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            continue
        vectors.append(embedding)
        meta_rows.append(
            {
                "chunk_id": row.get("chunk_id", ""),
                "source_file": row.get("source_file", ""),
                "card_name": row.get("card_name", ""),
                "bank": row.get("bank", ""),
                "section_title": row.get("section_title", ""),
                "chunk_index": row.get("chunk_index", 0),
                "token_count": row.get("token_count", 0),
                "annual_fee": row.get("annual_fee", 0),
                "usage_scope": row.get("usage_scope", ""),
                "brands": row.get("brands", []),
                "text": row.get("text", ""),
            }
        )

    matrix = np.asarray(vectors, dtype=np.float32)
    normalized = bool(args.normalize)
    if normalized:
        matrix = l2_normalize(matrix)

    np.savez(index_path, embeddings=matrix)

    with open(meta_path, "w", encoding="utf-8") as f:
        for row in meta_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    info = {
        "num_vectors": int(matrix.shape[0]),
        "dim": int(matrix.shape[1]) if matrix.ndim == 2 else 0,
        "normalized": normalized,
        "index_file": str(index_path),
        "meta_file": str(meta_path),
    }
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 70)
    print(f"[OK] vectors={info['num_vectors']} dim={info['dim']} normalized={normalized}")
    print(f"[OK] saved: {index_path}")
    print(f"[OK] saved: {meta_path}")
    print(f"[OK] saved: {info_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
