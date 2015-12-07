import braintree
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Subscription


@login_required
def get_client_token(request):
    sub = Subscription.objects.get(user=request.user)
    client_token = braintree.ClientToken.generate({
        "customer_id": sub.customer_id
    })

    return JsonResponse({"client_token": client_token})


def pricing(request):
    sub = None
    if request.user.is_authenticated():
        try:
            sub = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            sub = Subscription(user=request.user)
            sub.save()

    ctx = {
        "page": "pricing",
        "sub": sub
    }

    return render(request, "payments/pricing.html", ctx)


def log_and_bail(request, result):
    for error in result.errors.deep_errors:
        messages.error(request, error.message)

    return redirect("hc-pricing")


@login_required
@require_POST
def create_plan(request):
    price = int(request.POST["price"])
    assert price in (2, 5, 10, 15, 20, 25, 50, 100)

    sub = Subscription.objects.get(user=request.user)
    if not sub.customer_id:
        result = braintree.Customer.create({})
        if not result.is_success:
            return log_and_bail(request, result)

        sub.customer_id = result.customer.id
        sub.save()

    if "payment_method_nonce" in request.POST:
        result = braintree.PaymentMethod.create({
            "customer_id": sub.customer_id,
            "payment_method_nonce": request.POST["payment_method_nonce"]
        })

        if not result.is_success:
            return log_and_bail(request, result)

        sub.payment_method_token = result.payment_method.token
        sub.save()

    result = braintree.Subscription.create({
        "payment_method_token": sub.payment_method_token,
        "plan_id": "P%d" % price,
        "price": price
    })

    if not result.is_success:
        return log_and_bail(request, result)

    sub.subscription_id = result.subscription.id
    sub.save()

    return redirect("hc-pricing")


@login_required
@require_POST
def update_plan(request):
    sub = Subscription.objects.get(user=request.user)

    price = int(request.POST["price"])
    assert price in (2, 5, 10, 15, 20, 25, 50, 100)

    fields = {
        "plan_id": "P%s" % price,
        "price": price
    }

    braintree.Subscription.update(sub.subscription_id, fields)
    return redirect("hc-pricing")


@login_required
@require_POST
def cancel_plan(request):
    sub = Subscription.objects.get(user=request.user)

    braintree.Subscription.cancel(sub.subscription_id)
    sub.subscription_id = ""
    sub.save()

    return redirect("hc-pricing")
