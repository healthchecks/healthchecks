import base64
from datetime import timedelta as td
from urllib.parse import urlparse
import uuid

from django.db import transaction
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.urls import resolve, reverse, Resolver404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity
from fido2 import cbor
from hc.accounts import forms
from hc.accounts.decorators import require_sudo_mode
from hc.accounts.models import Credential, Profile, Project, Member
from hc.api.models import Channel, Check, TokenBucket
from hc.lib.date import choose_next_report_date
from hc.payments.models import Subscription

POST_LOGIN_ROUTES = (
    "hc-checks",
    "hc-details",
    "hc-log",
    "hc-channels",
    "hc-add-slack",
    "hc-add-pushover",
    "hc-add-telegram",
    "hc-project-settings",
)


def _allow_redirect(redirect_url):
    if not redirect_url:
        return False

    parsed = urlparse(redirect_url)
    try:
        match = resolve(parsed.path)
    except Resolver404:
        return False

    return match.url_name in POST_LOGIN_ROUTES


def _make_user(email, with_project=True):
    username = str(uuid.uuid4())[:30]
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
        check.save()

        channel = Channel(project=project)
        channel.kind = "email"
        channel.value = email
        channel.email_verified = True
        channel.save()

        channel.checks.add(check)

    # Ensure a profile gets created
    Profile.objects.for_user(user)

    return user


def _redirect_after_login(request):
    """ Redirect to the URL indicated in ?next= query parameter. """

    redirect_url = request.GET.get("next")
    if _allow_redirect(redirect_url):
        return redirect(redirect_url)

    if request.user.project_set.count() == 1:
        project = request.user.project_set.first()
        return redirect("hc-checks", project.code)

    return redirect("hc-index")


def _check_2fa(request, user):
    if user.credentials.exists():
        request.session["2fa_user_id"] = user.id

        path = reverse("hc-login-tfa")
        redirect_url = request.GET.get("next")
        if _allow_redirect(redirect_url):
            path += "?next=%s" % redirect_url

        return redirect(path)

    auth_login(request, user)
    return _redirect_after_login(request)


def login(request):
    form = forms.PasswordLoginForm()
    magic_form = forms.EmailLoginForm()

    if request.method == "POST":
        if request.POST.get("action") == "login":
            form = forms.PasswordLoginForm(request.POST)
            if form.is_valid():
                return _check_2fa(request, form.user)

        else:
            magic_form = forms.EmailLoginForm(request.POST)
            if magic_form.is_valid():
                redirect_url = request.GET.get("next")
                if not _allow_redirect(redirect_url):
                    redirect_url = None

                profile = Profile.objects.for_user(magic_form.user)
                profile.send_instant_login_link(redirect_url=redirect_url)
                response = redirect("hc-login-link-sent")

                # check_token_submit looks for this cookie to decide if
                # it needs to do the extra POST step.
                response.set_cookie("auto-login", "1", max_age=300, httponly=True)
                return response

    bad_link = request.session.pop("bad_link", None)
    ctx = {
        "page": "login",
        "form": form,
        "magic_form": magic_form,
        "bad_link": bad_link,
        "registration_open": settings.REGISTRATION_OPEN,
    }
    return render(request, "accounts/login.html", ctx)


def logout(request):
    auth_logout(request)
    return redirect("hc-index")


@require_POST
@csrf_exempt
def signup(request):
    if not settings.REGISTRATION_OPEN:
        return HttpResponseForbidden()

    ctx = {}
    form = forms.AvailableEmailForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["identity"]
        user = _make_user(email)
        profile = Profile.objects.for_user(user)
        profile.send_instant_login_link()
        ctx["created"] = True
    else:
        ctx = {"form": form}

    response = render(request, "accounts/signup_result.html", ctx)
    if ctx.get("created"):
        response.set_cookie("auto-login", "1", max_age=300, httponly=True)

    return response


def login_link_sent(request):
    return render(request, "accounts/login_link_sent.html")


def link_sent(request):
    return render(request, "accounts/link_sent.html")


def check_token(request, username, token):
    if request.user.is_authenticated and request.user.username == username:
        # User is already logged in
        return _redirect_after_login(request)

    # Some email servers open links in emails to check for malicious content.
    # To work around this, we sign user in if the method is POST
    # *or* if the browser presents a cookie we had set when sending the login link.
    #
    # If the method is GET and the auto-login cookie isn't present, we serve
    # a HTML form with a submit button.

    if request.method == "POST" or "auto-login" in request.COOKIES:
        user = authenticate(username=username, token=token)
        if user is not None and user.is_active:
            user.profile.token = ""
            user.profile.save()
            return _check_2fa(request, user)

        request.session["bad_link"] = True
        return redirect("hc-login")

    return render(request, "accounts/check_token_submit.html")


