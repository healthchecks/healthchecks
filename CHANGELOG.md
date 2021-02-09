# Changelog
All notable changes to this project will be documented in this file.

## v1.20.0 - Unreleased

## Improvements
- Rename VictorOps -> Splunk On-Call

## Bug Fixes
- Fix downtime summary to handle months when the check didn't exist yet (#472)
- Relax cron expression validation: accept all expressions that croniter accepts

## v1.19.0 - 2021-02-03

## Improvements
- Add tighter parameter checks in hc.front.views.serve_doc
- Update OpsGenie instructions (#450)
- Update the email notification template to include more check and last ping details
- Improve the crontab snippet in the "Check Details" page (#465)
- Add Signal integration (#428)
- Change Zulip onboarding, ask for the zuliprc file (#202)
- Add a section in Docs about running self-hosted instances
- Add experimental Dockerfile and docker-compose.yml
- Add rate limiting for Pushover notifications (6 notifications / user / minute)
- Add support for disabling specific integration types (#471)

## Bug Fixes
- Fix unwanted HTML escaping in SMS and WhatsApp notifications
- Fix a crash when adding an integration for an empty Trello account
- Change icon CSS class prefix to 'ic-' to work around Fanboy's filter list

## v1.18.0 - 2020-12-09

## Improvements
- Add a tooltip to the 'confirmation link' label (#436)
- Update API to allow specifying channels by names (#440)
- When saving a phone number, remove any invisible unicode characers
- Update the read-only dashboard's CSS for better mobile support (#442)
- Reduce the number of SQL queries used in the "Get Checks" API call
- Add support for script's exit status in ping URLs (#429)
- Improve phone number sanitization: remove spaces and hyphens
- Change the "Test Integration" behavior for webhooks: don't retry failed requests
- Add retries to the the email sending logic
- Require confirmation codes (sent to email) before sensitive actions
- Implement WebAuthn two-factor authentication
- Implement badge mode (up/down vs up/late/down) selector (#282)
- Add Ping.exitstatus field, store client's reported exit status values (#455)
- Implement header-based authentication (#457)
- Add a "Lost password?" link with instructions in the Sign In page

## Bug Fixes
- Fix db field overflow when copying a check with a long name

## v1.17.0 - 2020-10-14

## Improvements
- Django 3.1
- Handle status callbacks from Twilio, show delivery failures in Integrations
- Removing unused /api/v1/notifications/{uuid}/bounce endpoint
- Less verbose output in the `senddeletionnotices` command
- Host a read-only dashboard (from github.com/healthchecks/dashboard/)
- LINE Notify integration (#412)
- Read-only team members
- API support for setting the allowed HTTP methods for making ping requests

## Bug Fixes
- Handle excessively long email addresses in the signup form
- Handle excessively long email addresses in the team member invite form
- Don't allow duplicate team memberships
- When copying a check, copy all fields from the "Filtering Rules" dialog (#417)
- Fix missing Resume button (#421)
- When decoding inbound emails, decode encoded headers (#420)
- Escape markdown in MS Teams notifications (#426)
- Set the "title" and "summary" fields in MS Teams notifications (#435)

## v1.16.0 - 2020-08-04

### Improvements
- Paused ping handling can be controlled via API (#376)
- Add "Get a list of checks's logged pings" API call (#371)
- The /api/v1/checks/ endpoint now accepts either UUID or `unique_key` (#370)
- Added /api/v1/checks/uuid/flips/ endpoint (#349)
- In the cron expression dialog, show a human-friendly version of the expression
- Indicate a started check with a progress spinner under status icon (#338)
- Added "Docs > Reliability Tips" page
- Spike.sh integration (#402)
- Updated Discord integration to use discord.com instead of discordapp.com
- Add "Failure Keyword" filtering for inbound emails (#396)
- Add support for multiple, comma-separated keywords (#396)
- New integration: phone calls (#403)

### Bug Fixes
- Removing Pager Team integration, project appears to be discontinued
- Sending a test notification updates Channel.last_error (#391)
- Handle HTTP 429 responses from Matrix server when joining a Matrix room

## v1.15.0 - 2020-06-04

### Improvements
- Rate limiting for Telegram notifications (10 notifications per chat per minute)
- Use Slack V2 OAuth flow
- Users can edit their existing webhook integrations (#176)
- Add a "Transfer Ownership" feature in Project Settings
- In checks list, the pause button asks for confirmation (#356)
- Added /api/v1/metrics/ endpoint, useful for monitoring the service itself
- Added "When paused, ignore pings" option in the Filtering Rules dialog (#369)

### Bug Fixes
- "Get a single check" API call now supports read-only API keys (#346)
- Don't escape HTML in the subject line of notification emails
- Don't let users clone checks if the account is at check limit

## v1.14.0 - 2020-03-23

### Improvements
- Improved UI to invite users from account's other projects (#258)
- Experimental Prometheus metrics endpoint (#300)
- Don't store user's current project in DB, put it explicitly in page URLs (#336)
- API reference in Markdown
- Use Selectize.js for entering tags (#324)
- Zulip integration (#202)
- OpsGenie integration returns more detailed error messages
- Telegram integration returns more detailed error messages
- Added the "Get a single check" API call (#337)
- Display project name in Slack notifications (#342)

### Bug Fixes
- The "render_docs" command checks if markdown and pygments is installed (#329)
- The team size limit is applied to the n. of distinct users across all projects (#332)
- API: don't let SuspiciousOperation bubble up when validating channel ids
- API security: check channel ownership when setting check's channels
- API: update check's "alert_after" field when changing schedule
- API: validate channel identifiers before creating/updating a check (#335)
- Fix redirect after login when adding Telegram integration

## v1.13.0 - 2020-02-13

### Improvements
- Show a red "!" in project's top navigation if any integration is not working
- createsuperuser management command requires an unique email address (#318)
- For superusers, show "Site Administration" in top navigation, note in README (#317)
- Make Ping.body size limit configurable (#301)
- Show sub-second durations with higher precision, 2 digits after decimal point (#321)
- Replace the gear icon with three horizontal dots icon (#322)
- Add a Pause button in the checks list (#312)
- Documentation in Markdown
- Added an example of capturing and submitting log output (#315)
- The sendalerts commands measures dwell time and reports it over statsd protocol
- Django 3.0.3
- Show a warning in top navigation if the project has no integrations (#327)

### Bug Fixes
- Increase the allowable length of Matrix room alias to 100 (#320)
- Make sure Check.last_ping and Ping.created timestamps match exactly
- Don't trigger "down" notifications when changing schedule interactively in web UI
- Fix sendalerts crash loop when encountering a bad cron schedule
- Stricter cron validation, reject schedules like "At midnight of February 31"
- In hc.front.views.ping_details, if a ping does not exist, return a friendly message

## v1.12.0 - 2020-01-02

### Improvements
- Django 3.0
- "Filtering Rules" dialog, an option to require HTTP POST (#297)
- Show Healthchecks version in Django admin header (#306)
- Added JSON endpoint for Shields.io (#304)
- `senddeletionnotices` command skips profiles with recent last_active_date
- The "Update Check" API call can update check's description (#311)

### Bug Fixes
- Don't set CSRF cookie on first visit. Signup is exempt from CSRF protection
- Fix List-Unsubscribe email header value: add angle brackets
- Unsubscribe links serve a form, and require HTTP POST to actually unsubscribe
- For webhook integration, validate each header line separately
- Fix "Send Test Notification" for webhooks that only fire on checks going up
- Don't allow adding webhook integrations with both URLs blank
- Don't allow adding email integrations with both "up" and "down" unchecked


## v1.11.0 - 2019-11-22

### Improvements
- In monthly reports, no downtime stats for the current month (month has just started)
- Add Microsoft Teams integration (#135)
- Add Profile.last_active_date field for more accurate inactive user detection
- Add "Shell Commands" integration (#302)
- PagerDuty integration works with or without PD_VENDOR_KEY (#303)

### Bug Fixes
 - On mobile, "My Checks" page, always show the gear (Details) button (#286)
 - Make log events fit better on mobile screens


## v1.10.0 - 2019-10-21

### Improvements
- Add the "Last Duration" field in the "My Checks" page (#257)
- Add "last_duration" attribute to the Check API resource (#257)
- Upgrade to psycopg2 2.8.3
- Add Go usage example
- Send monthly reports on 1st of every month, not randomly during the month
- Signup form sets the "auto-login" cookie to avoid an extra click during first login
- Autofocus the email field in the signup form, and submit on enter key
- Add support for OpsGenie EU region (#294)
- Update OpsGenie logo and setup illustrations
- Add a "Create a Copy" function for cloning checks (#288)
- Send email notification when monthly SMS sending limit is reached (#292)

### Bug Fixes
- Prevent double-clicking the submit button in signup form
- Upgrade to Django 2.2.6 – fixes sqlite migrations (#284)


## v1.9.0 - 2019-09-03

### Improvements
- Show the number of downtimes and total downtime minutes in monthly reports (#104)
- Show the number of downtimes and total downtime minutes in "Check Details" page
- Add the `pruneflips` management command
- Add Mattermost integration (#276)
- Three choices in timezone switcher (UTC / check's timezone / browser's timezone) (#278)
- After adding a new check redirect to the "Check Details" page

### Bug Fixes
- Fix javascript code to construct correct URLs when running from a subdirectory (#273)
- Don't show the "Sign Up" link in the login page if registration is closed (#280)

## v1.8.0 - 2019-07-08

### Improvements
- Add the `prunetokenbucket` management command
- Show check counts in JSON "badges" (#251)
- Webhooks support HTTP PUT (#249)
- Webhooks can use different req. bodies and headers for "up" and "down" events (#249)
- Show check's code instead of full URL on 992px - 1200px wide screens (#253)
- Add WhatsApp integration (uses Twilio same as the SMS integration)
- Webhooks support the $TAGS placeholder
- Don't include ping URLs in API responses when the read-only key is used

### Bug Fixes
- Fix badges for tags containing special characters (#240, #237)
- Fix the "Integrations" page for when the user has no active project
- Prevent email clients from opening the one-time login links (#255)
- Fix `prunepings` and `prunepingsslow`, they got broken when adding Projects (#264)


## v1.7.0 - 2019-05-02

### Improvements
- Add the EMAIL_USE_VERIFICATION configuration setting (#232)
- Show "Badges" and "Settings" in top navigation (#234)
- Upgrade to Django 2.2
- Can configure the email integration to only report the "down" events (#231)
- Add "Test!" function in the Integrations page (#207)
- Rate limiting for the log in attempts
- Password strength meter and length check in the "Set Password" form
- Show the Description section even if the description is missing. (#246)
- Include the description in email alerts. (#247)


## v1.6.0 - 2019-04-01

### Improvements
- Add the "desc" field (check's description) to API responses
- Add maxlength attribute to HTML input=text elements
- Improved logic for displaying job execution times in log (#219)
- Add Matrix integration
- Add Pager Team integration
- Add a management command for sending inactive account notifications

### Bug Fixes
- Fix refreshing of the checks page filtered by tags (#221)
- Escape asterisks in Slack messages (#223)
- Fix a "invalid time format" in front.views.status_single on Windows hosts


## v1.5.0 - 2019-02-04

### Improvements
- Database schema: add uniqueness constraint to Check.code
- Database schema: add Ping.kind field. Remove "start" and "fail" fields
- Add "Email Settings..." dialog and "Subject Must Contain" setting
- Database schema: add the Project model
- Move project-specific settings to a new "Project Settings" page
- Add a "Transfer to Another Project..." dialog
- Add the "My Projects" page


## v1.4.0 - 2018-12-25

### Improvements
- Set Pushover alert priorities for "down" and "up" events separately
- Additional python usage examples
- Allow simultaneous access to checks from different teams
- Add CORS support to API endpoints
- Flip model, for tracking status changes of the Check objects
- Add `/ping/<code>/start` API endpoint
- When using the `/start` endpoint, show elapsed times in ping log

### Bug Fixes
- Fix after-login redirects (the "?next=" query parameter)
- Update Check.status field when user edits timeout & grace settings
- Use timezone-aware datetimes with croniter, avoid ambiguities around DST
- Validate and reject cron schedules with six components


## v1.3.0 - 2018-11-21

### Improvements
- Load settings from environment variables
- Add "List-Unsubscribe" header to alert and report emails
- Don't send monthly reports to inactive accounts (no pings in 6 months)
- Add search box in the "My Checks" page
- Add read-only API key support
- Remove Profile.bill_to field (obsolete)
- Show a warning when running with DEBUG=True
- Add "channels" attribute to the Check API resource
- Can specify channel codes when updating a check via API
- Add a workaround for email agents automatically opening "Unsubscribe" links
- Add Channel.name field, users can now name integrations
- Add "Get a List of Existing Integrations" API call

### Bug Fixes
- During DST transition, handle ambiguous dates as pre-transition


## v1.2.0 - 2018-10-20

### Improvements
- Content updates in the "Welcome" page.
- Added "Docs > Third-Party Resources" page.
- Improved  layout and styling in "Login" page.
- Separate "Sign Up" and "Log In" forms.
- "My Checks" page: support filtering checks by query string parameters.
- Added Trello integration

### Bug Fixes
- Timezones were missing in the "Change Schedule" dialog, fixed.
- Fix hamburger menu button in "Login" page.


## v1.1.0 - 2018-08-20

### Improvements
- A new "Check Details" page.
- Updated django-compressor, psycopg2, pytz, requests package versions.
- C# usage example.
- Checks have a "Description" field.
