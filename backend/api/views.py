import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

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
            category_config_path=BACKEND_ROOT / "config_files" / "card_category_rules.json",
            rag_config_path=BACKEND_ROOT / "config_files" / "rag_settings.json",
            synonyms_config_path=BACKEND_ROOT / "config_files" / "synonyms.json",
            rag_artifacts_dir=BACKEND_ROOT / "vector_store",
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
}


def _normalize_company(company: str) -> str:
    return COMPANY_KR_MAP.get(company.strip().lower(), company)


@require_http_methods(["GET"])
def cards_list_view(request):
    """data/cards/ 의 JSON 파일을 읽어 카드 목록 반환"""
    cards = []
    for idx, path in enumerate(sorted(CARDS_DIR.glob("*.json")), start=1):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            card_info = data.get("card", {})
            name = card_info.get("name") or data.get("metadata", {}).get("카드명", path.stem)
            company_raw = card_info.get("bank") or data.get("metadata", {}).get("카드사", "")
            company = _normalize_company(company_raw)
            cards.append({
                "id": idx,
                "name": name,
                "company": company,
                "card_id": path.stem,
            })
        except Exception as e:
            logger.warning("카드 파일 로드 실패 %s: %s", path.name, e)

    return JsonResponse({"cards": cards})


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

    user_filters = {
        "banks": [],
        "categories": [],
        "fee_bands": [],
    }

    try:
        from src.service import chat
        app_state = _get_app_state()

        result = chat(
            question=question,
            chat_history=history,
            user_filters=user_filters,
            user_profile=profile,
            app_state=app_state,
        )

        return JsonResponse({
            "answer": result["answer"],
            "inferred_filters": result.get("inferred_filters", {}),
        })

    except Exception as e:
        logger.exception("chat_view 처리 중 오류")
        return JsonResponse({"error": f"서버 오류: {str(e)}"}, status=500)