@login_required
def profile(request):
    profile = request.profile

    ctx = {
        "page": "profile",
        "profile": profile,
        "my_projects_status": "default",
        "tfa_status": "default",
        "added_credential_name": request.session.pop("added_credential_name", ""),
        "removed_credential_name": request.session.pop("removed_credential_name", ""),
        "credentials": request.user.credentials.order_by("id"),
    }

    if ctx["added_credential_name"]:
        ctx["tfa_status"] = "success"

    if ctx["removed_credential_name"]:
        ctx["tfa_status"] = "info"

    if request.method == "POST":
        if "change_email" in request.POST:
            profile.send_change_email_link()
            return redirect("hc-link-sent")
        elif "set_password" in request.POST:
            profile.send_set_password_link()
            return redirect("hc-link-sent")
        elif "leave_project" in request.POST:
            code = request.POST["code"]
            try:
                project = Project.objects.get(code=code, member__user=request.user)
            except Project.DoesNotExist:
                return HttpResponseBadRequest()

            Member.objects.filter(project=project, user=request.user).delete()

            ctx["left_project"] = project
            ctx["my_projects_status"] = "info"

    return render(request, "accounts/profile.html", ctx)


@login_required
@require_POST
def add_project(request):
    form = forms.ProjectNameForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()

    project = Project(owner=request.user)
    project.code = project.badge_key = str(uuid.uuid4())
    project.name = form.cleaned_data["name"]
    project.save()

    return redirect("hc-checks", project.code)


@login_required
def project(request, code):
    project = get_object_or_404(Project, code=code)
    is_owner = project.owner_id == request.user.id

    if request.user.is_superuser or is_owner:
        rw = True
    else:
        membership = get_object_or_404(Member, project=project, user=request.user)
        rw = membership.rw

    ctx = {
        "page": "project",
        "rw": rw,
        "project": project,
        "is_owner": is_owner,
        "show_api_keys": "show_api_keys" in request.GET,
    }

    if request.method == "POST":
        if not rw:
            return HttpResponseForbidden()

        if "create_api_keys" in request.POST:
            project.set_api_keys()
            project.save()

            ctx["show_api_keys"] = True
            ctx["api_keys_created"] = True
            ctx["api_status"] = "success"
        elif "revoke_api_keys" in request.POST:
            project.api_key = ""
            project.api_key_readonly = ""
            project.save()

            ctx["api_keys_revoked"] = True
            ctx["api_status"] = "info"
        elif "show_api_keys" in request.POST:
            ctx["show_api_keys"] = True
        elif "invite_team_member" in request.POST:
            if not is_owner:
                return HttpResponseForbidden()

            form = forms.InviteTeamMemberForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data["email"]

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

                if project.invite(user, rw=form.cleaned_data["rw"]):
                    ctx["team_member_invited"] = email
                    ctx["team_status"] = "success"
                else:
                    ctx["team_member_duplicate"] = email
                    ctx["team_status"] = "info"

        elif "remove_team_member" in request.POST:
            if not is_owner:
                return HttpResponseForbidden()

            form = forms.RemoveTeamMemberForm(request.POST)
            if form.is_valid():
                q = User.objects
                q = q.filter(email=form.cleaned_data["email"])
                q = q.filter(memberships__project=project)
                farewell_user = q.first()
                if farewell_user is None:
                    return HttpResponseBadRequest()

                Member.objects.filter(project=project, user=farewell_user).delete()

                ctx["team_member_removed"] = form.cleaned_data["email"]
                ctx["team_status"] = "info"
        elif "set_project_name" in request.POST:
            form = forms.ProjectNameForm(request.POST)
            if form.is_valid():
                project.name = form.cleaned_data["name"]
                project.save()

                ctx["project_name_updated"] = True
                ctx["project_name_status"] = "success"

        elif "transfer_project" in request.POST:
            if not is_owner:
                return HttpResponseForbidden()

            form = forms.TransferForm(request.POST)
            if form.is_valid():
                # Look up the proposed new owner
                email = form.cleaned_data["email"]
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
                tr.save()

                # 2. Change project's owner
                project.owner = request.user
                project.save()

            ctx["is_owner"] = True
            messages.success(request, "You are now the owner of this project!")

        elif "reject_transfer" in request.POST:
            tr = project.transfer_request()
            if not tr or tr.user != request.user:
                return HttpResponseForbidden()

            tr.transfer_request_date = None
            tr.save()

    return render(request, "accounts/project.html", ctx)


@login_required
def notifications(request):
    profile = request.profile

    ctx = {"status": "default", "page": "profile", "profile": profile}

    if request.method == "POST":
        form = forms.ReportSettingsForm(request.POST)
        if form.is_valid():
            if profile.reports_allowed != form.cleaned_data["reports_allowed"]:
                profile.reports_allowed = form.cleaned_data["reports_allowed"]
                if profile.reports_allowed:
                    profile.next_report_date = choose_next_report_date()
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
def set_password(request, token):
    if not request.profile.check_token(token, "set-password"):
        return HttpResponseBadRequest()

    if request.method == "POST":
        form = forms.SetPasswordForm(request.POST)
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
        form = forms.ChangeEmailForm(request.POST)
        if form.is_valid():
            request.user.email = form.cleaned_data["email"]
            request.user.set_unusable_password()
            request.user.save()

            request.profile.token = ""
            request.profile.save()

            return redirect("hc-change-email-done")
    else:
        form = forms.ChangeEmailForm()

    return render(request, "accounts/change_email.html", {"form": form})


