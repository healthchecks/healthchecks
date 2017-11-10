from django.conf.urls import url

from hc.api import views

urlpatterns = [
    url(r'^ping/([\w-]+)/$', views.ping, name="hc-ping-slash"),
    url(r'^ping/([\w-]+)$', views.ping, name="hc-ping"),
    url(r'^api/v1/checks/$', views.checks),
    url(r'^api/v1/checks/([\w-]+)$', views.update, name="hc-api-update"),
    url(r'^api/v1/checks/([\w-]+)/pause$', views.pause, name="hc-api-pause"),
    url(r'^api/v1/notifications/([\w-]+)/bounce$', views.bounce,
        name="hc-api-bounce"),

    url(r'^badge/([\w-]+)/([\w-]{8})/([\w-]+).svg$', views.badge,
        name="hc-badge"),

    url(r'^badge/([\w-]+)/([\w-]{8}).svg$', views.badge,
        {"tag": "*"}, name="hc-badge-all"),

    url(r'^badge/([\w-]+)/([\w-]{8})/([\w-]+).json$', views.badge,
        {"format": "json"}, name="hc-badge-json"),

    url(r'^badge/([\w-]+)/([\w-]{8}).json$', views.badge,
        {"format": "json", "tag": "*"}, name="hc-badge-json-all"),

    url(r'^api/v1/status/$', views.status),
]
