from __future__ import annotations

from django.urls import include, path

from hc.front import views

check_urls = [
    path("name/", views.update_name, name="hc-update-name"),
    path("details/", views.details, name="hc-details"),
    path("filtering_rules/", views.filtering_rules, name="hc-filtering-rules"),
    path("timeout/", views.update_timeout, name="hc-update-timeout"),
    path("pause/", views.pause, name="hc-pause"),
    path("resume/", views.resume, name="hc-resume"),
    path("remove/", views.remove_check, name="hc-remove-check"),
    path("clear_events/", views.clear_events, name="hc-clear-events"),
    path("log/", views.log, name="hc-log"),
    path("status/", views.status_single, name="hc-status-single"),
    path("last_ping/", views.ping_details, name="hc-last-ping"),
    path("transfer/", views.transfer, name="hc-transfer"),
    path("copy/", views.copy, name="hc-copy"),
    path(
        "channels/<uuid:channel_code>/enabled",
        views.switch_channel,
        name="hc-switch-channel",
    ),
    path("pings/<int:n>/", views.ping_details, name="hc-ping-details"),
    path("pings/<int:n>/body/", views.ping_body, name="hc-ping-body"),
]

channel_urls = [
    path("add_pushbullet/", views.add_pushbullet_complete),
    path("add_discord/", views.add_discord_complete),
    path("add_linenotify/", views.add_linenotify_complete),
    path("add_pagerduty/", views.add_pd_complete, name="hc-add-pd-complete"),
    path("add_pushover/", views.pushover_help, name="hc-pushover-help"),
    path("telegram/", views.telegram_help, name="hc-telegram-help"),
    path("telegram/bot/", views.telegram_bot, name="hc-telegram-webhook"),
    path("pagerduty/", views.pd_help, name="hc-pagerduty-help"),
    path("mattermost/", views.mattermost_help, name="hc-mattermost-help"),
    path("add_slack/", views.slack_help, name="hc-slack-help"),
    path("add_slack_btn/", views.add_slack_complete),
    path("add_telegram/", views.add_telegram, name="hc-add-telegram"),
    path("add_trello/settings/", views.trello_settings, name="hc-trello-settings"),
    path("<uuid:code>/checks/", views.channel_checks, name="hc-channel-checks"),
    path("<uuid:code>/name/", views.update_channel_name, name="hc-channel-name"),
    path("<uuid:code>/edit/", views.edit_channel, name="hc-edit-channel"),
    path("<uuid:code>/test/", views.send_test_notification, name="hc-channel-test"),
    path("<uuid:code>/remove/", views.remove_channel, name="hc-remove-channel"),
    path(
        "<uuid:code>/verify/<slug:token>/", views.verify_email, name="hc-verify-email"
    ),
    path(
        "<uuid:code>/unsub/<str:signed_token>/",
        views.unsubscribe_email,
        name="hc-unsubscribe-alerts",
    ),
]

project_urls = [
    path("add_apprise/", views.add_apprise, name="hc-add-apprise"),
    path("add_call/", views.add_call, name="hc-add-call"),
    path("add_discord/", views.add_discord, name="hc-add-discord"),
    path("add_email/", views.add_email, name="hc-add-email"),
    path("add_gotify/", views.add_gotify, name="hc-add-gotify"),
    path("add_linenotify/", views.add_linenotify, name="hc-add-linenotify"),
    path("add_matrix/", views.add_matrix, name="hc-add-matrix"),
    path("add_mattermost/", views.add_mattermost, name="hc-add-mattermost"),
    path("add_msteams/", views.add_msteams, name="hc-add-msteams"),
    path("add_ntfy/", views.add_ntfy, name="hc-add-ntfy"),
    path("add_opsgenie/", views.add_opsgenie, name="hc-add-opsgenie"),
    path("add_pagertree/", views.add_pagertree, name="hc-add-pagertree"),
    path("add_pd/", views.add_pd, name="hc-add-pd"),
    path("add_prometheus/", views.add_prometheus, name="hc-add-prometheus"),
    path("add_pushbullet/", views.add_pushbullet, name="hc-add-pushbullet"),
    path("add_pushover/", views.add_pushover, name="hc-add-pushover"),
    path("add_shell/", views.add_shell, name="hc-add-shell"),
    path("add_signal/", views.add_signal, name="hc-add-signal"),
    path("add_slack/", views.add_slack, name="hc-add-slack"),
    path("add_slack_btn/", views.add_slack_btn, name="hc-add-slack-btn"),
    path("add_sms/", views.add_sms, name="hc-add-sms"),
    path("add_spike/", views.add_spike, name="hc-add-spike"),
    path("add_trello/", views.add_trello, name="hc-add-trello"),
    path("add_victorops/", views.add_victorops, name="hc-add-victorops"),
    path("add_webhook/", views.add_webhook, name="hc-add-webhook"),
    path("add_whatsapp/", views.add_whatsapp, name="hc-add-whatsapp"),
    path("add_zulip/", views.add_zulip, name="hc-add-zulip"),
    path("badges/", views.badges, name="hc-badges"),
    path("checks/", views.my_checks, name="hc-checks"),
    path("checks/add/", views.add_check, name="hc-add-check"),
    path(
        "checks/metrics/<slug:key>",
        views.metrics,
    ),
    path(
        "metrics/<slug:key>",
        views.metrics,
        name="hc-metrics",
    ),
    path("checks/status/", views.status, name="hc-status"),
    path("integrations/", views.channels, name="hc-channels"),
]

urlpatterns = [
    path("", views.index, name="hc-index"),
    path("tv/", views.dashboard, name="hc-dashboard"),
    path("checks/cron_preview/", views.cron_preview),
    path("checks/validate_schedule/", views.validate_schedule),
    path("checks/<uuid:code>/", include(check_urls)),
    path("cloaked/<sha1:unique_key>/", views.uncloak, name="hc-uncloak"),
    path("integrations/", include(channel_urls)),
    path("projects/<uuid:code>/", include(project_urls)),
    path("docs/", views.serve_doc, name="hc-docs"),
    path("docs/cron/", views.docs_cron, name="hc-docs-cron"),
    path("docs/search/", views.docs_search, name="hc-docs-search"),
    path("docs/<slug:doc>/", views.serve_doc, name="hc-serve-doc"),
    path("signal_captcha/", views.signal_captcha, name="hc-signal-captcha"),
]