def change_email_done(request):
    return render(request, "accounts/change_email_done.html")


@csrf_exempt
def unsubscribe_reports(request, signed_username):
    # Some email servers open links in emails to check for malicious content.
    # To work around this, for GET requests we serve a confirmation form.
    # If the signature is more than 5 minutes old, we also include JS code to
    # auto-submit the form.

    ctx = {}
    signer = signing.TimestampSigner(salt="reports")
    # First, check the signature without looking at the timestamp:
    try:
        username = signer.unsign(signed_username)
    except signing.BadSignature:
        return render(request, "bad_link.html")

    # Check if timestamp is older than 5 minutes:
    try:
        username = signer.unsign(signed_username, max_age=300)
    except signing.SignatureExpired:
        ctx["autosubmit"] = True

    if request.method != "POST":
        return render(request, "accounts/unsubscribe_submit.html", ctx)

    user = User.objects.get(username=username)
    profile = Profile.objects.for_user(user)
    profile.reports_allowed = False
    profile.next_report_date = None
    profile.nag_period = td()
    profile.next_nag_date = None
    profile.save()

    return render(request, "accounts/unsubscribed.html")


@require_POST
@login_required
def close(request):
    user = request.user

    # Cancel their subscription:
    sub = Subscription.objects.filter(user=user).first()
    if sub:
        sub.cancel()

    user.delete()

    # Deleting user also deletes its profile, checks, channels etc.

    request.session.flush()
    return redirect("hc-index")


@require_POST
@login_required
def remove_project(request, code):
    project = get_object_or_404(Project, code=code, owner=request.user)
    project.delete()
    return redirect("hc-index")


def _verify_origin(aaa):
    return lambda o: True


@login_required
@require_sudo_mode
def add_credential(request):
    rp = PublicKeyCredentialRpEntity("localhost", "Healthchecks")
    # FIXME use HTTPS, remove the verify_origin hack
    server = Fido2Server(rp, verify_origin=_verify_origin)

    if request.method == "POST":
        form = forms.AddCredentialForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        auth_data = server.register_complete(
            request.session["state"],
            form.cleaned_data["client_data_json"],
            form.cleaned_data["attestation_object"],
        )

        c = Credential(user=request.user)
        c.name = request.POST["name"]
        c.data = auth_data.credential_data
        c.save()

        request.session["added_credential_name"] = c.name
        return redirect("hc-profile")

    credentials = [c.unpack() for c in request.user.credentials.all()]
    options, state = server.register_begin(
        {
            "id": request.user.username.encode(),
            "name": request.user.email,
            "displayName": request.user.email,
        },
        credentials,
    )

    request.session["state"] = state

    ctx = {"options": base64.b64encode(cbor.encode(options)).decode()}
    return render(request, "accounts/add_credential.html", ctx)


@login_required
@require_sudo_mode
def remove_credential(request, code):
    try:
        credential = Credential.objects.get(user=request.user, code=code)
    except Credential.DoesNotExist:
        return HttpResponseBadRequest()

    if request.method == "POST" and "remove_credential" in request.POST:
        request.session["removed_credential_name"] = credential.name
        credential.delete()
        return redirect("hc-profile")

    ctx = {"credential": credential}
    return render(request, "accounts/remove_credential.html", ctx)


def login_tfa(request):
    rp = PublicKeyCredentialRpEntity("localhost", "Healthchecks")
    # FIXME use HTTPS, remove the verify_origin hack
    server = Fido2Server(rp, verify_origin=_verify_origin)

    if "2fa_user_id" not in request.session:
        return HttpResponseBadRequest()

    user = User.objects.get(id=request.session["2fa_user_id"])
    credentials = [c.unpack() for c in user.credentials.all()]

    if request.method == "POST":
        form = forms.LoginTfaForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        server.authenticate_complete(
            request.session.pop("state", ""),
            credentials,
            form.cleaned_data["credential_id"],
            form.cleaned_data["client_data_json"],
            form.cleaned_data["authenticator_data"],
            form.cleaned_data["signature"],
        )

        request.session.pop("2fa_user_id")
        auth_login(request, user, "hc.accounts.backends.EmailBackend")
        return _redirect_after_login(request)

    options, state = server.authenticate_begin(credentials)
    request.session["state"] = state

    ctx = {"options": base64.b64encode(cbor.encode(options)).decode()}
    return render(request, "accounts/login_tfa.html", ctx)
