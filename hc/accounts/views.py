from __future__ import annotations

import logging
import time
from datetime import timedelta as td
from secrets import token_urlsafe
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pyotp
import segno
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.db.models.functions import Lower
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.middleware import csrf
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import Resolver404, resolve, reverse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from hc.accounts import forms
from hc.accounts.decorators import require_sudo_mode
from hc.accounts.http import AuthenticatedHttpRequest
from hc.accounts.models import Credential, Member, Profile, Project
from hc.api.models import Channel, Check, TokenBucket
from hc.lib.tz import all_timezones
from hc.lib.webauthn import CreateHelper, GetHelper
from hc.payments.models import Subscription

logger = logging.getLogger(__name__)

POST_LOGIN_ROUTES = (
    "hc-checks",
    "hc-details",
    "hc-log",
    "hc-channels",
    "hc-add-slack",
    "hc-add-pushover",
    "hc-add-telegram",
    "hc-project-settings",
    "hc-uncloak",
)


def _allow_redirect(redirect_url: str | None) -> bool:
    if not redirect_url:
        return False

    parsed = urlparse(redirect_url)
    if parsed.netloc:
        # Allow redirects only to relative URLs
        return False

    try:
        match = resolve(parsed.path)
    except Resolver404:
        return False

    return match.url_name in POST_LOGIN_ROUTES


def _make_user(email: str, tz: str | None = None, with_project: bool = True) -> User:
    username = str(uuid4())[:30]
    user = User(username=username, email=email)
    user.set_unusable_password()
    user.save()

    project = None
    if with_project:
        project = Project(owner=user)
        project.badge_key = user.username
        project.save()

        check = Check(project=project)
        check.name = "My First Check"
        check.slug = "my-first-check"
        check.save()

        channel = Channel(project=project)
        channel.kind = "email"
        channel.value = email
        channel.email_verified = True
        channel.save()

        channel.checks.add(check)

    # Ensure a profile gets created
    profile = Profile.objects.for_user(user)
    if tz:
        profile.tz = tz
        profile.save()

    return user


def _redirect_after_login(request: HttpRequest) -> HttpResponse:
    """Redirect to the URL indicated in ?next= query parameter."""

    redirect_url = request.GET.get("next")
    if redirect_url and _allow_redirect(redirect_url):
        return redirect(redirect_url)

    assert isinstance(request.user, User)
    if request.user.project_set.count() == 1:
        project = request.user.project_set.get()
        return redirect("hc-checks", project.code)

    return redirect("hc-index")


def _check_2fa(request: HttpRequest, user: User) -> HttpResponse:
    have_keys = user.credentials.exists()
    profile = Profile.objects.for_user(user)
    if have_keys or profile.totp:
        # We have verified user's password or token, and now must
        # verify their security key. We store the following in user's session:
        # - user.id, to look up the user in the login_webauthn view
        # - user.email, to make sure email was not changed between the auth steps
        # - timestamp, to limit the max time between the auth steps
        request.session["2fa_user"] = [user.id, user.email, int(time.time())]

        if have_keys:
            path = reverse("hc-login-webauthn")
        else:
            path = reverse("hc-login-totp")

        redirect_url = request.GET.get("next")
        if _allow_redirect(redirect_url):
            path += "?next=%s" % redirect_url

        return redirect(path)

    auth_login(request, user)
    return _redirect_after_login(request)


def _new_key(nbytes: int = 24) -> str:
    while True:
        candidate = token_urlsafe(nbytes)
        if candidate[0] not in "-_" and candidate[-1] not in "-_":
            return candidate


def _set_autologin_cookie(response: HttpResponse) -> None:
    # check_token looks for this cookie to decide if
    # it needs to do the extra POST step.
    response.set_cookie(
        "auto-login",
        "1",
        max_age=300,
        httponly=True,
        samesite="Lax",
        secure=bool(settings.SESSION_COOKIE_SECURE),
    )


