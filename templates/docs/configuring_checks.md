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

For simple schedules you configure two time durations, **Period** and **Grace Time**.

* **Period**: the expected time between pings
* **Grace Time**: when a check is late, how long to wait before sending an alert.
Use this variable to account for small, expected deviations in job execution times.

## Cron Schedules

Use "cron" for monitoring processes with more complex schedules, and to ensure
jobs run **at the correct time** (not just at correct intervals).

![Editing cron schedule](IMG_URL/edit_cron_schedule.png)

You will need to specify Cron Expression, Server's Time Zone and Grace Time.

* **Cron Expression**: enter the same expression you've used in the crontab.
* **Server's Time Zone**: cron daemon typically uses the local time of the machine it is
running on. If the machine is not using UTC timezone, you need to tell SITE_NAME
what timezone to use.
* **Grace Time**: same as for simple schedules, how long to wait before sending an alert
for a late check.

## Filtering Rules

![Setting filtering rules](IMG_URL/filtering_rules.png)

* **Allowed request methods for HTTP requests**: optionally require the HTTP ping
requests to use HTTP POST. Use this if you run into issues of bots hitting the ping
URLs when you send them in email or post them in chat.
* **Subject must contain**: when pinging via [email](../email/), require a particular
keyword in the subject line. SITE_NAME will ignore any email messages with the
keyword missing. This is useful, for example, when backup software sends
emails with "Backup Successful" or "Backup Failed" subject lines after each run,
and you want SITE_NAME to ignore the "Backup Failed" messages.
