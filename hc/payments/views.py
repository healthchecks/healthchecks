from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse, HttpResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from hc.api.models import Check
from hc.payments.invoices import PdfInvoice
from hc.payments.models import Subscription


@login_required
def get_client_token(request):
    sub = Subscription.objects.for_user(request.user)
    return JsonResponse({"client_token": sub.get_client_token()})


def pricing(request):
    if request.user.is_authenticated and request.profile != request.team:
        ctx = {"page": "pricing"}
        return render(request, "payments/pricing_not_owner.html", ctx)

    ctx = {"page": "pricing"}
    return render(request, "payments/pricing.html", ctx)


@login_required
def billing(request):
    if request.team != request.profile:
        request.team = request.profile
        request.profile.current_team = request.profile
        request.profile.save()

    # Don't use Subscription.objects.for_user method here, so a
    # subscription object is not created just by viewing a page.
    sub = Subscription.objects.filter(user_id=request.user.id).first()

    ctx = {
        "page": "billing",
        "profile": request.profile,
        "sub": sub,
        "num_checks": Check.objects.filter(user=request.user).count(),
        "team_size": request.profile.member_set.count() + 1,
        "team_max": request.profile.team_limit + 1
    }

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
def set_plan(request):
    plan_id = request.POST["plan_id"]
    if plan_id not in ("", "P5", "P50", "Y48", "Y480"):
        return HttpResponseBadRequest()

    sub = Subscription.objects.for_user(request.user)
    if sub.plan_id == plan_id:
        return redirect("hc-billing")

    # Cancel the previous plan
    sub.cancel()
    if plan_id == "":
        profile = request.user.profile
        profile.ping_log_limit = 100
        profile.check_limit = 20
        profile.team_limit = 2
        profile.sms_limit = 0
        profile.save()
        return redirect("hc-billing")

    result = sub.setup(plan_id)
    if not result.is_success:
        return log_and_bail(request, result)

    # Update user's profile
    profile = request.user.profile
    if plan_id in ("P5", "Y48"):
        profile.ping_log_limit = 1000
        profile.check_limit = 500
        profile.team_limit = 9
        profile.sms_limit = 50
        profile.sms_sent = 0
        profile.save()
    elif plan_id in ("P50", "Y480"):
        profile.ping_log_limit = 1000
        profile.check_limit = 500
        profile.team_limit = 500
        profile.sms_limit = 500
        profile.sms_sent = 0
        profile.save()

    request.session["first_charge"] = True
    return redirect("hc-billing")


@login_required
def address(request):
    sub = Subscription.objects.for_user(request.user)
    if request.method == "POST":
        error = sub.update_address(request.POST)
        if error:
            return log_and_bail(request, error)

        return redirect("hc-billing")

    ctx = {"a": sub.address}
    return render(request, "payments/address.html", ctx)


@login_required
def payment_method(request):
    sub = get_object_or_404(Subscription, user=request.user)

    if request.method == "POST":
        if "payment_method_nonce" not in request.POST:
            return HttpResponseBadRequest()

        nonce = request.POST["payment_method_nonce"]
        error = sub.update_payment_method(nonce)
        if error:
            return log_and_bail(request, error)

        return redirect("hc-billing")

    ctx = {
        "sub": sub,
        "pm": sub.payment_method
    }
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


@login_required
def pdf_invoice(request, transaction_id):
    sub = Subscription.objects.get(user=request.user)
    transaction = sub.get_transaction(transaction_id)
    if transaction is None:
        return HttpResponseForbidden()

    response = HttpResponse(content_type='application/pdf')
    filename = "MS-HC-%s.pdf" % transaction.id.upper()
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    bill_to = []
    if sub.address_id:
        ctx = {"a": sub.address}
        bill_to = render_to_string("payments/address_plain.html", ctx)
    elif request.user.profile.bill_to:
        bill_to = request.user.profile.bill_to
    else:
        bill_to = request.user.email

    PdfInvoice(response).render(transaction, bill_to)
    return response
