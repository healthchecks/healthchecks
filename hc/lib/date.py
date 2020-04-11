from datetime import datetime as dt
from random import randint
from django.utils import timezone


class Unit(object):
    def __init__(self, name, nsecs):
        self.name = name
        self.plural = name + "s"
        self.nsecs = nsecs


SECOND = Unit("second", 1)
MINUTE = Unit("minute", 60)
HOUR = Unit("hour", MINUTE.nsecs * 60)
DAY = Unit("day", HOUR.nsecs * 24)
WEEK = Unit("week", DAY.nsecs * 7)


def format_duration(td):
    remaining_seconds = int(td.total_seconds())

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


def format_hms(td):
    total_seconds = td.total_seconds()
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


def format_approx_duration(td):
    v = td.total_seconds()
    for unit in (DAY, HOUR, MINUTE, SECOND):
        if v >= unit.nsecs:
            vv = v // unit.nsecs
            if vv == 1:
                return "1 %s" % unit.name
            else:
                return "%d %s" % (vv, unit.plural)

    return ""


def month_boundaries(months=3):
    result = []

    now = timezone.now()
    y, m = now.year, now.month
    for x in range(0, months):
        result.insert(0, dt(y, m, 1, tzinfo=timezone.utc))

        m -= 1
        if m == 0:
            m = 12
            y = y - 1

    return result


def choose_next_report_date(now=None):
    """ Calculate the target date for the next monthly report.

    Monthly reports should get sent on 1st of each month, at a random
    time after 12PM UTC (so it's over the month boundary even in UTC-12).

    """

    if now is None:
        now = timezone.now()

    h, m, s = randint(12, 23), randint(0, 59), randint(0, 59)

    if now.month == 12:
        return now.replace(now.year + 1, 1, 1, h, m, s)
    else:
        return now.replace(now.year, now.month + 1, 1, h, m, s)
