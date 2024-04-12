from __future__ import annotations

import hashlib
import json
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from typing import Any, TypedDict
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from cronsim import CronSim
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import mail_admins
from django.core.signing import TimestampSigner
from django.db import models, transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import now
from oncalendar import OnCalendar
from pydantic import BaseModel, Field

from hc.accounts.models import Project
from hc.api import transports
from hc.lib import emails
from hc.lib.date import month_boundaries, seconds_in_month
from hc.lib.s3 import get_object, put_object, remove_objects

STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"), ("paused", "Paused"))
DEFAULT_TIMEOUT = td(days=1)
DEFAULT_GRACE = td(hours=1)
NEVER = datetime(3000, 1, 1, tzinfo=timezone.utc)
CHECK_KINDS = (("simple", "Simple"), ("cron", "Cron"), ("oncalendar", "OnCalendar"))
# max time between start and ping where we will consider both events related:
MAX_DURATION = td(hours=72)

TRANSPORTS: dict[str, tuple[str, type[transports.Transport]]] = {
    "apprise": ("Apprise", transports.Apprise),
    "call": ("Phone Call", transports.Call),
    "discord": ("Discord", transports.Discord),
    "email": ("Email", transports.Email),
    "gotify": ("Gotify", transports.Gotify),
    "group": ("Group", transports.Group),
    "hipchat": ("HipChat", transports.RemovedTransport),
    "linenotify": ("LINE Notify", transports.LineNotify),
    "matrix": ("Matrix", transports.Matrix),
    "mattermost": ("Mattermost", transports.Mattermost),
    "msteams": ("Microsoft Teams", transports.MsTeams),
    "ntfy": ("ntfy", transports.Ntfy),
    "opsgenie": ("Opsgenie", transports.Opsgenie),
    "pagerteam": ("Pager Team", transports.RemovedTransport),
    "pagertree": ("PagerTree", transports.PagerTree),
    "pd": ("PagerDuty", transports.PagerDuty),
    "po": ("Pushover", transports.Pushover),
    "pushbullet": ("Pushbullet", transports.Pushbullet),
    "rocketchat": ("Rocket.Chat", transports.RocketChat),
    "shell": ("Shell Command", transports.Shell),
    "signal": ("Signal", transports.Signal),
    "slack": ("Slack", transports.Slack),
    "sms": ("SMS", transports.Sms),
    "spike": ("Spike", transports.Spike),
    "telegram": ("Telegram", transports.Telegram),
    "trello": ("Trello", transports.Trello),
    "victorops": ("Splunk On-Call", transports.VictorOps),
    "webhook": ("Webhook", transports.Webhook),
    "whatsapp": ("WhatsApp", transports.WhatsApp),
    "zendesk": ("Zendesk", transports.RemovedTransport),
    "zulip": ("Zulip", transports.Zulip),
}


CHANNEL_KINDS = [(kind, label_cls[0]) for kind, label_cls in TRANSPORTS.items()]

PO_PRIORITIES = {
    -3: "disabled",
    -2: "lowest",
    -1: "low",
    0: "normal",
    1: "high",
    2: "emergency",
}

NTFY_PRIORITIES = {
    5: "max",
    4: "high",
    3: "default",
    2: "low",
    1: "min",
    0: "disabled",
}


def isostring(dt: datetime | None) -> str | None:
    """Convert the datetime to ISO 8601 format with no microseconds."""
    return dt.replace(microsecond=0).isoformat() if dt else None


class CheckDict(TypedDict, total=False):
    name: str
    slug: str
    tags: str
    desc: str
    grace: int
    n_pings: int
    status: str
    started: bool
    last_ping: str | None
    next_ping: str | None
    manual_resume: bool
    methods: str
    subject: str
    subject_fail: str
    start_kw: str
    success_kw: str
    failure_kw: str
    filter_subject: bool
    filter_body: bool
    last_duration: int
    unique_key: str
    ping_url: str
    update_url: str
    pause_url: str
    resume_url: str
    channels: str
    timeout: int
    schedule: str
    tz: str


@dataclass
class DowntimeRecord:
    boundary: datetime  # The start of this time interval (timezone-aware)
    tz: str  # For calculating total seconds in a month
    no_data: bool  # True if the check did not yet exist in this time interval
    duration: td  # Total downtime in this time interval
    count: int  # The number of downtime events in this time interval

    def monthly_uptime(self) -> float:
        # NB: this method assumes monthly boundaries.
        # It will yield incorrect results for weekly boundaries
        max_seconds = seconds_in_month(self.boundary.date(), self.tz)
        up_seconds = max_seconds - self.duration.total_seconds()
        return up_seconds / max_seconds


