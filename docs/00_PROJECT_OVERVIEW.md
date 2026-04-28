# 프로젝트 전체 흐름

---

## 구조 한눈에 보기

프로젝트는 크게 두 단계로 나뉩니다.

- **1단계 (데이터 준비)**: PDF 원본을 가공해 검색 가능한 형태로 만드는 오프라인 파이프라인
- **2단계 (앱 실행)**: 가공된 데이터를 기반으로 Streamlit 챗봇을 구동하는 런타임

---

## 1단계 — 데이터 파이프라인 (오프라인, 한 번만 실행)

```
data/raw/*.pdf  ← 카드 약관 PDF 원본
       │
       ▼  scripts/card_analyzer.py
       │  PDF 유형 판단 → 텍스트 PDF: GPT-4.1 텍스트 분석
       │                → 이미지 PDF: pdf2image + GPT-4o Vision
       │
data/cards/*.json  ← 카드 1개당 JSON 1개 (현재 105개)
       │
       ▼  scripts/build_chunks.py
       │  카드 JSON → summary / section / exclusions 청크로 분할
       │  (최대 1,200자, 120자 오버랩)
       │
vector_store/chunks.jsonl
       │
       ▼  scripts/build_embeddings.py
       │  청크 텍스트를 OpenAI text-embedding-3-small로 벡터화
       │
vector_store/embeddings.jsonl  (재생성용 원본, 앱 실행엔 미사용)
       │
       ▼  scripts/build_vector_index.py
       │  벡터를 L2 정규화 후 numpy 행렬로 압축 저장
       │
vector_store/vector_index.npz   ← 실제 검색에 쓰는 행렬
vector_store/vector_meta.jsonl  ← 각 벡터가 어느 카드/청크인지 메타
vector_store/index_info.json    ← 차원수 등 인덱스 정보
```

> `scripts/rebuild_rag_index.sh`는 `build_chunks` → `build_embeddings` → `build_vector_index` 세 단계를 한 번에 실행하는 단축 스크립트입니다.

---

## 2단계 — 앱 실행 (app.py + src/)

```
사용자 질문 입력 (Streamlit UI)
       │
       ▼  app.py
       │
       ├─ src/cards.py
       │    data/cards/*.json 전부 로드
       │    config/card_category_rules.json 으로 카테고리 분류
       │    각 카드에 검색용 파생 필드 추가
       │    (_tokens, _benefit_tokens, _derived)
       │
       ├─ src/retrieval.py
       │    config/synonyms.json 으로 쿼리 동의어 확장
       │    config/rag_settings.json 에서 top_k, 유사도 임계값 읽기
       │    vector_store/ 인덱스 로드
       │    키워드 + 벡터 하이브리드 검색 (RRF) → top-K 카드 반환
       │
       ├─ src/context.py
       │    검색된 카드들을 LLM 프롬프트용 텍스트로 포맷팅
       │
       └─ src/llm.py
            OpenAI Chat API 호출 → 상담형 답변 생성
            (API 키 없으면 규칙 기반 fallback)
       │
       ▼
사용자에게 답변 출력
```

---

## src/ 모듈 의존 관계

```
utils.py ◀── cards.py, retrieval.py, context.py, llm.py  (공통 유틸)
cards.py ◀── context.py, llm.py
__init__.py ◀── app.py  (서비스 이름·버전)
```

---

## API 키에 따른 동작 차이

| 상황 | 벡터 검색 | LLM 답변 |
|---|---|---|
| `OPENAI_API_KEY` 있음 | 활성 (풀기능) | GPT 상담형 답변 |
| `OPENAI_API_KEY` 없음 | 비활성 | 규칙 기반 텍스트 |

---

## 파일 존재 여부에 따른 영향

| 없는 파일 | 영향 |
|---|---|
| `data/cards/*.json` | 앱 실행 불가 |
| `vector_store/vector_index.npz` 등 | 벡터 검색 비활성, 키워드 검색만 동작 |
| `vector_store/embeddings.jsonl` | 앱엔 영향 없음, 인덱스 재빌드 시만 필요 |
| `config/*.json` | 기본값으로 fallback (앱은 동작) |
| `src/__init__.py` | `from src.xxx import` 전부 실패 |
| `src/utils.py` | `src/` 내 모든 모듈 import 실패 |

---

## 관련 문서

- [01_CARD_ANALYSIS_SYSTEM.md](01_CARD_ANALYSIS_SYSTEM.md) — 데이터 파이프라인 상세
- [CARD_DATA_GUIDE.md](CARD_DATA_GUIDE.md) — JSON 스키마 및 데이터 현황
- [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) — 스크립트 사용법
- [02_PROMPT_ENGINEERING.md](02_PROMPT_ENGINEERING.md) — LLM 프롬프트 구조
- [04_TROUBLESHOOTING.md](04_TROUBLESHOOTING.md) — 오류 해결
