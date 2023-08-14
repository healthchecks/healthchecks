# SITE_NAME Documentation

SITE_NAME is a service for monitoring cron jobs ([see guide](monitoring_cron_jobs/))
and similar periodic processes:

* SITE_NAME **listens for HTTP requests ("pings")** from your cron jobs and scheduled
  tasks.
* It **keeps silent** as long as pings arrive on time.
* It **raises an alert** as soon as a ping does not arrive on time.

SITE_NAME works as a [dead man's switch](https://en.wikipedia.org/wiki/Dead_man%27s_switch) for processes that need to
run continuously or on a regular, known schedule. Some examples of jobs that would
benefit from SITE_NAME monitoring:

* filesystem backups, database backups
* task queues
* database replication monitoring scripts
* report generation scripts
* periodic data import and sync jobs
* periodic antivirus scans
* DDNS updater scripts
* SSL renewal scripts

SITE_NAME is *not* the right tool for:

* monitoring website uptime by probing it with HTTP requests
* collecting application performance metrics
* log aggregation

## Concepts

A **Check** represents a single service you want to monitor. For example, when
[monitoring cron jobs](monitoring_cron_jobs/), you would create a separate check for
each cron job to be monitored. Each check has a unique ping URL, schedule,
and associated integrations. For the available configuration options, see
[Configuring checks](configuring_checks/).

Each check is always in one of the following states, depicted by a status icon:

<span class="status ic-new"></span>
:   **New**. A newly created check that has not received any pings yet. Each new
    check you create will start in this state.

<span class="status ic-up"></span>
:   **Up**. All is well. The last "success" signal has arrived on time.

<span class="status ic-grace"></span>
:   **Late**. The "success" signal is due but has not arrived yet.
    It is not yet late by more than the check's configured **Grace Time**.

<span class="status ic-down"></span>
:   **Down**. The "success" signal has not arrived yet, and the Grace Time has elapsed.
    When a check transitions into the "Down" state, SITE_NAME sends alert
    messages via the configured integrations.

<span class="status ic-paused"></span>
:   **Paused**. You can manually pause the monitoring of specific checks. For example,
    if a frequently running cron job has a known problem, and a fix is in the works 
    but not yet ready, you can pause monitoring the corresponding check temporarily to
    avoid unwanted alerts about a known issue.

<span class="status ic-up"></span><div class="spinner started"></div>
:   Additionally, if the most recent received signal is a "start" signal,
    this will be indicated by three animated dots under the check's status icon.

---

**Ping URL**. Each check has a unique **Ping URL**. Clients (cron jobs, background
workers, batch scripts, scheduled tasks, web services) make HTTP requests to the
ping URL to signal a start of the execution, a success, or a failure.

SITE_NAME supports two ping URL formats:

* `PING_ENDPOINT<uuid>`<br>
The check is identified by its UUID. Check UUIDs are assigned
automatically by SITE_NAME, and are guaranteed to be unique.
* `PING_ENDPOINT<project-ping-key>/<name-slug>`<br>
The check is identified by project's **Ping key** and check's
**slug** (user-chosen, URL-friendly identifier). Optionally supports auto-provisioning:
if you ping a slug value that does not have a corresponding check, SITE_NAME can
create the check automatically.

You can append `/start`, `/fail` or `/<exitcode>` to the base ping URL to send
"start" and "failure" signals. The "start" and "failure" signals are optional.
You don't have to use them, but you can gain additional monitoring insights
if you do use them. See [Measuring script run time](measuring_script_run_time/) and
[Signaling failures](signaling_failures/) for details.

You should treat check UUIDs and project Ping keys as secrets. If you make them public,
anybody can send telemetry signals to your checks and mess with your monitoring.

Read more about Ping URLs in [Pinging API](http_api/).

---

**Grace Time** is one of the configuration parameters you can set for each check.
It is the additional time to wait before sending an alert when a check
is late. Use this parameter to account for minor, expected deviations in job
execution times. If you use "start" signals to
[measure job execution time](measuring_script_run_time/), Grace Time also sets the
maximum allowed time gap between "start" and "success" signals. If a job
sends a "start" signal but does not send a "success" signal within grace time,
SITE_NAME will assume failure and send out alerts.

---

An **Integration** is a specific method for delivering monitoring alerts when a check's
change states. SITE_NAME supports many types of integrations: email,
webhooks, SMS, Slack, PagerDuty, etc. You can set up multiple integrations.
For each check, you can specify which integrations it should use.

For more information on integrations, see
[Configuring notifications](configuring_notifications/).

---

**Project**. To keep things organized, you can group checks and integrations in **Projects**.
Your account starts with a single default project, but you can create 
additional projects as needed. You can transfer existing checks between projects
while preserving their configuration and ping URLs.

Each project has a configurable name, a separate set of API keys, and a separate
project team. The project's team is the set of people you have granted read-only or
read-write access to the project.

For more information on projects, see [Projects and teams](projects_teams/).