class DowntimeRecorder(object):
    def __init__(self, boundaries: list[datetime], tz: str, created: datetime) -> None:
        """
        `boundaries` is a list of timezone-aware datetimes of the starts of time
        intervals (months or weeks), and should be pre-sorted in descending order.
        """
        self.records = []
        prev_boundary = None
        for b in boundaries:
            # If the check was created *after* the start of the previous time
            # interval then the check did not yet exist during this time interval:
            no_data = prev_boundary is not None and created > prev_boundary
            self.records.append(DowntimeRecord(b, tz, no_data, td(), 0))
            prev_boundary = b

    def add(self, when: datetime, duration: td) -> None:
        for record in self.records:
            if when >= record.boundary:
                record.duration += duration
                record.count += 1
                return


class Check(models.Model):
    name = models.CharField(max_length=100, blank=True)
    slug = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=500, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    desc = models.TextField(blank=True)
    project = models.ForeignKey(Project, models.CASCADE)
    created = models.DateTimeField(default=now)
    kind = models.CharField(max_length=10, default="simple", choices=CHECK_KINDS)
    timeout = models.DurationField(default=DEFAULT_TIMEOUT)
    grace = models.DurationField(default=DEFAULT_GRACE)
    schedule = models.CharField(max_length=100, default="* * * * *")
    tz = models.CharField(max_length=36, default="UTC")
    filter_subject = models.BooleanField(default=False)
    filter_body = models.BooleanField(default=False)
    start_kw = models.CharField(max_length=200, blank=True)
    success_kw = models.CharField(max_length=200, blank=True)
    failure_kw = models.CharField(max_length=200, blank=True)
    methods = models.CharField(max_length=30, blank=True)
    manual_resume = models.BooleanField(default=False)
    badge_key = models.UUIDField(null=True, unique=True)

    n_pings = models.IntegerField(default=0)
    last_ping = models.DateTimeField(null=True, blank=True)
    last_start = models.DateTimeField(null=True, blank=True)
    last_start_rid = models.UUIDField(null=True)
    last_duration = models.DurationField(null=True, blank=True)
    has_confirmation_link = models.BooleanField(default=False)
    alert_after = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=6, choices=STATUSES, default="new")

    class Meta:
        indexes = [
            # Index for the alert_after field. Exclude rows with status=down.
            # Used in the sendalerts management command.
            models.Index(
                fields=["alert_after"],
                name="api_check_aa_not_down",
                condition=~models.Q(status="down"),
            ),
            models.Index(fields=["project_id", "slug"], name="api_check_project_slug"),
        ]

    def __str__(self) -> str:
        return "%s (%d)" % (self.name or self.code, self.id)

    def name_then_code(self) -> str:
        if self.name:
            return self.name

        return str(self.code)

    def url(self) -> str | None:
        """Return check's ping url in user's preferred style.

        Note: this method reads self.project. If project is not loaded already,
        this causes a SQL query.

        """

        if self.project_id and self.project.show_slugs:
            if not self.slug:
                return None

            # If ping_key is not set, use dummy placeholder
            key = self.project.ping_key or "{ping_key}"
            return settings.PING_ENDPOINT + key + "/" + self.slug

        return settings.PING_ENDPOINT + str(self.code)

    def details_url(self, full: bool = True) -> str:
        result = reverse("hc-details", args=[self.code])
        return settings.SITE_ROOT + result if full else result

    def get_absolute_url(self) -> str:
        return self.details_url(full=False)

    def cloaked_url(self) -> str:
        return settings.SITE_ROOT + reverse("hc-uncloak", args=[self.unique_key])

    def email(self) -> str:
        return "%s@%s" % (self.code, settings.PING_EMAIL_DOMAIN)

    def clamped_last_duration(self) -> td | None:
        if self.last_duration and self.last_duration < MAX_DURATION:
            return self.last_duration
        return None

    def get_grace_start(self, *, with_started: bool = True) -> datetime | None:
        """Return the datetime when the grace period starts.

        If the check is currently new, paused or down, return None.
        """
        # NEVER is a constant sentinel value (year 3000).
        # Using None instead would make the min() logic clunky.
        result = NEVER

        if self.kind == "simple" and self.status == "up":
            assert self.last_ping is not None
            result = self.last_ping + self.timeout
        elif self.kind == "cron" and self.status == "up":
            assert self.last_ping is not None
            # The complex case, next ping is expected based on cron schedule.
            # Don't convert to naive datetimes (and so avoid ambiguities around
            # DST transitions). cronsim will handle the timezone-aware datetimes.
            last_local = self.last_ping.astimezone(ZoneInfo(self.tz))
            result = next(CronSim(self.schedule, last_local))
            # Important: convert from the local timezone back to UTC.
            # If the result is kept in the local timezone, adding
            # a timedelta to it later (in `going_down_after` and in `get_status`)
            # may yield incorrect results during DST transitions.
            result = result.astimezone(timezone.utc)
        elif self.kind == "oncalendar" and self.status == "up":
            assert self.last_ping is not None
            last_local = self.last_ping.astimezone(ZoneInfo(self.tz))
            try:
                result = next(OnCalendar(self.schedule, last_local))
                # Same as for cron, convert back to UTC:
                result = result.astimezone(timezone.utc)
            except StopIteration:
                result = NEVER

        if with_started and self.last_start and self.status != "down":
            result = min(result, self.last_start)

        return result if result != NEVER else None

    def going_down_after(self) -> datetime | None:
        """Return the datetime when the check goes down.

        If the check is new or paused, and not currently running, return None.
        If the check is already down, also return None.
        """
        grace_start = self.get_grace_start()
        if grace_start is not None:
            return grace_start + self.grace

        return None

    def get_status(self, *, with_started: bool = False) -> str:
        """Return current status for display."""
        frozen_now = now()

        if self.last_start:
            if frozen_now >= self.last_start + self.grace:
                return "down"
            elif with_started:
                return "started"

        if self.status in ("new", "paused", "down"):
            return self.status

        grace_start = self.get_grace_start(with_started=False)
        if grace_start is None:
            # next elapse is "never", so this check will stay up indefinitely
            return "up"

        grace_end = grace_start + self.grace
        if frozen_now >= grace_end:
            return "down"

        if frozen_now >= grace_start:
            return "grace"

        return "up"

    def lock_and_delete(self) -> None:
        """Acquire a DB lock for this check, then delete the check.

        Without the lock the delete can fail, if the check gets pinged while it is
        in the process of deletion.
        """
        with transaction.atomic():
            Check.objects.select_for_update().get(id=self.id).delete()

    def assign_all_channels(self) -> None:
        channels = Channel.objects.filter(project=self.project)
        self.channel_set.set(channels)

    def tags_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(" ") if t.strip()]

    def matches_tag_set(self, tag_set: set[str]) -> bool:
        return tag_set.issubset(self.tags_list())

    def channels_str(self) -> str:
        """Return a comma-separated string of assigned channel codes."""

        # Is this an unsaved instance?
        if not self.id:
            return ""

        # self.channel_set may already be prefetched.
        # Sort in python to make sure we don't run additional queries
        codes = [str(channel.code) for channel in self.channel_set.all()]
        return ",".join(sorted(codes))

    @property
    def unique_key(self) -> str:
        code_half = self.code.hex[:16]
        return hashlib.sha1(code_half.encode()).hexdigest()

    def prepare_badge_key(self) -> uuid.UUID:
        if not self.badge_key:
            self.badge_key = uuid.uuid4()
            Check.objects.filter(id=self.id).update(badge_key=self.badge_key)
        return self.badge_key

    def to_dict(self, *, readonly: bool = False, v: int = 3) -> CheckDict:
        with_started = v == 1
        result: CheckDict = {
            "name": self.name,
            "slug": self.slug,
            "tags": self.tags,
            "desc": self.desc,
            "grace": int(self.grace.total_seconds()),
            "n_pings": self.n_pings,
            "status": self.get_status(with_started=with_started),
            "started": self.last_start is not None,
            "last_ping": isostring(self.last_ping),
            "next_ping": isostring(self.get_grace_start()),
            "manual_resume": self.manual_resume,
            "methods": self.methods,
            "subject": self.success_kw if self.filter_subject else "",
            "subject_fail": self.failure_kw if self.filter_subject else "",
            "start_kw": self.start_kw,
            "success_kw": self.success_kw,
            "failure_kw": self.failure_kw,
            "filter_subject": self.filter_subject,
            "filter_body": self.filter_body,
        }

        if self.last_duration:
            result["last_duration"] = int(self.last_duration.total_seconds())

        if readonly:
            result["unique_key"] = self.unique_key
        else:
            result["ping_url"] = settings.PING_ENDPOINT + str(self.code)

            # Optimization: construct API URLs manually instead of using reverse().
            # This is significantly quicker when returning hundreds of checks.
            update_url = settings.SITE_ROOT + f"/api/v{v}/checks/{self.code}"
            result["update_url"] = update_url
            result["pause_url"] = update_url + "/pause"
            result["resume_url"] = update_url + "/resume"
            result["channels"] = self.channels_str()

        if self.kind == "simple":
            result["timeout"] = int(self.timeout.total_seconds())
        elif self.kind in ("cron", "oncalendar"):
            result["schedule"] = self.schedule
            result["tz"] = self.tz

        return result

    def ping(
        self,
        remote_addr: str,
        scheme: str,
        method: str,
        ua: str,
        body: bytes,
        action: str,
        rid: uuid.UUID | None,
        exitstatus: int | None = None,
    ) -> None:
        # The following block updates a Check object, then creates a Ping object.
        # There's a possible race condition where the "sendalerts" command sees
        # the updated Check object before the Ping object is created.
        # To avoid this, put both operations inside a transaction:
        with transaction.atomic():
            frozen_now = now()

            if self.status == "paused" and self.manual_resume:
                action = "ign"

            if action == "start":
                self.last_start = frozen_now
                self.last_start_rid = rid
                # Don't update "last_ping" field.
            elif action == "ign":
                pass
            elif action == "log":
                pass
            else:
                self.last_ping = frozen_now
                self.last_duration = None
                if self.last_start:
                    if self.last_start_rid == rid:
                        # rid matches: calculate last_duration, clear last_start
                        self.last_duration = self.last_ping - self.last_start
                        self.last_start = None
                    elif action == "fail" or rid is None:
                        # clear last_start (exit the "running" state) on:
                        # - "success" event with no rid
                        # - "fail" event, regardless of rid mismatch
                        self.last_start = None

                new_status = "down" if action == "fail" else "up"
                if self.status != new_status:
                    self.create_flip(new_status)
                    self.status = new_status

            self.alert_after = self.going_down_after()
            self.n_pings = models.F("n_pings") + 1
            body_lowercase = body.decode(errors="replace").lower()
            self.has_confirmation_link = "confirm" in body_lowercase
            self.save()
            self.refresh_from_db()

            ping = Ping(owner=self)
            ping.n = self.n_pings
            ping.created = frozen_now
            if action in ("start", "fail", "ign", "log"):
                ping.kind = action

            ping.remote_addr = remote_addr
            ping.scheme = scheme
            ping.method = method
            # If User-Agent is longer than 200 characters, truncate it:
            ping.ua = ua[:200]
            if len(body) > 100 and settings.S3_BUCKET:
                ping.object_size = len(body)
            else:
                ping.body_raw = body
            ping.rid = rid
            ping.exitstatus = exitstatus
            ping.save()

        # Upload ping body to S3 outside the DB transaction, because this operation
        # can potentially take a long time:
        if ping.object_size:
            put_object(self.code, ping.n, body)

        # Every 100 received pings, prune old pings and notifications:
        if self.n_pings % 100 == 0:
            self.prune()

    def prune(self, wait: bool = False) -> None:
        """Remove old pings and notifications."""

        threshold = self.n_pings - self.project.owner_profile.ping_log_limit

        # Remove ping bodies from object storage
        if settings.S3_BUCKET:
            remove_objects(str(self.code), threshold, wait=wait)

        # Remove ping objects from db
        self.ping_set.filter(n__lte=threshold).delete()

        try:
            # Important: sort by "created", not by "id". Sorting by id
            # may cause Postgres to use the "api_ping_pkey" index, and scan
            # a huge number of rows.
            ping = self.ping_set.earliest("created")

            # Delete notifications older than the oldest retained ping
            self.notification_set.filter(created__lt=ping.created).delete()

            # Delete flips older than the oldest retained ping *and*
            # older than 93 days. We need ~3 months of flips for calculating
            # downtime statistics. The precise requirement is
            # "we need the current month and full two previous months of data".
            # We could calculate this precisely, but 3*31 is close enough and
            # much simpler.
            flip_threshold = min(ping.created, now() - td(days=93))
            self.flip_set.filter(created__lt=flip_threshold).delete()
        except Ping.DoesNotExist:
            pass

    @property
    def visible_pings(self) -> QuerySet["Ping"]:
        threshold = self.n_pings - self.project.owner_profile.ping_log_limit
        return self.ping_set.filter(n__gt=threshold)

    def downtimes_by_boundary(
        self, boundaries: list[datetime], tz: str
    ) -> list[DowntimeRecord]:
        """Calculate downtime counts and durations for the given time intervals.

        Returns a list of DowntimeRecord instances in descending datetime order.

        `boundaries` are timezone-aware datetimes of the first days of time intervals
        (months or weeks), and should be pre-sorted in descending order.

        """

        summary = DowntimeRecorder(boundaries, tz, self.created)

        # A list of flips and time interval boundaries
        events = [(b, "---") for b in boundaries]
        q = self.flip_set.filter(created__gt=min(boundaries))
        for pair in q.values_list("created", "old_status"):
            events.append(pair)

        # Iterate through flips and boundaries,
        # and for each "down" event increase the counters in `totals`.
        dt, status = now(), self.status
        for prev_dt, prev_status in sorted(events, reverse=True):
            if status == "down":
                # Before subtracting datetimes convert them to UTC.
                # Otherwise we will get incorrect results around DST transitions:
                delta = dt.astimezone(timezone.utc) - prev_dt.astimezone(timezone.utc)
                summary.add(prev_dt, delta)

            dt = prev_dt
            if prev_status != "---":
                status = prev_status

        return summary.records

    def downtimes(self, months: int, tz: str) -> list[DowntimeRecord]:
        boundaries = month_boundaries(months, tz)
        return self.downtimes_by_boundary(boundaries, tz)

    def create_flip(self, new_status: str, mark_as_processed: bool = False) -> None:
        """Create a Flip object for this check.

        Flip objects record check status changes, and have two uses:
        - for sending notifications asynchronously (create a flip object in
          wwww process, a separate "sendalerts" process picks it up and processes it)
        - for downtime statistics calculation. The Check.downtimes() method
          analyzes the flips and calculates downtime counts and durations per
          month.
        """

        flip = Flip(owner=self)
        flip.created = now()
        if mark_as_processed:
            flip.processed = flip.created
        flip.old_status = self.status
        flip.new_status = new_status
        flip.save()


