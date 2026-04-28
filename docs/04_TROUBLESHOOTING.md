# 트러블슈팅 가이드

> 최종 업데이트: 2026-04-24

---

## PDF 추출 오류

### PDF 파일을 찾을 수 없음

```
FileNotFoundError: data/raw/BC/BC카드_신규카드.pdf
```

```bash
# PDF 위치 확인
find data/raw -name "*.pdf" | grep -i "카드명"

# 카드사 폴더 확인
ls data/raw/
```

### 텍스트 추출량 부족 (자동 이미지 모드 전환)

`pdftotext` 추출 결과가 100자 미만이면 자동으로 GPT-4o Vision 모드로 전환됩니다. 별도 조치 불필요.

Vision 모드는 타임아웃이 600초로 길기 때문에 정상적으로 오래 걸릴 수 있습니다.

---

## OpenAI API 오류

```
AuthenticationError: Invalid API key
RateLimitError: Rate limit exceeded
```

```bash
# API 키 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env | grep OPENAI_API_KEY

# 재설정
export OPENAI_API_KEY="sk-..."
```

Rate limit 오류는 잠시 후 재실행하거나 `batch_extract_all_pdfs.py`를 사용하면 자동 재시도합니다.

---

## JSON 품질 문제

### card.bank가 "미분류"로 저장됨

LLM이 카드사를 잘못 추출한 경우입니다. `normalize_bank()`가 파일명 접두사로 자동 보정하지만, LLM이 비어있지 않은 잘못된 값을 반환하면 덮어쓰지 못합니다.

```python
# 직접 수정
import json
path = "data/cards/카드명.json"
with open(path) as f:
    d = json.load(f)
d["card"]["bank"] = "BC카드"
d["metadata"]["카드사"] = "BC카드"
with open(path, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
```

### benefit_items가 비어있음

PDF에서 혜택 텍스트가 잘 추출되지 않았거나 이미지 PDF를 텍스트로 처리한 경우입니다.

```bash
# 강제로 이미지 모드로 재추출
python scripts/batch_extract_all_pdfs.py \
  --raw-dir data/raw \
  --data-dir data/cards \
  --image-only \
  --force \
  --limit 1
```

또는 직접 재실행:
```bash
python scripts/card_analyzer.py \
  --pdf data/raw/카드사/카드명.pdf \
  --output data/cards/카드명.json
```

### annual_fee 신뢰도 낮음 (UI ⚠️ 표시)

`extraction_provenance.annual_fee.confidence < 0.85`인 경우입니다. PDF에서 연회비를 직접 확인하여 수동으로 수정합니다.

---

## RAG 인덱스 문제

### 벡터 검색이 동작하지 않음

```
벡터 인덱스 없음: 키워드 검색으로 동작
```

```bash
# 인덱스 재구축
bash scripts/rebuild_rag_index.sh

# 인덱스 파일 확인
ls vector_store/
# vector_index.npz, vector_meta.jsonl, embeddings.jsonl, chunks.jsonl 있어야 함
```

### 새 카드가 검색에 나오지 않음

카드 JSON을 추가한 후 인덱스를 재구축하지 않은 경우입니다.

```bash
bash scripts/rebuild_rag_index.sh
```

앱에서 **"데이터 새로고침"** 버튼도 함께 클릭하세요.

---

## 앱 실행 오류

### 카드가 0개 로드됨

```bash
# 카드 JSON 존재 확인
ls data/cards/*.json | wc -l

# 앱의 "데이터 경로" 설정 확인
# 기본값: data/cards (절대경로 또는 프로젝트 루트 기준 상대경로)
```

### 카드사 필터가 동작하지 않음 (특정 카드사 카드가 안 나옴)

```python
# bank 필드 일괄 확인
import json, glob
from collections import Counter
banks = Counter()
for p in glob.glob("data/cards/*.json"):
    with open(p) as f:
        d = json.load(f)
    banks[d["card"]["bank"]] += 1
print(banks)
```

`"미분류"`나 잘못된 이름이 있으면 해당 JSON을 직접 수정합니다.

---

## 관련 문서

- [01_CARD_ANALYSIS_SYSTEM.md](01_CARD_ANALYSIS_SYSTEM.md) — 시스템 개요
- [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) — 스크립트 사용법
- [CARD_DATA_GUIDE.md](CARD_DATA_GUIDE.md) — 데이터 품질 이슈 목록
