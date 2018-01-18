from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse, HttpResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import six
from hc.api.models import Check
from hc.lib import emails
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

    # Don't use Subscription.objects.for_user method here, so a
    # subscription object is not created just by viewing a page.
    sub = Subscription.objects.filter(user_id=request.user.id).first()

    ctx = {"page": "pricing", "sub": sub}
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

    send_invoices_status = "default"
    if request.method == "POST":
        if "save_send_invoices" in request.POST:
            sub = Subscription.objects.for_user(request.user)
            sub.send_invoices = "send_invoices" in request.POST
            sub.save()
            send_invoices_status = "success"

    ctx = {
        "page": "billing",
        "profile": request.profile,
        "sub": sub,
        "num_checks": Check.objects.filter(user=request.user).count(),
        "team_size": request.profile.member_set.count() + 1,
        "team_max": request.profile.team_limit + 1,
        "send_invoices_status": send_invoices_status,
        "set_plan_status": "default",
        "address_status": "default",
        "payment_method_status": "default"
    }

    if "set_plan_status" in request.session:
        ctx["set_plan_status"] = request.session.pop("set_plan_status")

    if "address_status" in request.session:
        ctx["address_status"] = request.session.pop("address_status")

    if "payment_method_status" in request.session:
        ctx["payment_method_status"] = \
            request.session.pop("payment_method_status")

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
    if plan_id not in ("", "P5", "P50", "Y48", "Y480", "T144"):
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
    if plan_id in ("P5", "Y48", "T144"):
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

        request.session["payment_method_status"] = "success"
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
    sub, tx = Subscription.objects.by_transaction(transaction_id)

    # Does this transaction belong to a customer we know about?
    if sub is None or tx is None:
        return HttpResponseForbidden()

    # Does the transaction's customer match the currently logged in user?
    if sub.user != request.user and not request.user.is_superuser:
        return HttpResponseForbidden()

    response = HttpResponse(content_type='application/pdf')
    filename = "MS-HC-%s.pdf" % tx.id.upper()
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    PdfInvoice(response).render(tx, sub.flattened_address())
    return response


@csrf_exempt
@require_POST
def charge_webhook(request):
    sig = str(request.POST["bt_signature"])
    payload = str(request.POST["bt_payload"])

    import braintree
    doc = braintree.WebhookNotification.parse(sig, payload)
    if doc.kind != "subscription_charged_successfully":
        return HttpResponseBadRequest()

    sub = Subscription.objects.get(subscription_id=doc.subscription.id)
    if sub.send_invoices:
        transaction = doc.subscription.transactions[0]
        filename = "MS-HC-%s.pdf" % transaction.id.upper()

        sink = six.BytesIO()
        PdfInvoice(sink).render(transaction, sub.flattened_address())
        ctx = {"tx": transaction}
        emails.invoice(sub.user.email, ctx, filename, sink.getvalue())

    return HttpResponse()
