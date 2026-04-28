# RAIchU — 신용카드 추천 시스템

신용카드 상품설명서(PDF) 105개를 구조화 JSON으로 변환하고, 하이브리드 검색(벡터 + 키워드)과 LLM을 결합해 맞춤형 카드를 추천하는 대화형 챗봇입니다.

---

## 프로젝트 구조

```
RAIchU/
├── app.py                      # Streamlit 챗봇 앱 (진입점)
├── run_app.sh                  # .env 로드 + 포트 자동 선택 실행 스크립트
├── docker-compose.yml          # Docker 실행 설정
├── requirements.txt            # Python 패키지 목록
│
├── src/                        # 앱 핵심 모듈
│   ├── __init__.py             # 서비스 이름·버전 상수
│   ├── service.py              # 서비스 레이어 (단일 진입점 — Django 전환 시 view가 호출)
│   ├── cards.py                # 카드 로드, 카테고리 분류, 연회비 표시
│   ├── retrieval.py            # 하이브리드 검색 (벡터 + 키워드 RRF)
│   ├── llm.py                  # LLM 답변 생성 (OpenAI)
│   ├── context.py              # LLM 컨텍스트 빌더
│   └── utils.py                # 토크나이저, 동의어, 연회비 구간 (공통 유틸)
│
├── scripts/                    # 데이터 파이프라인 (오프라인)
│   ├── card_analyzer.py        # PDF → JSON 추출 (LLM)
│   ├── batch_extract_all_pdfs.py # 배치 추출
│   ├── build_chunks.py         # JSON → RAG 청크
│   ├── build_embeddings.py     # 청크 → 임베딩
│   ├── build_vector_index.py   # 임베딩 → 벡터 인덱스
│   └── rebuild_rag_index.sh    # 청크~인덱스 한 번에 재구축
│
├── data/
│   ├── cards/                  # 카드 JSON 105개 (검색·추천 데이터)
│   └── raw/                    # 원본 PDF (카드사별 폴더)
│
├── config/
│   ├── rag_settings.json       # 임베딩 모델, 검색 top-K, 유사도 임계값
│   ├── card_category_rules.json # 카테고리 분류 키워드 규칙 (11개)
│   └── synonyms.json           # 검색 동의어 사전
│
├── vector_store/               # RAG 벡터 인덱스 (빌드 산출물)
│   ├── vector_index.npz
│   ├── vector_meta.jsonl
│   ├── embeddings.jsonl
│   └── chunks.jsonl
│
└── docs/                       # 문서
    ├── CARD_DATA_GUIDE.md      # JSON 스키마 및 데이터 현황
    ├── 01_CARD_ANALYSIS_SYSTEM.md
    ├── 02_PROMPT_ENGINEERING.md
    ├── 04_TROUBLESHOOTING.md
    └── SCRIPTS_GUIDE.md
```

---

## 빠른 시작

### 1. 시스템 의존성 설치 (최초 1회)

`pdftotext`와 `pdf2image`가 필요합니다. OS에 맞게 설치하세요.

**macOS**
```bash
brew install poppler
```

**Ubuntu / Debian**
```bash
sudo apt-get install poppler-utils
```

**Windows**

[poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)에서 바이너리를 다운로드한 후, `bin/` 폴더를 시스템 PATH에 추가합니다.

> 앱 실행(조회)만 할 경우 poppler 설치는 불필요합니다. PDF → JSON 변환(`scripts/card_analyzer.py`) 시에만 필요합니다.

### 2. 가상환경 및 패키지 설치

```bash
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```
OPENAI_API_KEY=sk-proj-...
LLM_MODEL=gpt-4.1-mini
LLM_TEMPERATURE=0.2
```

> `OPENAI_API_KEY`는 벡터 검색과 LLM 답변에 필요합니다. 키 없이도 앱은 실행되지만 키워드 검색 + 규칙 기반 답변으로만 동작하며 추천 품질이 크게 낮아집니다.

### 4. 앱 실행

```bash
# macOS / Linux
bash run_app.sh

# 또는 직접 실행 (모든 OS)
streamlit run app.py
```

접속: http://localhost:8501

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 하이브리드 검색 | 벡터 검색 60% + 키워드 검색 40% (RRF 결합) |
| 동의어 확장 | "마일리지" → 스카이패스, 항공 등 자동 확장 |
| 자동 필터 감지 | 질문에서 카드사·카테고리·연회비 구간 자동 추출 |
| LLM 답변 생성 | 검색된 카드 데이터 기반 GPT 상담형 답변 |
| 신뢰도 표시 | 연회비 추출 신뢰도 낮으면 UI에 ⚠️ 경고 |

---

## 데이터 현황 (2026-04-24 기준)

| 항목 | 수치 |
|------|------|
| 총 카드 수 | 105개 |
| 카드사 수 | 10개 |
| 임베딩 모델 | text-embedding-3-small |
| 카테고리 | 11개 (여행, 항공, 쇼핑, 생활, 포인트, 할인, 주유, 비즈니스, 금융, 환경, 프리미엄) |

---

## 새 카드 추가

```bash
# 1. PDF 복사
cp 새카드.pdf data/raw/BC/BC카드_새카드.pdf

# 2. 추출 + 인덱스 재구축
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw --data-dir data/cards \
  --skip-existing --rebuild-index

# 3. 앱에서 "데이터 새로고침" 클릭
```

---

## 관련 문서

- [00_PROJECT_OVERVIEW.md](docs/00_PROJECT_OVERVIEW.md) — 전체 흐름 한눈에 보기
- [CARD_DATA_GUIDE.md](docs/CARD_DATA_GUIDE.md) — JSON 스키마 및 데이터 품질 현황
- [01_CARD_ANALYSIS_SYSTEM.md](docs/01_CARD_ANALYSIS_SYSTEM.md) — 파이프라인 상세
- [SCRIPTS_GUIDE.md](docs/SCRIPTS_GUIDE.md) — 스크립트 사용법
- [04_TROUBLESHOOTING.md](docs/04_TROUBLESHOOTING.md) — 오류 해결
