# Changelog
All notable changes to this project will be documented in this file.

## Unreleased

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
- Added a workaround for email agents automatically opening "Unsubscribe" links

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