#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최소 카드 분석기
- PDF 텍스트 추출(pdftotext)
- OpenAI로 구조화 정보 추출
- 현재 프로젝트 JSON 구조로 저장
"""

import argparse
import base64
import io
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from openai import NotFoundError, OpenAI

# 이미지 PDF 판단 기준: 추출 텍스트가 이 글자 수 미만이면 이미지 PDF로 간주
IMAGE_PDF_CHAR_THRESHOLD = 100
# Vision 처리 시 최대 페이지 수 (비용·속도 절충)
VISION_MAX_PAGES = 15
# Vision 처리 시 이미지 DPI (300은 한글 아웃라인 PDF도 선명하게 인식)
VISION_DPI = 300


BRAND_NORMALIZATION = {
    "amex": "American Express",
    "americanexpress": "American Express",
    "american express": "American Express",
    "master": "Mastercard",
    "mastercard": "Mastercard",
    "visa": "VISA",
    "jcb": "JCB",
    "unionpay": "UnionPay",
    "upi": "UnionPay",
    "국내전용": "국내전용",
}

ALLOWED_BRANDS = {"VISA", "Mastercard", "American Express", "UnionPay", "JCB", "국내전용"}

GRADE_PATTERNS = [
    (r"visa\s+signature|\bsignature\b", "Signature"),
    (r"platinum|플래티넘|플래티늄", "Platinum"),
    (r"\bclassic\b|클래식", "Classic"),
    (r"\bfirst\b|퍼스트", "First"),
    (r"\bmembers\b|멤버스", "Members"),
    (r"\bsoho\b|소호", "SOHO"),
]


def _pdftotext(pdf_path: Path) -> str:
    """pdftotext로 텍스트 레이어 추출. 이미지 PDF면 빈 문자열 반환."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _pdf_to_images_base64(pdf_path: Path, max_pages: int = VISION_MAX_PAGES, dpi: int = VISION_DPI) -> List[str]:
    """PDF를 페이지별 JPEG base64 문자열 리스트로 변환."""
    if not PDF2IMAGE_AVAILABLE:
        raise RuntimeError("pdf2image가 설치되지 않았습니다: pip install pdf2image")
    images = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=max_pages)
    result = []
    for img in images:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        result.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
    return result


def extract_pdf_text(pdf_path: Path) -> str:
    """텍스트 레이어가 있는 PDF에서 텍스트 추출. 이미지 PDF면 빈 문자열 반환."""
    return _pdftotext(pdf_path)


def is_image_pdf(pdf_path: Path) -> bool:
    """추출 텍스트가 너무 짧으면 이미지(아웃라인) PDF로 판단."""
    return len(_pdftotext(pdf_path)) < IMAGE_PDF_CHAR_THRESHOLD


