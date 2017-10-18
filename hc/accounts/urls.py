from django.conf.urls import url
from hc.accounts import views

urlpatterns = [
    url(r'^login/$', views.login, name="hc-login"),
    url(r'^logout/$', views.logout, name="hc-logout"),
    url(r'^login_link_sent/$',
        views.login_link_sent, name="hc-login-link-sent"),

    url(r'^link_sent/$',
        views.link_sent, name="hc-link-sent"),

    url(r'^check_token/([\w-]+)/([\w-]+)/$',
        views.check_token, name="hc-check-token"),

    url(r'^profile/$', views.profile, name="hc-profile"),
    url(r'^profile/notifications/$', views.notifications, name="hc-notifications"),
    url(r'^profile/badges/$', views.badges, name="hc-badges"),
    url(r'^close/$', views.close, name="hc-close"),

    url(r'^unsubscribe_reports/([\w\:-]+)/$',
        views.unsubscribe_reports, name="hc-unsubscribe-reports"),

    url(r'^set_password/([\w-]+)/$',
        views.set_password, name="hc-set-password"),

    url(r'^change_email/done/$',
        views.change_email_done, name="hc-change-email-done"),

    url(r'^change_email/([\w-]+)/$',
        views.change_email, name="hc-change-email"),

   url(r'^switch_team/([\w-]+)/$',
        views.switch_team, name="hc-switch-team"),

]
