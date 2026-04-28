#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAIchU (Real AI card hub system for you) — Streamlit 대화형 챗봇
- data/cards/*.json 기반 하이브리드 검색(벡터+키워드)
- LLM(OpenAI) 답변 생성, 키 없으면 규칙 기반 폴백
- 모든 비즈니스 로직은 src/ 아래 모듈에 위임, 이 파일은 UI만 담당
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

from src import __service_description__, __service_name__, __version__
from src.cards import annual_fee_display, resolve_card_data_dir
from src.service import AppState, chat, load_app_state
from src.utils import FEE_BANDS_ORDERED, safe_get


APP_ROOT = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(dotenv_path=APP_ROOT / ".env", override=False)


RECOMMENDED_KEYWORDS = [
    "해외여행자용 카드",
    "쇼핑 할인 많은 카드",
    "주유비 할인 카드",
    "공항 라운지 이용",
    "포인트/마일리지 많이 주는 카드",
    "연회비 싼 카드",
    "가족카드 무료",
]

CHAT_CSS = """
<style>
/* ── 전체 배경 ─────────────────────────────────────── */
.stApp { background-color: #b9cad6 !important; }
section[data-testid="stMain"] { background-color: #b9cad6 !important; }

/* ── 채팅 메시지 공통 ─────────────────────────────── */
[data-testid="stChatMessage"] {
    display: flex !important;
    background: none !important;
    border: none !important;
    padding: 3px 8px !important;
    align-items: flex-start !important;
}

/* ── 사용자 버블 (오른쪽, 카카오 노랑) ────────────── */
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
    flex-direction: row-reverse !important;
}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] {
    background-color: #fee500 !important;
    border-radius: 18px 4px 18px 18px !important;
    padding: 10px 15px !important;
    max-width: 68% !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
    margin-right: 6px !important;
    color: #1a1a1a !important;
}

/* ── 어시스턴트 버블 (왼쪽, 흰색) ────────────────── */
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageContent"] {
    background-color: #ffffff !important;
    border-radius: 4px 18px 18px 18px !important;
    padding: 10px 15px !important;
    max-width: 75% !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
    margin-left: 6px !important;
    color: #1a1a1a !important;
}

/* ── 채팅 입력창 ──────────────────────────────────── */
[data-testid="stChatInput"] textarea {
    border-radius: 22px !important;
    border: 1.5px solid #c8d8e4 !important;
    background: #ffffff !important;
    padding: 10px 18px !important;
    font-size: 14px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #4a90d9 !important;
    box-shadow: 0 0 0 2px rgba(74, 144, 217, 0.2) !important;
}

/* ── Expander (근거 패널) ─────────────────────────── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.55) !important;
    border: none !important;
    border-radius: 12px !important;
    backdrop-filter: blur(6px) !important;
}

/* ── Info 박스 ────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 13px !important;
}

/* ── 사이드바 ─────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #1e2a38 !important;
}
section[data-testid="stSidebar"] * {
    color: #dce8f0 !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 {
    color: #ffffff !important;
}

/* 사이드바 추천 버튼 */
section[data-testid="stSidebar"] .stButton button {
    border-radius: 20px !important;
    background-color: #2c3e50 !important;
    color: #dce8f0 !important;
    border: 1px solid #3d5166 !important;
    font-size: 13px !important;
    padding: 5px 12px !important;
    transition: all 0.18s ease !important;
    text-align: left !important;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background-color: #fee500 !important;
    color: #1a1a1a !important;
    border-color: #fee500 !important;
    transform: translateX(3px) !important;
}

/* 사이드바 divider */
section[data-testid="stSidebar"] hr {
    border-color: #3d5166 !important;
}

/* 사이드바 상태 박스 */
section[data-testid="stSidebar"] [data-testid="stAlert"] {
    font-size: 12px !important;
    padding: 6px 10px !important;
    border-radius: 8px !important;
}

