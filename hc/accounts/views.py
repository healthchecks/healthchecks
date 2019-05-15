from datetime import timedelta as td
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.http import (
    HttpResponseForbidden,
    HttpResponseBadRequest,
    HttpResponseNotFound,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.urls import resolve, Resolver404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from hc.accounts.forms import (
    ChangeEmailForm,
    PasswordLoginForm,
    InviteTeamMemberForm,
    RemoveTeamMemberForm,
    ReportSettingsForm,
    SetPasswordForm,
    ProjectNameForm,
    AvailableEmailForm,
    EmailLoginForm,
)
from hc.accounts.models import Profile, Project, Member
from hc.api.models import Channel, Check, TokenBucket
from hc.payments.models import Subscription

NEXT_WHITELIST = (
    "hc-checks",
    "hc-details",
    "hc-log",
    "hc-channels",
    "hc-add-slack",
    "hc-add-pushover",
)


def _is_whitelisted(path):
    try:
        match = resolve(path)
    except Resolver404:
        return False

    return match.url_name in NEXT_WHITELIST


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
    profile = Profile.objects.for_user(user)
    profile.current_project = project
    profile.save()

    return user


def _redirect_after_login(request):
    """ Redirect to the URL indicated in ?next= query parameter. """

    redirect_url = request.GET.get("next")
    if _is_whitelisted(redirect_url):
        return redirect(redirect_url)

    if request.user.project_set.count() == 1:
        project = request.user.project_set.first()
        return redirect("hc-checks", project.code)

    return redirect("hc-index")


def login(request):
    form = PasswordLoginForm()
    magic_form = EmailLoginForm()

    if request.method == "POST":
        if request.POST.get("action") == "login":
            form = PasswordLoginForm(request.POST)
            if form.is_valid():
                auth_login(request, form.user)
                return _redirect_after_login(request)

        else:
            magic_form = EmailLoginForm(request.POST)
            if magic_form.is_valid():
                redirect_url = request.GET.get("next")
                if not _is_whitelisted(redirect_url):
                    redirect_url = None

                profile = Profile.objects.for_user(magic_form.user)
                profile.send_instant_login_link(redirect_url=redirect_url)
                return redirect("hc-login-link-sent")

    bad_link = request.session.pop("bad_link", None)
    ctx = {
        "page": "login",
        "form": form,
        "magic_form": magic_form,
        "bad_link": bad_link,
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
    profile = request.profile

    ctx = {"page": "profile", "profile": profile, "my_projects_status": "default"}

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

            if profile.current_project == project:
                profile.current_project = None
                profile.save()

            Member.objects.filter(project=project, user=request.user).delete()

            ctx["left_project"] = project
            ctx["my_projects_status"] = "info"

    # Retrieve projects right before rendering the template--
    # The list of the projects might have *just* changed
    ctx["projects"] = list(profile.projects())
    return render(request, "accounts/profile.html", ctx)


@login_required
@require_POST
def add_project(request):
    form = ProjectNameForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()

    project = Project(owner=request.user)
    project.code = project.badge_key = str(uuid.uuid4())
    project.name = form.cleaned_data["name"]
    project.save()

    return redirect("hc-checks", project.code)


@login_required
def project(request, code):
    if request.user.is_superuser:
        q = Project.objects
    else:
        q = request.profile.projects()

    try:
        project = q.get(code=code)
    except Project.DoesNotExist:
        return HttpResponseNotFound()

    is_owner = project.owner_id == request.user.id
    ctx = {
        "page": "project",
        "project": project,
        "is_owner": is_owner,
        "show_api_keys": "show_api_keys" in request.GET,
        "project_name_status": "default",
        "api_status": "default",
        "team_status": "default",
    }

    if request.method == "POST":
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
            if not is_owner or not project.can_invite():
                return HttpResponseForbidden()

            form = InviteTeamMemberForm(request.POST)
            if form.is_valid():
                if not TokenBucket.authorize_invite(request.user):
                    return render(request, "try_later.html")

                email = form.cleaned_data["email"]
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = _make_user(email, with_project=False)

                project.invite(user)
                ctx["team_member_invited"] = email
                ctx["team_status"] = "success"

        elif "remove_team_member" in request.POST:
            if not is_owner:
                return HttpResponseForbidden()

            form = RemoveTeamMemberForm(request.POST)
            if form.is_valid():
                q = User.objects
                q = q.filter(email=form.cleaned_data["email"])
                q = q.filter(memberships__project=project)
                farewell_user = q.first()
                if farewell_user is None:
                    return HttpResponseBadRequest()

                farewell_user.profile.current_project = None
                farewell_user.profile.save()

                Member.objects.filter(project=project, user=farewell_user).delete()

                ctx["team_member_removed"] = form.cleaned_data["email"]
                ctx["team_status"] = "info"
        elif "set_project_name" in request.POST:
            form = ProjectNameForm(request.POST)
            if form.is_valid():
                project.name = form.cleaned_data["name"]
                project.save()

                if request.profile.current_project == project:
                    request.profile.current_project.name = project.name

                ctx["project_name_updated"] = True
                ctx["project_name_status"] = "success"

    # Count members right before rendering the template, in case
    # we just invited or removed someone
    ctx["num_members"] = project.member_set.count()
    return render(request, "accounts/project.html", ctx)


@login_required
def notifications(request):
    profile = request.profile

    ctx = {"status": "default", "page": "profile", "profile": profile}

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


@require_POST
@login_required
def remove_project(request, code):
    project = get_object_or_404(Project, code=code, owner=request.user)
    project.delete()
    return redirect("hc-index")
