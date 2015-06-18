from django.conf.urls import url

from hc.accounts import views

urlpatterns = [
    url(r'^login/$',                         views.login,           name="hc-login"),
    url(r'^logout/$',                        views.logout,          name="hc-logout"),
    url(r'^login_link_sent/$',               views.login_link_sent, name="hc-login-link-sent"),
    url(r'^check_token/([\w-]+)/([\w-]+)/$', views.check_token,     name="hc-check-token"),
]
