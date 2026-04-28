"""
LLM 답변 생성
- Jinja2 프롬프트 템플릿 (backend/prompts/) 사용
- OpenAI API 호출 (모델 fallback 포함)
- API 키 없을 시 규칙 기반 fallback
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from jinja2 import Environment, FileSystemLoader

from .cards import annual_fee_display, safe_get, summarize_key_benefits
from .context import build_context

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_jinja_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)

_INTENT_TEMPLATE_MAP = {
    "card_recommend": "instructions/card_recommend.j2",
    "benefit_compare": "instructions/benefit_compare.j2",
    "general": "instructions/general_chat.j2",
}

_COMPARE_KEYWORDS = ["비교", " vs ", "vs.", "차이", "어느게", "어느 게", "둘 중", "더 나은", "더 좋은"]
_RECOMMEND_KEYWORDS = ["추천", "골라", "뭐가 좋", "알려줘", "찾아줘", "뭐 써야", "어떤 카드"]


def _render_template(name: str, variables: dict) -> str:
    return _jinja_env.get_template(name).render(**variables)


def _build_template_vars(user_profile: Dict[str, Any]) -> dict:
    """user_profile dict → Jinja2 템플릿 변수 dict"""
    if not user_profile:
        return {
            "age_group": "미입력",
            "has_car": False,
            "annual_fee_range": "없음 선호",
            "monthly_spend": "미입력",
            "lifestyles": [],
            "preferred_benefits": [],
            "owned_cards": [],
        }
    raw_cards = user_profile.get("owned_cards", [])
    owned_cards = []
    for c in raw_cards:
        owned_cards.append({
            "name": c.get("name", ""),
            "company": c.get("company", c.get("bank", "")),
        })
    return {
        "age_group": user_profile.get("age_group", "미입력"),
        "has_car": bool(user_profile.get("has_car", False)),
        "annual_fee_range": user_profile.get("annual_fee_range", "없음 선호"),
        "monthly_spend": user_profile.get("monthly_spend", "미입력"),
        "lifestyles": user_profile.get("lifestyles", []),
        "preferred_benefits": user_profile.get("preferred_benefits", []),
        "owned_cards": owned_cards,
    }


def _format_retrieved_for_template(retrieved: List[Tuple[float, Dict[str, Any]]]) -> list:
    """retrieved 카드 리스트 → 템플릿용 card dict 리스트"""
    cards = []
    for _, card in retrieved:
        name = safe_get(card, ["card", "name"], "")
        company = safe_get(card, ["card", "bank"], "")
        fee_text, _ = annual_fee_display(card)
        benefit_items = safe_get(card, ["benefits", "benefit_items"], [])

        min_spends = [
            b.get("monthly_min_spending")
            for b in benefit_items
            if b.get("monthly_min_spending")
        ]
        min_spend = f"{min(min_spends):,}원" if min_spends else "없음"

        benefits = []
        for b in benefit_items[:5]:
            category = b.get("category", "기타")
            detail = b.get("rate") or b.get("description") or category
            benefits.append({"category": category, "detail": detail})

        cards.append({
            "name": name,
            "company": company,
            "annual_fee": fee_text,
            "min_spend": min_spend,
            "benefits": benefits,
        })
    return cards


def _classify_intent(question: str) -> str:
    """키워드 기반 의도 분류 (benefit_compare > card_recommend > general)"""
    q = question.lower()
    for kw in _COMPARE_KEYWORDS:
        if kw in q:
            return "benefit_compare"
    for kw in _RECOMMEND_KEYWORDS:
        if kw in q:
            return "card_recommend"
    return "general"


def _render_system_prompt(user_profile: Dict[str, Any]) -> str:
    try:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))
        tmpl = env.get_template("system_prompt.j2")
        owned = user_profile.get("owned_cards", [])
        normalized_owned = [
            c if isinstance(c, dict) else {"name": c, "company": ""}
            for c in owned
        ]
        return tmpl.render(
            age_group=user_profile.get("age_group") or "미확인",
            has_car=bool(user_profile.get("has_car")),
            annual_fee_range=user_profile.get("annual_fee_range") or "미확인",
            lifestyles=user_profile.get("lifestyles") or [],
            monthly_spend=user_profile.get("monthly_spend") or "미확인",
            owned_cards=normalized_owned,
            preferred_benefits=user_profile.get("preferred_benefits") or [],
        )
    except Exception:
        return _FALLBACK_SYSTEM_PROMPT


def fallback_answer(question: str, retrieved: List[Tuple[float, Dict[str, Any]]]) -> str:
    if not retrieved:
        return (
            "질문과 관련된 카드를 찾지 못했습니다.\n\n"
            "입력 팁:\n"
            "1. 카테고리 키워드(예: 쇼핑, 여행, 항공)를 넣어보세요.\n"
            "2. 연회비 조건(예: 3만원 이하)을 함께 적어보세요.\n"
            "3. 카드사(예: 하나카드, BC카드)를 지정하면 더 정확합니다."
        )

    lines = [
        "키를 읽지 못해 규칙 기반 모드로 안내합니다.",
        "",
        f"질문: {question}",
        "",
        "추천 카드 요약:",
    ]

    for idx, (_, card) in enumerate(retrieved[:5], start=1):
        name = safe_get(card, ["card", "name"], "알수없음")
        bank = safe_get(card, ["card", "bank"], "미분류")
        usage_scope = safe_get(card, ["card", "features", "usage_scope"], "미확인")
        fee_text, _ = annual_fee_display(card)
        categories = safe_get(card, ["_derived", "categories"], [])
        brands = safe_get(card, ["card", "brandType"], [])
        benefit_summary = summarize_key_benefits(card)
        lines.append(f"{idx}. {name} ({bank})")
        lines.append(f"   - 핵심 혜택: {benefit_summary}")
        lines.append(
            f"   - 실사용 맥락: 카테고리 {', '.join(categories) if isinstance(categories, list) else '기타'}"
        )
        lines.append(f"   - 사용범위: {usage_scope}")
        lines.append(f"   - 브랜드: {', '.join(brands) if isinstance(brands, list) and brands else '-'}")
        lines.append(f"   - 연회비(후순위 참고): {fee_text}")

    lines.append("")
    lines.append("키가 인식되면 더 자연스러운 상담형 답변으로 자동 전환됩니다.")
    return "\n".join(lines)


def llm_answer(
    question: str,
    retrieved: List[Tuple[float, Dict[str, Any]]],
    chat_history: List[Dict[str, str]],
    user_profile: Dict[str, Any],
    model: str,
    temperature: float,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return fallback_answer(question, retrieved)

    try:
        from openai import NotFoundError, OpenAI

        client = OpenAI(api_key=api_key)
        context = build_context(retrieved)

        template_vars = _build_template_vars(user_profile)
        system_content = _render_template("system_prompt.j2", template_vars)

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
        for m in chat_history[-8:]:
            messages.append({"role": m["role"], "content": m["content"]})

        intent = _classify_intent(question)
        instruction_vars = {
            **template_vars,
            "retrieved_cards": _format_retrieved_for_template(retrieved),
        }
        instruction = _render_template(_INTENT_TEMPLATE_MAP[intent], instruction_vars)

        user_content = (
            f"{instruction}\n\n"
            f"[카드 컨텍스트 (RAG 검색 결과)]\n{context}\n\n"
            f"[질문]\n{question}"
        )
        messages.append({"role": "user", "content": user_content})

        models_to_try: List[str] = []
        for candidate in [model, os.getenv("LLM_MODEL", ""), "gpt-4.1-mini", "gpt-4o-mini"]:
            if candidate and candidate not in models_to_try:
                models_to_try.append(candidate)

        last_error: Exception | None = None
        resp = None
        for candidate in models_to_try:
            try:
                resp = client.chat.completions.create(
                    model=candidate,
                    messages=messages,
                    temperature=temperature,
                )
                break
            except NotFoundError as exc:
                last_error = exc
                continue
git add backend/src/llm.py
        if resp is None:
            if last_error:
                raise last_error
            raise RuntimeError("No available LLM model for chat completion")

        content = resp.choices[0].message.content
        if not content:
            return "답변 생성에 실패했습니다."
        return content
    except Exception:
        return "LLM 호출 중 오류가 발생해 규칙 기반으로 안내합니다.\n\n" + fallback_answer(
            question, retrieved
        )
