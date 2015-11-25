import braintree
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Subscription


def setup_braintree():
    kw = {
        "merchant_id": settings.BRAINTREE_MERCHANT_ID,
        "public_key": settings.BRAINTREE_PUBLIC_KEY,
        "private_key": settings.BRAINTREE_PRIVATE_KEY
    }

    braintree.Configuration.configure(settings.BRAINTREE_ENV, **kw)


def pricing(request):
    setup_braintree()

    try:
        sub = Subscription.objects.get(user=request.user)
    except Subscription.DoesNotExist:
        sub = Subscription(user=request.user)
        sub.save()

    ctx = {
        "page": "pricing",
        "sub": sub,
        "client_token": braintree.ClientToken.generate()
    }

    return render(request, "payments/pricing.html", ctx)


@login_required
@require_POST
def create_plan(request):
    setup_braintree()
    sub = Subscription.objects.get(user=request.user)
    if not sub.customer_id:
        result = braintree.Customer.create({})
        assert result.is_success
        sub.customer_id = result.customer.id
        sub.save()

    if "payment_method_nonce" in request.POST:
        result = braintree.PaymentMethod.create({
            "customer_id": sub.customer_id,
            "payment_method_nonce": request.POST["payment_method_nonce"]
        })
        assert result.is_success
        sub.payment_method_token = result.payment_method.token
        sub.save()

    price = int(request.POST["price"])
    assert price in (2, 5, 10, 15, 20, 25, 50, 100)

    result = braintree.Subscription.create({
        "payment_method_token": sub.payment_method_token,
        "plan_id": "P%d" % price,
        "price": price
    })

    sub.subscription_id = result.subscription.id
    sub.save()

    return redirect("hc-pricing")


@login_required
@require_POST
def update_plan(request):
    setup_braintree()
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
    setup_braintree()
    sub = Subscription.objects.get(user=request.user)

    braintree.Subscription.cancel(sub.subscription_id)
    sub.subscription_id = ""
    sub.save()

    return redirect("hc-pricing")
