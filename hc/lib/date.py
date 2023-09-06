from __future__ import annotations

from datetime import datetime, timedelta
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
    v = duration.total_seconds()
    for unit in (DAY, HOUR, MINUTE, SECOND):
        if v >= unit.nsecs:
            vv = v // unit.nsecs
            if vv == 1:
                return f"1 {unit.name}"
            else:
                return f"{vv} {unit.plural}"

    return ""


def month_boundaries(months: int, tzstr: str) -> list[datetime]:
    tz = ZoneInfo(tzstr)
    result: list[datetime] = []

    now_value = now().astimezone(tz)
    y, m = now_value.year, now_value.month
    for x in range(0, months):
        result.insert(0, datetime(y, m, 1, tzinfo=tz))

        m -= 1
        if m == 0:
            m = 12
            y = y - 1

    return result


def week_boundaries(weeks: int, tzstr: str) -> list[datetime]:
    tz = ZoneInfo(tzstr)
    result: list[datetime] = []

    today = now().astimezone(tz).date()
    needle = today - timedelta(days=today.weekday())
    for x in range(0, weeks):
        result.insert(0, datetime(needle.year, needle.month, needle.day, tzinfo=tz))
        needle -= timedelta(days=7)

    return result
