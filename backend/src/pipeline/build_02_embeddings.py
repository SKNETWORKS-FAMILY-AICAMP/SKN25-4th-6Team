#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
청크(JSONL) -> 임베딩(JSONL) 생성기

출력 파일:
- vector_store/embeddings.jsonl
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List


def batched(items: List[Any], batch_size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def load_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="카드 청크 임베딩 생성")
    parser.add_argument("--chunks", default="vector_store/chunks.jsonl", help="입력 청크 JSONL")
    parser.add_argument("--out", default="vector_store/embeddings.jsonl", help="출력 임베딩 JSONL")
    parser.add_argument("--model", default="text-embedding-3-small", help="임베딩 모델")
    parser.add_argument("--batch-size", type=int, default=64, help="임베딩 배치 크기")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    chunks_path = (project_root / args.chunks).resolve()
    out_path = (project_root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("[ERROR] OPENAI_API_KEY가 없어 임베딩을 생성할 수 없습니다.")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    rows = load_rows(chunks_path)
    if not rows:
        raise SystemExit(f"[ERROR] 청크가 비어 있습니다: {chunks_path}")

    print(f"[INFO] chunks={len(rows)} model={args.model} batch={args.batch_size}")

    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for chunk_batch in batched(rows, max(1, args.batch_size)):
            inputs = [str(r.get("text", "")) for r in chunk_batch]
            resp = client.embeddings.create(model=args.model, input=inputs)

            vectors = [d.embedding for d in resp.data]
            for row, vec in zip(chunk_batch, vectors):
                out_row = dict(row)
                out_row["embedding_model"] = args.model
                out_row["embedding"] = vec
                f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
                written += 1

    print("=" * 70)
    print(f"[OK] embedded={written}")
    print(f"[OK] saved: {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
