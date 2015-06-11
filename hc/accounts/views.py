import uuid

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render

from hc.accounts.forms import EmailForm


def login(request):

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = EmailForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.get(email=email)
            token = str(uuid.uuid4())
            user.set_password(token)
            user.save()

            login_link = reverse("hc-check-token", args=[user.username, token])
            login_link = settings.SITE_ROOT + login_link
            body = "login link: %s" % login_link

            send_mail('Log In', body, 'cuu508@gmail.com', [email],
                      fail_silently=False)

            # FIXME send login token here
            return redirect("hc-login-link-sent")

    else:
        form = EmailForm()

    ctx = {
        "form": form
    }

    return render(request, "accounts/login.html", ctx)


def login_link_sent(request):
    return render(request, "accounts/login_link_sent.html")


def check_token(request, username, token):
    user = authenticate(username=username, password=token)
    if user is not None:
        if user.is_active:
            user.set_unusable_password()
            user.save()
            auth_login(request, user)
            return redirect("hc-checks")

    return render(request, "bad_link.html")