class PingDict(TypedDict, total=False):
    type: str
    date: str
    n: int | None
    scheme: str
    remote_addr: str | None
    method: str
    ua: str
    rid: uuid.UUID | None
    duration: float
    body_url: str | None


class Ping(models.Model):
    id = models.BigAutoField(primary_key=True)
    n = models.IntegerField(null=True)
    owner = models.ForeignKey(Check, models.CASCADE)
    created = models.DateTimeField(default=now)
    kind = models.CharField(max_length=6, blank=True, null=True)
    scheme = models.CharField(max_length=10, default="http")
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    method = models.CharField(max_length=10, blank=True)
    ua = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, null=True)
    body_raw = models.BinaryField(null=True)
    object_size = models.IntegerField(null=True)
    exitstatus = models.SmallIntegerField(null=True)
    rid = models.UUIDField(null=True)

    def to_dict(self) -> PingDict:
        if self.has_body():
            args = [self.owner.code, self.n]
            body_url = settings.SITE_ROOT + reverse("hc-api-ping-body", args=args)
        else:
            body_url = None

        result: PingDict = {
            "type": self.kind or "success",
            "date": self.created.isoformat(),
            "n": self.n,
            "scheme": self.scheme,
            "remote_addr": self.remote_addr,
            "method": self.method,
            "ua": self.ua,
            "rid": self.rid,
            "body_url": body_url,
        }

        duration = self.duration
        if duration is not None:
            result["duration"] = duration.total_seconds()

        return result

    def has_body(self) -> bool:
        if self.body or self.body_raw or self.object_size:
            return True

        return False

    def get_body_bytes(self) -> bytes | None:
        if self.body:
            return self.body.encode()
        if self.object_size and self.n:
            return get_object(str(self.owner.code), self.n)
        if self.body_raw:
            return self.body_raw

        return None

    def get_body(self) -> str | None:
        body_bytes = self.get_body_bytes()
        if body_bytes:
            return bytes(body_bytes).decode(errors="replace")

        return None

    def get_body_size(self) -> int:
        if self.body:
            return len(self.body)
        if self.body_raw:
            return len(self.body_raw)
        if self.object_size:
            return self.object_size
        return 0

    def get_kind_display(self) -> str:
        if self.kind == "ign":
            return "Ignored"
        if self.kind == "fail":
            if self.exitstatus:
                return f"Exit status {self.exitstatus}"
            return "Failure"
        if self.kind == "start":
            return "Start"
        if self.kind == "log":
            return "Log"

        return "Success"

    @cached_property
    def duration(self) -> td | None:
        # Return early if this is not a success or failure ping,
        # or if this is the very first ping:
        if self.kind not in (None, "", "fail") or self.n == 1:
            return None

        pings = Ping.objects.filter(owner=self.owner_id)
        # only look backwards but don't look further than MAX_DURATION in the past
        pings = pings.filter(id__lt=self.id, created__gte=self.created - MAX_DURATION)

        # Look for a "start" event, with no success/fail event in between:
        for ping in pings.order_by("-id").only("created", "kind", "rid"):
            if ping.kind == "start" and ping.rid == self.rid:
                return self.created - ping.created
            elif ping.kind in (None, "", "fail") and ping.rid == self.rid:
                return None

        return None


