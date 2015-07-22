import uuid

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from hc.accounts.forms import EmailForm
from hc.api.models import Check
from hc.lib.emails import send


def _make_user(email):
    username = str(uuid.uuid4())[:30]
    user = User(username=username, email=email)
    user.save()

    return user


def _associate_demo_check(request, user):
    if "welcome_code" in request.session:
        check = Check.objects.get(code=request.session["welcome_code"])
        check.user = user
        check.save()


def _send_login_link(user):
    token = str(uuid.uuid4())
    user.set_password(token)
    user.save()

    login_link = reverse("hc-check-token", args=[user.username, token])
    login_link = settings.SITE_ROOT + login_link
    ctx = {"login_link": login_link}

    send(user.email, "emails/login", ctx)


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
    user = authenticate(username=username, password=token)
    if user is not None:
        if user.is_active:
            user.set_unusable_password()
            user.save()
            auth_login(request, user)
            return redirect("hc-index")

    return render(request, "bad_link.html")
