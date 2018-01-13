from django.conf.urls import include, url

from hc.front import views

check_urls = [
    url(r'^name/$', views.update_name, name="hc-update-name"),
    url(r'^timeout/$', views.update_timeout, name="hc-update-timeout"),
    url(r'^pause/$', views.pause, name="hc-pause"),
    url(r'^remove/$', views.remove_check, name="hc-remove-check"),
    url(r'^log/$', views.log, name="hc-log"),
    url(r'^last_ping/$', views.last_ping, name="hc-last-ping"),
]

channel_urls = [
    url(r'^$', views.channels, name="hc-channels"),
    url(r'^add_email/$', views.add_email, name="hc-add-email"),
    url(r'^add_webhook/$', views.add_webhook, name="hc-add-webhook"),
    url(r'^add_pd/$', views.add_pd, name="hc-add-pd"),
    url(r'^add_pd/([\w]{12})/$', views.add_pd, name="hc-add-pd-state"),
    url(r'^add_pagertree/$', views.add_pagertree, name="hc-add-pagertree"),
    url(r'^add_slack/$', views.add_slack, name="hc-add-slack"),
    url(r'^add_slack_btn/$', views.add_slack_btn, name="hc-add-slack-btn"),
    url(r'^add_hipchat/$', views.add_hipchat, name="hc-add-hipchat"),
    url(r'^hipchat/capabilities/$', views.hipchat_capabilities, name="hc-hipchat-capabilities"),
    url(r'^add_pushbullet/$', views.add_pushbullet, name="hc-add-pushbullet"),
    url(r'^add_discord/$', views.add_discord, name="hc-add-discord"),
    url(r'^add_pushover/$', views.add_pushover, name="hc-add-pushover"),
    url(r'^add_opsgenie/$', views.add_opsgenie, name="hc-add-opsgenie"),
    url(r'^add_victorops/$', views.add_victorops, name="hc-add-victorops"),
    url(r'^telegram/bot/$', views.telegram_bot, name="hc-telegram-webhook"),
    url(r'^add_telegram/$', views.add_telegram, name="hc-add-telegram"),
    url(r'^add_sms/$', views.add_sms, name="hc-add-sms"),
    url(r'^add_zendesk/$', views.add_zendesk, name="hc-add-zendesk"),
    url(r'^([\w-]+)/checks/$', views.channel_checks, name="hc-channel-checks"),
    url(r'^([\w-]+)/remove/$', views.remove_channel, name="hc-remove-channel"),
    url(r'^([\w-]+)/verify/([\w-]+)/$', views.verify_email,
        name="hc-verify-email"),
    url(r'^([\w-]+)/unsub/([\w-]+)/$', views.unsubscribe_email,
        name="hc-unsubscribe-alerts"),
]

urlpatterns = [
    url(r'^$', views.index, name="hc-index"),
    url(r'^checks/$', views.my_checks, name="hc-checks"),
    url(r'^checks/add/$', views.add_check, name="hc-add-check"),
    url(r'^checks/cron_preview/$', views.cron_preview),
    url(r'^checks/([\w-]+)/', include(check_urls)),
    url(r'^integrations/', include(channel_urls)),

    url(r'^docs/$', views.docs, name="hc-docs"),
    url(r'^docs/api/$', views.docs_api, name="hc-docs-api"),
    url(r'^docs/cron/$', views.docs_cron, name="hc-docs-cron"),
]
