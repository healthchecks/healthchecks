from __future__ import annotations

from django.urls import path

from hc.accounts import views

urlpatterns = [
    path("login/", views.login, name="hc-login"),
    path("login/two_factor/", views.login_webauthn, name="hc-login-webauthn"),
    path("login/two_factor/totp/", views.login_totp, name="hc-login-totp"),
    path("logout/", views.logout, name="hc-logout"),
    path("signup/csrf/", views.signup_csrf),
    path("signup/", views.signup, name="hc-signup"),
    path("login_link_sent/", views.login_link_sent, name="hc-login-link-sent"),
    path(
        "check_token/<str:username>/<str:token>/",
        views.check_token,
        name="hc-check-token",
    ),
    path("profile/", views.profile, name="hc-profile"),
    path("profile/appearance/", views.appearance, name="hc-appearance"),
    path("profile/notifications/", views.notifications, name="hc-notifications"),
    path("close/", views.close, name="hc-close"),
    path(
        "unsubscribe_reports/<str:signed_username>/",
        views.unsubscribe_reports,
        name="hc-unsubscribe-reports",
    ),
    path("set_password/", views.set_password, name="hc-set-password"),
    path("change_email/", views.change_email, name="hc-change-email"),
    path(
        "change_email/<str:signed_payload>/",
        views.change_email_verify,
        name="hc-change-email-verify",
    ),
    path("two_factor/webauthn/", views.add_webauthn, name="hc-add-webauthn"),
    path("two_factor/totp/", views.add_totp, name="hc-add-totp"),
    path("two_factor/totp/remove/", views.remove_totp, name="hc-remove-totp"),
    path(
        "two_factor/<uuid:code>/remove/",
        views.remove_credential,
        name="hc-remove-credential",
    ),
]
