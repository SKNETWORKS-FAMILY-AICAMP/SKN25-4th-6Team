# 카드 분석 시스템 가이드

> 최종 업데이트: 2026-04-24

---

## 파이프라인 개요

```
data/raw/{카드사}/카드명.pdf
        │
        ▼  scripts/card_analyzer.py
data/cards/카드명.json
        │
        ▼  scripts/build_chunks.py
vector_store/chunks.jsonl
        │
        ▼  scripts/build_embeddings.py
vector_store/embeddings.jsonl
        │
        ▼  scripts/build_vector_index.py
vector_store/vector_index.npz
        │
        ▼  app.py (Streamlit)
카드 추천 챗봇
```

---

## 1단계: PDF → JSON (`card_analyzer.py`)

### PDF 유형 판단

| PDF 유형 | 판단 기준 | 처리 방법 |
|---------|---------|---------|
| 텍스트 PDF | `pdftotext -layout` 추출 텍스트 ≥ 100자 | GPT-4.1 텍스트 분석 |
| 이미지 PDF | 추출 텍스트 < 100자 | pdf2image → GPT-4o Vision |

### LLM 모델 우선순위
지정 모델 → `gpt-4.1` → `gpt-4o` → `gpt-4.1-mini` 순으로 폴백

### 카드사 표준화
파일명 접두사로 `card.bank`를 자동 결정합니다 (`normalize_bank()` 함수).

| 파일명 접두사 | card.bank |
|-----------|---------|
| `현대카드_` | 현대카드 |
| `IBK카드_` | IBK기업은행 |
| `국민카드_` | KB국민카드 |
| `농협카드_` | NH농협카드 |
| `BC카드_` | BC카드 |

LLM이 빈값 또는 `"미분류"`를 반환하면 파일명 기반 값으로 대체됩니다.

### 출력물
- `data/cards/카드명.json` — 검색·추천에 사용되는 구조화 데이터

---

## 2단계: JSON → RAG 인덱스

### 청크 구조 (`build_chunks.py`)

카드 JSON 1개에서 다음 청크를 생성합니다.

| 청크 유형 | 내용 |
|---------|------|
| `summary` | 카드명·카드사·브랜드·연회비 5줄 요약 |
| `📋 카드 기본 정보` 등 6개 | section_map 각 섹션 (최대 1,200자, 120자 오버랩) |
| `exclusions` | 혜택 제외 항목 목록 |

### 임베딩 (`build_embeddings.py`)
`text-embedding-3-small` 모델로 배치 임베딩(기본 64개씩)

### 벡터 인덱스 (`build_vector_index.py`)
L2 정규화 후 `.npz`(행렬) + `.jsonl`(메타) 저장

---

## 새 카드 추가 방법

```bash
# 1. PDF를 해당 카드사 폴더에 복사
cp 신규카드.pdf data/raw/BC/BC카드_신규카드.pdf

# 2. 단일 카드 추출
python scripts/card_analyzer.py \
  --pdf data/raw/BC/BC카드_신규카드.pdf \
  --output data/cards/BC카드_신규카드.json

# 3. 전체 미처리 PDF 배치 추출
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --skip-existing

# 4. RAG 인덱스 재구축
bash scripts/rebuild_rag_index.sh

# 5. 앱에서 "데이터 새로고침" 버튼 클릭
```

---

## 관련 문서

- [CARD_DATA_GUIDE.md](CARD_DATA_GUIDE.md) — JSON 스키마 및 데이터 현황
- [02_PROMPT_ENGINEERING.md](02_PROMPT_ENGINEERING.md) — LLM 프롬프트 구조
- [04_TROUBLESHOOTING.md](04_TROUBLESHOOTING.md) — 오류 해결
- [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) — 스크립트 사용법
