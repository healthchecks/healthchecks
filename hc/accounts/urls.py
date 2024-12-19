from __future__ import annotations

from django.urls import path

from hc.accounts import views

urlpatterns = [
    path("projects/add/", views.add_project, name="hc-add-project"),
    path("projects/<uuid:code>/settings/", views.project, name="hc-project-settings"),
    path(
        "projects/<uuid:code>/remove/", views.remove_project, name="hc-remove-project"
    ),
    path("accounts/login/", views.login, name="hc-login"),
    path("accounts/login/two_factor/", views.login_webauthn, name="hc-login-webauthn"),
    path("accounts/login/two_factor/totp/", views.login_totp, name="hc-login-totp"),
    path("accounts/logout/", views.logout, name="hc-logout"),
    path("accounts/signup/csrf/", views.signup_csrf),
    path("accounts/signup/", views.signup, name="hc-signup"),
    path("accounts/login_link_sent/", views.login_link_sent, name="hc-login-link-sent"),
    path(
        "accounts/check_token/<str:username>/<str:token>/",
        views.check_token,
        name="hc-check-token",
    ),
    path("accounts/profile/", views.profile, name="hc-profile"),
    path("accounts/profile/appearance/", views.appearance, name="hc-appearance"),
    path(
        "accounts/profile/notifications/", views.notifications, name="hc-notifications"
    ),
    path("accounts/close/", views.close, name="hc-close"),
    path(
        "accounts/unsubscribe_reports/<str:signed_username>/",
        views.unsubscribe_reports,
        name="hc-unsubscribe-reports",
    ),
    path("accounts/set_password/", views.set_password, name="hc-set-password"),
    path("accounts/change_email/", views.change_email, name="hc-change-email"),
    path(
        "accounts/change_email/<str:signed_payload>/",
        views.change_email_verify,
        name="hc-change-email-verify",
    ),
    path("accounts/two_factor/webauthn/", views.add_webauthn, name="hc-add-webauthn"),
    path("accounts/two_factor/totp/", views.add_totp, name="hc-add-totp"),
    path("accounts/two_factor/totp/remove/", views.remove_totp, name="hc-remove-totp"),
    path(
        "accounts/two_factor/<uuid:code>/remove/",
        views.remove_credential,
        name="hc-remove-credential",
    ),
]