@sensitive_post_parameters()
def login(request: HttpRequest) -> HttpResponse:
    form = forms.PasswordLoginForm()
    magic_form = forms.EmailLoginForm()
    if request.method == "POST":
        if request.POST.get("action") == "login":
            form = forms.PasswordLoginForm(request.POST)
            if form.is_valid():
                assert isinstance(form.user, User)
                return _check_2fa(request, form.user)

        else:
            magic_form = forms.EmailLoginForm(request)
            if magic_form.is_valid():
                redirect_url = request.GET.get("next")
                if not _allow_redirect(redirect_url):
                    redirect_url = None

                if magic_form.user:
                    profile = Profile.objects.for_user(magic_form.user)
                    profile.send_instant_login_link(redirect_url=redirect_url)

                response = redirect("hc-login-link-sent")
                _set_autologin_cookie(response)
                return response

    if request.user.is_authenticated:
        return _redirect_after_login(request)

    bad_link = request.session.pop("bad_link", None)
    ctx = {
        "page": "login",
        "form": form,
        "magic_form": magic_form,
        "bad_link": bad_link,
        "registration_open": settings.REGISTRATION_OPEN,
        "support_email": settings.SUPPORT_EMAIL,
        "account_closed": "account-closed" in request.GET,
    }
    return render(request, "accounts/login.html", ctx)


@require_POST
def logout(request: HttpRequest) -> HttpResponse:
    auth_logout(request)
    return redirect("hc-index")


def signup_csrf(request: HttpRequest) -> HttpResponse:
    if not settings.REGISTRATION_OPEN or request.user.is_authenticated:
        return HttpResponseForbidden()

    return HttpResponse(csrf.get_token(request))


@require_POST
def signup(request: HttpRequest) -> HttpResponse:
    if not settings.REGISTRATION_OPEN or request.user.is_authenticated:
        return HttpResponseForbidden()

    ctx = {}
    form = forms.SignupForm(request)
    if form.is_valid():
        email = form.cleaned_data["identity"]
        try:
            user = User.objects.get(email=email)
            # Sometimes existing users forget they already have an account.
            # They use the signup form and are confused why no email arrives.
            # To avoid this confusion, if we see the user account already exists,
            # we will send them sign-in link even though they used the wrong form
            # ("sign up" instead of "sign in").
        except User.DoesNotExist:
            # If the user does not exist, create a new user account.
            tz = form.cleaned_data["tz"]
            user = _make_user(email, tz)

        profile = Profile.objects.for_user(user)
        profile.send_instant_login_link()
    else:
        ctx = {"form": form}

    response = render(request, "accounts/signup_result.html", ctx)
    if "form" not in ctx:
        _set_autologin_cookie(response)

    return response


