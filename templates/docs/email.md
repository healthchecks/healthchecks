# Email

Alternatively to HTTP/HTTPS requests, you can "ping" checks by
sending email messages to special email addresses.

![Email address for pinging via email](IMG_URL/emails.png)

## Keyword Filtering {: #keyword-filtering }

By default, SITE_NAME will consider any email received at the displayed address as
a "success" signal. Optionally, you can configure SITE_NAME to look for specific
keywords in the subject line or the message body to decide if the message
is a "start," a "success," or a "failure" signal.

SITE_NAME treats keywords as case-sensitive (for example, "Error" and "error" are
different keywords), and matches them in a specific order:

* SITE_NAME first checks the message for presence of any **failure** keyword.
* It then checks for any **success** keyword.
* It then checks for any **start** keyword.
* If filtering is enabled but none of the keywords match, SITE_NAME **ignores**
  the email message. The email will show in the event log with an "Ignored" badge.

You can set up keywords in the **Filtering Rules** dialog:

![Setting filtering rules](IMG_URL/filtering_rules.png)

## Use Case: Newsletter Delivery Monitoring

Consider a cron job that runs weekly and sends newsletters
to a list of email addresses. You have already set up a check to get alerted
when your cron job fails to run. But you ultimately want to check if
**your emails are getting sent and delivered**.

The solution: set up another check, and add its email address to your list of
recipient email addresses. Set its Period to 1 week. As long as your weekly email
script runs correctly, and there are no email delivery issues,
SITE_NAME will regularly receive an email, and the check will stay up.

## Use Case: Backup Monitoring

If you use backup software that can be configured to send an email report
after each backup run, you can monitor it with SITE_NAME. Create a new check in
SITE_NAME and configure your backup software to send email reports to its email
address. Then set up keywords in the **Filtering Rules** dialog to distinguish
between successful and failed backup runs. SITE_NAME will keep quiet as long
as it receives regular success reports, but will notify you when it
does not receive a success report for too long or receives a failure report.

## Email Delivery Delays

Emails are more susceptible to random delivery delays than HTTP requests.
Adjust the grace time parameter for your checks to account for the
possible email delivery delays, and avoid false alerts.

Tracking job durations (using the "start" and "success" signals) will be less
accurate when pinging via email and may not be feasible at all for jobs with
very short durations.
