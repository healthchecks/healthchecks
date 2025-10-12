from __future__ import annotations

from django.urls import include, path
from hc.front import views

# /checks/<code>/
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
    path("log_events/", views.log_events, name="hc-log-events"),
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

# /integrations/
channel_urls = [
    path("<uuid:code>/checks/", views.channel_checks, name="hc-channel-checks"),
    path("<uuid:code>/name/", views.update_channel_name, name="hc-channel-name"),
    path("<uuid:code>/edit/", views.edit_channel, name="hc-edit-channel"),
    path("<uuid:code>/test/", views.send_test_notification, name="hc-channel-test"),
    path("<uuid:code>/remove/", views.remove_channel, name="hc-remove-channel"),
]

# /projects/<code>/
project_urls = [
    path("badges/", views.badges, name="hc-badges"),
    path("checks/", views.checks, name="hc-checks"),
    path("checks/add/", views.add_check, name="hc-add-check"),
    path("checks/status/", views.status, name="hc-status"),
    path("integrations/", views.channels, name="hc-channels"),
]

# /
urlpatterns = [
    path("", views.index, name="hc-index"),
    path("tv/", views.dashboard, name="hc-dashboard"),
    path("checks/cron_preview/", views.cron_preview),
    path("checks/oncalendar_preview/", views.oncalendar_preview),
    path("checks/validate_schedule/", views.validate_schedule),
    path("checks/<uuid:code>/", include(check_urls)),
    path("cloaked/<sha1:unique_key>/", views.uncloak, name="hc-uncloak"),
    path("integrations/", include(channel_urls)),
    path("projects/menu/", views.projects_menu, name="hc-projects-menu"),
    path("projects/<uuid:code>/", include(project_urls)),
    path("docs/", views.serve_doc, name="hc-docs"),
    path("docs/cron/", views.docs_cron, name="hc-docs-cron"),
    path("docs/search/", views.docs_search, name="hc-docs-search"),
    path("docs/<slug:doc>/", views.serve_doc, name="hc-serve-doc"),
    path("contact.vcf", views.contact_vcf, name="hc-contact-vcf"),
]
