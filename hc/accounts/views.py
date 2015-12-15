import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from hc.accounts.forms import EmailForm, ReportSettingsForm
from hc.accounts.models import Profile
from hc.api.models import Channel, Check
from hc.lib import emails


def _make_user(email):
    username = str(uuid.uuid4())[:30]
    user = User(username=username, email=email)
    user.save()

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


def _send_login_link(user):
    token = str(uuid.uuid4())
    user.set_password(token)
    user.save()

    login_link = reverse("hc-check-token", args=[user.username, token])
    login_link = settings.SITE_ROOT + login_link
    ctx = {"login_link": login_link}

    emails.login(user.email, ctx)


def login(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = _make_user(email)
                _associate_demo_check(request, user)

            # We don't want to reset passwords of staff users :-)
            if user.is_staff:
                return HttpResponseBadRequest()

            _send_login_link(user)

            return redirect("hc-login-link-sent")

    else:
        form = EmailForm()

    ctx = {"form": form}
    return render(request, "accounts/login.html", ctx)


def logout(request):
    auth_logout(request)
    return redirect("hc-index")


def login_link_sent(request):
    return render(request, "accounts/login_link_sent.html")


def check_token(request, username, token):
    if request.user.is_authenticated() and request.user.username == username:
        # User is already logged in
        return redirect("hc-checks")

    user = authenticate(username=username, password=token)
    if user is not None:
        if user.is_active:
            # This should get rid of "welcome_code" in session
            request.session.flush()

            user.set_unusable_password()
            user.save()
            auth_login(request, user)

            return redirect("hc-checks")

    ctx = {"bad_link": True}
    return render(request, "accounts/login.html", ctx)


@login_required
def profile(request):
    profile = Profile.objects.for_user(request.user)

    if request.method == "POST":
        form = ReportSettingsForm(request.POST)
        if form.is_valid():
            profile.reports_allowed = form.cleaned_data["reports_allowed"]
            profile.save()
            messages.info(request, "Your settings have been updated!")

    ctx = {
        "profile": profile
    }

    return render(request, "accounts/profile.html", ctx)


def unsubscribe_reports(request, username):
    try:
        signing.Signer().unsign(request.GET.get("token"))
    except signing.BadSignature:
        return HttpResponseBadRequest()

    user = User.objects.get(username=username)
    profile = Profile.objects.for_user(user)
    profile.reports_allowed = False
    profile.save()

    return render(request, "accounts/unsubscribed.html")
