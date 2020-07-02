# Configuring Notifications

You can set up multiple ways to receive notifications when checks in your account
change state. This is useful for multiple reasons:

* **Redundancy in case of notification failures.** Set up notifications using two different
transports (for example, email and Slack). If one transport fails (e.g., an email
message goes to spam), you still receive the notification over the other transport.
* **Use different notification methods depending on urgency**. For example, if a
low-priority housekeeping script fails, post a message in chat. If a vital service fails,
post in chat, send an email, and send SMS.
* Route notifications to the right people.

Notification methods ("integrations") are scoped to a project:
if you want to use a notification method in multiple projects, it must be
set up in each project separately.

In the web interface, the list of checks shows a visual overview of which alerting
methods are enabled for each check. You can click the icons to toggle them on and off:

![Integration icons in the checks list](IMG_URL/checks_integrations.png)

You can also toggle the integrations on and off when viewing an individual check by
clicking on the "ON" / "OFF" labels:

![Integration on/off toggles in the check details page](IMG_URL/details_integrations.png)

## SMS and WhatsApp Monthly Quotas

SITE_NAME limits the maximum number of SMS and WhatsApp notifications an account
can send per any given month. The specific limit depends on account's billing plan.

The limit is applied to the combined number of sent SMS and WhatsApp notifications. It
automatically resets at the start of each month. The "unused" sends from one month do
not carry over to the next month.

When an account exceeds its SMS / WhatsApp monthly limit, SITE_NAME will:

* Send a warning email to account's primary email address
* Show a warning message in the **Integrations** page


## Repeated Notifications

If you want to receive repeated notifications for as long as a particular check is
down, you have a few different options:

* If you use an **incident management system** (PagerDuty, VictorOps, OpsGenie,
PagerTree), you can set up escalation rules there.
* Use the **Pushover** integration with the "Emergency" priority. Pushover will
play a loud notification sound on your phone every 5 minutes until the notification
is acknowledged.
* SITE_NAME can send **hourly or daily email reminders** if any check is down
across all projects you have access to.
Set them up in [Account Settings › Email Reports](../../accounts/profile/notifications):

![Email reminder options](IMG_URL/email_reports.png)

## Monthly Reports

SITE_NAME sends monthly email reports at the start of each month. Use them
to make sure all checks have their expected state and nothing has
"fallen through the cracks".

A monthly report shows checks from all projects you have access
to. For each check it lists:

* check's current status
* the number of downtimes by month, for the two previous months
* the total downtime duration by month, for the two previous months

![Example monthly report](IMG_URL/monthly_report.png)

You can opt out from the monthly reports in the
[Account Settings › Email Reports](../../accounts/profile/notifications/) page
or by clicking the "Unsubscribe" link in report's footer.