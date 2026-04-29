"""
카드 데이터 로딩/가공
- JSON 로드
- 검색용 텍스트/토큰 빌드
- 카테고리 자동 분류
- 연회비 표시용 포맷
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .utils import classify_fee_band, safe_get, tokenize


def resolve_card_data_dir(data_dir: Path) -> Path:
    if data_dir.is_dir() and any(data_dir.glob("*.json")):
        return data_dir
    cards_dir = data_dir / "cards"
    if cards_dir.is_dir() and any(cards_dir.glob("*.json")):
        return cards_dir
    return data_dir


def load_mbti_profiles(config_path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        return raw.get("profiles", {}) if isinstance(raw, dict) else {}
    except Exception:
        return {}


def infer_mbti(card: Dict[str, Any], mbti_profiles: Dict[str, Any]) -> List[str]:
    if not mbti_profiles:
        return []

    from collections import Counter
    cat_counts: Counter = Counter()
    for item in (card.get("benefits", {}).get("benefit_items") or []):
        c = item.get("category", "")
        if c:
            cat_counts[c] += 1

    fee_band = safe_get(card, ["_derived", "fee_band"], "")

    scores: Dict[str, float] = {}
    for mbti, profile in mbti_profiles.items():
        cat_score = sum(cat_counts.get(c, 0) for c in profile.get("categories", []))
        if cat_score == 0:
            continue
        fee_bonus = 1.5 if fee_band in profile.get("fee_bands", []) else 0.0
        scores[mbti] = cat_score + fee_bonus

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [mbti for mbti, _ in ranked[:2] if _ > 0]


def load_category_rules(config_path: Path) -> List[Dict[str, Any]]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        rules = raw.get("rules", []) if isinstance(raw, dict) else []
        normalized: List[Dict[str, Any]] = []
        for r in rules:
            if not isinstance(r, dict):
                continue
            category = r.get("category")
            keywords = r.get("keywords", [])
            if isinstance(category, str) and isinstance(keywords, list):
                normalized.append({"category": category, "keywords": [str(k).lower() for k in keywords]})
        return normalized
    except Exception:
        return []


def build_card_text(data: Dict[str, Any]) -> str:
    """검색 인덱싱용 텍스트 (토큰화 대상)"""
    card = data.get("card", {})
    annual_fee = data.get("annual_fee", {})
    benefits = data.get("benefits", {})
    exclusions = data.get("exclusions", {})
    metadata = data.get("metadata", {})

    chunks: List[str] = []
    chunks.append(str(card.get("name", "")))
    chunks.append(str(card.get("bank", "")))
    brand_type = card.get("brandType", [])
    chunks.append(" ".join(brand_type) if isinstance(brand_type, list) else "")
    chunks.append(str(safe_get(card, ["features", "usage_scope"], "")))

    primary_fee = safe_get(annual_fee, ["primary_card", "amount"], 0) or safe_get(
        annual_fee, ["primary_card", "total"], 0
    )
    chunks.append(f"연회비 {primary_fee}")

    # 브랜드별 연회비
    brand_fees = annual_fee.get("brand_fees", [])
    if isinstance(brand_fees, list):
        for bf in brand_fees:
            if isinstance(bf, dict):
                chunks.append(f"{bf.get('brand','')} 연회비 {bf.get('amount', 0)}")

    yearly_hints = benefits.get("yearly_spending_evaluation_hints", {}) if isinstance(
        benefits.get("yearly_spending_evaluation_hints"), dict
    ) else {}
    rules = yearly_hints.get("rules", []) if isinstance(yearly_hints.get("rules"), list) else []
    for rule in rules:
        chunks.append(str(rule.get("condition_type", "")))
        chunks.append(str(rule.get("reference_period", "")))
        chunks.append(str(rule.get("required_spending_krw", "")))

    excluded_items = exclusions.get("excluded_items", []) if isinstance(
        exclusions.get("excluded_items"), list
    ) else []
    chunks.extend([str(x) for x in excluded_items])

    section_map = safe_get(data, ["document_understanding", "section_map"], {})
    if isinstance(section_map, dict):
        for title, content in section_map.items():
            chunks.append(str(title))
            chunks.append(str(content)[:1500])

    chunks.append(str(metadata.get("소스파일", "")))
    return "\n".join(chunks)


def build_benefit_text(data: Dict[str, Any]) -> str:
    """혜택 관련 토큰만 강조한 텍스트 (랭킹 가중치용)"""
    benefits = data.get("benefits", {}) if isinstance(data.get("benefits", {}), dict) else {}
    chunks: List[str] = []

    # 구조화된 benefit_items 우선 활용
    for item in (benefits.get("benefit_items") or []):
        if not isinstance(item, dict):
            continue
        chunks.append(str(item.get("category", "")))
        chunks.append(str(item.get("description", "")))
        chunks.append(str(item.get("type", "")))
        chunks.append(str(item.get("rate", "")))
        chunks.append(str(item.get("applicable_stores", "")))
        monthly = item.get("monthly_min_spending", 0)
        if monthly:
            chunks.append(f"전월실적 {monthly}원")
        monthly_cap = item.get("monthly_cap", 0)
        if monthly_cap:
            chunks.append(f"월한도 {monthly_cap}원")

    # 전년도(1년차) 실적 조건 (2년차 이후에만)
    ybt = benefits.get("yearly_benefit_tiers") or {}
    y2 = ybt.get("year2_and_beyond", {}) if isinstance(ybt, dict) else {}
    pyt = y2.get("prev_year_spending_tiers", {}) if isinstance(y2, dict) else {}
    if pyt.get("has_prev_year_condition"):
        chunks.append(str(pyt.get("description", "")))
        for tier in (pyt.get("tiers") or []):
            if isinstance(tier, dict):
                chunks.append(str(tier.get("label", "")))
                chunks.append(str(tier.get("benefit_summary", "")))

    # 1년차/2년차 혜택 차이
    ybt = benefits.get("yearly_benefit_tiers") or {}
    if ybt.get("is_different_between_years"):
        chunks.append(str(ybt.get("difference_note", "")))
        chunks.append(str((ybt.get("year1") or {}).get("summary", "")))
        chunks.append(str((ybt.get("year2_and_beyond") or {}).get("summary", "")))

    # 기존 extraction_notes fallback
    msg = safe_get(benefits, ["extraction_notes", "message"], "")
    if msg and msg != "혜택 상세는 추가 확인이 필요합니다.":
        chunks.append(str(msg))

    exclusions = data.get("exclusions", {}) if isinstance(data.get("exclusions", {}), dict) else {}
    if exclusions:
        chunks.append(str(exclusions.get("notes", "")))
        for ex in (exclusions.get("excluded_items") or []):
            chunks.append(str(ex))

    characteristics = data.get("characteristics", {})
    if isinstance(characteristics, dict):
        for key in ["strengths", "weaknesses", "recommended_scenario", "positioning"]:
            v = characteristics.get(key)
            if isinstance(v, list):
                chunks.extend(str(x) for x in v)
            elif v:
                chunks.append(str(v))
    return "\n".join(chunks)


def infer_categories(data: Dict[str, Any], category_rules: List[Dict[str, Any]]) -> List[str]:
    text = build_card_text(data).lower()
    categories: List[str] = []
    for rule in category_rules:
        category = rule.get("category", "")
        keywords = rule.get("keywords", [])
        if category and any(k in text for k in keywords):
            categories.append(category)
    if not categories:
        categories.append("기타")
    return categories


def load_cards(data_dir: Path, category_rules: List[Dict[str, Any]], mbti_profiles: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """data_dir 아래 카드 JSON을 모두 로드하고 검색용 파생 필드를 붙여 반환"""
    cards: List[Dict[str, Any]] = []
    resolved_dir = resolve_card_data_dir(data_dir)
    for file in sorted(resolved_dir.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            data["_file"] = file.name
            data["_search_text"] = build_card_text(data)
            data["_tokens"] = set(tokenize(data["_search_text"]))
            data["_benefit_text"] = build_benefit_text(data)
            data["_benefit_tokens"] = set(tokenize(data["_benefit_text"]))

            annual_fee = safe_get(data, ["annual_fee", "primary_card", "amount"], 0) or safe_get(
                data, ["annual_fee", "primary_card", "total"], 0
            )
            if not isinstance(annual_fee, int):
                annual_fee = 0

            data["_derived"] = {
                "annual_fee": annual_fee,
                "fee_band": classify_fee_band(annual_fee),
                "categories": infer_categories(data, category_rules),
            }
            if mbti_profiles:
                data["_derived"]["mbti_types"] = infer_mbti(data, mbti_profiles)
            cards.append(data)
        except Exception:
            continue
    return cards


def annual_fee_is_uncertain(card: Dict[str, Any], fee: int) -> bool:
    if fee != 0:
        return False
    notes = str(safe_get(card, ["annual_fee", "notes"], ""))
    uncertain_markers = [
        "연회비 청구",
        "연회비 반환",
        "명시되어 있지",
        "정보가 제공되지 않",
        "확인 필요",
        "미확인",
    ]
    # confidence 필드가 없는 경우(None) 1.0으로 간주 — 106개 전 카드가 None이므로 기본값 0.0은 잘못된 판정
    conf = safe_get(card, ["extraction_provenance", "annual_fee", "confidence"], 1.0)
    if conf is None:
        conf = 1.0
    return conf < 0.85 or any(marker in notes for marker in uncertain_markers)


def annual_fee_display(card: Dict[str, Any]) -> Tuple[str, bool]:
    fee = safe_get(card, ["_derived", "annual_fee"], 0)
    fee_band = safe_get(card, ["_derived", "fee_band"], "")
    uncertain = annual_fee_is_uncertain(card, fee)
    if uncertain:
        return "확인 필요(문서 재확인 권장)", True

    brand_fees = safe_get(card, ["annual_fee", "brand_fees"], [])
    has_diff = safe_get(card, ["annual_fee", "has_brand_fee_difference"], False)
    if isinstance(brand_fees, list) and has_diff and len(brand_fees) > 1:
        fee_range = safe_get(card, ["annual_fee", "fee_range"], {})
        min_fee = fee_range.get("min", fee) if isinstance(fee_range, dict) else fee
        max_fee = fee_range.get("max", fee) if isinstance(fee_range, dict) else fee
        brand_parts = [f"{bf.get('brand')} {bf.get('amount', 0):,}원" for bf in brand_fees if isinstance(bf, dict)]
        return " / ".join(brand_parts[:3]), False

    return f"{fee:,}원", False


def summarize_key_benefits(card: Dict[str, Any]) -> str:
    benefits = card.get("benefits", {}) if isinstance(card.get("benefits", {}), dict) else {}
    items = benefits.get("benefit_items") or []

    if items:
        # 구조화 데이터로 요약
        cat_map: Dict[str, List[str]] = {}
        for it in items:
            if not isinstance(it, dict):
                continue
            cat = it.get("category") or "기타"
            rate = it.get("rate") or ""
            desc = it.get("description") or ""
            label = rate or desc[:20]
            if label:
                cat_map.setdefault(cat, []).append(label)
        parts = [f"{cat}({', '.join(rates[:2])})" for cat, rates in list(cat_map.items())[:4]]
        extra = []
        ybt = benefits.get("yearly_benefit_tiers") or {}
        if ybt.get("is_different_between_years"):
            extra.append("연차별혜택상이")
        # prev_year_spending_tiers는 이제 year2_and_beyond 내부
        y2 = ybt.get("year2_and_beyond", {}) if isinstance(ybt, dict) else {}
        pyt = y2.get("prev_year_spending_tiers", {}) if isinstance(y2, dict) else {}
        if pyt.get("has_prev_year_condition"):
            extra.append("1년차실적조건")
        result = ", ".join(parts)
        if extra:
            result += " [" + "/".join(extra) + "]"
        return result or "주요 혜택 정보 확인 필요"

    # 구조화 데이터 없을 때 section_map fallback (이전 로직 제거)
    msg = safe_get(benefits, ["extraction_notes", "message"], "")
    if msg and msg != "혜택 상세는 추가 확인이 필요합니다.":
        return msg[:80]
    return "주요 혜택 정보 확인 필요"


def card_brief(card: Dict[str, Any]) -> str:
    name = safe_get(card, ["card", "name"], "알수없음")
    bank = safe_get(card, ["card", "bank"], "미분류")
    brands = safe_get(card, ["card", "brandType"], [])
    if not isinstance(brands, list):
        brands = []
    usage_scope = safe_get(card, ["card", "features", "usage_scope"], "미확인")
    fee_text, fee_uncertain = annual_fee_display(card)
    categories = safe_get(card, ["_derived", "categories"], [])
    category_text = ", ".join(categories) if isinstance(categories, list) else "기타"
    benefit_summary = summarize_key_benefits(card)
    fee_label = "연회비(확인중)" if fee_uncertain else "연회비"
    return (
        f"{name} | {bank} | 혜택 {benefit_summary} | 카테고리 {category_text} "
        f"| 사용범위 {usage_scope} | 브랜드 {', '.join(brands) if brands else '-'} "
        f"| {fee_label} {fee_text}"
    )