def call_openai_vision(pdf_path: Path, pdf_name: str, bank_name: str) -> Dict[str, Any]:
    """이미지 PDF를 GPT-4o Vision으로 직접 분석해 JSON 반환."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 미설정")

    print(f"    [Vision] 이미지 PDF → GPT-4o Vision 직접 추출: {pdf_path.name}")
    images_b64 = _pdf_to_images_base64(pdf_path)
    if not images_b64:
        raise RuntimeError("PDF 이미지 변환 실패")

    # 이미지들을 content에 추가
    content: List[Any] = []
    for b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
        })

    # 텍스트 기반 build_prompt와 동일한 JSON 스키마를 Vision 프롬프트에 포함
    schema_prompt = build_prompt(pdf_name, bank_name, "")
    # 앞부분의 지시문만 교체 (이미지를 봐라)
    vision_instruction = (
        f"위 이미지들은 한국 신용카드 상품설명서({pdf_name}, 카드사: {bank_name})다.\n"
        "카드 분석 전문가로서 이미지를 꼼꼼히 읽고 아래 스키마에 맞춰 JSON으로만 답하라.\n"
        "모르면 빈 문자열·빈 배열·0·false를 사용하라. 추정 금지.\n\n"
    )
    # schema_prompt에서 "PDF 텍스트:" 이전 부분(지시문 + 스키마)만 추출
    schema_part = schema_prompt
    if "PDF 텍스트:" in schema_part:
        schema_part = schema_part[:schema_part.index("PDF 텍스트:")]

    content.append({"type": "text", "text": vision_instruction + schema_part})

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=16384,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "너는 한국 신용카드 상품설명서 이미지를 구조화하는 데이터 추출기다. 추정하지 말고 근거가 없으면 비워라.",
            },
            {"role": "user", "content": content},
        ],
    )
    result = json.loads(response.choices[0].message.content or "{}")
    print(f"    [Vision] 완료: {len(images_b64)}페이지 처리")
    return result


def normalize_bank(pdf_stem: str) -> str:
    if pdf_stem.startswith("신한카드"):
        return "신한카드"
    if pdf_stem.startswith("롯데카드"):
        return "롯데카드"
    if pdf_stem.startswith("IBK카드"):
        return "IBK기업은행"
    if pdf_stem.startswith("BC카드"):
        return "BC카드"
    if pdf_stem.startswith("하나카드"):
        return "하나카드"
    if pdf_stem.startswith("농협카드"):
        return "NH농협카드"
    if pdf_stem.startswith("현대카드"):
        return "현대카드"
    if pdf_stem.startswith("삼성카드"):
        return "삼성카드"
    if pdf_stem.startswith("우리카드"):
        return "우리카드"
    if pdf_stem.startswith("국민카드") or pdf_stem.startswith("국민카드"):
        return "KB국민카드"
    return "미분류"


def normalize_brand_types(raw_brands: Any) -> list[str]:
    if isinstance(raw_brands, str):
        items = [raw_brands]
    elif isinstance(raw_brands, list):
        items = raw_brands
    else:
        items = []

    normalized = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        compact = text.lower().replace(" ", "")
        mapped = BRAND_NORMALIZATION.get(compact) or BRAND_NORMALIZATION.get(text.lower())
        if mapped in ALLOWED_BRANDS and mapped not in normalized:
            normalized.append(mapped)
    return normalized


def normalize_grade(raw_grade: Any) -> str:
    text = str(raw_grade or "").strip()
    if not text:
        return ""

    lowered = text.lower()
    for pattern, normalized in GRADE_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            return normalized

    return text


def infer_grade(extracted: Dict[str, Any], card_name: str, pdf_text: str) -> str:
    explicit_grade = normalize_grade(extracted.get("grade", ""))
    if explicit_grade:
        return explicit_grade

    haystack = f"{card_name}\n{pdf_text[:20000]}"
    for pattern, normalized in GRADE_PATTERNS:
        if re.search(pattern, haystack, re.IGNORECASE):
            return normalized

    return "미확인"


def build_prompt(pdf_name: str, bank_name: str, text: str) -> str:
    trimmed = text[:30000]
    return f"""
다음은 한국 신용카드 상품 PDF에서 추출한 텍스트다.
카드 정보를 보수적으로 추출해서 JSON으로만 답하라.
모르면 추정하지 말고 빈 문자열, 빈 배열, 0 또는 false를 사용하라.
반드시 아래 키만 사용하라.

입력 메타:
- 파일명: {pdf_name}
- 카드사: {bank_name}

