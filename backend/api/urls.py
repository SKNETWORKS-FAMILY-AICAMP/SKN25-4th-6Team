from django.urls import path

from .views import chat_view, health_check, session_detail_view, sessions_view

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("chat/", chat_view, name="chat"),
    path("sessions/", sessions_view, name="sessions"),
    path("sessions/<int:session_id>/", session_detail_view, name="session_detail"),
]
