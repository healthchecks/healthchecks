from django.urls import path

from hc.api import views

urlpatterns = [
    path('ping/<uuid:code>/', views.ping, name="hc-ping-slash"),
    path('ping/<uuid:code>', views.ping, name="hc-ping"),
    path('ping/<uuid:code>/fail', views.ping, {"is_fail": True},
         name="hc-fail"),

    path('api/v1/checks/', views.checks),
    path('api/v1/checks/<uuid:code>', views.update, name="hc-api-update"),
    path('api/v1/checks/<uuid:code>/pause', views.pause, name="hc-api-pause"),
    path('api/v1/notifications/<uuid:code>/bounce', views.bounce,
         name="hc-api-bounce"),

    path('api/v1/channels/', views.channels),


    path('badge/<slug:username>/<slug:signature>/<slug:tag>.svg', views.badge,
         name="hc-badge"),

    path('badge/<slug:username>/<slug:signature>.svg', views.badge,
         {"tag": "*"}, name="hc-badge-all"),

    path('badge/<slug:username>/<slug:signature>/<slug:tag>.json', views.badge,
         {"format": "json"}, name="hc-badge-json"),

    path('badge/<slug:username>/<slug:signature>.json', views.badge,
         {"format": "json", "tag": "*"}, name="hc-badge-json-all"),

    path('api/v1/status/', views.status),
]
