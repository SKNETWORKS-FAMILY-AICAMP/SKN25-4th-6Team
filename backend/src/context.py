"""
LLM 컨텍스트 빌더
- 검색 결과를 LLM에 전달할 텍스트로 포맷팅
- section_map 전체 + 구조화된 강점/약점/추천대상 포함
"""

from typing import Any, Dict, List, Tuple

from .cards import card_brief
from .utils import safe_get


SECTION_LABEL_MAP = {
    "🎁 주요 혜택": "주요혜택",
    "💡 카드의 강점 및 약점": "강점/약점",
    "👥 추천 대상": "추천대상",
    "⚠️ 주의사항 및 제외사항": "주의사항",
    "📊 손익분기점 분석 (1년 기준)": "손익분기점",
    "💳 연회비 구조": "연회비구조",
}


def build_context(retrieved: List[Tuple[float, Dict[str, Any]]], max_section_chars: int = 1500) -> str:
    """검색된 카드들을 LLM용 컨텍스트 문자열로 변환 (구조화된 혜택 데이터 우선)"""
    lines: List[str] = []
    for score, card in retrieved:
        lines.append(f"[score={score:.2f}] {card_brief(card)}")

        # === 브랜드별 연회비 구조 ===
        brand_fees = safe_get(card, ["annual_fee", "brand_fees"], [])
        if isinstance(brand_fees, list) and len(brand_fees) > 1:
            has_diff = safe_get(card, ["annual_fee", "has_brand_fee_difference"], False)
            if has_diff:
                fee_parts = [f"{bf.get('brand')} {bf.get('amount', 0):,}원" for bf in brand_fees if isinstance(bf, dict)]
                lines.append("[브랜드별연회비] " + " / ".join(fee_parts))

        # === 구조화된 benefit_items (전월실적별 혜택) ===
        benefit_items = safe_get(card, ["benefits", "benefit_items"], [])
        if isinstance(benefit_items, list) and benefit_items:
            lines.append("[혜택항목별 구조]")
            # 전월실적 기준으로 그룹화
            by_threshold: Dict[int, List[str]] = {}
            for item in benefit_items:
                if not isinstance(item, dict):
                    continue
                threshold = item.get("monthly_min_spending", 0)
                cat = item.get("category", "")
                rate = item.get("rate", "")
                cap = item.get("monthly_cap", 0)
                label = f"{cat} {rate}(월한도 {cap:,}원)" if cap else f"{cat} {rate}"
                by_threshold.setdefault(threshold, []).append(label)

            for threshold in sorted(by_threshold.keys()):
                if threshold == 0:
                    lines.append(f"  [조건없음] " + ", ".join(by_threshold[threshold][:3]))
                else:
                    lines.append(f"  [전월 {threshold:,}원 이상] " + ", ".join(by_threshold[threshold][:3]))

        # === 1년차/2년차 혜택 차이 ===
        ybt = safe_get(card, ["benefits", "yearly_benefit_tiers"], {})
        if isinstance(ybt, dict) and ybt.get("is_different_between_years"):
            lines.append("[연차별혜택차이]")
            lines.append(f"  {ybt.get('difference_note', '1년차와 2년차 이후가 다름')}")
            y1 = ybt.get("year1", {})
            y2 = ybt.get("year2_and_beyond", {})
            if y1:
                lines.append(f"  1년차: {y1.get('summary', '')} (조건: {y1.get('fee_waiver_condition', '')})")
            if y2:
                lines.append(f"  2년차+: {y2.get('summary', '')} (조건: {y2.get('fee_waiver_condition', '')})")

        # === 전년도(1년차) 실적 기반 혜택 (2년차 이후에만) ===
        y2 = ybt.get("year2_and_beyond", {}) if isinstance(ybt, dict) else {}
        pyt = y2.get("prev_year_spending_tiers", {}) if isinstance(y2, dict) else {}
        if isinstance(pyt, dict) and pyt.get("has_prev_year_condition"):
            lines.append("[1년차실적기반(2년차이후)]")
            lines.append(f"  {pyt.get('description', '')}")
            for tier in (pyt.get("tiers") or [])[:5]:
                if isinstance(tier, dict):
                    lines.append(f"    {tier.get('label')}: {tier.get('benefit_summary')}")

        # === Spending thresholds 요약 ===
        thresholds = safe_get(card, ["benefits", "spending_thresholds"], [])
        if isinstance(thresholds, list) and thresholds:
            lines.append("[전월실적구간별혜택]")
            for t in thresholds[:5]:
                if isinstance(t, dict):
                    benefits_str = ", ".join(t.get("benefits_unlocked", [])[:2])
                    lines.append(f"  {t.get('label')}: {benefits_str}")

        # === 기존 텍스트 요약 (fallback) ===
        benefit_msg = safe_get(card, ["benefits", "extraction_notes", "message"], "")
        if benefit_msg and benefit_msg != "혜택 상세는 추가 확인이 필요합니다.":
            lines.append(f"[혜택요약] {benefit_msg[:200]}")

        # === 강점/약점 ===
        strengths = safe_get(card, ["characteristics", "strengths"], [])
        weaknesses = safe_get(card, ["characteristics", "weaknesses"], [])
        if isinstance(strengths, list) and strengths:
            lines.append("강점: " + ", ".join(str(s) for s in strengths[:5]))
        if isinstance(weaknesses, list) and weaknesses:
            lines.append("약점: " + ", ".join(str(w) for w in weaknesses[:5]))

        # === 추천대상 ===
        target_primary = safe_get(card, ["target_customers", "primary"], [])
        if isinstance(target_primary, list) and target_primary:
            lines.append("주요대상: " + ", ".join(str(t) for t in target_primary[:5]))

        recommended_scenario = safe_get(card, ["characteristics", "recommended_scenario"], "")
        if recommended_scenario:
            lines.append(f"추천시나리오: {recommended_scenario}")

        # === Section map (크기 더 줄임 — 구조화 필드가 주역) ===
        section_map = safe_get(card, ["document_understanding", "section_map"], {})
        if isinstance(section_map, dict):
            # 주요 4개 섹션만, 각 500자로 제한
            key_sections = ["🎁 주요 혜택", "⚠️ 주의사항 및 제외사항", "💳 연회비 구조", "👥 추천 대상"]
            for section_key in key_sections:
                content = section_map.get(section_key, "").strip()
                if content:
                    truncated = content[:500]
                    label = SECTION_LABEL_MAP.get(section_key, section_key)
                    if len(content) > 500:
                        truncated += "..."
                    lines.append(f"[{label}]\n{truncated}")

        # === 제외항목 ===
        excluded_items = safe_get(card, ["exclusions", "excluded_items"], [])
        if isinstance(excluded_items, list) and excluded_items:
            lines.append("실적/혜택 제외 항목: " + ", ".join([str(x) for x in excluded_items[:12]]))

        evidence = str(card.get("_retrieval_evidence", "")).strip()
        if evidence:
            lines.append("벡터근거: " + evidence[:200])

        lines.append("---")
    return "\n".join(lines)


def build_evidence_footer(retrieved: List[Tuple[float, Dict[str, Any]]]) -> str:
    if not retrieved:
        return "\n\n근거 파일: 없음"
    files: List[str] = []
    for _, card in retrieved[:5]:
        file_name = card.get("_file", "")
        if file_name and file_name not in files:
            files.append(file_name)
    return "\n\n근거 파일: " + ", ".join(files)
