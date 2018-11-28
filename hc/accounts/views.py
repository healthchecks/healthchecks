from datetime import timedelta as td
import uuid
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from hc.accounts.forms import (ChangeEmailForm, EmailPasswordForm,
                               InviteTeamMemberForm, RemoveTeamMemberForm,
                               ReportSettingsForm, SetPasswordForm,
                               TeamNameForm, AvailableEmailForm,
                               ExistingEmailForm)
from hc.accounts.models import Profile, Member
from hc.api.models import Channel, Check
from hc.lib.badges import get_badge_url
from hc.payments.models import Subscription

NEXT_WHITELIST = ("/checks/",
                  "/integrations/add_slack/",
                  "/integrations/add_pushover/")


def _make_user(email):
    username = str(uuid.uuid4())[:30]
    user = User(username=username, email=email)
    user.set_unusable_password()
    user.save()

    # Ensure a profile gets created
    Profile.objects.for_user(user)

    check = Check(user=user)
    check.name = "My First Check"
    check.save()

    channel = Channel(user=user)
    channel.kind = "email"
    channel.value = email
    channel.email_verified = True
    channel.save()

    channel.checks.add(check)

    return user


def _ensure_own_team(request):
    """ Make sure user is switched to their own team. """

    if request.team != request.profile:
        request.team = request.profile
        request.profile.current_team = request.profile
        request.profile.save()


def _redirect_after_login(request):
    """ Redirect to the URL indicated in ?next= query parameter. """

    redirect_url = request.GET.get("next")
    if redirect_url in NEXT_WHITELIST:
        return redirect(redirect_url)

    return redirect("hc-checks")


def login(request):
    form = EmailPasswordForm()
    magic_form = ExistingEmailForm()

    if request.method == 'POST':
        if request.POST.get("action") == "login":
            form = EmailPasswordForm(request.POST)
            if form.is_valid():
                auth_login(request, form.user)
                return _redirect_after_login(request)

        else:
            magic_form = ExistingEmailForm(request.POST)
            if magic_form.is_valid():
                profile = Profile.objects.for_user(magic_form.user)

                redirect_url = request.GET.get("next")
                if redirect_url in NEXT_WHITELIST:
                    profile.send_instant_login_link(redirect_url=redirect_url)
                else:
                    profile.send_instant_login_link()

                return redirect("hc-login-link-sent")

    bad_link = request.session.pop("bad_link", None)
    ctx = {
        "page": "login",
        "form": form,
        "magic_form": magic_form,
        "bad_link": bad_link
    }
    return render(request, "accounts/login.html", ctx)


def logout(request):
    auth_logout(request)
    return redirect("hc-index")


@require_POST
def signup(request):
    if not settings.REGISTRATION_OPEN:
        return HttpResponseForbidden()

    ctx = {}
    form = AvailableEmailForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["identity"]
        user = _make_user(email)
        profile = Profile.objects.for_user(user)
        profile.send_instant_login_link()
        ctx["created"] = True
    else:
        ctx = {"form": form}

    return render(request, "accounts/signup_result.html", ctx)


def login_link_sent(request):
    return render(request, "accounts/login_link_sent.html")


def link_sent(request):
    return render(request, "accounts/link_sent.html")


def check_token(request, username, token):
    if request.user.is_authenticated and request.user.username == username:
        # User is already logged in
        return _redirect_after_login(request)

    # Some email servers open links in emails to check for malicious content.
    # To work around this, we sign user in if the method is POST.
    #
    # If the method is GET, we instead serve a HTML form and a piece
    # of Javascript to automatically submit it.

    if request.method == "POST":
        user = authenticate(username=username, token=token)
        if user is not None and user.is_active:
            user.profile.token = ""
            user.profile.save()
            auth_login(request, user)

            return _redirect_after_login(request)

        request.session["bad_link"] = True
        return redirect("hc-login")

    return render(request, "accounts/check_token_submit.html")


@login_required
def profile(request):
    _ensure_own_team(request)
    profile = request.profile

    ctx = {
        "page": "profile",
        "profile": profile,
        "show_api_keys": False,
        "api_status": "default",
        "team_status": "default"
    }

    if request.method == "POST":
        if "change_email" in request.POST:
            profile.send_change_email_link()
            return redirect("hc-link-sent")
        elif "set_password" in request.POST:
            profile.send_set_password_link()
            return redirect("hc-link-sent")
        elif "create_api_keys" in request.POST:
            profile.set_api_keys()
            ctx["show_api_keys"] = True
            ctx["api_keys_created"] = True
            ctx["api_status"] = "success"
        elif "revoke_api_keys" in request.POST:
            profile.api_key_id = ""
            profile.api_key = ""
            profile.api_key_readonly = ""
            profile.save()
            ctx["api_keys_revoked"] = True
            ctx["api_status"] = "info"
        elif "show_api_keys" in request.POST:
            ctx["show_api_keys"] = True
        elif "invite_team_member" in request.POST:
            if not profile.can_invite():
                return HttpResponseForbidden()

            form = InviteTeamMemberForm(request.POST)
            if form.is_valid():

                email = form.cleaned_data["email"]
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = _make_user(email)

                profile.invite(user)
                ctx["team_member_invited"] = email
                ctx["team_status"] = "success"

        elif "remove_team_member" in request.POST:
            form = RemoveTeamMemberForm(request.POST)
            if form.is_valid():

                email = form.cleaned_data["email"]
                farewell_user = User.objects.get(email=email)
                farewell_user.profile.current_team = None
                farewell_user.profile.save()

                Member.objects.filter(team=profile,
                                      user=farewell_user).delete()

                ctx["team_member_removed"] = email
                ctx["team_status"] = "info"
        elif "set_team_name" in request.POST:
            form = TeamNameForm(request.POST)
            if form.is_valid():
                profile.team_name = form.cleaned_data["team_name"]
                profile.save()
                ctx["team_name_updated"] = True
                ctx["team_status"] = "success"

    return render(request, "accounts/profile.html", ctx)