class WebhookSpec(BaseModel):
    method: str
    url: str
    body: str
    headers: dict[str, str]


class TelegramConf(BaseModel):
    id: int
    thread_id: int | None = None
    type: str | None = None
    name: str | None = None


class ShellConf(BaseModel):
    cmd_down: str
    cmd_up: str


class PdConf(BaseModel):
    service_key: str
    account: str | None = None

    @classmethod
    def load(cls, data: Any) -> PdConf:
        # Is it plain service_key value?
        if not data.startswith("{"):
            return cls.model_validate({"service_key": data})

        return super().model_validate_json(data)


class PhoneConf(BaseModel):
    value: str
    notify_up: bool | None = Field(None, alias="up")
    notify_down: bool | None = Field(None, alias="down")


class EmailConf(BaseModel):
    value: str
    notify_up: bool = Field(alias="up")
    notify_down: bool = Field(alias="down")

    @classmethod
    def load(cls, data: Any) -> EmailConf:
        # Is it a plain email address?
        if not data.startswith("{"):
            return cls.model_validate({"value": data, "up": True, "down": True})

        return super().model_validate_json(data)


class OpsgenieConf(BaseModel):
    key: str
    region: str


class ZulipConf(BaseModel):
    bot_email: str
    api_key: str
    mtype: str
    to: str
    site: str = ""
    topic: str = ""

    def model_post_init(self, context: Any) -> None:
        if self.site == "":
            # Fallback if we don't have the site value:
            # derive it from bot's email
            _, domain = self.bot_email.split("@")
            self.site = f"https://{domain}"


