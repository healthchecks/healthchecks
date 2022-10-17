from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from hc.front.views import _get_project_for_user
from hc.payments.forms import InvoiceEmailingForm
from hc.payments.models import Subscription


@login_required
def token(request):
    sub = Subscription.objects.for_user(request.user)
    return JsonResponse({"client_token": sub.get_client_token()})


def pricing(request, code=None):
    project = None
    if code:
        if not request.user.is_authenticated:
            raise Http404()

        project, rw = _get_project_for_user(request, code)
        if project.owner != request.user:
            ctx = {"page": "pricing", "project": project}
            return render(request, "payments/pricing_not_owner.html", ctx)

    sub = None
    if request.user.is_authenticated:
        # Don't use Subscription.objects.for_user method here, so a
        # subscription object is not created just by viewing a page.
        sub = Subscription.objects.filter(user_id=request.user.id).first()

    ctx = {"page": "pricing", "project": project, "sub": sub}
    return render(request, "payments/pricing.html", ctx)


@login_required
def billing(request):
    # Don't use Subscription.objects.for_user method here, so a
    # subscription object is not created just by viewing a page.
    sub = Subscription.objects.filter(user_id=request.user.id).first()
    if sub is None:
        sub = Subscription(user=request.user)

    send_invoices_status = "default"
    if request.method == "POST":
        form = InvoiceEmailingForm(request.POST)
        if form.is_valid():
            sub = Subscription.objects.for_user(request.user)
            form.update_subscription(sub)
            send_invoices_status = "success"

    ctx = {
        "page": "billing",
        "profile": request.profile,
        "sub": sub,
        "send_invoices_status": send_invoices_status,
        "set_plan_status": "default",
        "address_status": "default",
        "payment_method_status": "default",
    }

    if "set_plan_status" in request.session:
        ctx["set_plan_status"] = request.session.pop("set_plan_status")

    if "address_status" in request.session:
        ctx["address_status"] = request.session.pop("address_status")

    if "payment_method_status" in request.session:
        ctx["payment_method_status"] = request.session.pop("payment_method_status")

    return render(request, "accounts/billing.html", ctx)


def log_and_bail(request, result):
    logged_deep_error = False

    for error in result.errors.deep_errors:
        messages.error(request, error.message)
        logged_deep_error = True

    if not logged_deep_error:
        messages.error(request, result.message)

    return redirect("hc-billing")


@login_required
@require_POST
def update(request):
    plan_id = request.POST["plan_id"]
    nonce = request.POST["nonce"]

    sub = Subscription.objects.for_user(request.user)
    # If plan_id has not changed then just update the payment method:
    if plan_id == sub.plan_id:
        if not sub.subscription_id:
            error = sub.setup(plan_id, nonce)
        else:
            error = sub.update_payment_method(nonce)

        if error:
            return log_and_bail(request, error)

        request.session["payment_method_status"] = "success"
        return redirect("hc-billing")

    if plan_id not in ("", "P20", "P80", "Y192", "Y768", "S5", "S48"):
        return HttpResponseBadRequest()

    # Cancel the previous plan and reset limits:
    sub.cancel()

    profile = request.user.profile
    profile.ping_log_limit = 100
    profile.check_limit = 20
    profile.team_limit = 2
    profile.sms_limit = 5
    profile.call_limit = 0
    profile.save()

    if plan_id == "":
        request.session["set_plan_status"] = "success"
        return redirect("hc-billing")

    error = sub.setup(plan_id, nonce)
    if error:
        return log_and_bail(request, error)

    # Update user's profile
    profile = request.user.profile
    if plan_id in ("S5", "S48"):
        profile.check_limit = 20
        profile.team_limit = 2
        profile.ping_log_limit = 1000
        profile.sms_limit = 5
        profile.sms_sent = 0
        profile.call_limit = 5
        profile.calls_sent = 0
        profile.save()
    elif plan_id in ("P20", "Y192"):
        profile.check_limit = 100
        profile.team_limit = 9
        profile.ping_log_limit = 1000
        profile.sms_limit = 50
        profile.sms_sent = 0
        profile.call_limit = 20
        profile.calls_sent = 0
        profile.save()
    elif plan_id in ("P80", "Y768"):
        profile.check_limit = 1000
        profile.team_limit = 500
        profile.ping_log_limit = 1000
        profile.sms_limit = 500
        profile.sms_sent = 0
        profile.call_limit = 100
        profile.calls_sent = 0
        profile.save()

    request.session["set_plan_status"] = "success"
    return redirect("hc-billing")


@login_required
def address(request):
    sub = Subscription.objects.for_user(request.user)
    if request.method == "POST":
        error = sub.update_address(request.POST)
        if error:
            return log_and_bail(request, error)

        request.session["address_status"] = "success"
        return redirect("hc-billing")

    ctx = {"a": sub.address, "email": request.user.email}
    return render(request, "payments/address.html", ctx)


@login_required
def payment_method(request):
    sub = get_object_or_404(Subscription, user=request.user)
    ctx = {"sub": sub, "pm": sub.payment_method}
    return render(request, "payments/payment_method.html", ctx)


@login_required
def billing_history(request):
    try:
        sub = Subscription.objects.get(user=request.user)
        transactions = sub.transactions
    except Subscription.DoesNotExist:
        transactions = []

    ctx = {"transactions": transactions}
    return render(request, "payments/billing_history.html", ctx)
