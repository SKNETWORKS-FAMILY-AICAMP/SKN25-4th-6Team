#!/usr/bin/env bash
set -euo pipefail

# 카드 JSON -> 청크 -> 임베딩 -> 벡터 인덱스 전체 재생성
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "[ERROR] OPENAI_API_KEY가 없습니다. .env 또는 환경변수를 확인하세요."
  exit 1
fi

MODEL="${1:-text-embedding-3-small}"
BATCH_SIZE="${2:-64}"

python3 src/pipeline/build_01_chunks.py --data-dir data/cards --out vector_store/chunks.jsonl
python3 src/pipeline/build_02_embeddings.py \
  --chunks vector_store/chunks.jsonl \
  --out vector_store/embeddings.jsonl \
  --model "$MODEL" \
  --batch-size "$BATCH_SIZE"
python3 src/pipeline/build_03_vector_index.py --embeddings vector_store/embeddings.jsonl --out-dir vector_store --normalize

echo "[OK] RAG 인덱스 재생성 완료"