반환 JSON 스키마:
{{
  "card_name": "",
  "name_english": "",
  "bank": "",
  "brand_types": [],
  "grade": "",
  "issued_date": "",
  "usage_scope": "",
  "primary_fee_basic": 0,
  "primary_fee_partnership": 0,
  "primary_fee_total": 0,
  "family_fee_basic": 0,
  "family_fee_partnership": 0,
  "family_fee_total": 0,
  "family_can_issue_unlimited": false,
  "annual_fee_notes": "",
  "brand_fees": [
    {{
      "scope": "국내전용",
      "brand": "국내전용",
      "amount": 0
    }},
    {{
      "scope": "해외겸용",
      "brand": "VISA",
      "amount": 0
    }}
  ],
  "benefit_summary": [],
  "benefit_items": [
    {{
      "category": "",
      "description": "",
      "type": "",
      "rate": "",
      "monthly_min_spending": 0,
      "monthly_cap": 0,
      "monthly_occurrence_limit": 0,
      "annual_occurrence_limit": 0,
      "per_transaction_min": 0,
      "applicable_stores": "",
      "note": ""
    }}
  ],
  "yearly_benefit_tiers": {{
    "is_different_between_years": false,
    "difference_note": "",
    "year1": {{
      "summary": "",
      "monthly_min_spending": 0
    }},
    "year2_and_beyond": {{
      "summary": "",
      "monthly_min_spending": 0,
      "prev_year_spending_tiers": {{
        "has_prev_year_condition": false,
        "description": "",
        "tiers": [
          {{
            "year1_min": 0,
            "year1_max": null,
            "label": "",
            "benefit_summary": "",
            "annual_fee_waiver": false
          }}
        ]
      }}
    }}
  }},
  "spending_thresholds": [
    {{
      "amount": 0,
      "label": "",
      "benefits_unlocked": []
    }}
  ],
  "target_primary": [],
  "target_secondary": [],
  "target_exclusions": [],
  "strengths": [],
  "weaknesses": [],
  "recommended_scenario": "",
  "positioning": "",
  "excluded_items": [],
  "exclusion_notes": "",
  "caution_notes": [],
  "key_sections": {{
    "📋 카드 기본 정보": "",
    "💳 연회비 구조": "",
    "🎁 주요 혜택": "",
    "👥 추천 대상": "",
    "💡 카드의 강점 및 약점": "",
    "⚠️ 주의사항 및 제외사항": ""
  }},
  "annual_fee_confidence": 0.0
}}

===== 필드별 상세 규칙 =====

[기본 필드]
- brand_types: VISA, Mastercard, American Express, UnionPay, JCB, 국내전용 중 하나 이상
- usage_scope: 해외겸용, 국내전용, 미확인 중 하나
- 연회비 금액은 원 단위 정수만 (예: 15000)
- annual_fee_confidence: 연회비 금액 확신도 0.0~1.0 (명시된 경우 0.9, 추정인 경우 0.5 이하)

[brand_fees — 브랜드별 연회비 구조화]
국내전용·해외겸용·브랜드별로 연회비가 다른 카드를 위한 배열. 모든 카드에 필수 기입.
- scope: "국내전용" 또는 "해외겸용"
- brand: 국내전용, VISA, Mastercard, American Express, UnionPay, JCB 중 하나
- amount: 해당 브랜드의 연회비(원, 정수)
예시: 국내전용 10,000원, VISA 15,000원, Mastercard 15,000원인 경우:
  [{{"scope":"국내전용","brand":"국내전용","amount":10000}},
   {{"scope":"해외겸용","brand":"VISA","amount":15000}},
   {{"scope":"해외겸용","brand":"Mastercard","amount":15000}}]
브랜드 구분 없이 단일 연회비인 경우에도 반드시 명시:
  [{{"scope":"해외겸용","brand":"VISA","amount":15000}}]  ← 브랜드가 VISA 하나라면 이렇게
  [{{"scope":"국내전용","brand":"국내전용","amount":15000}}]  ← 국내전용이면 이렇게
primary_fee_total은 brand_fees 중 최솟값(기본 연회비)으로 설정하라.

