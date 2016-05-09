import uuid

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import redirect, render
from hc.accounts.forms import (EmailPasswordForm, InviteTeamMemberForm,
                               RemoveTeamMemberForm, ReportSettingsForm,
                               SetPasswordForm, TeamNameForm)
from hc.accounts.models import Profile, Member
from hc.api.models import Channel, Check


def _make_user(email):
    username = str(uuid.uuid4())[:30]
    user = User(username=username, email=email)
    user.set_unusable_password()
    user.save()

    profile = Profile(user=user)
    profile.save()

    channel = Channel()
    channel.user = user
    channel.kind = "email"
    channel.value = email
    channel.email_verified = True
    channel.save()

    return user


def _associate_demo_check(request, user):
    if "welcome_code" in request.session:
        check = Check.objects.get(code=request.session["welcome_code"])

        # Only associate demo check if it doesn't have an owner already.
        if check.user is None:
            check.user = user
            check.save()

            check.assign_all_channels()

            del request.session["welcome_code"]


def login(request):
    bad_credentials = False
    if request.method == 'POST':
        form = EmailPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            if len(password):
                user = authenticate(username=email, password=password)
                if user is not None and user.is_active:
                    auth_login(request, user)
                    return redirect("hc-checks")
                bad_credentials = True
            else:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = _make_user(email)
                    _associate_demo_check(request, user)

                user.profile.send_instant_login_link()
                return redirect("hc-login-link-sent")

    else:
        form = EmailPasswordForm()

    bad_link = request.session.pop("bad_link", None)
    ctx = {
        "form": form,
        "bad_credentials": bad_credentials,
        "bad_link": bad_link
    }
    return render(request, "accounts/login.html", ctx)


def logout(request):
    auth_logout(request)
    return redirect("hc-index")


def login_link_sent(request):
    return render(request, "accounts/login_link_sent.html")


def set_password_link_sent(request):
    return render(request, "accounts/set_password_link_sent.html")


def check_token(request, username, token):
    if request.user.is_authenticated() and request.user.username == username:
        # User is already logged in
        return redirect("hc-checks")

    user = authenticate(username=username, token=token)
    if user is not None and user.is_active:
        # This should get rid of "welcome_code" in session
        request.session.flush()

        user.profile.token = ""
        user.profile.save()
        auth_login(request, user)

        return redirect("hc-checks")

    request.session["bad_link"] = True
    return redirect("hc-login")


@login_required
def profile(request):
    profile = request.user.profile

    show_api_key = False
    if request.method == "POST":
        if "set_password" in request.POST:
            profile.send_set_password_link()
            return redirect("hc-set-password-link-sent")
        elif "create_api_key" in request.POST:
            profile.set_api_key()
            show_api_key = True
            messages.info(request, "The API key has been created!")
        elif "revoke_api_key" in request.POST:
            profile.api_key = ""
            profile.save()
            messages.info(request, "The API key has been revoked!")
        elif "show_api_key" in request.POST:
            show_api_key = True
        elif "update_reports_allowed" in request.POST:
            form = ReportSettingsForm(request.POST)
            if form.is_valid():
                profile.reports_allowed = form.cleaned_data["reports_allowed"]
                profile.save()
                messages.info(request, "Your settings have been updated!")
        elif "invite_team_member" in request.POST:
            form = InviteTeamMemberForm(request.POST)
            if form.is_valid():

                email = form.cleaned_data["email"]
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = _make_user(email)

                profile.invite(user)
                messages.info(request, "Invitation to %s sent!" % email)
        elif "remove_team_member" in request.POST:
            form = RemoveTeamMemberForm(request.POST)
            if form.is_valid():

                email = form.cleaned_data["email"]
                Member.objects.filter(team=profile, user__email=email).delete()
                messages.info(request, "%s removed from team!" % email)
        elif "set_team_name" in request.POST:
            form = TeamNameForm(request.POST)
            if form.is_valid():
                profile.team_name = form.cleaned_data["team_name"]
                profile.save()
                messages.info(request, "Team Name updated!")

    ctx = {
        "profile": profile,
        "show_api_key": show_api_key
    }

    return render(request, "accounts/profile.html", ctx)


@login_required
def set_password(request, token):
    profile = request.user.profile
    if not check_password(token, profile.token):
        return HttpResponseBadRequest()

    if request.method == "POST":
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data["password"]
            request.user.set_password(password)
            request.user.save()

            profile.token = ""
            profile.save()

            # Setting a password logs the user out, so here we
            # log them back in.
            u = authenticate(username=request.user.email, password=password)
            auth_login(request, u)

            messages.info(request, "Your password has been set!")
            return redirect("hc-profile")

    return render(request, "accounts/set_password.html", {})


def unsubscribe_reports(request, username):
    try:
        signing.Signer().unsign(request.GET.get("token"))
    except signing.BadSignature:
        return HttpResponseBadRequest()

    user = User.objects.get(username=username)
    user.profile.reports_allowed = False
    user.profile.save()

    return render(request, "accounts/unsubscribed.html")


def switch_team(request, target_username):
    other_user = User.objects.get(username=target_username)

    # Superuser can switch to any team.
    # Other users can only switch to a team they are members of.
    if not request.user.is_superuser:
        q = Member.objects.filter(team=other_user.profile, user=request.user)
        if q.count() == 0:
            return HttpResponseForbidden()

    request.user.profile.current_team = other_user.profile
    request.user.profile.save()

    return redirect("hc-checks")