@login_required
def notifications(request):
    _ensure_own_team(request)
    profile = request.profile

    ctx = {
        "status": "default",
        "page": "profile",
        "profile": profile
    }

    if request.method == "POST":
        form = ReportSettingsForm(request.POST)
        if form.is_valid():
            if profile.reports_allowed != form.cleaned_data["reports_allowed"]:
                profile.reports_allowed = form.cleaned_data["reports_allowed"]
                if profile.reports_allowed:
                    profile.next_report_date = now() + td(days=30)
                else:
                    profile.next_report_date = None

            if profile.nag_period != form.cleaned_data["nag_period"]:
                # Set the new nag period
                profile.nag_period = form.cleaned_data["nag_period"]
                # and schedule next_nag_date:
                if profile.nag_period:
                    profile.next_nag_date = now() + profile.nag_period
                else:
                    profile.next_nag_date = None

            profile.save()
            ctx["status"] = "info"

    return render(request, "accounts/notifications.html", ctx)


@login_required
def badges(request):
    _ensure_own_team(request)

    teams = [request.profile]
    for membership in request.user.memberships.all():
        teams.append(membership.team)

    badge_sets = []
    for team in teams:
        tags = set()
        for check in Check.objects.filter(user=team.user):
            tags.update(check.tags_list())

        sorted_tags = sorted(tags, key=lambda s: s.lower())
        sorted_tags.append("*")  # For the "overall status" badge

        urls = []
        username = team.user.username
        for tag in sorted_tags:
            if not re.match("^[\w-]+$", tag) and tag != "*":
                continue

            urls.append({
                "svg": get_badge_url(username, tag),
                "json": get_badge_url(username, tag, format="json"),
            })

        badge_sets.append({"team": team, "urls": urls})

    ctx = {
        "page": "profile",
        "badges": badge_sets
    }

    return render(request, "accounts/badges.html", ctx)


@login_required
def set_password(request, token):
    if not request.profile.check_token(token, "set-password"):
        return HttpResponseBadRequest()

    if request.method == "POST":
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data["password"]
            request.user.set_password(password)
            request.user.save()

            request.profile.token = ""
            request.profile.save()

            # Setting a password logs the user out, so here we
            # log them back in.
            u = authenticate(username=request.user.email, password=password)
            auth_login(request, u)

            messages.success(request, "Your password has been set!")
            return redirect("hc-profile")

    return render(request, "accounts/set_password.html", {})


@login_required
def change_email(request, token):
    if not request.profile.check_token(token, "change-email"):
        return HttpResponseBadRequest()

    if request.method == "POST":
        form = ChangeEmailForm(request.POST)
        if form.is_valid():
            request.user.email = form.cleaned_data["email"]
            request.user.set_unusable_password()
            request.user.save()

            request.profile.token = ""
            request.profile.save()

            return redirect("hc-change-email-done")
    else:
        form = ChangeEmailForm()

    return render(request, "accounts/change_email.html", {"form": form})


def change_email_done(request):
    return render(request, "accounts/change_email_done.html")


@csrf_exempt
def unsubscribe_reports(request, username):
    signer = signing.TimestampSigner(salt="reports")
    try:
        username = signer.unsign(username)
    except signing.BadSignature:
        return render(request, "bad_link.html")

    # Some email servers open links in emails to check for malicious content.
    # To work around this, we serve a form that auto-submits with JS.
    if "ask" in request.GET and request.method != "POST":
        return render(request, "accounts/unsubscribe_submit.html")

    user = User.objects.get(username=username)
    profile = Profile.objects.for_user(user)
    profile.reports_allowed = False
    profile.next_report_date = None
    profile.nag_period = td()
    profile.next_nag_date = None
    profile.save()

    return render(request, "accounts/unsubscribed.html")


@login_required
def switch_team(request, target_username):
    try:
        target_team = Profile.objects.get(user__username=target_username)
    except Profile.DoesNotExist:
        return HttpResponseForbidden()

    # The rules:
    # Superuser can switch to any team.
    access_ok = request.user.is_superuser

    # Users can switch to their own teams.
    if not access_ok and target_team == request.profile:
        access_ok = True

    # Users can switch to teams they are members of.
    if not access_ok:
        access_ok = request.user.memberships.filter(team=target_team).exists()

    if not access_ok:
        return HttpResponseForbidden()

    request.profile.current_team = target_team
    request.profile.save()

    return redirect("hc-checks")


@require_POST
@login_required
def close(request):
    user = request.user

    # Subscription needs to be canceled before it is deleted:
    sub = Subscription.objects.filter(user=user).first()
    if sub:
        sub.cancel()

    user.delete()

    # Deleting user also deletes its profile, checks, channels etc.

    request.session.flush()
    return redirect("hc-index")
