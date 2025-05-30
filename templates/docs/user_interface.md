# User Interface Features

SITE_NAME provides several user interface features to customize your monitoring experience and make it easier to view and manage your checks.

## Time Zone Display Settings

When viewing event logs and ping details for your checks, SITE_NAME can display timestamps in different time zones. You can configure your preferred default time zone selection in your account's appearance settings.

### Default Time Zone Selection

In your account settings under "Appearance," you can set a default time zone preference for event logs:

* **Default**: Uses the system's default behavior (UTC for simple checks, check's time zone for cron/OnCalendar checks)
* **UTC**: Always display event timestamps in UTC
* **Check's time zone**: Always display timestamps in the check's configured time zone
* **Browser's time zone**: Always display timestamps in your browser's local time zone

This setting affects how timestamps are displayed when you view:
* Check event logs and ping history
* Ping details dialogs
* Event summaries

### Time Zone Button Deduplication

When viewing event logs, SITE_NAME displays time zone buttons that allow you to switch between different time zone views. To improve the user interface, SITE_NAME automatically deduplicates these buttons when they would show identical times.

For example, if you're viewing events during a period when your check's time zone (e.g., "America/New_York") has the same UTC offset as UTC itself, SITE_NAME will show only one button instead of two identical ones. The system intelligently merges buttons that would display the same timestamp, keeping the one with the highest priority:

1. **Check's time zone** (highest priority) - for cron and OnCalendar checks
2. **UTC** (medium priority) - universal reference time  
3. **Browser's time zone** (lowest priority) - local display

This deduplication makes the interface cleaner and less confusing while preserving all the functionality you need.

## Account Settings Organization

Your account settings are organized into separate sections for easy navigation:

* **Theme Settings**: Choose between light, dark, or system theme
* **Time Zone Display**: Configure default time zone preferences for event logs
* **Email Reports**: Set up periodic email summaries and notifications
* **Two-Factor Authentication**: Manage security keys and TOTP settings

Settings changes are automatically saved and take effect immediately throughout the interface.