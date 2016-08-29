from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse)
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Subscription

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
    sub = None
    if request.user.is_authenticated:
        # Don't use Subscription.objects.for_user method here, so a
        # subscription object is not created just by viewing a page.
        sub = Subscription.objects.filter(user_id=request.user.id).first()

    ctx = {
        "page": "pricing",
        "sub": sub,
        "first_charge": request.session.pop("first_charge", False)
    }

    return render(request, "payments/pricing.html", ctx)


def log_and_bail(request, result):
    for error in result.errors.deep_errors:
        messages.error(request, error.message)
    else:
        messages.error(request, result.message)

    return redirect("hc-pricing")


@login_required
@require_POST
def create_plan(request):
    plan_id = request.POST["plan_id"]
    if plan_id not in ("P5", "P20"):
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
    if plan_id == "P5":
        profile.ping_log_limit = 1000
        profile.team_access_allowed = True
        profile.save()
    elif plan_id == "P20":
        profile.ping_log_limit = 10000
        profile.team_access_allowed = True
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

    braintree.Subscription.cancel(sub.subscription_id)
    sub.subscription_id = ""
    sub.plan_id = ""
    sub.save()

    return redirect("hc-pricing")


@login_required
def billing(request):
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
