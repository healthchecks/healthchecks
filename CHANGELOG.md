# Changelog
All notable changes to this project will be documented in this file.

## v2.3 - 2022-08-05

### Improvements
- Update Dockerfile to start SMTP listener (#668)
- Implement the "Add Check" dialog
- Include last ping type in Slack, Mattermost, Discord notifications
- Upgrade to cron-descriptor 1.2.30
- Add "Filter by keywords in the message body" feature (#653)
- Upgrade to HiDPI screenshots in the documentation
- Add support for the $JSON placeholder in webhook payloads
- Add ping endpoints for "log" events
- Add the "Badges" page in docs
- Add support for multiple recipients in incoming email (#669)
- Upgrade to fido2 1.0.0, requests 2.28.1, segno 1.5.2
- Implement auto-refresh and running indicator in the My Projects page (#681)
- Upgrade to Django 4.1 and django-compressor 4.1
- Add API support for resuming paused checks (#687)

### Bug Fixes
- Fix the display of ignored pings with non-zero exit status
- Fix a race condition in the "Change Email" flow
- Fix grouping and sorting in the text version of the report/nag emails (#679)
- Fix the update_timeout and pause views to create flips (for downtime bookkeeping)
- Fix the checks list to preserve selected filters when adding/updating checks (#684)
- Fix duration calculation to skip "log" and "ign" events

## v2.2.1 - 2022-06-13

### Improvements
- Improve the text version of the alert email template

### Bug Fixes
- Fix the version number displayed in the footer

## v2.2 - 2022-06-13

### Improvements
- Add address verification step in the "Change Email" flow
- Reduce logging output from sendalerts and sendreports management commands (#656)
- Add Ctrl+C handler in sendalerts and sendreports management commands
- Add notes in docs about configuring uWSGI via UWSGI_ env vars (#656)
- Implement login link expiration (login links will now expire in 1 hour)
- Add Gotify integration (#270)
- Add API support for reading/writing the subject and subject_fail fields (#659)
- Add "Disabled" priority for Pushover notifications (#663)

### Bug Fixes
- Update hc.front.views.channels to handle empty strings in settings (#635)
- Add logic to handle ContentDecodingError exceptions

## v2.1 - 2022-05-10

### Improvements
- Add logic to alert ADMINS when Signal transport hits a CAPTCHA challenge
- Implement the "started" progress spinner in the details pages
- Add "hc_check_started" metric in the Prometheus metrics endpoint (#630)
- Add a management command for submitting Signal rate limit challenges
- Upgrade to django-compressor 4.0
- Update the C# snippet
- Increase max displayed duration from 24h to 72h (#644)
- Add "Ping-Body-Limit" response header in ping API responses

### Bug Fixes
- Fix unwanted localization in badge SVG generation (#629)
- Update email template to handle not yet uploaded ping bodies
- Add small delay in transports.Email.notify to allow ping body to upload
- Fix prunenotifications to handle checks with missing pings (#636)
- Fix "Send Test Notification" for integrations that only send "up" notifications

## v2.0.1 - 2022-03-18

### Bug Fixes
- Fix the GHA workflow for building arm/v7 docker image

## v2.0 - 2022-03-18

This release contains a backwards-incompatible change to the Signal integration
(hence the major version number bump). Healthchecks uses signal-cli to deliver
Signal notifications. In the past versions, Healthchecks interfaced with
signal-cli over DBus. Starting from this version, Healthchecks interfaces
with signal-cli using JSON RPC. Please see README for details on how to set
this up.

### Improvements
- Update Telegram integration to treat "group chat was deleted" as permanent error
- Update email bounce handler to mark email channels as disabled (#446)
- Update Signal integration to use JSON RPC over UNIX socket
- Update the "Add TOTP" form to display plaintext TOTP secret (#602)
- Improve PagerDuty notifications
- Add Ping.body_raw field for storing body as bytes
- Add support for storing ping bodies in S3-compatible object storage (#609)
- Add a "Download Original" link in the "Ping Details" dialog

### Bug Fixes
- Fix unwanted special character escaping in notification messages (#606)
- Fix JS error after copying a code snippet
- Make email non-editable in the "Invite Member" dialog when team limit reached
- Fix Telegram bot to handle TransportError exceptions
- Fix Signal integration to handle UNREGISTERED_FAILURE errors
- Fix unwanted localization of period and grace values in data- attributes (#617)
- Fix Mattermost integration to treat 404 as a transient error (#613)

## v1.25.0 - 2022-01-07

### Improvements
- Implement Pushover emergency alert cancellation when check goes up
- Add "The following checks are also down" section in Telegram notifications
- Add "The following checks are also down" section in Signal notifications
- Upgrade to django-compressor 3.0
- Add support for Telegram channels (#592)
- Implement Telegram group to supergroup migration (#132)
- Update the Slack integration to not retry when Slack returns 404
- Refactor transport classes to raise exceptions on delivery problems
- Add Channel.disabled field, for disabling integrations on permanent errors
- Upgrade to Django 4
- Bump the min. Python version from 3.6 to 3.8 (as required by Django 4)

### Bug Fixes
- Fix report templates to not show the "started" status (show UP or DOWN instead)
- Update Dockerfile to avoid running "pip wheel" more than once (#594)

## v1.24.1 - 2021-11-10

### Bug Fixes
- Fix Dockerfile for arm/v7 - install all dependencies from piwheels

## v1.24.0 - 2021-11-10

### Improvements
- Switch from croniter to cronsim
- Change outgoing webhook timeout to 10s, but cap the total time to 20s
- Implement automatic `api_ping` and `api_notification` pruning (#556)
- Update Dockerfile to install apprise (#581)
- Improve period and grace controls, allow up to 365 day periods (#281)
- Add SIGTERM handling in sendalerts and sendreports
- Remove the "welcome" landing page, direct users to the sign in form instead

### Bug Fixes
- Fix hc.api.views.ping to handle non-utf8 data in request body (#574)
- Fix a crash when hc.api.views.pause receives a single integer in request body

## v1.23.1 - 2021-10-13

### Bug Fixes
- Fix missing uwsgi dependencies in arm/v7 Docker image

## v1.23.0 - 2021-10-13

### Improvements
- Add /api/v1/badges/ endpoint (#552)
- Add ability to edit existing email, Signal, SMS, WhatsApp integrations
- Add new ping URL format: /{ping_key}/{slug} (#491)
- Reduce Docker image size by using slim base image and multi-stage Dockerfile
- Upgrade to Bootstrap 3.4.1
- Upgrade to jQuery 3.6.0

### Bug Fixes
- Add handling for non-latin-1 characters in webhook headers
- Fix dark mode bug in selectpicker widgets
- Fix a crash during login when user's profile does not exist (#77)
- Drop API support for GET, DELETE requests with a request body
- Add missing @csrf_exempt annotations in API views
- Fix the ping handler to reject status codes > 255
- Add 'schemaVersion' field in the shields.io endpoint (#566)

## v1.22.0 - 2021-08-06

### Improvements
- Use multicolor channel icons for better appearance in the dark mode
- Add SITE_LOGO_URL setting (#323)
- Add admin action to log in as any user
- Add a "Manager" role (#484)
- Add support for 2FA using TOTP (#354)
- Add Whitenoise (#548)

### Bug Fixes
- Fix dark mode styling issues in Cron Syntax Cheatsheet
- Fix a 403 when transferring a project to a read-only team member
- Security: fix allow_redirect function to reject absolute URLs

## v1.21.0 - 2021-07-02

### Improvements
- Increase "Success / Failure Keywords" field lengths to 200
- Django 3.2.4
- Improve the handling of unknown email addresses in the Sign In form
- Add support for "... is UP" SMS notifications
- Add an option for weekly reports (in addition to monthly)
- Implement PagerDuty Simple Install Flow, remove PD Connect
- Implement dark mode

### Bug Fixes
- Fix off-by-one-month error in monthly reports, downtime columns (#539)

## v1.20.0 - 2021-04-22

### Improvements
- Django 3.2
- Rename VictorOps -> Splunk On-Call
- Implement email body decoding in the "Ping Details" dialog
- Add a "Subject" field in the "Ping Details" dialog
- Improve HTML email display in the "Ping Details" dialog
- Add a link to check's details page in Slack notifications
- Replace details_url with cloaked_url in email and chat notifications
- In the "My Projects" page, show projects with failing checks first

### Bug Fixes
- Fix downtime summary to handle months when the check didn't exist yet (#472)
- Relax cron expression validation: accept all expressions that croniter accepts
- Fix sendalerts to clear Profile.next_nag_date if all checks up
- Fix the pause action to clear Profile.next_nag_date if all checks up
- Fix the "Email Reports" screen to clear Profile.next_nag_date if all checks up
- Fix the month boundary calculation in monthly reports (#497)

## v1.19.0 - 2021-02-03

### Improvements
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

### Bug Fixes
- Fix unwanted HTML escaping in SMS and WhatsApp notifications
- Fix a crash when adding an integration for an empty Trello account
- Change icon CSS class prefix to 'ic-' to work around Fanboy's filter list

## v1.18.0 - 2020-12-09

### Improvements
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

### Bug Fixes
- Fix db field overflow when copying a check with a long name

## v1.17.0 - 2020-10-14

### Improvements
- Django 3.1
- Handle status callbacks from Twilio, show delivery failures in Integrations
- Removing unused /api/v1/notifications/{uuid}/bounce endpoint
- Less verbose output in the `senddeletionnotices` command
- Host a read-only dashboard (from github.com/healthchecks/dashboard/)
- LINE Notify integration (#412)
- Read-only team members
- API support for setting the allowed HTTP methods for making ping requests

### Bug Fixes
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
