from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from django.utils.timezone import now


class Unit(object):
    def __init__(self, name: str, nsecs: int):
        self.name = name
        self.plural = name + "s"
        self.nsecs = nsecs


SECOND = Unit("second", 1)
MINUTE = Unit("minute", 60)
HOUR = Unit("hour", MINUTE.nsecs * 60)
DAY = Unit("day", HOUR.nsecs * 24)
WEEK = Unit("week", DAY.nsecs * 7)


def format_duration(duration: timedelta) -> str:
    remaining_seconds = int(duration.total_seconds())

    result = []

    for unit in (WEEK, DAY, HOUR, MINUTE):
        if unit == WEEK and remaining_seconds % unit.nsecs != 0:
            # Say "8 days" instead of "1 week 1 day"
            continue

        v, remaining_seconds = divmod(remaining_seconds, unit.nsecs)
        if v == 1:
            result.append("1 %s" % unit.name)
        elif v > 1:
            result.append("%d %s" % (v, unit.plural))

    return " ".join(result)


def format_hms(duration: timedelta) -> str:
    total_seconds = duration.total_seconds()
    if 0.01 <= total_seconds < 1:
        return "%.2f sec" % total_seconds

    total_seconds = int(total_seconds)
    result = []

    mins, secs = divmod(total_seconds, 60)
    h, mins = divmod(mins, 60)

    if h:
        result.append("%d h" % h)

    if h or mins:
        result.append("%d min" % mins)

    result.append("%s sec" % secs)

    return " ".join(result)


def format_approx_duration(duration: timedelta) -> str:
    total_seconds = int(duration.total_seconds())

    mins, secs = divmod(total_seconds, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)

    if days == 1:
        return f"1 day {hours} h"

    if days:
        return f"{days} days {hours} h"

    if hours:
        return f"{hours} h {mins} min"

    return f"{mins} min {secs} sec"


def month_boundaries(months: int, tzstr: str) -> list[datetime]:
    """Return month start times in descending order starting from the current month."""
    tz = ZoneInfo(tzstr)
    result: list[datetime] = []

    now_value = now().astimezone(tz)
    y, m = now_value.year, now_value.month
    for x in range(0, months):
        result.append(datetime(y, m, 1, tzinfo=tz))

        m -= 1
        if m == 0:
            m = 12
            y = y - 1

    return result


def week_boundaries(weeks: int, tzstr: str) -> list[datetime]:
    """Return week start times in descending order starting from the current week."""
    tz = ZoneInfo(tzstr)
    result: list[datetime] = []

    today = now().astimezone(tz).date()
    needle = today - timedelta(days=today.weekday())
    for x in range(0, weeks):
        result.append(datetime(needle.year, needle.month, needle.day, tzinfo=tz))
        needle -= timedelta(days=7)

    return result


def seconds_in_month(d: date, tzstr: str) -> float:
    tz = ZoneInfo(tzstr)
    start = datetime(d.year, d.month, 1, tzinfo=tz)
    start_utc = start.astimezone(timezone.utc)

    y, m = d.year, d.month
    m += 1
    if m > 12:
        y += 1
        m = 1

    end = datetime(y, m, 1, tzinfo=tz)
    end_utc = end.astimezone(timezone.utc)
    return (end_utc - start_utc).total_seconds()