[benefit_items — 혜택 항목별 구조화 배열]
각 혜택 항목을 별도 객체로 분리해 나열하라.
- category: 주유, 교통, 식음료, 쇼핑, 온라인쇼핑, 여행, 항공마일리지, 포인트적립, 캐시백, 라운지, 통신, 의료, 교육, 주거, 기타 중 하나
- type: 청구할인, 포인트적립, 마일리지적립, 캐시백, 서비스제공, 바우처 중 하나
- rate: 할인율 또는 적립률 문자열 (예: "5%", "1,000원당 1마일", "2,000원 정액할인")
- monthly_min_spending: 이 혜택이 활성화되는 전월실적 최소 금액(원). 없으면 0
- monthly_cap: 월 할인/적립 한도(원). 없으면 0
- monthly_occurrence_limit: 월 최대 이용 횟수. 없으면 0
- annual_occurrence_limit: 연 최대 이용 횟수. 없으면 0
- per_transaction_min: 건당 최소 이용금액(원). 없으면 0
- applicable_stores: 적용 가맹점·업종 (예: "전국 모든 주유소·LPG충전소")
- note: 기타 조건 (예: "전월실적 미충족 시 기본 적립으로 전환")

[yearly_benefit_tiers — 1년차/2년차 혜택 차이]
중요: 1년차는 이전 연도가 없으므로 prev_year_spending_tiers를 가질 수 없음. 오직 2년차 이후만 가능.
- is_different_between_years: 1년차와 2년차 이후 혜택(또는 실적 조건)이 다르면 true
- difference_note: 차이 요약 (예: "1년차 연회비 면제, 2년차부터 전년도 실적 300만원 이상 시 면제")
- year1.summary: 1년차 혜택 또는 조건 요약 (전월실적이나 다른 조건만 포함, 전년도 기반 조건은 불가)
- year1.monthly_min_spending: 1년차 전월실적 기준 (원). 없으면 0
- year2_and_beyond.summary: 2년차 이후 혜택 또는 조건 요약
- year2_and_beyond.monthly_min_spending: 2년차 이후 전월실적 기준 (원). 없으면 0
- year2_and_beyond.prev_year_spending_tiers: 2년차 이후의 "전년도(1년차) 실적 기반" 혜택 차등. 구조는 아래 참고.

[prev_year_spending_tiers — 전년도 실적 기반 혜택 차등 (year2_and_beyond 내부)]
2년차 이후 혜택이나 연회비가 1년차 이용실적에 따라 달라지는 카드에만 사용.
- has_prev_year_condition: 해당 구조가 있으면 true (1년차는 항상 false)
- description: 전체 조건 요약 (예: "2년차 연회비는 1년차 실적 300만원 이상 시 면제")
- tiers[].year1_min: 1년차 실적 구간 하한(원, 포함), tiers[].year1_max: 구간 상한(원, 미포함, null=상한없음)
- tiers[].label: 구간 레이블 (예: "1년차 300만원 미만", "1년차 300만원 이상")
- tiers[].benefit_summary: 이 구간의 1년차 실적에 따라 2년차에 적용되는 혜택 요약
- tiers[].annual_fee_waiver: 2년차 연회비가 이 구간에서 면제되는지 여부

[spending_thresholds — 전월실적 구간별 혜택 정리]
전월실적 금액 구간마다 활성화되는 혜택을 정리.
- amount: 실적 기준 금액(원)
- label: 레이블 (예: "50만원 이상")
- benefits_unlocked: 이 구간에서 활성화되는 혜택 설명 배열

[key_sections — 섹션별 상세 텍스트]
각 섹션의 내용을 원문 기반으로 최대한 상세하게 추출하라. 절대 생략하지 말 것.
- "🎁 주요 혜택": 모든 혜택과 조건(전월실적, 한도, 횟수제한, 적용처)을 구체적 수치와 함께 서술
- "💳 연회비 구조": 연회비 금액, 면제 조건, 해외브랜드별 차이, 1년차/2년차 차이, 전년도 실적 조건
- "⚠️ 주의사항 및 제외사항": 혜택 제외 업종(국세, 지방세, 아파트관리비 등), 적립 불가 항목, 주의 조건
- "👥 추천 대상": 최적/보조/비추천 대상 명시
- "💡 카드의 강점 및 약점": 강점 3~5개, 약점 3~5개 구체적으로 서술

