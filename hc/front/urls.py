from django.urls import include, path

from hc.front import views

check_urls = [
    path("name/", views.update_name, name="hc-update-name"),
    path("details/", views.details, name="hc-details"),
    path("email_settings/", views.email_settings, name="hc-email-settings"),
    path("timeout/", views.update_timeout, name="hc-update-timeout"),
    path("pause/", views.pause, name="hc-pause"),
    path("remove/", views.remove_check, name="hc-remove-check"),
    path("log/", views.log, name="hc-log"),
    path("status/", views.status_single, name="hc-status-single"),
    path("last_ping/", views.ping_details, name="hc-last-ping"),
    path("transfer/", views.transfer, name="hc-transfer"),
    path(
        "channels/<uuid:channel_code>/enabled",
        views.switch_channel,
        name="hc-switch-channel",
    ),
    path("pings/<int:n>/", views.ping_details, name="hc-ping-details"),
]

channel_urls = [
    path("", views.channels, name="hc-channels"),
    path("add_email/", views.add_email, name="hc-add-email"),
    path("add_webhook/", views.add_webhook, name="hc-add-webhook"),
    path("add_pd/", views.add_pd, name="hc-add-pd"),
    path("add_pd/<str:state>/", views.add_pd, name="hc-add-pd-state"),
    path("add_pagertree/", views.add_pagertree, name="hc-add-pagertree"),
    path("add_pagerteam/", views.add_pagerteam, name="hc-add-pagerteam"),
    path("add_slack/", views.add_slack, name="hc-add-slack"),
    path("add_mattermost/", views.add_mattermost, name="hc-add-mattermost"),
    path("add_slack_btn/", views.add_slack_btn, name="hc-add-slack-btn"),
    path("add_pushbullet/", views.add_pushbullet, name="hc-add-pushbullet"),
    path("add_discord/", views.add_discord, name="hc-add-discord"),
    path("add_pushover/", views.add_pushover, name="hc-add-pushover"),
    path("add_opsgenie/", views.add_opsgenie, name="hc-add-opsgenie"),
    path("add_victorops/", views.add_victorops, name="hc-add-victorops"),
    path("telegram/bot/", views.telegram_bot, name="hc-telegram-webhook"),
    path("add_telegram/", views.add_telegram, name="hc-add-telegram"),
    path("add_sms/", views.add_sms, name="hc-add-sms"),
    path("add_whatsapp/", views.add_whatsapp, name="hc-add-whatsapp"),
    path("add_trello/", views.add_trello, name="hc-add-trello"),
    path("add_trello/settings/", views.trello_settings, name="hc-trello-settings"),
    path("add_matrix/", views.add_matrix, name="hc-add-matrix"),
    path("add_apprise/", views.add_apprise, name="hc-add-apprise"),
    path("<uuid:code>/checks/", views.channel_checks, name="hc-channel-checks"),
    path("<uuid:code>/name/", views.update_channel_name, name="hc-channel-name"),
    path("<uuid:code>/test/", views.send_test_notification, name="hc-channel-test"),
    path("<uuid:code>/remove/", views.remove_channel, name="hc-remove-channel"),
    path(
        "<uuid:code>/verify/<slug:token>/", views.verify_email, name="hc-verify-email"
    ),
    path(
        "<uuid:code>/unsub/<slug:token>/",
        views.unsubscribe_email,
        name="hc-unsubscribe-alerts",
    ),
]

urlpatterns = [
    path("", views.index, name="hc-index"),
    path("projects/<uuid:code>/checks/", views.my_checks, name="hc-checks"),
    path("projects/<uuid:code>/badges/", views.badges, name="hc-badges"),
    path("projects/<uuid:code>/checks/add/", views.add_check, name="hc-add-check"),
    path("checks/cron_preview/", views.cron_preview),
    path("projects/<uuid:code>/checks/status/", views.status, name="hc-status"),
    path("checks/<uuid:code>/", include(check_urls)),
    path("integrations/", include(channel_urls)),
    path("docs/", views.docs, name="hc-docs"),
    path("docs/api/", views.docs_api, name="hc-docs-api"),
    path("docs/cron/", views.docs_cron, name="hc-docs-cron"),
    path("docs/resources/", views.docs_resources, name="hc-docs-resources"),
]
