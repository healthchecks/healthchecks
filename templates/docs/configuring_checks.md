# Configuring Checks

In SITE_NAME, a **Check** represents a single service you want to
monitor. For example, when monitoring cron jobs, you would create a separate check for
each cron job to be monitored. SITE_NAME pricing plans are structured primarily
around how many checks you can have in your account. You can create checks
either in SITE_NAME web interface or by calling [API](../api/).

## Name, Tags, Description

Describe each check using optional name, tags and description fields.

![Editing name, tags and description](IMG_URL/edit_name.png)

* **Name**: names are optional, but it is a good idea to set them.
Good naming becomes especially important as you add more checks in the
account. Names are displayed in the web interface, in email reports and in the
notifications that SITE_NAME sends out.
* **Tags**: a space-separated list of optional labels. Use tags to organize and group
checks within a project. You can tag checks by environment
(`prod`, `staging`, `dev`, ...) or by role (`www`, `db`, `worker`, ...) or using
any other system.
* **Description**: a free-form text field with any related information for your team
or for your future self: what is being monitored, who set it up,
what to do in case of failures, where to look for additional information.

## Simple Schedules

SITE_NAME supports two types of schedules: "simple" and "cron". Use "Simple" schedules
for monitoring processes that are expected to run at relatively regular time
intervals: once an hour, once a day, once a week.

![Editing the period and grace time](IMG_URL/edit_simple_schedule.png)

For simple schedules you configure two time durations, Period and Grace Time.

* **Period**: the expected time between pings
* **Grace Time**: when a check is late, how long to wait before sending an alert.
Use this variable to account for small, expected deviations in job execution times.

## Cron Schedules

Use "cron" for monitoring processes with more complex schedules, and to ensure
jobs run **at the correct time** (not just at correct time intervals).

![Editing cron schedule](IMG_URL/edit_cron_schedule.png)

You will need to specify Cron Expression, Server's Time Zone and Grace Time.

* **Cron Expression**: enter the same expression you've used in the crontab.
* **Server's Time Zone**: cron daemon typically uses the local time of the machine it is
running on. If the machine is not using UTC timezone, you need to tell SITE_NAME
what timezone to use.
* **Grace Time**: same as for simple schedules, how long to wait before sending an alert
for a late check.

## Filtering Rules

In the "Filtering Rules" dialog you can control several advanced aspects of
how SITE_NAME handles incoming pings for a particular check.

![Setting filtering rules](IMG_URL/filtering_rules.png)

* **Allowed request methods for HTTP requests**. You can require the ping
requests to use HTTP POST. Use the "Only POST" option if you run into issues of
preview bots hitting the ping URLs when you send them in email or post them in chat.
* **Filter by keywords in the Subject line**. When pinging via [email](../email/),
look for specific keywords in the subject line. If the subject line contains any of
the keywords listed in **Success Keywords**, SITE_NAME will assume it to be a success
signal. Likewise, if it contains any of the keywords listed in **Failure Keywords**,
SITE_NAME will treat it as an explicit failure signal.
This is useful, for example, if your backup software sends an email after each backup
run with a different subject line depending on success or failure.
* **Pinging a Paused Check**. When you ping a paused check, normally it leaves
the paused state and goes into the "up" or "down" state (depending on the type of
the ping). This changes if you select the "Ignore the ping, stay in the paused state"
option: the paused state becomes "sticky". SITE_NAME will ignore all incoming pings
until you explicitly *resume* the check.
