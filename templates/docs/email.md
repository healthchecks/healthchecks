# Email

As an alternative to HTTP/HTTPS requests, you can "ping" checks by
sending email messages to special email addresses.

![Email address for pinging via email](IMG_URL/emails.png)

By default, SITE_NAME will consider any email received at the displayed address as
a "success" signal. You can also configure SITE_NAME to look for specific
keywords in the subject line or the message body to decide if the message
is a "start", a "success" or a "failure" signal. You can set up the keywords in
the **Filtering Rules** dialog:

![Setting filtering rules](IMG_URL/filtering_rules.png)

## Use Case: Newsletter Delivery Monitoring

Consider a cron job that runs weekly and sends weekly newsletters
to a list of email addresses. You have already set up a check to get alerted
when your cron job fails to run. But what you ultimately want to check is if
**your emails are getting sent and delivered**.

The solution: set up another check, and add its email address to your list of
recipient email addresses. Set its Period to 1 week. As long as your weekly email
script runs correctly, and there are no email delivery issues,
SITE_NAME will regularly receive an email, and the check will stay up.

## Email Delivery Delays

Emails are more susceptible to random delivery delays than HTTP requests.
You may need to increase the grace time parameter for your checks to account for the
possible email delivery delays, and avoid false alerts.

Tracking job durations (using the "start" and "success" signals) will be less
accurate when pinging via email, and may not be feasible at all for jobs with
very short durations.