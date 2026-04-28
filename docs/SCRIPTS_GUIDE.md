# 스크립트 가이드

> 최종 업데이트: 2026-04-24

---

## 스크립트 목록

### PDF 추출

#### `card_analyzer.py` — 단일 PDF 추출
```bash
python scripts/card_analyzer.py \
  --pdf data/raw/BC/BC카드_신규카드.pdf \
  --output data/cards/BC카드_신규카드.json
```

#### `batch_extract_all_pdfs.py` — 배치 추출
```bash
# 미처리 PDF만 추출
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --skip-existing

# 강제 재추출 (이미 있는 것도 덮어씀)
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --force

# 이미지 PDF만 처리 (Vision 모드 강제)
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --image-only

# 추출 후 RAG 인덱스 자동 재구축
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --skip-existing \
  --rebuild-index

# 테스트용 (n개만)
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --limit 3
```

---

### RAG 인덱스 구축

#### `rebuild_rag_index.sh` — 전체 재구축 (권장)
```bash
bash scripts/rebuild_rag_index.sh
```
내부적으로 `build_chunks.py` → `build_embeddings.py` → `build_vector_index.py` 순서로 실행합니다.

#### 개별 실행 (단계별 디버깅용)
```bash
python scripts/build_chunks.py \
  --data-dir data/cards \
  --out vector_store/chunks.jsonl

python scripts/build_embeddings.py \
  --chunks vector_store/chunks.jsonl \
  --out vector_store/embeddings.jsonl \
  --model text-embedding-3-small \
  --batch-size 64

python scripts/build_vector_index.py \
  --embeddings vector_store/embeddings.jsonl \
  --out-dir vector_store \
  --normalize
```

---

## 일반 작업 흐름

### 새 카드 추가
```bash
# 1. PDF 배치
cp 신규카드.pdf data/raw/BC/BC카드_신규카드.pdf

# 2. 추출 + 인덱스 재구축
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --skip-existing \
  --rebuild-index

# 3. 앱에서 "데이터 새로고침" 클릭
```

### 인덱스만 재구축 (카드 데이터 수정 후)
```bash
bash scripts/rebuild_rag_index.sh
```

---

## 환경변수 (`.env`)

```
OPENAI_API_KEY=sk-proj-...
LLM_MODEL=gpt-4.1-mini
LLM_TEMPERATURE=0.2
```

---

## 관련 문서

- [01_CARD_ANALYSIS_SYSTEM.md](01_CARD_ANALYSIS_SYSTEM.md) — 파이프라인 개요
- [04_TROUBLESHOOTING.md](04_TROUBLESHOOTING.md) — 오류 해결
