# coding: utf-8

import hashlib
import json
import uuid
from datetime import datetime, timedelta as td

from croniter import croniter
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from hc.accounts.models import Project
from hc.api import transports
from hc.lib import emails
from hc.lib.date import month_boundaries
import pytz

STATUSES = (("up", "Up"), ("down", "Down"), ("new", "New"), ("paused", "Paused"))
DEFAULT_TIMEOUT = td(days=1)
DEFAULT_GRACE = td(hours=1)
NEVER = datetime(3000, 1, 1, tzinfo=pytz.UTC)
CHECK_KINDS = (("simple", "Simple"), ("cron", "Cron"))

CHANNEL_KINDS = (
    ("email", "Email"),
    ("webhook", "Webhook"),
    ("hipchat", "HipChat"),
    ("slack", "Slack"),
    ("pd", "PagerDuty"),
    ("pagertree", "PagerTree"),
    ("pagerteam", "Pager Team"),
    ("po", "Pushover"),
    ("pushbullet", "Pushbullet"),
    ("opsgenie", "OpsGenie"),
    ("victorops", "VictorOps"),
    ("discord", "Discord"),
    ("telegram", "Telegram"),
    ("sms", "SMS"),
    ("zendesk", "Zendesk"),
    ("trello", "Trello"),
    ("matrix", "Matrix"),
    ("whatsapp", "WhatsApp"),
    ("apprise", "Apprise"),
    ("mattermost", "Mattermost"),
)

PO_PRIORITIES = {-2: "lowest", -1: "low", 0: "normal", 1: "high", 2: "emergency"}


def isostring(dt):
    """Convert the datetime to ISO 8601 format with no microseconds. """

    if dt:
        return dt.replace(microsecond=0).isoformat()


