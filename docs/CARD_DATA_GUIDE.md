# 카드 데이터 전처리 가이드

> 최종 업데이트: 2026-04-24  
> 대상 데이터: `data/cards/` 카드 JSON 105개

---

## 1. 전처리 파이프라인 개요

원본 카드 상품설명서(PDF) → 구조화 JSON → RAG 청크 → 임베딩 → 벡터 인덱스 순서로 처리됩니다.

```
raw/*.pdf
    │
    ▼  scripts/card_analyzer.py  (or batch_extract_all_pdfs.py)
data/cards/*.json          ← 최종 검색·추천에 사용되는 카드 데이터
    │
    ▼  scripts/build_chunks.py
vector_store/chunks.jsonl ← 섹션별 청크 (벡터 검색 단위)
    │
    ▼  scripts/build_embeddings.py
vector_store/embeddings.jsonl
    │
    ▼  scripts/build_vector_index.py
vector_store/vector_index.npz
vector_store/vector_meta.jsonl
vector_store/index_info.json
```

### 1단계: PDF → JSON (`card_analyzer.py`)

PDF 유형에 따라 두 경로로 분기합니다.

| PDF 유형 | 판단 기준 | 처리 방법 |
|---------|---------|---------|
| 텍스트 PDF | 추출 텍스트 100자 이상 | `pdftotext -layout` → GPT-4.1 텍스트 분석 |
| 이미지/아웃라인 PDF | 추출 텍스트 100자 미만 | `pdf2image` → GPT-4o Vision 이미지 분석 |

LLM 프롬프트는 모든 필드에 대해 **"모르면 추정하지 말고 빈값(빈 문자열·빈 배열·0·false)을 사용하라"** 원칙을 적용합니다. 추출이 완료되면 `data/cards/`에 JSON이 저장됩니다.

### 2단계: JSON → 청크 (`build_chunks.py`)

카드 JSON 1개에서 다음 단위로 청크를 생성합니다.

| 청크 유형 | `section_title` | 내용 |
|---------|---------------|------|
| 카드 요약 | `summary` | 카드명·카드사·브랜드·연회비 5줄 요약 |
| 섹션별 | `📋 카드 기본 정보` 등 6개 | section_map의 각 섹션 (최대 1,200자, 120자 오버랩) |
| 제외항목 | `exclusions` | 혜택 제외 항목 목록 |

### 3단계: 청크 → 임베딩 → 벡터 인덱스

`text-embedding-3-small` 모델로 배치 임베딩(기본 64개씩)하고, 정규화된 행렬을 `.npz`로 저장합니다.

---

## 2. JSON 스키마 상세

### 최상위 구조

```
{
  "metadata"              카드 파일 메타정보
  "card"                  카드 기본 식별 정보
  "annual_fee"            연회비 구조
  "benefits"              혜택 정보
  "breakeven_analysis"    손익분기점 (현재 미구현, 빈 객체)
  "target_customers"      추천 대상 고객 (현재 미구현, 빈 배열)
  "characteristics"       강점·약점·포지셔닝
  "exclusions"            혜택 제외 항목
  "섹션"                  섹션별 구조 배열 (document_understanding과 중복)
  "document_understanding" 섹션 맵 및 커버리지 메타
  "extraction_provenance"  추출 근거 및 신뢰도
  "통계"                  파일 크기·단어 수 등 부가 통계
}
```

### `card` — 기본 식별 정보

| 필드 | 설명 | 예시 |
|------|------|------|
| `name` | 카드 정식 명칭 | `"신한카드 Deep Oil"` |
| `bank` | 카드사 (표준화된 값) | `"신한카드"` |
| `brandType` | 국제 브랜드 목록 | `["국내전용", "Mastercard"]` |
| `grade` | 카드 등급 | `"Platinum"`, `"Members"`, `"미확인"` |
| `features.usage_scope` | 사용 범위 | `"해외겸용"`, `"국내전용"` |

**카드사 표준 값 목록** (10개):
`신한카드`, `롯데카드`, `IBK기업은행`, `KB국민카드`, `NH농협카드`, `삼성카드`, `하나카드`, `현대카드`, `BC카드`, `우리카드`

### `annual_fee` — 연회비 구조

