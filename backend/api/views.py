import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ChatSession, ChatMessage

try:
    from src.utils import safe_get
except Exception:
    def safe_get(obj, keys, default=None):
        for k in keys:
            if not isinstance(obj, dict):
                return default
            obj = obj.get(k, default)
        return obj

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent

_app_state = None


def _get_app_state():
    global _app_state
    if _app_state is not None:
        return _app_state

    try:
        from src.service import load_app_state
        _app_state = load_app_state(
            data_dir=BACKEND_ROOT / "data" / "cards",
            category_config_path=BACKEND_ROOT / "rag_config" / "card_category_rules.json",
            rag_config_path=BACKEND_ROOT / "rag_config" / "rag_settings.json",
            synonyms_config_path=BACKEND_ROOT / "rag_config" / "synonyms.json",
            rag_artifacts_dir=BACKEND_ROOT / "vector_store",
            mbti_config_path=BACKEND_ROOT / "rag_config" / "mbti_rules.json",
        )
        logger.info("AppState 로드 완료: 카드 %d개", len(_app_state.cards))
    except Exception as e:
        logger.error("AppState 로드 실패: %s", e)
        raise

    return _app_state


def health_check(request):
    return JsonResponse({"status": "ok"})


CARDS_DIR = BACKEND_ROOT / "data" / "cards"

COMPANY_KR_MAP = {
    "hyundai card": "현대카드",
    "hyundaicard": "현대카드",
    "samsung card": "삼성카드",
    "samsungcard": "삼성카드",
    "shinhan card": "신한카드",
    "shinhancard": "신한카드",
    "kb card": "KB국민카드",
    "kb kookmin card": "KB국민카드",
    "lotte card": "롯데카드",
    "lottecard": "롯데카드",
    "hana card": "하나카드",
    "hanacard": "하나카드",
    "woori card": "우리카드",
    "wooricard": "우리카드",
    "nh card": "NH농협카드",
    "nh농협": "NH농협카드",
    "ibk": "IBK기업은행",
    "bc card": "BC카드",
    "bccard": "BC카드",
    "비씨카드": "BC카드",
    "bc바로카드": "BC카드",
}


def _normalize_company(company: str) -> str:
    return COMPANY_KR_MAP.get(company.strip().lower(), company)


_FOLLOWUP_KEYWORDS = [
    "그 중에서", "그중에서", "그 중", "그중",
    "거기서", "그 카드들", "아까", "방금",
    "앞에서", "위에서", "그것들",
    "이 카드", "그 카드", "해당 카드", "방금 추천",
    # 이전 답변에 대한 후속 상세 질문
    "자세히", "상세히", "더 알려", "설명해줘", "설명해주세요",
    "혜택도", "혜택에 대해", "혜택 알려", "혜택은", "혜택이",
    "에 대해서도", "에 대해서", "도 알려줘",
]

_RECOMMENDATION_KEYWORDS = [
    "추천", "추천해", "추천해줘", "추천해주세요",
    "좋은 카드", "어떤 카드", "뭐가 좋", "어느 카드",
    "찾아줘", "찾아주세요",
    "적합한 카드", "맞는 카드", "맞춤 카드",
]

_DETAIL_KEYWORDS = [
    "설명해줘", "설명해주세요", "설명 해줘",
    "자세히", "상세히",
    "혜택 알려줘", "혜택 알려주세요",
    "어떤 카드야", "어떤 카드인가",
    "어떻게 돼", "어떻게 되나요",
]

# 카드 개수 전체 요청 키워드
_ALL_KEYWORDS = ["전부", "전체", "모두", "다 알려", "다 추천", "전부 보여", "전체 보여"]


def _is_recommendation_query(
    question: str,
    inferred_filters: dict,
    is_owned_card_question: bool = False,
) -> bool:
    # 보유 카드 질문은 텍스트 답변으로 처리
    if is_owned_card_question:
        return False
    if any(kw in question for kw in _DETAIL_KEYWORDS):
        return False
    has_keyword = any(kw in question for kw in _RECOMMENDATION_KEYWORDS)
    has_categories = len(inferred_filters.get("categories", [])) > 0
    has_fee_bands = len(inferred_filters.get("fee_bands", [])) > 0
    return has_keyword or has_categories or has_fee_bands


def _serialize_card(card: dict) -> dict:
    try:
        from src.cards import annual_fee_display
        from src.utils import safe_get
    except Exception:
        return {}

    name = safe_get(card, ["card", "name"], "알수없음")
    bank = safe_get(card, ["card", "bank"], "미분류")
    fee_text, _ = annual_fee_display(card)
    categories = safe_get(card, ["_derived", "categories"], []) or []
    benefit_items = safe_get(card, ["benefits", "benefit_items"], []) or []
    brands = safe_get(card, ["card", "brandType"], []) or []

    by_threshold: dict = {}
    for item in benefit_items:
        if not isinstance(item, dict):
            continue
        threshold = item.get("monthly_min_spending", 0) or 0
        cat = item.get("category", "")
        rate = item.get("rate", "")
        desc = (item.get("description") or "")[:60]
        cap = item.get("monthly_cap", 0) or 0
        label = cat
        if rate:
            label += f" {rate}"
        if desc and desc != cat:
            label += f" — {desc}"
        if cap:
            label += f" (월 {cap:,}원 한도)"
        by_threshold.setdefault(threshold, []).append(label)

    benefit_groups = [
        {
            "threshold_label": "조건없음" if t == 0 else f"전월 {t:,}원 이상",
            "items": items[:4],
        }
        for t, items in sorted(by_threshold.items())
    ][:4]

    mbti_types = safe_get(card, ["_derived", "mbti_types"], []) or []

    return {
        "card_id": card.get("_file", "").replace(".json", ""),
        "name": name,
        "company": _normalize_company(bank),
        "annual_fee": fee_text,
        "categories": categories[:5],
        "brands": brands[:3] if isinstance(brands, list) else [],
        "benefit_groups": benefit_groups,
        "mbti_types": mbti_types[:2],
    }


