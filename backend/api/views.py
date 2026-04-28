import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_app_state = None


def _get_app_state():
    global _app_state
    if _app_state is not None:
        return _app_state

    try:
        from src.service import load_app_state
        _app_state = load_app_state(
            data_dir=PROJECT_ROOT / "data" / "cards",
            category_config_path=PROJECT_ROOT / "config" / "card_category_rules.json",
            rag_config_path=PROJECT_ROOT / "config" / "rag_settings.json",
            synonyms_config_path=PROJECT_ROOT / "config" / "synonyms.json",
            rag_artifacts_dir=PROJECT_ROOT / "vector_store",
        )
        logger.info("AppState 로드 완료: 카드 %d개", len(_app_state.cards))
    except Exception as e:
        logger.error("AppState 로드 실패: %s", e)
        raise

    return _app_state


def health_check(request):
    return JsonResponse({"status": "ok"})


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
            app_state=app_state,
        )

        return JsonResponse({
            "answer": result["answer"],
            "inferred_filters": result.get("inferred_filters", {}),
        })

    except Exception as e:
        logger.exception("chat_view 처리 중 오류")
        return JsonResponse({"error": f"서버 오류: {str(e)}"}, status=500)
