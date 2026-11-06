from django.urls import path

from .views import RagAskView, RagIndexView

urlpatterns = [
    path("index/", RagIndexView.as_view(), name="ragchat-index"),
    path("ask/", RagAskView.as_view(), name="ragchat-ask"),
]
