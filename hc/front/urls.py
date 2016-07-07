from django.conf.urls import url

from hc.front import views

urlpatterns = [
    url(r'^$',                          views.index,  name="hc-index"),
    url(r'^checks/$',                   views.my_checks, name="hc-checks"),
    url(r'^checks/add/$',               views.add_check, name="hc-add-check"),
    url(r'^checks/([\w-]+)/name/$',     views.update_name, name="hc-update-name"),
    url(r'^checks/([\w-]+)/timeout/$',  views.update_timeout, name="hc-update-timeout"),
    url(r'^checks/([\w-]+)/remove/$',   views.remove_check, name="hc-remove-check"),
    url(r'^checks/([\w-]+)/log/$',      views.log, name="hc-log"),
    url(r'^docs/$',                     views.docs, name="hc-docs"),
    url(r'^docs/api/$',                 views.docs_api, name="hc-docs-api"),
    url(r'^about/$',                    views.about, name="hc-about"),
    url(r'^privacy/$',                  views.privacy, name="hc-privacy"),
    url(r'^terms/$',                    views.terms, name="hc-terms"),
    url(r'^integrations/$',                 views.channels, name="hc-channels"),
    url(r'^integrations/add/$',             views.add_channel, name="hc-add-channel"),
    url(r'^integrations/add_email/$',       views.add_email, name="hc-add-email"),
    url(r'^integrations/add_webhook/$',     views.add_webhook, name="hc-add-webhook"),
    url(r'^integrations/add_pd/$',          views.add_pd, name="hc-add-pd"),
    url(r'^integrations/add_slack/$',       views.add_slack, name="hc-add-slack"),
    url(r'^integrations/add_slack_btn/$',   views.add_slack_btn, name="hc-add-slack-btn"),
    url(r'^integrations/add_hipchat/$',     views.add_hipchat, name="hc-add-hipchat"),
    url(r'^integrations/add_pushover/$',    views.add_pushover, name="hc-add-pushover"),
    url(r'^integrations/add_victorops/$',   views.add_victorops, name="hc-add-victorops"),
    url(r'^integrations/([\w-]+)/checks/$', views.channel_checks, name="hc-channel-checks"),
    url(r'^integrations/([\w-]+)/remove/$', views.remove_channel, name="hc-remove-channel"),
    url(r'^integrations/([\w-]+)/verify/([\w-]+)/$',
        views.verify_email, name="hc-verify-email"),

]