/* metric */
section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
    color: #fee500 !important;
}
</style>
"""


def _init_session(
    data_dir: Path,
    category_config_path: Path,
    rag_config_path: Path,
    synonyms_config_path: Path,
    rag_artifacts_dir: Path,
    reload_clicked: bool,
) -> None:
    if "app_state" not in st.session_state or reload_clicked:
        st.session_state.app_state = load_app_state(
            data_dir=data_dir,
            category_config_path=category_config_path,
            rag_config_path=rag_config_path,
            synonyms_config_path=synonyms_config_path,
            rag_artifacts_dir=rag_artifacts_dir,
        )


def _render_retrieval_debug(retrieved: List[Any]) -> None:
    with st.expander("🔍 검색된 카드 근거", expanded=False):
        if not retrieved:
            st.info("검색 결과가 없습니다.")
            return
        rows = []
        for score, card in retrieved:
            fee_text, fee_uncertain = annual_fee_display(card)
            evidence = str(card.get("_retrieval_evidence", "")).strip()
            brands = safe_get(card, ["card", "brandType"], [])
            row = {
                "점수": round(score, 2),
                "카드명": safe_get(card, ["card", "name"], "알수없음"),
                "카드사": safe_get(card, ["card", "bank"], "미분류"),
                "사용범위": safe_get(card, ["card", "features", "usage_scope"], "미확인"),
                "연회비": fee_text,
                "신뢰도": "⚠️" if fee_uncertain else "✅",
                "카테고리": ", ".join(safe_get(card, ["_derived", "categories"], [])),
                "브랜드": ", ".join(brands) if isinstance(brands, list) else "",
            }
            if evidence:
                row["근거"] = evidence
            rows.append(row)
        st.dataframe(rows, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(
        page_title=f"{__service_name__} 카드 추천",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

    default_data_dir = APP_ROOT / "data" / "cards"
    category_config_path = APP_ROOT / "config" / "card_category_rules.json"
    rag_config_path = APP_ROOT / "config" / "rag_settings.json"
    synonyms_config_path = APP_ROOT / "config" / "synonyms.json"
    rag_artifacts_dir = APP_ROOT / "vector_store"

    # ── 사이드바 ──────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"# ⚡ {__service_name__}")
        st.caption(__service_description__)
        st.divider()

        st.markdown("#### 빠른 검색")

        def on_keyword_click(keyword: str) -> None:
            st.session_state["keyword_query"] = keyword

        for keyword in RECOMMENDED_KEYWORDS:
            st.button(
                keyword,
                key=f"sidebar_keyword_{keyword}",
                use_container_width=True,
                on_click=on_keyword_click,
                args=(keyword,),
            )

        st.divider()
        st.markdown("#### 필터")
        # 카드 데이터 로드 후 채워질 placeholder
        filter_bank_ph = st.empty()
        filter_cat_ph = st.empty()
        filter_fee_ph = st.empty()

        st.divider()
        with st.expander("⚙️ 고급 설정", expanded=False):
            data_dir_text = st.text_input("데이터 경로", value=str(default_data_dir))
            top_k = st.slider("검색 카드 수", min_value=1, max_value=10, value=5)
            model = st.text_input("LLM 모델", value=os.getenv("LLM_MODEL", "gpt-4.1-mini"))
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.2,
                value=float(os.getenv("LLM_TEMPERATURE", "0.2")),
                step=0.1,
            )
            reload_clicked = st.button("🔄 데이터 새로고침")
            st.caption(f"경로: {resolve_card_data_dir(Path(data_dir_text))}")

    # ── 앱 상태 로드 ────────────────────────────────────────
    data_dir = resolve_card_data_dir(Path(data_dir_text))
    _init_session(
        data_dir=data_dir,
        category_config_path=category_config_path,
        rag_config_path=rag_config_path,
        synonyms_config_path=synonyms_config_path,
        rag_artifacts_dir=rag_artifacts_dir,
        reload_clicked=reload_clicked,
    )

    app_state: AppState = st.session_state.app_state

    # 필터 위젯 채우기
    with st.sidebar:
        selected_banks = filter_bank_ph.multiselect("카드사", options=app_state.banks, default=[])
        selected_categories = filter_cat_ph.multiselect("카테고리", options=app_state.all_categories, default=[])
        selected_fee_bands = filter_fee_ph.multiselect("연회비 구간", options=app_state.fee_bands, default=[])

        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("카드", f"{len(app_state.cards)}개")
        col2.metric("카테고리", f"{len(app_state.all_categories)}개")

        if app_state.vector_store:
            st.success("벡터 검색 활성")
        else:
            st.warning("키워드 검색 모드")
        if os.getenv("OPENAI_API_KEY"):
            st.success("LLM 활성")
        else:
            st.warning("규칙 기반 모드")

    user_filters: Dict[str, List[str]] = {
        "banks": selected_banks,
        "categories": selected_categories,
        "fee_bands": selected_fee_bands,
    }

    # ── 채팅 히스토리 초기화 ────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    f"안녕하세요! ⚡ **{__service_name__}**입니다.\n\n"
                    "카드명, 카드사, 연회비, 전월실적, 혜택 등 원하시는 조건을 자유롭게 질문해 주세요."
                ),
            }
        ]

    # ── 채팅 히스토리 렌더링 ────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🙋" if msg["role"] == "user" else "⚡"):
            st.markdown(msg["content"])

    # ── 사용자 입력 처리 ────────────────────────────────────
    if "keyword_query" in st.session_state:
        user_q = st.session_state.pop("keyword_query")
    else:
        user_q = st.chat_input("예: 전월실적 50만원 이하이고 해외겸용인 카드 추천해줘")

    if not user_q:
        return

    st.session_state.messages.append({"role": "user", "content": user_q})
    with st.chat_message("user", avatar="🙋"):
        st.markdown(user_q)

    # ── 검색 + 답변 생성 ────────────────────────────────────
    with st.spinner("카드를 찾고 있어요..."):
        result = chat(
            question=user_q,
            chat_history=st.session_state.messages,
            user_filters=user_filters,
            app_state=app_state,
            top_k=top_k,
            model=model,
            temperature=temperature,
        )

    answer = result["answer"]
    retrieved = result["retrieved"]
    inferred = result["inferred_filters"]

    if inferred["banks"] or inferred["categories"] or inferred["fee_bands"]:
        st.info(
            "자동 감지된 필터 — "
            + f"카드사: {inferred['banks'] or '전체'} / "
            + f"카테고리: {inferred['categories'] or '전체'} / "
            + f"연회비: {inferred['fee_bands'] or '전체'}"
        )

    _render_retrieval_debug(retrieved)

    with st.chat_message("assistant", avatar="⚡"):
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