def login_link_sent(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/login_link_sent.html")


def check_token(
    request: HttpRequest, username: str, token: str, new_email: str | None = None
) -> HttpResponse:
    if request.user.is_authenticated:
        auth_logout(request)

    # Some email servers open links in emails to check for malicious content.
    # To work around this, we sign user in if the method is POST
    # *or* if the browser presents a cookie we had set when sending the login link.
    #
    # If the method is GET and the auto-login cookie isn't present, we serve
    # a HTML form with a submit button.
    if request.method != "POST" and "auto-login" not in request.COOKIES:
        return render(request, "accounts/check_token_submit.html")

    user = authenticate(username=username, token=token)
    if user is not None and user.is_active:
        assert isinstance(user, User)
        if new_email:
            if User.objects.filter(email=new_email).exists():
                request.session["bad_link"] = True
                return redirect("hc-login")

            user.email = new_email
            user.set_unusable_password()
            user.save()

        user.profile.token = ""
        user.profile.save()
        return _check_2fa(request, user)

    request.session["bad_link"] = True
    return redirect("hc-login")


@login_required
def profile(request: AuthenticatedHttpRequest) -> HttpResponse:
    profile = request.profile

    ctx = {
        "page": "profile",
        "profile": profile,
        "my_projects_status": "default",
        "2fa_status": "default",
        "added_credential_name": request.session.pop("added_credential_name", ""),
        "removed_credential_name": request.session.pop("removed_credential_name", ""),
        "enabled_totp": request.session.pop("enabled_totp", False),
        "disabled_totp": request.session.pop("disabled_totp", False),
        "credentials": list(request.user.credentials.order_by("id")),
        "use_webauthn": settings.RP_ID,
    }

    if ctx["added_credential_name"] or ctx["enabled_totp"]:
        ctx["2fa_status"] = "success"

    if ctx["removed_credential_name"] or ctx["disabled_totp"]:
        ctx["2fa_status"] = "info"

    if request.session.pop("changed_password", False):
        ctx["changed_password"] = True
        ctx["email_password_status"] = "success"

    if request.method == "POST" and "leave_project" in request.POST:
        code = request.POST["code"]
        try:
            project = Project.objects.get(code=code, member__user=request.user)
        except Project.DoesNotExist:
            return HttpResponseBadRequest()

        Member.objects.filter(project=project, user=request.user).delete()

        ctx["left_project"] = project
        ctx["my_projects_status"] = "info"

    ctx["ownerships"] = request.user.project_set.order_by(Lower("name"))
    ctx["memberships"] = request.user.memberships.order_by(Lower("project__name"))
    return render(request, "accounts/profile.html", ctx)


@login_required
@require_POST
def add_project(request: AuthenticatedHttpRequest) -> HttpResponse:
    form = forms.ProjectNameForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()

    project = Project(owner=request.user)
    project.code = project.badge_key = str(uuid4())
    project.name = form.cleaned_data["name"]
    project.save()

    return redirect("hc-checks", project.code)


@login_required
def project(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = get_object_or_404(Project, code=code)
    is_owner = project.owner_id == request.user.id

    if request.user.is_superuser or is_owner:
        is_manager = True
        rw = True
    else:
        membership = get_object_or_404(Member, project=project, user=request.user)
        is_manager = membership.role == Member.Role.MANAGER
        rw = membership.is_rw

    ctx = {
        "page": "project",
        "rw": rw,
        "project": project,
        "is_owner": is_owner,
        "is_manager": is_manager,
        "show_api_keys": "show_api_keys" in request.GET,
        "enable_prometheus": settings.PROMETHEUS_ENABLED is True,
    }

    if request.method == "POST":
        if "create_key" in request.POST:
            if not rw:
                return HttpResponseForbidden()

            if request.POST["create_key"] == "api_key":
                project.api_key = _new_key(24)
            elif request.POST["create_key"] == "api_key_readonly":
                project.api_key_readonly = _new_key(24)
            elif request.POST["create_key"] == "ping_key":
                project.ping_key = _new_key(16)
            project.save()

            ctx["key_created"] = True
            ctx["api_status"] = "success"
            ctx["show_keys"] = True
        elif "revoke_key" in request.POST:
            if not rw:
                return HttpResponseForbidden()

            if request.POST["revoke_key"] == "api_key":
                project.api_key = ""
            elif request.POST["revoke_key"] == "api_key_readonly":
                project.api_key_readonly = ""
            elif request.POST["revoke_key"] == "ping_key":
                project.ping_key = None
            project.save()

            ctx["key_revoked"] = True
            ctx["api_status"] = "info"
        elif "show_keys" in request.POST:
            if not rw:
                return HttpResponseForbidden()

            ctx["show_keys"] = True
        elif "invite_team_member" in request.POST:
            if not is_manager:
                return HttpResponseForbidden()

            invite_form = forms.InviteTeamMemberForm(request.POST)
            if invite_form.is_valid():
                email = invite_form.cleaned_data["email"]

                invite_suggestions = project.invite_suggestions()
                if not invite_suggestions.filter(email=email).exists():
                    # We're inviting a new user. Are we within team size limit?
                    if not project.can_invite_new_users():
                        return HttpResponseForbidden()

                    # And are we not hitting a rate limit?
                    if not TokenBucket.authorize_invite(request.user):
                        return render(request, "try_later.html")

                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = _make_user(email, with_project=False)

                if project.invite(user, role=invite_form.cleaned_data["role"]):
                    ctx["team_member_invited"] = email
                    ctx["team_status"] = "success"
                else:
                    ctx["team_member_duplicate"] = email
                    ctx["team_status"] = "info"

        elif "remove_team_member" in request.POST:
            if not is_manager:
                return HttpResponseForbidden()

            remove_form = forms.RemoveTeamMemberForm(request.POST)
            if remove_form.is_valid():
                q = User.objects.filter(
                    email=remove_form.cleaned_data["email"],
                    memberships__project=project,
                )
                farewell_user = q.first()
                if farewell_user is None:
                    return HttpResponseBadRequest()

                if farewell_user == request.user:
                    return HttpResponseBadRequest()

                Member.objects.filter(project=project, user=farewell_user).delete()

                ctx["team_member_removed"] = remove_form.cleaned_data["email"]
                ctx["team_status"] = "info"
        elif "set_project_name" in request.POST:
            if not rw:
                return HttpResponseForbidden()

            name_form = forms.ProjectNameForm(request.POST)
            if name_form.is_valid():
                project.name = name_form.cleaned_data["name"]
                project.save()

                ctx["project_name_updated"] = True
                ctx["project_name_status"] = "success"

        elif "transfer_project" in request.POST:
            if not is_owner:
                return HttpResponseForbidden()

            transfer_form = forms.TransferForm(request.POST)
            if transfer_form.is_valid():
                # Look up the proposed new owner
                email = transfer_form.cleaned_data["email"]
                try:
                    membership = project.member_set.filter(user__email=email).get()
                except Member.DoesNotExist:
                    return HttpResponseBadRequest()

                # Revoke any previous transfer requests
                project.member_set.update(transfer_request_date=None)

                # Initiate the new request
                membership.transfer_request_date = now()
                membership.save()

                # Send an email notification
                profile = Profile.objects.for_user(membership.user)
                profile.send_transfer_request(project)

                ctx["transfer_initiated"] = True
                ctx["transfer_status"] = "success"

        elif "cancel_transfer" in request.POST:
            if not is_owner:
                return HttpResponseForbidden()

            project.member_set.update(transfer_request_date=None)
            ctx["transfer_cancelled"] = True
            ctx["transfer_status"] = "success"

        elif "accept_transfer" in request.POST:
            tr = project.transfer_request()
            if not tr or tr.user != request.user:
                return HttpResponseForbidden()

            if not tr.can_accept():
                return HttpResponseBadRequest()

            with transaction.atomic():
                # 1. Reuse the existing membership, and change its user
                tr.user = project.owner
                tr.transfer_request_date = None
                # The previous owner becomes a regular member
                # (not readonly, not manager):
                tr.role = Member.Role.REGULAR
                tr.save()

                # 2. Change project's owner
                project.owner = request.user
                project.save()

            ctx["is_owner"] = True
            ctx["is_manager"] = True
            messages.success(request, "You are now the owner of this project!")

        elif "reject_transfer" in request.POST:
            tr = project.transfer_request()
            if not tr or tr.user != request.user:
                return HttpResponseForbidden()

            tr.transfer_request_date = None
            tr.save()

    mq = project.member_set.select_related("user").order_by("user__email")
    ctx["memberships"] = list(mq)
    ctx["can_invite_new_users"] = project.can_invite_new_users()
    return render(request, "accounts/project.html", ctx)


@login_required
def notifications(request: AuthenticatedHttpRequest) -> HttpResponse:
    profile = request.profile

    ctx = {
        "status": "default",
        "page": "profile",
        "profile": profile,
        "timezones": all_timezones,
    }

    if request.method == "POST":
        form = forms.ReportSettingsForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["tz"]:
                profile.tz = form.cleaned_data["tz"]
            profile.reports = form.cleaned_data["reports"]
            profile.next_report_date = profile.choose_next_report_date()

            if profile.nag_period != form.cleaned_data["nag_period"]:
                # Set the new nag period
                profile.nag_period = form.cleaned_data["nag_period"]
                # and update next_nag_date:
                if profile.nag_period:
                    profile.update_next_nag_date()
                else:
                    profile.next_nag_date = None

            profile.save()
            ctx["status"] = "info"

    return render(request, "accounts/notifications.html", ctx)


@login_required
@sensitive_post_parameters()
@require_sudo_mode
def set_password(request: AuthenticatedHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = forms.SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data["password"]
            request.user.set_password(password)
            request.user.save()

            request.profile.token = ""
            request.profile.save()

            # update the session with the new password hash so that
            # the user doesn't  get logged out
            update_session_auth_hash(request, request.user)

            request.session["changed_password"] = True
            return redirect("hc-profile")

    return render(request, "accounts/set_password.html", {})


@login_required
@require_sudo_mode
def change_email(request: AuthenticatedHttpRequest) -> HttpResponse:
    if "sent" in request.session:
        ctx = {"email": request.session.pop("sent")}
        return render(request, "accounts/change_email_instructions.html", ctx)

    if request.method == "POST":
        form = forms.ChangeEmailForm(request.POST)
        if form.is_valid():
            # The user has entered a valid-looking new email address.
            # Send a special login link to the new address. When the user
            # clicks the special login link, hc.accounts.views.change_email_verify
            # unpacks the payload, and passes it to hc.accounts.views.check_token,
            # which finally updates user's email address.
            email = form.cleaned_data["email"]
            request.profile.send_change_email_link(email)
            request.session["sent"] = email

            response = redirect(reverse("hc-change-email"))
            # check_token looks for this cookie to decide if
            # it needs to do the extra POST step.
            _set_autologin_cookie(response)
            return response
    else:
        form = forms.ChangeEmailForm()

    return render(request, "accounts/change_email.html", {"form": form})


def change_email_verify(request: HttpRequest, signed_payload: str) -> HttpResponse:
    try:
        payload = TimestampSigner().unsign_object(signed_payload, max_age=900)
    except BadSignature:
        return render(request, "bad_link.html")

    return check_token(request, payload["u"], payload["t"], payload["e"])


@csrf_exempt
def unsubscribe_reports(request: HttpRequest, signed_username: str) -> HttpResponse:
    # Some email servers open links in emails to check for malicious content.
    # To work around this, for GET requests we serve a confirmation form.
    # If the signature is more than 5 minutes old, we also include JS code to
    # auto-submit the form.

    signer = TimestampSigner(salt="reports")
    # First, check the signature without looking at the timestamp:
    try:
        username = signer.unsign(signed_username)
    except BadSignature:
        return render(request, "bad_link.html")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # This is likely an old unsubscribe link, and the user account has already
        # been deleted. Show the "Unsubscribed!" page nevertheless.
        return render(request, "accounts/unsubscribed.html")

    if request.method != "POST":
        # Unsign again, now with max_age set,
        # to see if the timestamp is older than 5 minutes
        try:
            autosubmit = False
            username = signer.unsign(signed_username, max_age=300)
        except SignatureExpired:
            autosubmit = True

        ctx = {"autosubmit": autosubmit}
        return render(request, "accounts/unsubscribe_submit.html", ctx)

    profile = Profile.objects.for_user(user)
    profile.reports = "off"
    profile.next_report_date = None
    profile.nag_period = td()
    profile.next_nag_date = None
    profile.save()

    return render(request, "accounts/unsubscribed.html")


@login_required
@require_sudo_mode
def close(request: AuthenticatedHttpRequest) -> HttpResponse:
    user = request.user

    if request.method == "POST":
        if request.POST.get("confirmation") == request.user.email:
            # Cancel their subscription:
            if sub := Subscription.objects.filter(user=user).first():
                sub.cancel()

            # Deleting user also deletes its profile, checks, channels etc.
            user.delete()

            request.session.flush()
            path = reverse("hc-login") + "?account-closed"
            return redirect(path)

    ctx = {}
    if "confirmation" in request.POST:
        ctx["wrong_confirmation"] = True

    return render(request, "accounts/close_account.html", ctx)


@require_POST
@login_required
def remove_project(request: AuthenticatedHttpRequest, code: str) -> HttpResponse:
    project = get_object_or_404(Project, code=code, owner=request.user)
    for check in project.check_set.all():
        check.lock_and_delete()
    project.delete()
    return redirect("hc-index")


@login_required
@require_sudo_mode
def add_webauthn(request: AuthenticatedHttpRequest) -> HttpResponse:
    if not settings.RP_ID:
        return HttpResponse(status=404)

    credentials = request.user.credentials.values_list("data", flat=True)
    helper = CreateHelper(settings.RP_ID, credentials)

    if request.method == "POST":
        form = forms.AddWebAuthnForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        state = request.session["state"]
        try:
            credential_bytes = helper.verify(state, form.cleaned_data["response"])
        except ValueError as e:
            logger.exception("CreateHelper.verify failed, form: %s", form.cleaned_data)
            return HttpResponseBadRequest()

        c = Credential(user=request.user)
        c.name = form.cleaned_data["name"]
        c.data = credential_bytes
        c.save()

        request.session.pop("state")
        request.session["added_credential_name"] = c.name
        return redirect("hc-profile")

    options, request.session["state"] = helper.prepare(request.user.email)
    return render(request, "accounts/add_credential.html", {"options": options})


@login_required
@require_sudo_mode
def add_totp(request: AuthenticatedHttpRequest) -> HttpResponse:
    if request.profile.totp:
        # TOTP is already configured, refuse to continue
        return HttpResponseBadRequest()

    if "totp_secret" not in request.session:
        request.session["totp_secret"] = pyotp.random_base32()

    totp = pyotp.totp.TOTP(request.session["totp_secret"])

    if request.method == "POST":
        form = forms.TotpForm(totp, request.POST)
        if form.is_valid():
            request.profile.totp = request.session["totp_secret"]
            request.profile.totp_created = now()
            request.profile.save()

            request.session["enabled_totp"] = True
            request.session.pop("totp_secret")
            return redirect("hc-profile")
    else:
        form = forms.TotpForm(totp)

    uri = totp.provisioning_uri(name=request.user.email, issuer_name=settings.SITE_NAME)
    qr_data_uri = segno.make(uri).png_data_uri(scale=8)
    ctx = {
        "form": form,
        "qr_data_uri": qr_data_uri,
        "secret": request.session["totp_secret"],
    }
    return render(request, "accounts/add_totp.html", ctx)


@login_required
@require_sudo_mode
def remove_totp(request: AuthenticatedHttpRequest) -> HttpResponse:
    if request.method == "POST" and "disable_totp" in request.POST:
        request.profile.totp = None
        request.profile.totp_created = None
        request.profile.save()
        request.session["disabled_totp"] = True
        return redirect("hc-profile")

    ctx = {"is_last": not request.user.credentials.exists()}
    return render(request, "accounts/remove_totp.html", ctx)


@login_required
@require_sudo_mode
def remove_credential(request: AuthenticatedHttpRequest, code: str) -> HttpResponse:
    if not settings.RP_ID:
        return HttpResponse(status=404)

    try:
        credential = Credential.objects.get(user=request.user, code=code)
    except Credential.DoesNotExist:
        return HttpResponseBadRequest()

    if request.method == "POST" and "remove_credential" in request.POST:
        request.session["removed_credential_name"] = credential.name
        credential.delete()
        return redirect("hc-profile")

    if request.profile.totp:
        is_last = False
    else:
        is_last = request.user.credentials.count() == 1

    ctx = {"credential": credential, "is_last": is_last}
    return render(request, "accounts/remove_credential.html", ctx)


def login_webauthn(request: HttpRequest) -> HttpResponse:
    # We require RP_ID. Fail predicably if it is not set:
    if not settings.RP_ID:
        return HttpResponse(status=404)

    # Expect an unauthenticated user
    if request.user.is_authenticated:
        return HttpResponseBadRequest()

    if "2fa_user" not in request.session:
        return HttpResponseBadRequest()

    user_id, email, timestamp = request.session["2fa_user"]
    if timestamp + 300 < time.time():
        return redirect("hc-login")

    try:
        user = User.objects.get(id=user_id, email=email)
    except User.DoesNotExist:
        return HttpResponseBadRequest()

    credentials = user.credentials.values_list("data", flat=True)
    helper = GetHelper(settings.RP_ID, credentials)

    if request.method == "POST":
        form = forms.WebAuthnForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        if not helper.verify(request.session["state"], form.cleaned_data["response"]):
            return HttpResponseBadRequest()

        request.session.pop("state")
        request.session.pop("2fa_user")
        auth_login(request, user, "hc.accounts.backends.EmailBackend")
        return _redirect_after_login(request)

    options, request.session["state"] = helper.prepare()

    totp_url = None
    if user.profile.totp:
        totp_url = reverse("hc-login-totp")
        redirect_url = request.GET.get("next")
        if _allow_redirect(redirect_url):
            totp_url += "?next=%s" % redirect_url

    ctx = {
        "options": options,
        "totp_url": totp_url,
    }
    return render(request, "accounts/login_webauthn.html", ctx)


def login_totp(request: HttpRequest) -> HttpResponse:
    # Expect an unauthenticated user
    if request.user.is_authenticated:
        return HttpResponseBadRequest()

    if "2fa_user" not in request.session:
        return HttpResponseBadRequest()

    user_id, email, timestamp = request.session["2fa_user"]
    if timestamp + 300 < time.time():
        return redirect("hc-login")

    try:
        user = User.objects.get(id=user_id, email=email)
    except User.DoesNotExist:
        return HttpResponseBadRequest()

    if not user.profile.totp:
        return HttpResponseBadRequest()

    totp = pyotp.totp.TOTP(user.profile.totp)
    if request.method == "POST":
        # To guard against brute-forcing TOTP codes, we allow
        # 96 attempts per user per 24h.
        if not TokenBucket.authorize_totp_attempt(user):
            return render(request, "try_later.html")

        form = forms.TotpForm(totp, request.POST)
        if form.is_valid():
            # We blacklist an used TOTP code for 90 seconds,
            # so an attacker cannot reuse a stolen code.
            if not TokenBucket.authorize_totp_code(user, form.cleaned_data["code"]):
                return render(request, "try_later.html")

            request.session.pop("2fa_user")
            auth_login(request, user, "hc.accounts.backends.EmailBackend")
            return _redirect_after_login(request)
    else:
        form = forms.TotpForm(totp)

    return render(request, "accounts/login_totp.html", {"form": form})


@login_required
def appearance(request: AuthenticatedHttpRequest) -> HttpResponse:
    profile = request.profile

    ctx = {
        "page": "appearance",
        "profile": profile,
        "status": "default",
    }

    if request.method == "POST":
        theme = request.POST.get("theme", "")
        if theme in ("", "dark", "system"):
            profile.theme = theme
            profile.save()
            ctx["status"] = "info"

    return render(request, "accounts/appearance.html", ctx)
