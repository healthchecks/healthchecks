# Changelog
All notable changes to this project will be documented in this file.

## 1.9.0 - 2019-09-03

### Improvements
- Show the number of downtimes and total downtime minutes in monthly reports (#104)
- Show the number of downtimes and total downtime minutes in "Check Details" page
- Add the `pruneflips` management command
- Add Mattermost integration (#276)
- Three choices in timezone switcher (UTC / check's timezone / browser's timezone) (#278)
- After adding a new check redirect to the "Check Details" page

## Bug Fixes
- Fix javascript code to construct correct URLs when running from a subdirectory (#273)
- Don't show the "Sign Up" link in the login page if registration is closed (#280)

## 1.8.0 - 2019-07-08

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


## 1.7.0 - 2019-05-02

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

## 1.6.0 - 2019-04-01

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


## 1.5.0 - 2019-02-04

### Improvements
- Database schema: add uniqueness constraint to Check.code
- Database schema: add Ping.kind field. Remove "start" and "fail" fields
- Add "Email Settings..." dialog and "Subject Must Contain" setting
- Database schema: add the Project model
- Move project-specific settings to a new "Project Settings" page
- Add a "Transfer to Another Project..." dialog
- Add the "My Projects" page


## 1.4.0 - 2018-12-25

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


## 1.3.0 - 2018-11-21

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


## 1.2.0 - 2018-10-20

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


## 1.1.0 - 2018-08-20

### Improvements
- A new "Check Details" page.
- Updated django-compressor, psycopg2, pytz, requests package versions.
- C# usage example.
- Checks have a "Description" field.
