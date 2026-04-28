# 프롬프트 엔지니어링 가이드

> 최종 업데이트: 2026-04-24  
> 대상 스크립트: `scripts/card_analyzer.py` → `build_prompt()` 함수

---

## 프롬프트 원칙

- **빈값 우선**: 불확실한 필드는 추정하지 않고 빈값(`""`, `[]`, `0`, `false`)을 사용
- **근거 기반**: PDF 원문에 없는 정보는 절대 추가하지 않음
- **구조 고정**: 출력은 반드시 JSON 스키마를 준수

---

## 텍스트 PDF 프롬프트 구조 (`build_prompt()`)

PDF 텍스트 최대 30,000자를 LLM에 전달하며 다음 섹션으로 구성됩니다.

### 역할 정의
```
당신은 신용카드 상품설명서 분석 전문가다.
규칙:
1. 모르면 추정하지 말고 빈값을 사용
2. PDF 원문에 없는 정보는 추가 금지
3. 출력은 반드시 유효한 JSON
```

### 추출 대상 필드 (주요)

| 필드 | 설명 | 주의사항 |
|------|------|---------|
| `card.bank` | 카드사 | 코드에서 파일명으로 덮어씀 — 틀려도 무방 |
| `annual_fee.primary_card.amount` | 실제 사용 연회비 | `brand_fees` 있으면 최솟값 |
| `annual_fee.brand_fees[]` | 브랜드별 연회비 | 국내/해외 분리 시 배열로 |
| `benefits.benefit_items[]` | 혜택 항목 배열 | 카테고리·비율·조건·한도 포함 |
| `benefits.spending_thresholds[]` | 전월실적 구간별 혜택 | 구간 조건이 있는 카드만 |
| `exclusions.excluded_items[]` | 혜택 제외 항목 | 제외 업종·가맹점 목록 |

### `benefit_items` 항목 구조

```json
{
  "category": "주유 / 교통 / 식음료 / 쇼핑 / 온라인쇼핑 / 여행 / 항공마일리지 / 포인트적립 / 캐시백 / 라운지 / 통신 / 의료 / 교육 / 기타",
  "description": "혜택 설명 (자연어)",
  "type": "청구할인 / 포인트적립 / 마일리지적립 / 캐시백 / 서비스제공 / 바우처",
  "rate": "할인·적립률 문자열 (예: '5%', '1,000원당 1마일')",
  "monthly_min_spending": 300000,
  "monthly_cap": 10000,
  "applicable_stores": "적용 가맹점·업종",
  "note": "기타 조건"
}
```

---

## 이미지 PDF 처리 (`call_openai_vision()`)

`pdftotext` 추출 텍스트가 100자 미만이면 이미지 모드로 전환합니다.

- `pdf2image`로 각 페이지를 JPEG로 변환 (base64 인코딩)
- GPT-4o Vision에 이미지 + 동일 프롬프트 전달
- 타임아웃: 600초 (텍스트 모드 180초보다 3배 길게)

---

## 신뢰도 (`extraction_provenance`)

각 주요 필드별로 근거 텍스트와 신뢰도(`0.0~1.0`)를 기록합니다.

```json
"extraction_provenance": {
  "annual_fee": {
    "evidence_span": "연회비 30,000원",
    "confidence": 0.9
  }
}
```

`annual_fee.confidence < 0.85`이면 앱 UI에서 "⚠️ 낮음" 경고를 표시합니다.

---

## 프롬프트 수정 시 주의사항

- 프롬프트는 `card_analyzer.py`의 `build_prompt()` 함수 내에 있습니다.
- 필드를 추가하면 `build_current_json()`의 조립 로직도 함께 수정해야 합니다.
- 수정 후 반드시 샘플 카드 1~2개로 출력 JSON을 검증하세요.

```bash
# 테스트 실행
python scripts/card_analyzer.py \
  --pdf data/raw/BC/BC카드_ON\&OFF.pdf \
  --output /tmp/test_output.json

# 결과 확인
python3 -c "import json; d=json.load(open('/tmp/test_output.json')); print(len(d['benefits']['benefit_items']), '개 혜택 추출')"
```

---

## 관련 문서

- [01_CARD_ANALYSIS_SYSTEM.md](01_CARD_ANALYSIS_SYSTEM.md) — 전체 파이프라인
- [CARD_DATA_GUIDE.md](CARD_DATA_GUIDE.md) — JSON 스키마 상세