class NtfyConf(BaseModel):
    topic: str
    url: str
    priority: int
    priority_up: int
    token: str = ""

    @property
    def priority_display(self) -> str:
        return NTFY_PRIORITIES[self.priority]


class TrelloConf(BaseModel):
    token: str
    list_id: str
    board_name: str
    list_name: str


class GotifyConf(BaseModel):
    url: str
    token: str


class Channel(models.Model):
    name = models.CharField(max_length=100, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(Project, models.CASCADE)
    created = models.DateTimeField(default=now)
    kind = models.CharField(max_length=20, choices=CHANNEL_KINDS)
    value = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    last_notify = models.DateTimeField(null=True, blank=True)
    last_notify_duration = models.DurationField(null=True, blank=True)
    last_error = models.CharField(max_length=200, blank=True)
    checks = models.ManyToManyField(Check)

    def __str__(self) -> str:
        if self.name:
            return self.name
        if self.kind == "email":
            return f"Email to {self.email.value}"
        elif self.kind == "sms":
            return f"SMS to {self.phone.value}"
        elif self.kind == "slack":
            return f"Slack {self.slack_channel}"
        elif self.kind == "telegram":
            return f"Telegram {self.telegram.name}"
        elif self.kind == "zulip":
            if self.zulip.mtype == "stream":
                return f"Zulip stream {self.zulip.to}"
            if self.zulip.mtype == "private":
                return f"Zulip user {self.zulip.to}"

        return self.get_kind_display()

    def to_dict(self) -> dict[str, str]:
        return {"id": str(self.code), "name": self.name, "kind": self.kind}

    def is_editable(self) -> bool:
        return self.kind in (
            "email",
            "webhook",
            "sms",
            "signal",
            "whatsapp",
            "ntfy",
            "group",
        )

    def assign_all_checks(self) -> None:
        checks = Check.objects.filter(project=self.project)
        self.checks.add(*checks)

    def make_token(self) -> str:
        seed = "%s%s" % (self.code, settings.SECRET_KEY)
        seed_bytes = seed.encode()
        return hashlib.sha1(seed_bytes).hexdigest()

    def send_verify_link(self) -> None:
        args = [self.code, self.make_token()]
        verify_link = reverse("hc-verify-email", args=args)
        verify_link = settings.SITE_ROOT + verify_link
        emails.verify_email(self.email.value, {"verify_link": verify_link})

    def get_unsub_link(self) -> str:
        signer = TimestampSigner(salt="alerts")
        signed_token = signer.sign(self.make_token())
        args = [self.code, signed_token]
        verify_link = reverse("hc-unsubscribe-alerts", args=args)
        return settings.SITE_ROOT + verify_link

    def send_signal_captcha_alert(self, challenge: str, raw: str) -> None:
        subject = "Signal CAPTCHA proof required"
        message = f"Challenge token: {challenge}"
        hostname = socket.gethostname()
        submit_url = settings.SITE_ROOT + reverse("hc-signal-captcha")
        submit_url += "?" + urlencode({"host": hostname, "challenge": challenge})
        html_message = f"""
            On host <b>{hostname}</b>, run:<br>
            <pre>manage.py submitchallenge {challenge} CAPTCHA-SOLUTION-HERE</pre><br>
            <br>
            Alternatively, <a href="{submit_url}">submit CAPTCHA solution here</a>.<br>
            <br>
            Message from Signal:<br>
            <pre>{raw}</pre>
        """
        mail_admins(subject, message, html_message=html_message)

    def send_signal_rate_limited_notice(self, message: str, plaintext: str) -> None:
        email = self.project.owner.email
        ctx = {
            "recipient": self.phone.value,
            "subject": plaintext.split("\n")[0],
            "message": message,
            "plaintext": plaintext,
        }
        emails.signal_rate_limited(email, ctx)

    @property
    def transport(self) -> transports.Transport:
        if self.kind not in TRANSPORTS:
            raise NotImplementedError(f"Unknown channel kind: {self.kind}")

        _, cls = TRANSPORTS[self.kind]
        return cls(self)

    def notify(self, flip: "Flip", is_test: bool = False) -> str:
        if self.transport.is_noop(flip.new_status):
            return "no-op"

        n = Notification(channel=self)
        if is_test:
            # When sending a test notification we leave the owner field null.
            # (the passed check is a dummy, unsaved Check instance)
            pass
        else:
            n.owner = flip.owner

        n.check_status = flip.new_status
        n.error = "Sending"
        n.save()

        start, error, disabled = now(), "", self.disabled
        try:
            self.transport.notify(flip, notification=n)

        except transports.TransportError as e:
            disabled = True if e.permanent else disabled
            error = e.message

        Notification.objects.filter(id=n.id).update(error=error)
        Channel.objects.filter(id=self.id).update(
            last_notify=start,
            last_notify_duration=now() - start,
            last_error=error,
            disabled=disabled,
        )

        return error

    def icon_path(self) -> str:
        return f"img/integrations/{self.kind}.png"

    @property
    def json(self) -> Any:
        return json.loads(self.value)

    @property
    def po_priority(self) -> str:
        assert self.kind == "po"
        parts = self.value.split("|")
        prio = int(parts[1])
        return PO_PRIORITIES[prio]

    def webhook_spec(self, status: str) -> WebhookSpec:
        assert self.kind == "webhook"
        assert status in ("up", "down")

        doc = json.loads(self.value)
        return WebhookSpec(
            method=doc[f"method_{status}"],
            url=doc[f"url_{status}"],
            body=doc[f"body_{status}"],
            headers=doc[f"headers_{status}"],
        )

    @property
    def down_webhook_spec(self) -> WebhookSpec:
        return self.webhook_spec("down")

    @property
    def up_webhook_spec(self) -> WebhookSpec:
        return self.webhook_spec("up")

    @property
    def shell(self) -> ShellConf:
        assert self.kind == "shell"
        return ShellConf.model_validate_json(self.value)

    @property
    def slack_team(self) -> str | None:
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return None

        doc = json.loads(self.value)
        if "team_name" in doc:
            assert isinstance(doc["team_name"], str)
            return doc["team_name"]

        if "team" in doc:
            assert isinstance(doc["team"]["name"], str)
            return doc["team"]["name"]

        return None

    @property
    def slack_channel(self) -> str | None:
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return None

        doc = json.loads(self.value)
        v = doc["incoming_webhook"]["channel"]
        assert isinstance(v, str)
        return v

    @property
    def slack_webhook_url(self) -> str:
        assert self.kind in ("slack", "mattermost")
        if not self.value.startswith("{"):
            return self.value

        doc = json.loads(self.value)
        v = doc["incoming_webhook"]["url"]
        assert isinstance(v, str)
        return v

    @property
    def discord_webhook_url(self) -> str:
        assert self.kind == "discord"
        url = self.json["webhook"]["url"]
        assert isinstance(url, str)
        # Discord migrated to discord.com,
        # and is dropping support for discordapp.com on 7 November 2020
        if url.startswith("https://discordapp.com/"):
            url = "https://discord.com/" + url[23:]

        return url

    @property
    def telegram(self) -> TelegramConf:
        assert self.kind == "telegram"
        return TelegramConf.model_validate_json(self.value)

    def update_telegram_id(self, new_chat_id: int) -> None:
        doc = json.loads(self.value)
        doc["id"] = new_chat_id
        self.value = json.dumps(doc)
        self.save()

    @property
    def pd(self) -> PdConf:
        assert self.kind == "pd"
        return PdConf.load(self.value)

    @property
    def phone(self) -> PhoneConf:
        assert self.kind in ("call", "sms", "whatsapp", "signal")
        return PhoneConf.model_validate_json(self.value)

    @property
    def trello(self) -> TrelloConf:
        assert self.kind == "trello"
        return TrelloConf.model_validate_json(self.value, strict=True)

    @property
    def email(self) -> EmailConf:
        return EmailConf.load(self.value)

    @property
    def opsgenie(self) -> OpsgenieConf:
        return OpsgenieConf.model_validate_json(self.value)

    @property
    def zulip(self) -> ZulipConf:
        return ZulipConf.model_validate_json(self.value)

    @property
    def linenotify_token(self) -> str:
        assert self.kind == "linenotify"
        return self.value

    @property
    def gotify(self) -> GotifyConf:
        assert self.kind == "gotify"
        return GotifyConf.model_validate_json(self.value, strict=True)

    @property
    def group_channels(self) -> QuerySet[Channel]:
        assert self.kind == "group"
        return Channel.objects.filter(
            project=self.project, code__in=self.value.split(",")
        )

    @property
    def ntfy(self) -> NtfyConf:
        assert self.kind == "ntfy"
        return NtfyConf.model_validate_json(self.value, strict=True)


class Notification(models.Model):
    code = models.UUIDField(default=uuid.uuid4, null=True, editable=False)
    # owner is null for test notifications, produced by the "Test!" button
    # in the Integrations page
    owner = models.ForeignKey(Check, models.CASCADE, null=True)
    check_status = models.CharField(max_length=6)
    channel = models.ForeignKey(Channel, models.CASCADE)
    created = models.DateTimeField(default=now)
    error = models.CharField(max_length=200, blank=True)

    class Meta:
        get_latest_by = "created"

    def status_url(self) -> str:
        path = reverse("hc-api-notification-status", args=[self.code])
        return settings.SITE_ROOT + path


class FlipDict(TypedDict):
    timestamp: str
    up: int


class Flip(models.Model):
    owner = models.ForeignKey(Check, models.CASCADE)
    created = models.DateTimeField()
    processed = models.DateTimeField(null=True, blank=True)
    old_status = models.CharField(max_length=8, choices=STATUSES)
    new_status = models.CharField(max_length=8, choices=STATUSES)

    class Meta:
        indexes = [
            # For quickly looking up unprocessed flips.
            # Used in the sendalerts management command.
            models.Index(
                fields=["processed"],
                name="api_flip_not_processed",
                condition=models.Q(processed=None),
            )
        ]

    def to_dict(self) -> FlipDict:
        return {
            "timestamp": self.created.replace(microsecond=0).isoformat(),
            "up": 1 if self.new_status == "up" else 0,
        }

    def select_channels(self) -> list[Channel]:
        """Return a list of channels that need to be notified.

        * Exclude all channels for new->up and paused->up transitions.
        * Exclude disabled channels
        * Exclude channels where transport.is_noop(status) returns True
        """

        # Don't send alerts on new->up and paused->up transitions
        if self.new_status == "up" and self.old_status in ("new", "paused"):
            return []

        if self.new_status not in ("up", "down"):
            raise NotImplementedError(f"Unexpected status: {self.new_status}")

        q = self.owner.channel_set.exclude(disabled=True)
        return [ch for ch in q if not ch.transport.is_noop(self.new_status)]


class TokenBucket(models.Model):
    value = models.CharField(max_length=80, unique=True)
    tokens = models.FloatField(default=1.0)
    updated = models.DateTimeField(default=now)

    @staticmethod
    def authorize(value: str, capacity: int, refill_time_secs: int) -> bool:
        frozen_now = now()
        obj, created = TokenBucket.objects.get_or_create(value=value)

        if not created:
            # Top up the bucket:
            duration_secs = (frozen_now - obj.updated).total_seconds()
            obj.tokens = min(1.0, obj.tokens + duration_secs / refill_time_secs)

        obj.tokens -= 1.0 / capacity
        if obj.tokens < 0:
            # Not enough tokens
            return False

        # Race condition: two concurrent authorize calls can overwrite each
        # other's changes. It's OK to be a little inexact here for the sake
        # of simplicity.
        obj.updated = frozen_now
        obj.save()

        return True

    @staticmethod
    def authorize_auth_ip(request: HttpRequest) -> bool:
        headers = request.META
        remote_addr = headers.get("HTTP_X_FORWARDED_FOR", headers["REMOTE_ADDR"])
        remote_addr = remote_addr.split(",")[0]
        if "." in remote_addr and ":" in remote_addr:
            # If remote_addr is in a ipv4address:port format
            # (like in Azure App Service), remove the port:
            remote_addr = remote_addr.split(":")[0]

        value = f"auth-ip-{remote_addr}"
        # 20 signup/login attempts for a single IP per hour:
        return TokenBucket.authorize(value, 20, 3600)

    @staticmethod
    def authorize_login_email(email: str) -> bool:
        # remove dots and alias:
        mailbox, domain = email.split("@")
        mailbox = mailbox.replace(".", "")
        mailbox = mailbox.split("+")[0]
        email = mailbox + "@" + domain

        salted_encoded = (email + settings.SECRET_KEY).encode()
        value = "em-%s" % hashlib.sha1(salted_encoded).hexdigest()

        # 20 login attempts for a single email per hour:
        return TokenBucket.authorize(value, 20, 3600)

    @staticmethod
    def authorize_invite(user: User) -> bool:
        value = "invite-%d" % user.id

        # 20 invites per day
        return TokenBucket.authorize(value, 20, 3600 * 24)

    @staticmethod
    def authorize_login_password(email: str) -> bool:
        salted_encoded = (email + settings.SECRET_KEY).encode()
        value = "pw-%s" % hashlib.sha1(salted_encoded).hexdigest()

        # 20 password attempts per day
        return TokenBucket.authorize(value, 20, 3600 * 24)

    @staticmethod
    def authorize_telegram(telegram_id: int) -> bool:
        value = "tg-%s" % telegram_id

        # 6 messages for a single chat per minute:
        return TokenBucket.authorize(value, 6, 60)

    @staticmethod
    def authorize_signal(phone: str) -> bool:
        salted_encoded = (phone + settings.SECRET_KEY).encode()
        value = "signal-%s" % hashlib.sha1(salted_encoded).hexdigest()

        # 6 messages for a single recipient per minute:
        return TokenBucket.authorize(value, 6, 60)

    @staticmethod
    def authorize_signal_verification(user: User) -> bool:
        value = "signal-verify-%d" % user.id

        # 50 signal recipient verifications per day
        return TokenBucket.authorize(value, 50, 3600 * 24)

    @staticmethod
    def authorize_pushover(user_key: str) -> bool:
        salted_encoded = (user_key + settings.SECRET_KEY).encode()
        value = "po-%s" % hashlib.sha1(salted_encoded).hexdigest()
        # 6 messages for a single user key per minute:
        return TokenBucket.authorize(value, 6, 60)

    @staticmethod
    def authorize_sudo_code(user: User) -> bool:
        value = "sudo-%d" % user.id

        # 10 sudo attempts per day
        return TokenBucket.authorize(value, 10, 3600 * 24)

    @staticmethod
    def authorize_totp_attempt(user: User) -> bool:
        value = "totp-%d" % user.id

        # 96 attempts per user per 24 hours
        # (or, on average, one attempt per 15 minutes)
        return TokenBucket.authorize(value, 96, 3600 * 24)

    @staticmethod
    def authorize_totp_code(user: User, code: str) -> bool:
        value = "totpc-%d-%s" % (user.id, code)

        # A code has a validity period of 3 * 30 = 90 seconds.
        # During that period, allow the code to only be used once,
        # so an eavesdropping attacker cannot reuse a code.
        return TokenBucket.authorize(value, 1, 90)