```
annual_fee
  ├─ primary_card         본인카드 연회비
  │    ├─ amount          실제 사용되는 연회비 (원, 정수) ← 코드에서 이 필드 우선
  │    ├─ total           amount와 동일 (중복 보관)
  │    ├─ basic           기본 연회비 (카드사에 따라 정확도 낮음)
  │    └─ partnership     제휴 연회비 (카드사에 따라 정확도 낮음)
  ├─ family_card          가족카드 연회비 (구조 동일)
  ├─ brand_fees[]         브랜드별 연회비 배열
  │    ├─ scope           "국내전용" / "해외겸용"
  │    ├─ brand           브랜드명
  │    └─ amount          해당 브랜드의 연회비 (원)
  ├─ has_brand_fee_difference  브랜드별 금액 차이 여부
  └─ fee_range            { min, max } 연회비 범위
```

> **주의**: `basic + partnership ≠ total` 케이스가 42개 존재합니다. 이는 카드사별 연회비 구조 차이를 LLM이 일관되게 매핑하지 못한 결과입니다. 실제 연회비 표시는 항상 `primary_card.amount`를 사용하며, `brand_fees`가 있는 경우 그 최솟값이 `amount`로 설정됩니다.

### `benefits` — 혜택 정보 (가장 중요한 필드)

```
benefits
  ├─ extraction_notes.message   혜택 한 줄 요약 (폴백용)
  ├─ benefit_items[]            혜택 항목별 구조화 배열 ← 검색·LLM에서 핵심 활용
  │    ├─ category              주유 / 교통 / 식음료 / 쇼핑 / 온라인쇼핑 / 여행 / 항공마일리지
  │    │                        / 포인트적립 / 캐시백 / 라운지 / 통신 / 의료 / 교육 / 기타
  │    ├─ description           혜택 설명 (자연어)
  │    ├─ type                  청구할인 / 포인트적립 / 마일리지적립 / 캐시백 / 서비스제공 / 바우처
  │    ├─ rate                  할인/적립률 문자열 ("5%", "1,000원당 1마일")
  │    ├─ monthly_min_spending  전월실적 조건 (원, 0=조건없음)
  │    ├─ monthly_cap           월 한도 (원, 0=무한)
  │    ├─ monthly_occurrence_limit  월 이용 횟수 제한 (0=무제한)
  │    ├─ annual_occurrence_limit   연 이용 횟수 제한 (0=무제한)
  │    ├─ per_transaction_min   건당 최소 금액 (원, 0=없음)
  │    ├─ applicable_stores     적용 가맹점·업종
  │    └─ note                  기타 조건·예외
  ├─ yearly_benefit_tiers       1년차/2년차 혜택 차이
  │    ├─ is_different_between_years
  │    ├─ year1.summary
  │    └─ year2_and_beyond
  │         └─ prev_year_spending_tiers  전년도 실적 기반 혜택 차등
  └─ spending_thresholds[]      전월실적 구간별 혜택 정리
       ├─ amount                실적 기준 (원)
       ├─ label                 레이블 ("30만원 이상")
       └─ benefits_unlocked[]   해당 구간 활성 혜택 설명
```

### `document_understanding` — 섹션 맵

6개 고정 섹션으로 구성됩니다.

| 섹션 키 | 내용 |
|--------|------|
| `📋 카드 기본 정보` | 카드명, 카드사, 브랜드 등 기본 소개 |
| `💳 연회비 구조` | 연회비 금액, 브랜드별 차이, 면제 조건 |
| `🎁 주요 혜택` | 혜택 전체 목록 (전월실적·한도·적용처 포함) |
| `👥 추천 대상` | 최적/보조/비추천 고객 유형 |
| `💡 카드의 강점 및 약점` | 강점 3~5개, 약점 3~5개 |
| `⚠️ 주의사항 및 제외사항` | 제외 업종, 주의 조건 |

`coverage` 객체에 각 섹션의 채움 여부(boolean)가 기록됩니다.

### `extraction_provenance` — 추출 신뢰도

각 주요 필드별로 근거 텍스트(`evidence_span`)와 신뢰도(`confidence` 0.0~1.0)를 보관합니다. `annual_fee.confidence < 0.85`이면 UI에서 "확인 필요" 경고를 표시합니다.

---

## 3. 데이터 현황 (2026-04-24 기준)

### 카드사별 현황

| 카드사 | 카드 수 |
|-------|--------|
| 롯데카드 | 14개 |
| 우리카드 | 12개 |
| IBK기업은행 | 10개 |
| KB국민카드 | 10개 |
| NH농협카드 | 10개 |
| 삼성카드 | 10개 |
| 신한카드 | 10개 |
| 하나카드 | 10개 |
| 현대카드 | 10개 |
| BC카드 | 9개 |
| **합계** | **105개** |

### 연회비 구간 분포