class Check(models.Model):
    name = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=500, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    desc = models.TextField(blank=True)
    project = models.ForeignKey(Project, models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=10, default="simple", choices=CHECK_KINDS)
    timeout = models.DurationField(default=DEFAULT_TIMEOUT)
    grace = models.DurationField(default=DEFAULT_GRACE)
    schedule = models.CharField(max_length=100, default="* * * * *")
    tz = models.CharField(max_length=36, default="UTC")
    subject = models.CharField(max_length=100, blank=True)
    n_pings = models.IntegerField(default=0)
    last_ping = models.DateTimeField(null=True, blank=True)
    last_start = models.DateTimeField(null=True, blank=True)
    last_ping_was_fail = models.NullBooleanField(default=False)
    has_confirmation_link = models.BooleanField(default=False)
    alert_after = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=6, choices=STATUSES, default="new")

    class Meta:
        indexes = [
            # Index for the alert_after field. Excludes rows with status=down.
            # Used in the sendalerts management command.
            models.Index(
                fields=["alert_after"],
                name="api_check_aa_not_down",
                condition=~models.Q(status="down"),
            )
        ]

    def __str__(self):
        return "%s (%d)" % (self.name or self.code, self.id)

    def name_then_code(self):
        if self.name:
            return self.name

        return str(self.code)

    def url(self):
        return settings.PING_ENDPOINT + str(self.code)

    def details_url(self):
        return settings.SITE_ROOT + reverse("hc-details", args=[self.code])

    def email(self):
        return "%s@%s" % (self.code, settings.PING_EMAIL_DOMAIN)

    def get_grace_start(self):
        """ Return the datetime when the grace period starts.

        If the check is currently new, paused or down, return None.

        """

        # NEVER is a constant sentinel value (year 3000).
        # Using None instead would make the logic clunky.
        result = NEVER

        if self.kind == "simple" and self.status == "up":
            result = self.last_ping + self.timeout
        elif self.kind == "cron" and self.status == "up":
            # The complex case, next ping is expected based on cron schedule.
            # Don't convert to naive datetimes (and so avoid ambiguities around
            # DST transitions). Croniter will handle the timezone-aware datetimes.

            zone = pytz.timezone(self.tz)
            last_local = timezone.localtime(self.last_ping, zone)
            it = croniter(self.schedule, last_local)
            result = it.next(datetime)

        if self.last_start and self.status != "down":
            result = min(result, self.last_start)

        if result != NEVER:
            return result

    def going_down_after(self):
        """ Return the datetime when the check goes down.

        If the check is new or paused, and not currently running, return None.
        If the check is already down, also return None.

        """

        grace_start = self.get_grace_start()
        if grace_start is not None:
            return grace_start + self.grace

    def get_status(self, now=None, with_started=True):
        """ Return current status for display. """

        if now is None:
            now = timezone.now()

        if self.last_start:
            if now >= self.last_start + self.grace:
                return "down"
            elif with_started:
                return "started"

        if self.status in ("new", "paused", "down"):
            return self.status

        grace_start = self.get_grace_start()
        grace_end = grace_start + self.grace
        if now >= grace_end:
            return "down"

        if now >= grace_start:
            return "grace"

        return "up"

    def assign_all_channels(self):
        channels = Channel.objects.filter(project=self.project)
        self.channel_set.set(channels)

    def tags_list(self):
        return [t.strip() for t in self.tags.split(" ") if t.strip()]

    def matches_tag_set(self, tag_set):
        return tag_set.issubset(self.tags_list())

    def channels_str(self):
        """ Return a comma-separated string of assigned channel codes. """

        codes = self.channel_set.order_by("code").values_list("code", flat=True)
        return ",".join(map(str, codes))

    def to_dict(self, readonly=False):

        result = {
            "name": self.name,
            "tags": self.tags,
            "desc": self.desc,
            "grace": int(self.grace.total_seconds()),
            "n_pings": self.n_pings,
            "status": self.get_status(),
            "last_ping": isostring(self.last_ping),
            "next_ping": isostring(self.get_grace_start()),
        }

        if readonly:
            code_half = self.code.hex[:16]
            result["unique_key"] = hashlib.sha1(code_half.encode()).hexdigest()
        else:
            update_rel_url = reverse("hc-api-update", args=[self.code])
            pause_rel_url = reverse("hc-api-pause", args=[self.code])

            result["ping_url"] = self.url()
            result["update_url"] = settings.SITE_ROOT + update_rel_url
            result["pause_url"] = settings.SITE_ROOT + pause_rel_url
            result["channels"] = self.channels_str()

        if self.kind == "simple":
            result["timeout"] = int(self.timeout.total_seconds())
        elif self.kind == "cron":
            result["schedule"] = self.schedule
            result["tz"] = self.tz

        return result

    def ping(self, remote_addr, scheme, method, ua, body, action):
        if action == "start":
            self.last_start = timezone.now()
            # Don't update "last_ping" field.
        elif action == "ign":
            pass
        else:
            self.last_start = None
            self.last_ping = timezone.now()

            new_status = "down" if action == "fail" else "up"
            if self.status != new_status:
                flip = Flip(owner=self)
                flip.created = self.last_ping
                flip.old_status = self.status
                flip.new_status = new_status
                flip.save()

                self.status = new_status

        self.alert_after = self.going_down_after()
        self.n_pings = models.F("n_pings") + 1
        self.has_confirmation_link = "confirm" in str(body).lower()
        self.save()
        self.refresh_from_db()

        ping = Ping(owner=self)
        ping.n = self.n_pings
        if action in ("start", "fail", "ign"):
            ping.kind = action

        ping.remote_addr = remote_addr
        ping.scheme = scheme
        ping.method = method
        # If User-Agent is longer than 200 characters, truncate it:
        ping.ua = ua[:200]
        ping.body = body[:10000]
        ping.save()

    def downtimes(self, months=2):
        """ Calculate the number of downtimes and downtime minutes per month.

        Returns a list of (datetime, downtime_in_secs, number_of_outages) tuples.

        """

        def monthkey(dt):
            return dt.year, dt.month

        # Datetimes of the first days of months we're interested in. Ascending order.
        boundaries = month_boundaries(months=months)

        # Will accumulate totals here.
        # (year, month) -> [datetime, total_downtime, number_of_outages]
        totals = {monthkey(b): [b, td(), 0] for b in boundaries}

        # A list of flips and month boundaries
        events = [(b, "---") for b in boundaries]
        q = self.flip_set.filter(created__gt=min(boundaries))
        for pair in q.values_list("created", "old_status"):
            events.append(pair)

        # Iterate through flips and month boundaries in reverse order,
        # and for each "down" event increase the counters in `totals`.
        dt, status = timezone.now(), self.status
        for prev_dt, prev_status in sorted(events, reverse=True):
            if status == "down":
                delta = dt - prev_dt
                totals[monthkey(prev_dt)][1] += delta
                totals[monthkey(prev_dt)][2] += 1

            dt = prev_dt
            if prev_status != "---":
                status = prev_status

        return sorted(totals.values())


