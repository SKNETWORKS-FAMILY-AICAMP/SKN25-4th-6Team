"""
서비스 레이어 — 비즈니스 로직의 단일 진입점
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .cards import load_cards, load_category_rules, load_mbti_profiles
from .llm import llm_answer
from .retrieval import (
    infer_filters_from_question,
    load_rag_settings,
    load_vector_store,
    retrieve_cards_hybrid,
)
from .utils import FEE_BANDS_ORDERED, load_synonyms, safe_get

# 보유 카드 질문 감지 키워드 — 단일 정의 (llm.py·views.py가 이 결과를 받아서 사용)
OWNED_CARD_KEYWORDS = [
    "보유한 카드", "내 카드", "내카드", "보유 카드",
    "갖고 있는 카드", "가진 카드", "내가 가진",
]

MBTI_TYPES = {
    "ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ", "ESTP", "ESFP", "ENFP", "ENTP",
}


@dataclass
class AppState:
    cards: List[Dict[str, Any]]
    vector_store: Optional[Dict[str, Any]]
    rag_settings: Dict[str, Any]
    synonyms: Dict[str, Set[str]]
    banks: List[str]
    all_categories: List[str]
    fee_bands: List[str]


def load_app_state(
    data_dir: Path,
    category_config_path: Path,
    rag_config_path: Path,
    synonyms_config_path: Path,
    rag_artifacts_dir: Path,
    mbti_config_path: Optional[Path] = None,
) -> AppState:
    category_rules = load_category_rules(category_config_path)
    rag_settings = load_rag_settings(rag_config_path)
    synonyms = load_synonyms(str(synonyms_config_path))
    mbti_profiles = load_mbti_profiles(mbti_config_path) if mbti_config_path and mbti_config_path.exists() else {}
    cards = load_cards(data_dir, category_rules, mbti_profiles)
    vector_store = load_vector_store(rag_artifacts_dir)

    banks = sorted({safe_get(c, ["card", "bank"], "미분류") for c in cards})
    all_categories = sorted({
        cat
        for c in cards
        for cat in (safe_get(c, ["_derived", "categories"], []) or [])
        if isinstance(safe_get(c, ["_derived", "categories"], []), list)
    })
    present_bands = {safe_get(c, ["_derived", "fee_band"], "") for c in cards}
    fee_bands = [b for b in reversed(FEE_BANDS_ORDERED) if b in present_bands]

    return AppState(
        cards=cards,
        vector_store=vector_store,
        rag_settings=rag_settings,
        synonyms=synonyms,
        banks=banks,
        all_categories=all_categories,
        fee_bands=fee_bands,
    )


def _detect_mbti(text: str) -> str:
    upper = text.upper()
    for m in MBTI_TYPES:
        if m in upper:
            return m
    return ""


def chat(
    question: str,
    chat_history: List[Dict[str, str]],
    user_filters: Dict[str, List[str]],
    app_state: AppState,
    user_profile: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.2,
    prev_card_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    단일 대화 턴 처리.

    Returns:
        answer: LLM 또는 규칙 기반 답변 텍스트
        retrieved: 검색된 카드 목록 [(score, card), ...]
        filters_applied: 실제 적용된 필터
        inferred_filters: 질문에서 자동 추론된 필터
        is_owned_card_question: 보유 카드 관련 질문 여부
    """
    # 보유 카드 질문 여부 — 이후 모든 분기에서 사용
    is_owned_card_question = any(kw in question for kw in OWNED_CARD_KEYWORDS)

    # 동의어 확장을 포함한 필터 추론
    inferred = infer_filters_from_question(
        question,
        app_state.banks,
        app_state.all_categories,
        app_state.fee_bands,
        synonyms=app_state.synonyms,
    )
    merged_banks = sorted(set(user_filters.get("banks", []) + inferred["banks"]))
    merged_categories = sorted(set(user_filters.get("categories", []) + inferred["categories"]))
    merged_fee_bands = sorted(set(user_filters.get("fee_bands", []) + inferred["fee_bands"]))

    # MBTI 감지: 보유 카드 질문엔 적용하지 않음 (엉뚱한 카드 풀 제한 방지)
    question_mbti = _detect_mbti(question) if not is_owned_card_question else ""
    profile_mbti = (user_profile or {}).get("mbti", "")

    # 검색 풀 결정 — 질문에 MBTI 명시 시 해당 타입 카드만 검색
    search_cards = app_state.cards
    if question_mbti and not prev_card_ids:
        mbti_pool = [
            c for c in app_state.cards
            if question_mbti in (safe_get(c, ["_derived", "mbti_types"], []) or [])
        ]
        if len(mbti_pool) >= 3:
            search_cards = mbti_pool

    # 이전 추천 카드 ID가 있으면 해당 카드를 우선 컨텍스트로 사용
    if prev_card_ids:
        prev_id_set = set(prev_card_ids)
        prev_retrieved = [
            (1.0, card) for card in app_state.cards
            if card.get("_file", "").replace(".json", "") in prev_id_set
        ]
        retrieved = prev_retrieved if prev_retrieved else retrieve_cards_hybrid(
            cards=search_cards,
            query=question,
            top_k=top_k,
            banks=merged_banks,
            categories=merged_categories,
            fee_bands=merged_fee_bands,
            vector_store=app_state.vector_store,
            embedding_model=app_state.rag_settings["embedding_model"],
            similarity_threshold=app_state.rag_settings["similarity_threshold"],
            synonyms=app_state.synonyms,
        )
    else:
        retrieved = retrieve_cards_hybrid(
            cards=search_cards,
            query=question,
            top_k=top_k,
            banks=merged_banks,
            categories=merged_categories,
            fee_bands=merged_fee_bands,
            vector_store=app_state.vector_store,
            embedding_model=app_state.rag_settings["embedding_model"],
            similarity_threshold=app_state.rag_settings["similarity_threshold"],
            synonyms=app_state.synonyms,
        )

    # 프로필 MBTI 부스팅 — 보유 카드 질문·followup·MBTI 명시 질문엔 적용 안 함
    if profile_mbti and not question_mbti and not prev_card_ids and not is_owned_card_question:
        matched = [(s, c) for s, c in retrieved if profile_mbti in (safe_get(c, ["_derived", "mbti_types"], []) or [])]
        unmatched = [(s, c) for s, c in retrieved if profile_mbti not in (safe_get(c, ["_derived", "mbti_types"], []) or [])]
        retrieved = (matched + unmatched)[:top_k]

    # 보유 카드 처리
    owned_cards = (user_profile or {}).get("owned_cards", [])
    if owned_cards:
        owned_card_ids = {c.get("card_id", "") for c in owned_cards}
        owned_retrieved = [
            (1.0, card) for card in app_state.cards
            if card.get("_file", "").replace(".json", "") in owned_card_ids
        ]
        if is_owned_card_question:
            # 보유 카드 질문이면 owned cards만 컨텍스트로 사용
            retrieved = owned_retrieved if owned_retrieved else retrieved
        else:
            # 일반 질문이면 보유 카드를 앞에 추가하되 중복 제거
            already_included = {card.get("_file", "") for _, card in retrieved}
            missing_owned = [
                (score, card) for score, card in owned_retrieved
                if card.get("_file", "") not in already_included
            ]
            retrieved = missing_owned + list(retrieved)

    answer = llm_answer(
        question=question,
        retrieved=retrieved,
        chat_history=chat_history,
        user_profile=user_profile or {},
        model=model,
        temperature=temperature,
        is_owned_card_question=is_owned_card_question,
    )

    return {
        "answer": answer,
        "retrieved": retrieved,
        "filters_applied": {
            "banks": merged_banks,
            "categories": merged_categories,
            "fee_bands": merged_fee_bands,
        },
        "inferred_filters": inferred,
        "is_owned_card_question": is_owned_card_question,
    }