| 구간 | 카드 수 |
|-----|--------|
| FREE (0원) | 3개 |
| ENTRY (1만원 이하) | 37개 |
| STANDARD (1~3만원) | 42개 |
| PREMIUM (3~10만원) | 15개 |
| PRESTIGE (10만원 초과) | 8개 |

### 카드 등급 분포

| 등급 | 카드 수 |
|-----|--------|
| Platinum | 28개 |
| Members | 17개 |
| Signature | 4개 |
| First | 2개 |
| SOHO | 2개 |
| 기타 | 2개 |
| **미확인** | **50개 (48%)** |

### 혜택 데이터 품질

| 항목 | 수치 |
|-----|------|
| `benefit_items` 총 항목 수 | 338개 |
| 카드당 평균 혜택 항목 | 3.2개 |
| 최다 혜택 항목 (1개 카드) | 8개 |
| 브랜드별 연회비 다른 카드 | 51개 (49%) |
| 전월실적 구간 정보 있는 카드 | 64개 (61%) |
| 1년차/2년차 혜택 다른 카드 | 5개 |
| 전년도 실적 기반 혜택 카드 | 4개 |

### 섹션 커버리지

| 섹션 | 채워진 카드 |
|-----|-----------|
| 연회비 구조 | 102/105 (97%) |
| 주요 혜택 | 102/105 (97%) |
| 주의사항 | 91/105 (87%) |
| 강점·약점 | 74/105 (70%) |
| 카드 기본 정보 | 69/105 (66%) |
| 추천 대상 | 29/105 (28%) |

---

## 4. 알려진 데이터 품질 이슈

### 수정 완료

| 이슈 | 대상 | 수정 내용 |
|-----|------|---------|
| 현대카드 `bank` 누락 | 현대카드_D·H·O·S·T·The_Orange·The_Red·블루멤버스·올리브영 (9개) | `"미분류"` → `"현대카드"` |
| BC카드 이름 불일치 | BC카드_바로_KaPick, BC카드_바로_클리어_플러스 (2개) | `"BC"` → `"BC카드"` |
| 케이뱅크 카드사 오분류 | BC카드_케이뱅크_SIMPLE_카드 (1개) | `"케이뱅크"` → `"BC카드"` (케이뱅크는 BC카드 네트워크 발급) |

### 미해결 (기능에 영향 없음)

| 이슈 | 규모 | 영향 |
|-----|------|------|
| `annual_fee.primary_card.basic + partnership ≠ total` | 42개 (40%) | 없음. 코드는 `amount` 필드만 사용 |
| `target_customers.primary` 전체 비어있음 | 105/105 | LLM 컨텍스트에서 추천 대상 정보 미전달 |
| `breakeven_analysis` 전체 비어있음 | 105/105 | 해당 필드를 읽는 코드 없음 |
| `excluded_items` 비어있음 | 21개 (20%) | 해당 카드의 제외항목 검색·표시 불가 |
| `grade` 미확인 | 50개 (48%) | 등급 기반 필터링 불가 |
| `추천 대상` 섹션 비어있음 | 76개 (72%) | 추천 대상 정보 미전달 |

---

## 5. 파일 네이밍 규칙

```
{카드사}_{카드명}.json
```

예시:
- `신한카드_Deep_Oil_20231204.json` — 날짜 접미사는 동명 카드의 버전 구분용
- `BC카드_ON&OFF.json` — 특수문자는 그대로 유지
- `IBK카드_IBK-하이브리드.json` — 카드사 식별자(`IBK카드`)와 `card.bank`(`IBK기업은행`)가 다를 수 있음

`card_analyzer.py`의 `normalize_bank()` 함수가 파일명 접두사를 보고 `card.bank` 표준값을 결정합니다. 파일명 접두사와 표준 카드사명 매핑:

| 파일명 접두사 | `card.bank` 값 |
|------------|--------------|
| `신한카드_` | `신한카드` |
| `IBK카드_` | `IBK기업은행` |
| `국민카드_` | `KB국민카드` |
| `농협카드_` | `NH농협카드` |
| `현대카드_` | `현대카드` |

---

## 6. 새 카드 추가 방법

```bash
# 1. 단일 PDF 처리
python scripts/card_analyzer.py \
  --pdf raw/신한카드_신규카드.pdf \
  --output data/cards/신한카드_신규카드.json

# 2. 전체 배치 처리 (새 PDF만)
python scripts/batch_extract_all_pdfs.py --skip-existing

# 3. RAG 인덱스 재생성
python scripts/build_chunks.py
python scripts/build_embeddings.py
python scripts/build_vector_index.py
```

데이터 추가 후 Streamlit 앱에서 **"데이터 새로고침"** 버튼을 클릭하면 반영됩니다.
