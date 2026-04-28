import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VISION_DIR = PROJECT_ROOT / "data" / "documents" / "vision"
OUTPUT_DIR = PROJECT_ROOT / "data" / "cards"

MODEL = "gpt-5.4-mini-2026-03-17"

client = OpenAI()

SYSTEM_PROMPT = """
당신은 신용카드 상품설명서 텍스트를 분석하여 구조화된 JSON을 생성하는 전문가입니다.

규칙:
1. JSON 스키마의 문자열 값은 "무엇을 추출할지 설명하는 지시문"입니다. 해당 설명에 맞는 내용을 텍스트에서 직접 찾아서 채워 넣으세요.
2. 지시문 자체를 값으로 출력하지 마세요. 반드시 실제 텍스트 내용을 출력하세요.
3. 추론이나 가정 없이 텍스트에 명시된 내용만 사용하세요.
4. 확인되지 않은 항목은 빈 문자열(""), 빈 배열([]), 또는 0으로 처리하세요.
5. JSON만 출력하고 다른 설명은 절대 쓰지 마세요.
"""

USER_PROMPT_TEMPLATE = """
다음은 카드 상품설명서에서 추출한 텍스트입니다.

파일명: {filename}

--- 텍스트 시작 ---
{text}
--- 텍스트 끝 ---

아래 JSON 스키마에 맞게 구조화해서 출력하세요.
JSON만 출력하고 다른 설명은 절대 쓰지 마세요.

{{
  "metadata": {{
    "카드명": "카드 정식 명칭",
    "카드사": "카드사명",
    "분석일": "{today}",
    "스키마버전": "1.0",
    "언어": "Korean",
    "소스형식": "PDF",
    "소스파일": "{filename}"
  }},
  "card": {{
    "name": "카드 정식 명칭",
    "bank": "카드사명",
    "brandType": ["VISA", "Mastercard" 등 브랜드 목록],
    "grade": "일반/골드/플래티넘 등, 확인 불가 시 미확인",
    "features": {{
      "usage_scope": "텍스트에서 확인된 사용범위. 국내전용이면 '국내전용', 해외겸용이면 '해외겸용', 둘 다 있으면 '해외겸용'으로 출력"
    }}
  }},
  "annual_fee": {{
    "primary_card": {{
      "amount": 연회비 숫자(원 단위 정수),
      "total": 연회비 숫자(원 단위 정수)
    }},
    "brand_fees": [
      {{"brand": "브랜드명", "amount": 연회비 정수}}
    ]
  }},
  "benefits": {{
    "benefit_items": [
      {{
        "category": "카테고리(식음료/교통/쇼핑/여행/주유/포인트적립 등)",
        "description": "혜택 설명",
        "type": "캐시백/포인트적립/청구할인/할인 등",
        "rate": "할인율 또는 적립율 (예: 5%, 2000원)",
        "monthly_min_spending": 전월실적 조건 금액(정수, 없으면 0),
        "monthly_cap": 월 최대 혜택 금액(정수, 없으면 0),
        "applicable_stores": "적용 가맹점",
        "note": "주의사항"
      }}
    ],
    "yearly_benefit_tiers": {{
      "is_different_between_years": false,
      "year1": {{
        "summary": "1년차 혜택 요약",
        "monthly_min_spending": 0
      }},
      "year2_and_beyond": {{
        "summary": "2년차 이후 혜택 요약",
        "monthly_min_spending": 0
      }}
    }}
  }},
  "exclusions": {{
    "excluded_items": ["제외 항목 목록"],
    "notes": "기타 제외 관련 안내"
  }},
  "document_understanding": {{
    "section_map": {{
      "📋 카드 기본 정보": "텍스트에서 추출한 카드 기본 정보 실제 내용 (카드명, 카드사, 발급 대상, 유효기간 등)",
      "💳 연회비 구조": "텍스트에서 추출한 연회비 실제 내용 (브랜드별 금액, 가족카드 여부 등)",
      "🎁 주요 혜택": "텍스트에서 추출한 혜택 실제 내용 (적립률, 할인율, 대상 가맹점 등 구체적 수치 포함)",
      "👥 추천 대상": "텍스트에서 추출한 추천 고객 실제 내용",
      "💡 카드의 강점 및 약점": "텍스트에서 추출한 강점과 약점 실제 내용",
      "⚠️ 주의사항 및 제외사항": "텍스트에서 추출한 주의사항 및 제외 항목 실제 내용"
    }}
  }},
  "characteristics": {{
    "strengths": ["강점 목록"],
    "weaknesses": ["약점 목록"],
    "recommended_scenario": "추천 사용 시나리오",
    "positioning": "카드 포지셔닝 한 줄 요약"
  }}
}}
"""


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def structure_card(txt_path: Path) -> dict:
    text = read_txt(txt_path)
    prompt = USER_PROMPT_TEMPLATE.format(
        filename=txt_path.name,
        text=text,
        today=date.today().isoformat(),
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def run_all(skip_existing: bool = True) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    txt_paths = sorted(VISION_DIR.rglob("*.txt"))
    print(f"[INFO] 발견된 txt 파일 : {len(txt_paths)}개")

    success, fail, skipped = 0, 0, 0

    for txt_path in txt_paths:
        out_name = txt_path.stem + ".json"
        out_path = OUTPUT_DIR / out_name

        if skip_existing and out_path.exists():
            print(f"[SKIP] {out_name}")
            skipped += 1
            continue

        print(f"[처리중] {txt_path.relative_to(VISION_DIR)}")
        try:
            data = structure_card(txt_path)
            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"[저장] {out_path.name}")
            success += 1
        except Exception as e:
            print(f"[ERROR] {txt_path.name} : {e}")
            fail += 1

    print("=" * 60)
    print(f"[완료] 성공={success}  실패={fail}  스킵={skipped}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="vision txt → 구조화 JSON 변환")
    parser.add_argument(
        "--no-skip", action="store_true", help="이미 있는 JSON도 덮어쓰기"
    )
    args = parser.parse_args()

    run_all(skip_existing=not args.no_skip)
