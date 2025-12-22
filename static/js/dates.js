class DateFormatter {
    constructor(tz) {
        this.yearFmt = null;
        this.dateFmt = null;
        this.dateYearFmt = null;
        this.timeFmt = null;
        this.timestampFmt = null;
        this.currentYear = null;
        if (tz) {
            this.setTimezone(tz);
        }
    }

    setTimezone(tz) {
        this.yearFmt = new Intl.DateTimeFormat("en-US", {year: "numeric", timeZone: tz});
        this.dateFmt = new Intl.DateTimeFormat("en-US", {month: "short", day: "numeric", timeZone: tz});
        this.dateYearFmt = new Intl.DateTimeFormat("en-US", {month: "short", day: "numeric", year: "numeric", timeZone: tz});
        this.timeFmt = new Intl.DateTimeFormat("en-GB", {hour: "numeric", minute: "numeric", timeZone: tz});

        var tsOptions = {
            weekday: "short",
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "numeric",
            minute: "numeric",
            timeZoneName: "short",
            timeZone: tz
        }
        this.timestampFmt = new Intl.DateTimeFormat("en-GB", tsOptions);
        // Don't use getFullYear() because we want the year *in the specified timezone*
        this.currentYear = this.yearFmt.format();
    }

    // "12:34"
    formatTime(dt) {
        return this.timeFmt.format(dt);
    }

    // "Jan 15" or "Jan 15, 2025"
    formatDate(dt, requireYear) {
        if (requireYear || this.yearFmt.format(dt) != this.currentYear) {
            return this.dateYearFmt.format(dt);
        }

        return this.dateFmt.format(dt);
    }

    // "Jan 15, 12:34" or "Jan 15, 2025, 12:34"
    formatDateTime(dt) {
        return this.formatDate(dt) + ", " + this.formatTime(dt);
    }

    // "Wed, 15 Jan 2025, 12:34 EET"
    formatTimestamp(dt) {
        return this.timestampFmt.format(dt);
    }

}
