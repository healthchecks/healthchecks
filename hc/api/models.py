from __future__ import annotations

import hashlib
import json
import socket
import sys
import time
import uuid
from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from typing import TypedDict
from urllib.parse import urlencode

from cronsim import CronSim
from django.conf import settings
from django.core.mail import mail_admins
from django.core.signing import TimestampSigner
from django.db import models, transaction
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import now

from hc.accounts.models import Project
from hc.api import transports
from hc.lib import emails
from hc.lib.date import month_boundaries
from hc.lib.s3 import get_object, put_object, remove_objects

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
else:
    from backports.zoneinfo import ZoneInfo


STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"), ("paused", "Paused"))
DEFAULT_TIMEOUT = td(days=1)
DEFAULT_GRACE = td(hours=1)
NEVER = datetime(3000, 1, 1, tzinfo=timezone.utc)
CHECK_KINDS = (("simple", "Simple"), ("cron", "Cron"))
# max time between start and ping where we will consider both events related:
MAX_DURATION = td(hours=72)

TRANSPORTS = {
    "apprise": ("Apprise", transports.Apprise),
    "call": ("Phone Call", transports.Call),
    "discord": ("Discord", transports.Discord),
    "email": ("Email", transports.Email),
    "gotify": ("Gotify", transports.Gotify),
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


def isostring(dt) -> str | None:
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


class DowntimeSummary(object):
    def __init__(self, boundaries: list[datetime]):
        self.boundaries = list(sorted(boundaries, reverse=True))
        self.durations = [td() for _ in boundaries]
        self.counts = [0 for _ in boundaries]

    def add(self, when: datetime, duration: td) -> None:
        for i in range(0, len(self.boundaries)):
            if when >= self.boundaries[i]:
                self.durations[i] += duration
                self.counts[i] += 1
                return

    def as_tuples(self) -> zip[tuple[datetime, td, int]]:
        return zip(self.boundaries, self.durations, self.counts)


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

    def __str__(self):
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

    def details_url(self) -> str:
        return settings.SITE_ROOT + reverse("hc-details", args=[self.code])

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
        assert grace_start is not None
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
        elif self.kind == "cron":
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

    def prune(self) -> None:
        """Remove old pings and notifications."""

        threshold = self.n_pings - self.project.owner_profile.ping_log_limit

        # Remove ping bodies from object storage
        if settings.S3_BUCKET:
            remove_objects(self.code, threshold)

        # Remove ping objects from db
        self.ping_set.filter(n__lte=threshold).delete()

        try:
            ping = self.ping_set.earliest("id")
            self.notification_set.filter(created__lt=ping.created).delete()
        except Ping.DoesNotExist:
            pass

    @property
    def visible_pings(self):
        threshold = self.n_pings - self.project.owner_profile.ping_log_limit
        return self.ping_set.filter(n__gt=threshold)

    def downtimes_by_boundary(self, boundaries: list[datetime]):
        """Calculate downtime counts and durations for the given time intervals.

        Returns a list of (datetime, downtime_in_secs, number_of_outages) tuples
        in ascending datetime order.

        `boundaries` are the datetimes of the first days of time intervals
        (months or weeks) we're interested in, in ascending order.

        """

        summary = DowntimeSummary(boundaries)

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
                summary.add(prev_dt, dt - prev_dt)

            dt = prev_dt
            if prev_status != "---":
                status = prev_status

        # Convert to a list of tuples and set counters to None
        # for intervals when the check didn't exist yet
        prev_boundary = None
        result: list[tuple[datetime, td | None, int | None]] = []
        for triple in summary.as_tuples():
            if prev_boundary and self.created > prev_boundary:
                result.append((triple[0], None, None))
                continue

            prev_boundary = triple[0]
            result.append(triple)

        result.sort()
        return result

    def downtimes(self, months: int, tz: str):
        boundaries = month_boundaries(months, tz)
        return self.downtimes_by_boundary(boundaries)

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
        if self.object_size:
            return get_object(self.owner.code, self.n)
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

    def get_kind_display(self):
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


def json_property(kind, field):
    def fget(instance):
        assert instance.kind == kind
        return instance.json[field]

    return property(fget)


class Channel(models.Model):
    name = models.CharField(max_length=100, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(Project, models.CASCADE)
    created = models.DateTimeField(default=now)
    kind = models.CharField(max_length=20, choices=CHANNEL_KINDS)
    value = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    disabled = models.BooleanField(null=True)
    last_notify = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=200, blank=True)
    checks = models.ManyToManyField(Check)

    def __str__(self):
        if self.name:
            return self.name
        if self.kind == "email":
            return "Email to %s" % self.email_value
        elif self.kind == "sms":
            return "SMS to %s" % self.phone_number
        elif self.kind == "slack":
            return "Slack %s" % self.slack_channel
        elif self.kind == "telegram":
            return "Telegram %s" % self.telegram_name
        elif self.kind == "zulip":
            if self.zulip_type == "stream":
                return "Zulip stream %s" % self.zulip_to
            if self.zulip_type == "private":
                return "Zulip user %s" % self.zulip_to

        return self.get_kind_display()

    def to_dict(self):
        return {"id": str(self.code), "name": self.name, "kind": self.kind}

    def is_editable(self):
        return self.kind in ("email", "webhook", "sms", "signal", "whatsapp", "ntfy")

    def assign_all_checks(self):
        checks = Check.objects.filter(project=self.project)
        self.checks.add(*checks)

    def make_token(self):
        seed = "%s%s" % (self.code, settings.SECRET_KEY)
        seed = seed.encode()
        return hashlib.sha1(seed).hexdigest()

    def send_verify_link(self):
        args = [self.code, self.make_token()]
        verify_link = reverse("hc-verify-email", args=args)
        verify_link = settings.SITE_ROOT + verify_link
        emails.verify_email(self.email_value, {"verify_link": verify_link})

    def get_unsub_link(self):
        signer = TimestampSigner(salt="alerts")
        signed_token = signer.sign(self.make_token())
        args = [self.code, signed_token]
        verify_link = reverse("hc-unsubscribe-alerts", args=args)
        return settings.SITE_ROOT + verify_link

    def send_signal_captcha_alert(self, challenge, raw):
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

    def send_signal_rate_limited_notice(self, message):
        email = self.project.owner.email
        ctx = {
            "recipient": self.phone_number,
            "subject": message.split("\n")[0],
            "message": message,
        }
        emails.signal_rate_limited(email, ctx)

    @property
    def transport(self):
        if self.kind not in TRANSPORTS:
            raise NotImplementedError(f"Unknown channel kind: {self.kind}")

        _, cls = TRANSPORTS[self.kind]
        return cls(self)

    def notify(self, check, is_test=False):
        if self.transport.is_noop(check):
            return "no-op"

        n = Notification(channel=self)
        if is_test:
            # When sending a test notification we leave the owner field null.
            # (the passed check is a dummy, unsaved Check instance)
            pass
        else:
            n.owner = check

        n.check_status = check.status
        n.error = "Sending"
        n.save()

        error, disabled = "", self.disabled
        try:
            self.transport.notify(check, notification=n)
        except transports.TransportError as e:
            disabled = True if e.permanent else disabled
            error = e.message

        Notification.objects.filter(id=n.id).update(error=error)
        Channel.objects.filter(id=self.id).update(
            last_notify=now(), last_error=error, disabled=disabled
        )

        return error

    def icon_path(self):
        return "img/integrations/%s.png" % self.kind

    @property
    def json(self):
        return json.loads(self.value)

    @property
    def po_priority(self):
        assert self.kind == "po"
        parts = self.value.split("|")
        prio = int(parts[1])
        return PO_PRIORITIES[prio]

    def webhook_spec(self, status):
        assert self.kind == "webhook"

        doc = json.loads(self.value)
        if status == "down" and "method_down" in doc:
            return {
                "method": doc["method_down"],
                "url": doc["url_down"],
                "body": doc["body_down"],
                "headers": doc["headers_down"],
            }
        elif status == "up" and "method_up" in doc:
            return {
                "method": doc["method_up"],
                "url": doc["url_up"],
                "body": doc["body_up"],
                "headers": doc["headers_up"],
            }

    @property
    def down_webhook_spec(self):
        return self.webhook_spec("down")

    @property
    def up_webhook_spec(self):
        return self.webhook_spec("up")

    @property
    def url_down(self):
        return self.down_webhook_spec["url"]

    @property
    def url_up(self):
        return self.up_webhook_spec["url"]

    cmd_down = json_property("shell", "cmd_down")
    cmd_up = json_property("shell", "cmd_up")

    @property
    def slack_team(self):
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return None

        doc = json.loads(self.value)
        if "team_name" in doc:
            return doc["team_name"]

        if "team" in doc:
            return doc["team"]["name"]

    @property
    def slack_channel(self):
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return None

        doc = json.loads(self.value)
        return doc["incoming_webhook"]["channel"]

    @property
    def slack_webhook_url(self):
        assert self.kind in ("slack", "mattermost")
        if not self.value.startswith("{"):
            return self.value

        doc = json.loads(self.value)
        return doc["incoming_webhook"]["url"]

    @property
    def discord_webhook_url(self):
        assert self.kind == "discord"
        url = self.json["webhook"]["url"]

        # Discord migrated to discord.com,
        # and is dropping support for discordapp.com on 7 November 2020
        if url.startswith("https://discordapp.com/"):
            url = "https://discord.com/" + url[23:]

        return url

    @property
    def telegram_id(self):
        assert self.kind == "telegram"
        return self.json.get("id")

    @property
    def telegram_type(self):
        assert self.kind == "telegram"
        return self.json.get("type")

    @property
    def telegram_name(self):
        assert self.kind == "telegram"
        return self.json.get("name")

    def update_telegram_id(self, new_chat_id) -> None:
        doc = self.json
        doc["id"] = new_chat_id
        self.value = json.dumps(doc)
        self.save()

    @property
    def pd_service_key(self):
        assert self.kind == "pd"
        if not self.value.startswith("{"):
            return self.value

        return self.json["service_key"]

    @property
    def pd_account(self):
        assert self.kind == "pd"
        if self.value.startswith("{"):
            return self.json.get("account")

    @property
    def phone_number(self):
        assert self.kind in ("call", "sms", "whatsapp", "signal")
        if self.value.startswith("{"):
            return self.json["value"]

        return self.value

    trello_token = json_property("trello", "token")
    trello_list_id = json_property("trello", "list_id")

    @property
    def trello_board_list(self):
        assert self.kind == "trello"
        doc = json.loads(self.value)
        return doc["board_name"], doc["list_name"]

    @property
    def email_value(self):
        assert self.kind == "email"
        if not self.value.startswith("{"):
            return self.value

        return self.json["value"]

    @property
    def email_notify_up(self):
        assert self.kind == "email"
        if not self.value.startswith("{"):
            return True

        return self.json.get("up")

    @property
    def email_notify_down(self):
        assert self.kind == "email"
        if not self.value.startswith("{"):
            return True

        return self.json.get("down")

    whatsapp_notify_up = json_property("whatsapp", "up")
    whatsapp_notify_down = json_property("whatsapp", "down")

    signal_notify_up = json_property("signal", "up")
    signal_notify_down = json_property("signal", "down")

    @property
    def sms_notify_up(self):
        assert self.kind == "sms"
        return self.json.get("up", False)

    @property
    def sms_notify_down(self):
        assert self.kind == "sms"
        return self.json.get("down", True)

    @property
    def opsgenie_key(self):
        assert self.kind == "opsgenie"
        if not self.value.startswith("{"):
            return self.value

        return self.json["key"]

    @property
    def opsgenie_region(self):
        assert self.kind == "opsgenie"
        if not self.value.startswith("{"):
            return "us"

        return self.json["region"]

    zulip_bot_email = json_property("zulip", "bot_email")
    zulip_api_key = json_property("zulip", "api_key")
    zulip_type = json_property("zulip", "mtype")
    zulip_to = json_property("zulip", "to")

    @property
    def zulip_site(self):
        assert self.kind == "zulip"
        doc = json.loads(self.value)
        if "site" in doc:
            return doc["site"]

        # Fallback if we don't have the site value:
        # derive it from bot's email
        _, domain = doc["bot_email"].split("@")
        return "https://" + domain

    @property
    def zulip_topic(self):
        assert self.kind == "zulip"
        return self.json.get("topic", "")

    @property
    def linenotify_token(self):
        assert self.kind == "linenotify"
        return self.value

    gotify_url = json_property("gotify", "url")
    gotify_token = json_property("gotify", "token")

    ntfy_topic = json_property("ntfy", "topic")
    ntfy_url = json_property("ntfy", "url")
    ntfy_priority = json_property("ntfy", "priority")
    ntfy_priority_up = json_property("ntfy", "priority_up")

    @property
    def ntfy_priority_display(self):
        return NTFY_PRIORITIES[self.ntfy_priority]


class Notification(models.Model):
    code = models.UUIDField(default=uuid.uuid4, null=True, editable=False)
    owner = models.ForeignKey(Check, models.CASCADE, null=True)
    check_status = models.CharField(max_length=6)
    channel = models.ForeignKey(Channel, models.CASCADE)
    created = models.DateTimeField(default=now)
    error = models.CharField(max_length=200, blank=True)

    class Meta:
        get_latest_by = "created"

    def status_url(self):
        path = reverse("hc-api-notification-status", args=[self.code])
        return settings.SITE_ROOT + path


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

    def to_dict(self):
        return {
            "timestamp": isostring(self.created),
            "up": 1 if self.new_status == "up" else 0,
        }

    def send_alerts(self):
        """Loop over the enabled channels, call notify() on each.

        For each channel, yield a (channel, error, send_time) triple:
         * channel is a Channel instance
         * error is an empty string ("") on success, error message otherwise
         * send_time is specified in seconds (float)
        """

        # Don't send alerts on new->up and paused->up transitions
        if self.new_status == "up" and self.old_status in ("new", "paused"):
            return

        if self.new_status not in ("up", "down"):
            raise NotImplementedError("Unexpected status: %s" % self.status)

        for channel in self.owner.channel_set.exclude(disabled=True):
            start = time.time()
            error = channel.notify(self.owner)
            if error == "no-op":
                continue

            yield channel, error, time.time() - start


class TokenBucket(models.Model):
    value = models.CharField(max_length=80, unique=True)
    tokens = models.FloatField(default=1.0)
    updated = models.DateTimeField(default=now)

    @staticmethod
    def authorize(value, capacity, refill_time_secs):
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
    def authorize_auth_ip(request):
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
    def authorize_login_email(email):
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
    def authorize_invite(user):
        value = "invite-%d" % user.id

        # 20 invites per day
        return TokenBucket.authorize(value, 20, 3600 * 24)

    @staticmethod
    def authorize_login_password(email):
        salted_encoded = (email + settings.SECRET_KEY).encode()
        value = "pw-%s" % hashlib.sha1(salted_encoded).hexdigest()

        # 20 password attempts per day
        return TokenBucket.authorize(value, 20, 3600 * 24)

    @staticmethod
    def authorize_telegram(telegram_id):
        value = "tg-%s" % telegram_id

        # 6 messages for a single chat per minute:
        return TokenBucket.authorize(value, 6, 60)

    @staticmethod
    def authorize_signal(phone):
        salted_encoded = (phone + settings.SECRET_KEY).encode()
        value = "signal-%s" % hashlib.sha1(salted_encoded).hexdigest()

        # 6 messages for a single recipient per minute:
        return TokenBucket.authorize(value, 6, 60)

    @staticmethod
    def authorize_signal_verification(user):
        value = "signal-verify-%d" % user.id

        # 50 signal recipient verifications per day
        return TokenBucket.authorize(value, 50, 3600 * 24)

    @staticmethod
    def authorize_pushover(user_key):
        salted_encoded = (user_key + settings.SECRET_KEY).encode()
        value = "po-%s" % hashlib.sha1(salted_encoded).hexdigest()
        # 6 messages for a single user key per minute:
        return TokenBucket.authorize(value, 6, 60)

    @staticmethod
    def authorize_sudo_code(user):
        value = "sudo-%d" % user.id

        # 10 sudo attempts per day
        return TokenBucket.authorize(value, 10, 3600 * 24)

    @staticmethod
    def authorize_totp_attempt(user):
        value = "totp-%d" % user.id

        # 96 attempts per user per 24 hours
        # (or, on average, one attempt per 15 minutes)
        return TokenBucket.authorize(value, 96, 3600 * 24)

    @staticmethod
    def authorize_totp_code(user, code):
        value = "totpc-%d-%s" % (user.id, code)

        # A code has a validity period of 3 * 30 = 90 seconds.
        # During that period, allow the code to only be used once,
        # so an eavesdropping attacker cannot reuse a code.
        return TokenBucket.authorize(value, 1, 90)
