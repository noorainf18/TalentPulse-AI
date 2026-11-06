from django.urls import path

from talentplus_ai.users.api.auth_views import auth_csrf, auth_login, auth_logout, auth_me

urlpatterns = [
    path("csrf/", auth_csrf, name="api-auth-csrf"),
    path("login/", auth_login, name="api-auth-login"),
    path("logout/", auth_logout, name="api-auth-logout"),
    path("me/", auth_me, name="api-auth-me"),
]