class Ping(models.Model):
    id = models.BigAutoField(primary_key=True)
    n = models.IntegerField(null=True)
    owner = models.ForeignKey(Check, models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=6, blank=True, null=True)
    scheme = models.CharField(max_length=10, default="http")
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    method = models.CharField(max_length=10, blank=True)
    ua = models.CharField(max_length=200, blank=True)
    body = models.CharField(max_length=10000, blank=True, null=True)


class Channel(models.Model):
    name = models.CharField(max_length=100, blank=True)
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(Project, models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=20, choices=CHANNEL_KINDS)
    value = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    checks = models.ManyToManyField(Check)

    def __str__(self):
        if self.name:
            return self.name
        if self.kind == "email":
            return "Email to %s" % self.email_value
        elif self.kind == "sms":
            return "SMS to %s" % self.sms_number
        elif self.kind == "slack":
            return "Slack %s" % self.slack_channel
        elif self.kind == "telegram":
            return "Telegram %s" % self.telegram_name

        return self.get_kind_display()

    def to_dict(self):
        return {"id": str(self.code), "name": self.name, "kind": self.kind}

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
        args = [self.code, self.make_token()]
        verify_link = reverse("hc-unsubscribe-alerts", args=args)
        return settings.SITE_ROOT + verify_link

    @property
    def transport(self):
        if self.kind == "email":
            return transports.Email(self)
        elif self.kind == "webhook":
            return transports.Webhook(self)
        elif self.kind in ("slack", "mattermost"):
            return transports.Slack(self)
        elif self.kind == "hipchat":
            return transports.HipChat(self)
        elif self.kind == "pd":
            return transports.PagerDuty(self)
        elif self.kind == "pagertree":
            return transports.PagerTree(self)
        elif self.kind == "pagerteam":
            return transports.PagerTeam(self)
        elif self.kind == "victorops":
            return transports.VictorOps(self)
        elif self.kind == "pushbullet":
            return transports.Pushbullet(self)
        elif self.kind == "po":
            return transports.Pushover(self)
        elif self.kind == "opsgenie":
            return transports.OpsGenie(self)
        elif self.kind == "discord":
            return transports.Discord(self)
        elif self.kind == "telegram":
            return transports.Telegram(self)
        elif self.kind == "sms":
            return transports.Sms(self)
        elif self.kind == "trello":
            return transports.Trello(self)
        elif self.kind == "matrix":
            return transports.Matrix(self)
        elif self.kind == "whatsapp":
            return transports.WhatsApp(self)
        elif self.kind == "apprise":
            return transports.Apprise(self)
        else:
            raise NotImplementedError("Unknown channel kind: %s" % self.kind)

    def notify(self, check):
        if self.transport.is_noop(check):
            return "no-op"

        n = Notification(owner=check, channel=self)
        n.check_status = check.status
        n.error = "Sending"
        n.save()

        if self.kind == "email":
            error = self.transport.notify(check, n.bounce_url()) or ""
        else:
            error = self.transport.notify(check) or ""

        n.error = error
        n.save()

        return error

    def icon_path(self):
        return "img/integrations/%s.png" % self.kind

    @property
    def po_priority(self):
        assert self.kind == "po"
        parts = self.value.split("|")
        prio = int(parts[1])
        return PO_PRIORITIES[prio]

    def webhook_spec(self, status):
        assert self.kind == "webhook"

        if not self.value.startswith("{"):
            parts = self.value.split("\n")
            url_down = parts[0]
            url_up = parts[1] if len(parts) > 1 else ""
            post_data = parts[2] if len(parts) > 2 else ""

            return {
                "method": "POST" if post_data else "GET",
                "url": url_down if status == "down" else url_up,
                "body": post_data,
                "headers": {},
            }

        doc = json.loads(self.value)
        if "post_data" in doc:
            # Legacy "post_data" in doc -- use the legacy fields
            return {
                "method": "POST" if doc["post_data"] else "GET",
                "url": doc["url_down"] if status == "down" else doc["url_up"],
                "body": doc["post_data"],
                "headers": doc["headers"],
            }

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

    @property
    def slack_team(self):
        assert self.kind == "slack"
        if not self.value.startswith("{"):
            return None

        doc = json.loads(self.value)
        return doc["team_name"]

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
        doc = json.loads(self.value)
        return doc["webhook"]["url"]

    @property
    def discord_webhook_id(self):
        assert self.kind == "discord"
        doc = json.loads(self.value)
        return doc["webhook"]["id"]

    @property
    def telegram_id(self):
        assert self.kind == "telegram"
        doc = json.loads(self.value)
        return doc.get("id")

    @property
    def telegram_type(self):
        assert self.kind == "telegram"
        doc = json.loads(self.value)
        return doc.get("type")

    @property
    def telegram_name(self):
        assert self.kind == "telegram"
        doc = json.loads(self.value)
        return doc.get("name")

    @property
    def pd_service_key(self):
        assert self.kind == "pd"
        if not self.value.startswith("{"):
            return self.value

        doc = json.loads(self.value)
        return doc["service_key"]

    @property
    def pd_account(self):
        assert self.kind == "pd"
        if self.value.startswith("{"):
            doc = json.loads(self.value)
            return doc["account"]

    def latest_notification(self):
        return Notification.objects.filter(channel=self).latest()

    @property
    def sms_number(self):
        assert self.kind in ("sms", "whatsapp")
        if self.value.startswith("{"):
            doc = json.loads(self.value)
            return doc["value"]
        return self.value

    @property
    def sms_label(self):
        assert self.kind == "sms"
        if self.value.startswith("{"):
            doc = json.loads(self.value)
            return doc["label"]

    @property
    def trello_token(self):
        assert self.kind == "trello"
        if self.value.startswith("{"):
            doc = json.loads(self.value)
            return doc["token"]

    @property
    def trello_board_list(self):
        assert self.kind == "trello"
        if self.value.startswith("{"):
            doc = json.loads(self.value)
            return doc["board_name"], doc["list_name"]

    @property
    def trello_list_id(self):
        assert self.kind == "trello"
        if self.value.startswith("{"):
            doc = json.loads(self.value)
            return doc["list_id"]

    @property
    def email_value(self):
        assert self.kind == "email"
        if not self.value.startswith("{"):
            return self.value

        doc = json.loads(self.value)
        return doc.get("value")

    @property
    def email_notify_up(self):
        assert self.kind == "email"
        if not self.value.startswith("{"):
            return True

        doc = json.loads(self.value)
        return doc.get("up")

    @property
    def email_notify_down(self):
        assert self.kind == "email"
        if not self.value.startswith("{"):
            return True

        doc = json.loads(self.value)
        return doc.get("down")

    @property
    def whatsapp_notify_up(self):
        assert self.kind == "whatsapp"
        doc = json.loads(self.value)
        return doc["up"]

    @property
    def whatsapp_notify_down(self):
        assert self.kind == "whatsapp"
        doc = json.loads(self.value)
        return doc["down"]


