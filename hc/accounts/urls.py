from django.urls import path
from hc.accounts import views

urlpatterns = [
    path("login/", views.login, name="hc-login"),
    path("login/two_factor/", views.login_webauthn, name="hc-login-webauthn"),
    path("logout/", views.logout, name="hc-logout"),
    path("signup/", views.signup, name="hc-signup"),
    path("login_link_sent/", views.login_link_sent, name="hc-login-link-sent"),
    path("link_sent/", views.link_sent, name="hc-link-sent"),
    path(
        "check_token/<slug:username>/<slug:token>/",
        views.check_token,
        name="hc-check-token",
    ),
    path("profile/", views.profile, name="hc-profile"),
    path("profile/notifications/", views.notifications, name="hc-notifications"),
    path("close/", views.close, name="hc-close"),
    path(
        "unsubscribe_reports/<str:signed_username>/",
        views.unsubscribe_reports,
        name="hc-unsubscribe-reports",
    ),
    path("set_password/", views.set_password, name="hc-set-password"),
    path("change_email/done/", views.change_email_done, name="hc-change-email-done"),
    path("change_email/<slug:token>/", views.change_email, name="hc-change-email"),
    path("two_factor/add/", views.add_credential, name="hc-add-credential"),
    path(
        "two_factor/<uuid:code>/remove/",
        views.remove_credential,
        name="hc-remove-credential",
    ),
]
