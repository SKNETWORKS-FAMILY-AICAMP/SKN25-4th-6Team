"""
LLM 답변 생성
- OpenAI API 호출 (모델 fallback 포함)
- API 키 없을 시 규칙 기반 fallback
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .cards import annual_fee_display, safe_get, summarize_key_benefits
from .context import build_context, build_evidence_footer

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_FALLBACK_SYSTEM_PROMPT = (
    "당신은 RAIchU(Real AI card hub system for you)의 신용카드 추천 상담사야. "
    "친근하고 캐주얼하게 존댓말(~요, ~해요 체)로 말해줘. "
    "반드시 제공된 카드 컨텍스트 안에서만 답하고, 컨텍스트에 없는 사실은 절대 추가하지 마. "
    "추천할 때는 카드명, 혜택 내용(할인율/적립률/한도), 연회비를 함께 안내해. "
    "이모지를 적절히 활용해도 괜찮아."
)


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
    return "\n".join(lines) + build_evidence_footer(retrieved)


def _build_profile_context(user_profile: Dict[str, Any]) -> str:
    """사용자 프로필을 LLM에 전달할 텍스트로 변환"""
    if not user_profile:
        return ""
    lines = ["[사용자 프로필]"]
    owned = user_profile.get("owned_cards", [])
    if owned:
        card_names = ", ".join(c.get("name", "") for c in owned if c.get("name"))
        lines.append(f"- 보유 카드: {card_names}")
    if user_profile.get("age_group"):
        lines.append(f"- 나이대: {user_profile['age_group']}")
    if user_profile.get("monthly_spend"):
        lines.append(f"- 월 사용액: {user_profile['monthly_spend']}")
    if user_profile.get("annual_fee_range"):
        lines.append(f"- 연회비 허용: {user_profile['annual_fee_range']}")
    lifestyles = user_profile.get("lifestyles", [])
    if lifestyles:
        lines.append(f"- 라이프스타일: {', '.join(lifestyles)}")
    benefits = user_profile.get("preferred_benefits", [])
    if benefits:
        lines.append(f"- 선호 혜택: {', '.join(benefits)}")
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
        system_prompt = _render_system_prompt(user_profile)

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for m in chat_history[-8:]:
            messages.append({"role": m["role"], "content": m["content"]})

        user_content = (
            "아래 카드 컨텍스트를 참고해 질문에 답해줘.\n\n"
            f"[카드 컨텍스트]\n{context}\n\n"
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

        if resp is None:
            if last_error:
                raise last_error
            raise RuntimeError("No available LLM model for chat completion")

        content = resp.choices[0].message.content
        if not content:
            return "답변 생성에 실패했습니다." + build_evidence_footer(retrieved)
        return content + build_evidence_footer(retrieved)
    except Exception:
        return "LLM 호출 중 오류가 발생해 규칙 기반으로 안내합니다.\n\n" + fallback_answer(
            question, retrieved
        )