class Notification(models.Model):
    class Meta:
        get_latest_by = "created"

    code = models.UUIDField(default=uuid.uuid4, null=True, editable=False)
    owner = models.ForeignKey(Check, models.CASCADE)
    check_status = models.CharField(max_length=6)
    channel = models.ForeignKey(Channel, models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    error = models.CharField(max_length=200, blank=True)

    def bounce_url(self):
        return settings.SITE_ROOT + reverse("hc-api-bounce", args=[self.code])


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

    def send_alerts(self):
        if self.new_status == "up" and self.old_status in ("new", "paused"):
            # Don't send alerts on new->up and paused->up transitions
            return []

        if self.new_status not in ("up", "down"):
            raise NotImplementedError("Unexpected status: %s" % self.status)

        errors = []
        for channel in self.owner.channel_set.all():
            error = channel.notify(self.owner)
            if error not in ("", "no-op"):
                errors.append((channel, error))

        return errors


class TokenBucket(models.Model):
    value = models.CharField(max_length=80, unique=True)
    tokens = models.FloatField(default=1.0)
    updated = models.DateTimeField(default=timezone.now)

    @staticmethod
    def authorize(value, capacity, refill_time_secs):
        now = timezone.now()
        obj, created = TokenBucket.objects.get_or_create(value=value)

        if not created:
            # Top up the bucket:
            delta_secs = (now - obj.updated).total_seconds()
            obj.tokens = min(1.0, obj.tokens + delta_secs / refill_time_secs)

        obj.tokens -= 1.0 / capacity
        if obj.tokens < 0:
            # Not enough tokens
            return False

        # Race condition: two concurrent authorize calls can overwrite each
        # other's changes. It's OK to be a little inexact here for the sake
        # of simplicity.
        obj.updated = now
        obj.save()

        return True

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
