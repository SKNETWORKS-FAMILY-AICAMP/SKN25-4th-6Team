from django.urls import path

from .views import chat_view, health_check

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("chat/", chat_view, name="chat"),
]
