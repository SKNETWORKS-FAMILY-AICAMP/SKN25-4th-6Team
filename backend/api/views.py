import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ChatSession, ChatMessage

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
@require_http_methods(["GET", "POST"])
def session_detail_view(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "세션을 찾을 수 없습니다."}, status=404)

    if request.method == "GET":
        messages = session.messages.all()
        return JsonResponse({
            "id": session.id,
            "title": session.title,
            "messages": [{"id": m.id, "role": m.role, "text": m.text} for m in messages],
        })

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

    role = body.get("role")
    text = body.get("text")
    if role not in ("user", "assistant") or not text:
        return JsonResponse({"error": "role과 text가 필요합니다."}, status=400)

    msg = ChatMessage.objects.create(session=session, role=role, text=text)
    return JsonResponse({"id": msg.id, "role": msg.role, "text": msg.text}, status=201)