@require_http_methods(["GET"])
def cards_list_view(request):
    """AppState에서 카드 목록 반환 (MBTI 포함)"""
    try:
        app_state = _get_app_state()
        cards = []
        for idx, card in enumerate(sorted(app_state.cards, key=lambda c: c.get("_file", "")), start=1):
            name = safe_get(card, ["card", "name"], "") or safe_get(card, ["metadata", "카드명"], card.get("_file", "").replace(".json", ""))
            company_raw = safe_get(card, ["card", "bank"], "") or safe_get(card, ["metadata", "카드사"], "")
            company = _normalize_company(company_raw)
            mbti_types = safe_get(card, ["_derived", "mbti_types"], []) or []
            cards.append({
                "id": idx,
                "name": name,
                "company": company,
                "card_id": card.get("_file", "").replace(".json", ""),
                "mbti_types": mbti_types[:2],
            })
        return JsonResponse({"cards": cards})
    except Exception as e:
        logger.exception("cards_list_view 오류")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_view(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

    question = body.get("message", "").strip()
    if not question:
        return JsonResponse({"error": "message 필드가 필요합니다."}, status=400)

    history = body.get("history", [])
    profile = body.get("profile", {})
    prev_card_ids = body.get("prev_card_ids", [])

    user_filters = {
        "banks": [],
        "categories": [],
        "fee_bands": [],
    }

    try:
        from src.service import chat
        app_state = _get_app_state()

        # followup 판단: 명시적 followup 키워드 있거나, 단일 prev 카드로 좁혀진 상태에서
        # 새 추천·제외 의도가 없는 질문 (단, 보유 카드 질문은 항상 새 검색)
        _is_owned = any(kw in question for kw in ["내 카드", "내카드", "보유 카드", "내가 가진", "가진 카드"])
        is_followup = (
            not _is_owned
            and bool(prev_card_ids)
            and (
                any(kw in question for kw in _FOLLOWUP_KEYWORDS)
                or any(kw in question for kw in ["가장 좋은", "제일 좋은", "최고의"])
                or (
                    len(prev_card_ids) == 1
                    and not any(kw in question for kw in _RECOMMENDATION_KEYWORDS)
                    and not any(kw in question for kw in ["다른 카드", "다른 거", "새로운", "말고", "제외", "대신"])
                )
            )
        )

        result = chat(
            question=question,
            chat_history=history,
            user_filters=user_filters,
            user_profile=profile,
            app_state=app_state,
            prev_card_ids=prev_card_ids if is_followup else None,
        )

        import re as _re
        _single_keywords = [
            "가장 좋은", "제일 좋은", "최고의", "최고로 좋은",
            "하나만", "한 개만", "한개만", "1개만", "딱 하나", "딱 1개",
        ]
        _num_match = _re.search(r'([1-9])\s*개', question)
        if any(kw in question for kw in _single_keywords):
            _top_k = 1
        elif any(kw in question for kw in _ALL_KEYWORDS):
            _top_k = 8
        elif _num_match:
            _top_k = min(int(_num_match.group(1)), 8)
        else:
            _top_k = 5

        cards_data = [_serialize_card(card) for _, card in result.get("retrieved", [])[:_top_k]]
        cards_data = [c for c in cards_data if c.get("name")]

        inferred = result.get("inferred_filters", {})
        is_owned_card_question = result.get("is_owned_card_question", False)
        is_recommendation = (
            _is_recommendation_query(question, inferred, is_owned_card_question)
            and len(cards_data) >= 1
        )

        return JsonResponse({
            "answer": result["answer"],
            "cards": cards_data,
            "is_recommendation": is_recommendation,
            "inferred_filters": result.get("inferred_filters", {}),
        })

    except Exception as e:
        logger.exception("chat_view 처리 중 오류")
        return JsonResponse({"error": f"서버 오류: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def sessions_view(request):
    if request.method == "GET":
        sessions = ChatSession.objects.all()
        data = [{"id": s.id, "title": s.title} for s in sessions]
        return JsonResponse(data, safe=False)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

    title = body.get("title", "새 대화")
    session = ChatSession.objects.create(title=title)
    return JsonResponse({"id": session.id, "title": session.title}, status=201)


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE"])
def session_detail_view(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "세션을 찾을 수 없습니다."}, status=404)

    if request.method == "DELETE":
        session.delete()
        return JsonResponse({"ok": True})

    if request.method == "GET":
        messages = session.messages.all()
        return JsonResponse({
            "id": session.id,
            "title": session.title,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "text": m.text,
                    "payload": m.payload or {},
                }
                for m in messages
            ],
        })

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

    role = body.get("role")
    text = body.get("text")
    payload = body.get("payload", {})
    if role not in ("user", "assistant") or not text:
        return JsonResponse({"error": "role과 text가 필요합니다."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "payload는 객체여야 합니다."}, status=400)

    msg = ChatMessage.objects.create(session=session, role=role, text=text, payload=payload)
    return JsonResponse(
        {"id": msg.id, "role": msg.role, "text": msg.text, "payload": msg.payload},
        status=201,
    )
