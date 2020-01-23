## Monitoring Cron Jobs

SITE_NAME is perfectly suited for monitoring cron jobs.
Let's look at an example: a machine with the following cron job:

```bash
$ crontab -l
# m h dom mon dow command
  8 6 * * * /home/user/backup.sh
```

You can use SITE_NAME to get a notification whenever the `backup.sh` script does not
complete successfully. Here is how to set that up.

1. If you have not already, sign up for a free SITE_NAME account.

1. In your SITE_NAME account, **add a new check**.

    Note: in SITE_NAME, a **check** represents a single service you want to
    monitor. For example, a single cron job. For each additional cron job you will
    create another check. SITE_NAME pricing plans are structured primarily
    around how many checks you can have in the account.

1. Give the check **a meaningful name**. Good naming will become
increasingly important as you add more checks to your account.

1. Edit the check's **schedule**:

    * change its type from "Simple" to "Cron"
    * enter `8 6 * * *` in the cron epression field
    * set the timezone to match your machine's timezone

1. Take note of your check's unique **ping URL**

Finally, edit your crontab and append a curl or wget call after the command:

```bash
$ crontab -e
# m h dom mon dow command
  8 6 * * * /home/user/backup.sh && curl -fsS --retry 3 PING_URL > /dev/null
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

The extra options tells curl to not print anything to standard output unless
there is an error. Feel free to adjust the curl options to suit your needs.

<table class="table curl-opts">
    <tr>
        <th>&amp;&amp;</th>
        <td>Run curl only if <code>/home/user/backup.sh</code> exits with an exit code 0</td>
    </tr>
    <tr>
        <th>
            -f,  --fail
        </th>
        <td>Makes curl treat non-200 responses as errors</td>
    </tr>
    <tr>
        <th>-s, --silent</th>
        <td>Silent or quiet mode. Don't show progress meter or error messages.</td>
    </tr>
    <tr>
        <th>-S, --show-error</th>
        <td>When used with -s it makes curl show error message if it fails.</td>
    </tr>
    <tr>
        <th>--retry &lt;num&gt;</th>
        <td>
            If a transient error is returned when curl tries to perform a
            transfer, it will retry this number of times before  giving  up.
            Setting  the number  to  0  makes curl do no retries
            (which is the default). Transient error means either: a timeout,
            an FTP 4xx response code or an HTTP 5xx response code.
        </td>
    </tr>
    <tr>
        <th>&gt; /dev/null</th>
        <td>
            Redirect curl's stdout to /dev/null (error messages go to stderr,)
        </td>
    </tr>
</table>

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