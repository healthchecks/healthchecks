# Monitoring Cron Jobs

SITE_NAME is perfectly suited for monitoring cron jobs. All you have to do is
update your cron job command to send a HTTP request to SITE_NAME
after a job completes.

Let's look at an example:

```bash
$ crontab -l
# m h dom mon dow command
  8 6 * * * /home/user/backup.sh
```

The above job runs `/home/user/backup.sh` every day at 6:08. The backup
script is presumably a headless, background process. Even if it works
correctly currently, it can start silently failing in future, without
anyone noticing.

You can set up SITE_NAME to notify you whenever the backup script does not
run on time or does not complete successfully. Here are the steps to do that.

1. If you have not already, sign up for a free SITE_NAME account.

1. In your SITE_NAME account, **add a new check**.

1. Give the check **a meaningful name**. Good naming will become
increasingly important as you add more checks to your account.

1. Edit the check's **schedule**:

    * change its type from "Simple" to "Cron"
    * enter `8 6 * * *` in the cron expression field
    * set the timezone to match your machine's timezone

1. Take note of your check's unique **ping URL**.

Finally, edit your cron job definition and append a curl or wget call
after the command:

```bash
$ crontab -e
# m h dom mon dow command
  8 6 * * * /home/user/backup.sh && curl -fsS --retry 5 -o /dev/null PING_URL
```

Now, each time your cron job runs, it will send a HTTP request to the ping URL.
Since SITE_NAME knows the schedule of your cron job, it can calculate
the dates and times when the job should run. As soon as your cron job doesn't
report at an expected time, SITE_NAME will send you a notification.

This monitoring technique takes care of various failure scenarios that could
potentially go unnoticed otherwise:

* The whole machine goes down (power outage, janitor stumbles on wires, VPS provider problems, etc.)
* cron daemon is not running, or has invalid configuration
* cron does start your task, but the task exits with non-zero exit code

## Curl Options

The extra options in the above example tells curl to retry failed HTTP requests, and
to silence output unless there is an error. Feel free to adjust the curl options to
suit your needs.

**&amp;&amp;**
:   Run curl only if `/home/user/backup.sh` exits with an exit code 0.

**-f, --fail**
:   Makes curl treat non-200 responses as errors.

**-s, --silent**
:   Silent or quiet mode. Hides the progress meter, but also hides error messages.

**-S, --show-error**
:   Re-enables error messages when -s is used.

**--retry &lt;num&gt;**
:   If a transient error is returned when curl tries to perform a
    transfer, it will retry this number of times before  giving  up.
    Setting  the number to  0 makes curl do no retries (which is the default).
    Transient error is a timeout or an HTTP 5xx response code.

**-o /dev/null**
:   Redirect curl's stdout to /dev/null (error messages still go to stderr).

## Looking up Your Machine's Time Zone

On modern GNU/Linux systems, you can look up the time zone using the
`timedatectl status` command and looking for "Time zone" in its output:

```text hl_lines="6"
$ timedatectl status

               Local time: C  2020-01-23 12:35:50 EET
           Universal time: C  2020-01-23 10:35:50 UTC
                 RTC time: C  2020-01-23 10:35:50
                Time zone: Europe/Riga (EET, +0200)
System clock synchronized: yes
              NTP service: active
          RTC in local TZ: no
```