[기타]
- benefit_summary: 핵심 혜택을 한 줄씩 나열 (예: "전국 주유소 5% 청구할인(전월 50만원, 월한도 1만원)")
- strengths/weaknesses: 각각 3~5개 항목, 구체적 수치 포함
- excluded_items: 혜택 제외 업종·항목 배열 (예: ["국세", "지방세", "아파트관리비", "상품권"])
- 카드명이 파일명보다 텍스트에서 더 명확하면 텍스트를 우선

PDF 텍스트:
{trimmed}
""".strip()


def call_openai(prompt: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    requested_model = os.getenv("LLM_MODEL", "gpt-4.1")
    fallback_models = []
    for model in [requested_model, "gpt-4.1", "gpt-4o", "gpt-4.1-mini"]:
        if model and model not in fallback_models:
            fallback_models.append(model)

    client = OpenAI(api_key=api_key)
    last_error: Exception | None = None
    for model in fallback_models:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "너는 한국 신용카드 상품설명서를 구조화하는 데이터 추출기다. 추정하지 말고 근거가 없으면 비워라.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except NotFoundError as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error
    raise RuntimeError("OpenAI call failed without a recoverable model fallback")


def build_current_json(pdf_path: Path, extracted: Dict[str, Any], pdf_text: str) -> Dict[str, Any]:
    bank = extracted.get("bank") or normalize_bank(pdf_path.stem)
    card_name = extracted.get("card_name") or pdf_path.stem
    brand_types = normalize_brand_types(extracted.get("brand_types"))
    grade = infer_grade(extracted, card_name, pdf_text)
    annual_fee_confidence = extracted.get("annual_fee_confidence", 0.6)
    if not isinstance(annual_fee_confidence, (int, float)):
        annual_fee_confidence = 0.6

    primary_total = int(extracted.get("primary_fee_total", 0) or 0)
    primary_basic = int(extracted.get("primary_fee_basic", 0) or 0)
    primary_partnership = int(extracted.get("primary_fee_partnership", 0) or 0)
    family_total = int(extracted.get("family_fee_total", 0) or 0)
    family_basic = int(extracted.get("family_fee_basic", 0) or 0)
    family_partnership = int(extracted.get("family_fee_partnership", 0) or 0)

    # brand_fees: 브랜드별 연회비 구조화
    raw_brand_fees = extracted.get("brand_fees") or []
    brand_fees: List[Dict[str, Any]] = []
    for bf in raw_brand_fees:
        if not isinstance(bf, dict):
            continue
        scope = str(bf.get("scope") or "")
        brand = str(bf.get("brand") or "")
        amount = int(bf.get("amount") or 0)
        if not scope or not brand:
            continue
        brand_fees.append({"scope": scope, "brand": brand, "amount": amount})

    # brand_fees가 있으면 최솟값을 primary_total(기본 연회비)로 사용
    if brand_fees:
        min_fee = min(bf["amount"] for bf in brand_fees)
        max_fee = max(bf["amount"] for bf in brand_fees)
        primary_total = min_fee  # brand_fees가 진실의 원천
        if not primary_basic:
            primary_basic = min_fee
    else:
        min_fee = primary_total
        max_fee = primary_total

    key_sections = extracted.get("key_sections") or {}
    section_map = {
        "📋 카드 기본 정보": str(key_sections.get("📋 카드 기본 정보", "")),
        "💳 연회비 구조": str(key_sections.get("💳 연회비 구조", "")),
        "🎁 주요 혜택": str(key_sections.get("🎁 주요 혜택", "")),
        "👥 추천 대상": str(key_sections.get("👥 추천 대상", "")),
        "💡 카드의 강점 및 약점": str(key_sections.get("💡 카드의 강점 및 약점", "")),
        "⚠️ 주의사항 및 제외사항": str(key_sections.get("⚠️ 주의사항 및 제외사항", "")),
    }

    sections = []
    for idx, (title, content) in enumerate(section_map.items(), start=1):
        keywords = re.findall(r"[0-9a-zA-Z가-힣&]+", content)[:12]
        sections.append(
            {
                "seq": idx,
                "제목": title,
                "내용": content,
                "소제목수": 0,
                "소제목목록": [],
                "키워드": keywords,
                "토큰수": len(keywords),
            }
        )

    benefit_summary = extracted.get("benefit_summary") or []
    benefit_message = " ".join(str(item) for item in benefit_summary if item)

    raw_benefit_items = extracted.get("benefit_items") or []
    benefit_items = []
    for item in raw_benefit_items:
        if not isinstance(item, dict):
            continue
        benefit_items.append({
            "category": str(item.get("category") or "기타"),
            "description": str(item.get("description") or ""),
            "type": str(item.get("type") or ""),
            "rate": str(item.get("rate") or ""),
            "monthly_min_spending": int(item.get("monthly_min_spending") or 0),
            "monthly_cap": int(item.get("monthly_cap") or 0),
            "monthly_occurrence_limit": int(item.get("monthly_occurrence_limit") or 0),
            "annual_occurrence_limit": int(item.get("annual_occurrence_limit") or 0),
            "per_transaction_min": int(item.get("per_transaction_min") or 0),
            "applicable_stores": str(item.get("applicable_stores") or ""),
            "note": str(item.get("note") or ""),
        })

    raw_ybt = extracted.get("yearly_benefit_tiers") or {}

    # year1 구조 (prev_year_spending_tiers는 불가능)
    year1_data = raw_ybt.get("year1") or {}
    year1 = {
        "summary": str(year1_data.get("summary") or ""),
        "monthly_min_spending": int(year1_data.get("monthly_min_spending") or 0),
    }

    # year2_and_beyond 구조 (prev_year_spending_tiers 포함 가능)
    year2_data = raw_ybt.get("year2_and_beyond") or {}

    # year2_and_beyond 내부의 prev_year_spending_tiers 처리
    raw_pyt = year2_data.get("prev_year_spending_tiers") or {}
    raw_tiers = raw_pyt.get("tiers") or []
    prev_year_spending_tiers = {
        "has_prev_year_condition": bool(raw_pyt.get("has_prev_year_condition", False)),
        "description": str(raw_pyt.get("description") or ""),
        "tiers": [
            {
                "year1_min": int(t.get("year1_min") or 0),
                "year1_max": t.get("year1_max"),  # None 허용
                "label": str(t.get("label") or ""),
                "benefit_summary": str(t.get("benefit_summary") or ""),
                "annual_fee_waiver": bool(t.get("annual_fee_waiver", False)),
            }
            for t in raw_tiers if isinstance(t, dict)
        ],
    }

    year2_and_beyond = {
        "summary": str(year2_data.get("summary") or ""),
        "monthly_min_spending": int(year2_data.get("monthly_min_spending") or 0),
        "prev_year_spending_tiers": prev_year_spending_tiers,
    }

    yearly_benefit_tiers = {
        "is_different_between_years": bool(raw_ybt.get("is_different_between_years", False)),
        "difference_note": str(raw_ybt.get("difference_note") or ""),
        "year1": year1,
        "year2_and_beyond": year2_and_beyond,
    }

    raw_st = extracted.get("spending_thresholds") or []
    spending_thresholds = [
        {
            "amount": int(t.get("amount") or 0),
            "label": str(t.get("label") or ""),
            "benefits_unlocked": [str(b) for b in (t.get("benefits_unlocked") or [])],
        }
        for t in raw_st if isinstance(t, dict)
    ]

    benefits = {
        "extraction_notes": {
            "status": "structured" if benefit_items else "partial",
            "message": benefit_message or "혜택 상세는 추가 확인이 필요합니다.",
        },
        "benefit_items": benefit_items,
        "yearly_benefit_tiers": yearly_benefit_tiers,
        "spending_thresholds": spending_thresholds,
    }

    cautions = extracted.get("caution_notes") or []
    exclusion_notes = extracted.get("exclusion_notes") or ""
    note_parts = [str(item) for item in cautions if item]
    if exclusion_notes:
        note_parts.append(str(exclusion_notes))

    usage_scope = extracted.get("usage_scope") or "미확인"
    overseas_brands = [brand for brand in brand_types if brand != "국내전용"]
    combined_section_text = "\n".join(section_map.values())

    return {
        "metadata": {
            "카드명": card_name,
            "카드사": bank,
            "분석일": str(date.today()),
            "스키마버전": "1.0",
            "언어": "Korean",
            "소스형식": "PDF",
            "소스파일": pdf_path.name,
        },
        "card": {
            "name": card_name,
            "bank": bank,
            "id": "",
            "nameEnglish": extracted.get("name_english", ""),
            "brandType": brand_types,
            "grade": grade,
            "issuedDate": extracted.get("issued_date", ""),
            "targetCustomer": "",
            "features": {
                "usage_scope": usage_scope,
            },
        },
        "annual_fee": {
            "primary_card": {
                "basic": primary_basic,
                "partnership": primary_partnership,
                "total": primary_total,
                "amount": primary_total,
                "currency": "KRW",
                "period": "annual",
            },
            "family_card": {
                "basic": family_basic,
                "partnership": family_partnership,
                "total": family_total,
                "amount": family_total,
                "currency": "KRW",
                "period": "annual",
                "can_issue_unlimited": bool(extracted.get("family_can_issue_unlimited", False)),
            },
            "yearly_fee_tiers": {
                "primary_card": {
                    "year1": {
                        "basic": primary_basic,
                        "partnership": primary_partnership,
                        "total": primary_total,
                        "amount": primary_total,
                        "currency": "KRW",
                        "period": "annual",
                    },
                    "year2_and_beyond": {
                        "basic": primary_basic,
                        "partnership": primary_partnership,
                        "total": primary_total,
                        "amount": primary_total,
                        "currency": "KRW",
                        "period": "annual",
                    },
                },
                "family_card": {
                    "year1": {
                        "basic": family_basic,
                        "partnership": family_partnership,
                        "total": family_total,
                        "amount": family_total,
                        "currency": "KRW",
                        "period": "annual",
                    },
                    "year2_and_beyond": {
                        "basic": family_basic,
                        "partnership": family_partnership,
                        "total": family_total,
                        "amount": family_total,
                        "currency": "KRW",
                        "period": "annual",
                    },
                },
                "is_different_between_years": {"primary_card": False, "family_card": False},
                "fee_difference_krw": {"primary_card": 0, "family_card": 0},
            },
            "notes": extracted.get("annual_fee_notes", ""),
            "brand_fees": brand_fees,
            "has_brand_fee_difference": len(set(bf["amount"] for bf in brand_fees)) > 1 if brand_fees else False,
            "fee_range": {"min": min_fee, "max": max_fee} if brand_fees else {"min": primary_total, "max": primary_total},
            "overseas_brand_options": {
                "count": len(overseas_brands),
                "brands": overseas_brands,
            },
        },
        "benefits": benefits,
        "breakeven_analysis": {},
        "target_customers": {
            "primary": extracted.get("target_primary") or [],
            "secondary": extracted.get("target_secondary") or [],
            "exclusions": extracted.get("target_exclusions") or [],
        },
        "characteristics": {
            "strengths": extracted.get("strengths") or [],
            "weaknesses": extracted.get("weaknesses") or [],
            "recommended_scenario": extracted.get("recommended_scenario", ""),
            "positioning": extracted.get("positioning", ""),
        },
        "exclusions": {
            "excluded_items": extracted.get("excluded_items") or [],
            "notes": " ".join(note_parts).strip(),
        },
        "notes": {},
        "섹션": sections,
        "document_understanding": {
            "section_titles": list(section_map.keys()),
            "section_map": section_map,
            "coverage": {
                "기본정보": bool(section_map["📋 카드 기본 정보"]),
                "연회비": bool(section_map["💳 연회비 구조"]),
                "혜택": bool(section_map["🎁 주요 혜택"]),
                "추천대상": bool(section_map["👥 추천 대상"]),
                "강약점": bool(section_map["💡 카드의 강점 및 약점"]),
                "주의사항": bool(section_map["⚠️ 주의사항 및 제외사항"]),
            },
            "signals": {
                "money_value_count": len(re.findall(r"\d{1,3}(?:,\d{3})*원", combined_section_text)),
                "date_value_count": len(re.findall(r"\d{4}-\d{2}-\d{2}", combined_section_text)),
                "bullet_count": sum(text.count("-") for text in section_map.values()),
                "table_line_count": sum(text.count("|") for text in section_map.values()),
            },
        },
        "extraction_provenance": {
            "card_name": {
                "evidence_span": card_name,
                "source_section": "📋 카드 기본 정보",
                "source_page": None,
                "confidence": 0.85,
            },
            "bank_name": {
                "evidence_span": bank,
                "source_section": "📋 카드 기본 정보",
                "source_page": None,
                "confidence": 0.9,
            },
            "brand_types": {
                "evidence_span": ", ".join(brand_types),
                "source_section": "📋 카드 기본 정보",
                "source_page": None,
                "confidence": 0.85 if brand_types else 0.3,
            },
            "annual_fee": {
                "evidence_span": f"{primary_total} KRW",
                "source_section": "💳 연회비 구조",
                "source_page": None,
                "confidence": float(annual_fee_confidence),
            },
            "yearly_spending_conditions": {
                "evidence_span": "",
                "source_section": "🎁 주요 혜택",
                "source_page": None,
                "confidence": 0.3,
            },
        },
        "통계": {
            "총섹션수": len(sections),
            "총라인수": sum(len((section.get("내용") or "").splitlines()) for section in sections),
            "총바이트": len(json.dumps(section_map, ensure_ascii=False).encode("utf-8")),
            "총글자수": len(combined_section_text),
            "총단어수": len(re.findall(r"[0-9a-zA-Z가-힣&]+", combined_section_text)),
            "키워드": re.findall(r"[0-9a-zA-Z가-힣&]+", combined_section_text)[:20],
            "소제목수": 0,
        },
    }


def save_markdown(output_json: Path, data: Dict[str, Any]) -> None:
    project_root = output_json.parent.parent.parent if output_json.parent.name == "cards" else output_json.parent.parent
    md_dir = project_root / "analysis" / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / f"{output_json.stem}_분석.md"
    section_map = data.get("document_understanding", {}).get("section_map", {})
    lines = [f"# {data.get('card', {}).get('name', output_json.stem)}", ""]
    for title, content in section_map.items():
        lines.append(f"## {title}")
        lines.append("")
        lines.append(content or "*(분석 내용 없음)*")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF 카드 분석기")
    parser.add_argument("--pdf", required=True, help="입력 PDF 경로")
    parser.add_argument("--output", required=True, help="출력 JSON 경로")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    if load_dotenv:
        load_dotenv(project_root / ".env", override=False)

    pdf_path = Path(args.pdf).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bank_name = normalize_bank(pdf_path.stem)

    if is_image_pdf(pdf_path):
        # 이미지/아웃라인 PDF → Vision 직접 추출
        extracted = call_openai_vision(pdf_path, pdf_path.stem, bank_name)
        pdf_text = ""  # Vision 경로에서는 텍스트 없음
    else:
        # 텍스트 PDF → 기존 경로
        pdf_text = extract_pdf_text(pdf_path)
        prompt = build_prompt(pdf_path.stem, bank_name, pdf_text)
        extracted = call_openai(prompt)

    data = build_current_json(pdf_path, extracted, pdf_text)

    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    save_markdown(output_path, data)
    print(f"[OK] saved: {output_path}")


if __name__ == "__main__":
    main()