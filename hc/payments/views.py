from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse, HttpResponse)
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from hc.payments.forms import BillToForm
from hc.payments.invoices import PdfInvoice
from hc.payments.models import Subscription

if settings.USE_PAYMENTS:
    import braintree
else:
    # hc.payments tests mock this object, so tests should
    # still be able to run:
    braintree = None


@login_required
def get_client_token(request):
    sub = Subscription.objects.for_user(request.user)
    client_token = braintree.ClientToken.generate({
        "customer_id": sub.customer_id
    })

    return JsonResponse({"client_token": client_token})


def pricing(request):
    if request.user.is_authenticated and request.profile != request.team:
        ctx = {"page": "pricing"}
        return render(request, "payments/pricing_not_owner.html", ctx)

    sub = None
    if request.user.is_authenticated:
        # Don't use Subscription.objects.for_user method here, so a
        # subscription object is not created just by viewing a page.
        sub = Subscription.objects.filter(user_id=request.user.id).first()

    period = "monthly"
    if sub and sub.plan_id.startswith("Y"):
        period = "annual"

    ctx = {
        "page": "pricing",
        "sub": sub,
        "period": period,
        "first_charge": request.session.pop("first_charge", False)
    }

    return render(request, "payments/pricing.html", ctx)


def log_and_bail(request, result):
    logged_deep_error = False

    for error in result.errors.deep_errors:
        messages.error(request, error.message)
        logged_deep_error = True

    if not logged_deep_error:
        messages.error(request, result.message)

    return redirect("hc-pricing")


@login_required
@require_POST
def create_plan(request):
    plan_id = request.POST["plan_id"]
    if plan_id not in ("P5", "P50", "Y48", "Y480"):
        return HttpResponseBadRequest()

    sub = Subscription.objects.for_user(request.user)

    # Cancel the previous plan
    if sub.subscription_id:
        braintree.Subscription.cancel(sub.subscription_id)
        sub.subscription_id = ""
        sub.plan_id = ""
        sub.save()

    # Create Braintree customer record
    if not sub.customer_id:
        result = braintree.Customer.create({
            "email": request.user.email
        })
        if not result.is_success:
            return log_and_bail(request, result)

        sub.customer_id = result.customer.id
        sub.save()

    # Create Braintree payment method
    if "payment_method_nonce" in request.POST:
        result = braintree.PaymentMethod.create({
            "customer_id": sub.customer_id,
            "payment_method_nonce": request.POST["payment_method_nonce"]
        })

        if not result.is_success:
            return log_and_bail(request, result)

        sub.payment_method_token = result.payment_method.token
        sub.save()

    # Create Braintree subscription
    result = braintree.Subscription.create({
        "payment_method_token": sub.payment_method_token,
        "plan_id": plan_id,
    })

    if not result.is_success:
        return log_and_bail(request, result)

    sub.subscription_id = result.subscription.id
    sub.plan_id = plan_id
    sub.save()

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
    return redirect("hc-pricing")


@login_required
@require_POST
def update_payment_method(request):
    sub = Subscription.objects.for_user(request.user)

    if not sub.customer_id or not sub.subscription_id:
        return HttpResponseBadRequest()

    if "payment_method_nonce" not in request.POST:
        return HttpResponseBadRequest()

    result = braintree.PaymentMethod.create({
        "customer_id": sub.customer_id,
        "payment_method_nonce": request.POST["payment_method_nonce"]
    })

    if not result.is_success:
        return log_and_bail(request, result)

    payment_method_token = result.payment_method.token
    result = braintree.Subscription.update(sub.subscription_id, {
        "payment_method_token": payment_method_token
    })

    if not result.is_success:
        return log_and_bail(request, result)

    sub.payment_method_token = payment_method_token
    sub.save()

    return redirect("hc-pricing")


@login_required
@require_POST
def cancel_plan(request):
    sub = Subscription.objects.get(user=request.user)
    sub.cancel()

    # Revert to default limits--
    profile = request.user.profile
    profile.ping_log_limit = 100
    profile.check_limit = 20
    profile.team_limit = 2
    profile.sms_limit = 0
    profile.save()

    return redirect("hc-pricing")


@login_required
def billing(request):
    if request.method == "POST":
        form = BillToForm(request.POST)
        if form.is_valid():
            request.user.profile.bill_to = form.cleaned_data["bill_to"]
            request.user.profile.save()
            return redirect("hc-billing")

    sub = Subscription.objects.get(user=request.user)

    transactions = braintree.Transaction.search(
        braintree.TransactionSearch.customer_id == sub.customer_id)

    ctx = {"transactions": transactions}
    return render(request, "payments/billing.html", ctx)


@login_required
def invoice(request, transaction_id):
    sub = Subscription.objects.get(user=request.user)
    transaction = braintree.Transaction.find(transaction_id)
    if transaction.customer_details.id != sub.customer_id:
        return HttpResponseForbidden()

    ctx = {"tx": transaction}
    return render(request, "payments/invoice.html", ctx)


@login_required
def pdf_invoice(request, transaction_id):
    sub = Subscription.objects.get(user=request.user)
    transaction = braintree.Transaction.find(transaction_id)
    if transaction.customer_details.id != sub.customer_id:
        return HttpResponseForbidden()

    response = HttpResponse(content_type='application/pdf')
    filename = "MS-HC-%s.pdf" % transaction.id.upper()
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    bill_to = request.user.profile.bill_to or request.user.email
    PdfInvoice(response).render(transaction, bill_to)
    return response
