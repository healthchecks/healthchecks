import braintree
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Subscription


def setup_braintree():
    kw = {
        "merchant_id": settings.BRAINTREE_MERCHANT_ID,
        "public_key": settings.BRAINTREE_PUBLIC_KEY,
        "private_key": settings.BRAINTREE_PRIVATE_KEY
    }

    braintree.Configuration.configure(settings.BRAINTREE_ENV, **kw)


def pricing(request):
    ctx = {
        "page": "pricing",
    }
    return render(request, "payments/pricing.html", ctx)


@login_required
def create(request):
    setup_braintree()

    try:
        sub = Subscription.objects.get(user=request.user)
    except Subscription.DoesNotExist:
        sub = Subscription(user=request.user)
        sub.save()

    if request.method == "POST":
        if not sub.customer_id:
            result = braintree.Customer.create({})
            assert result.is_success
            sub.customer_id = result.customer.id
            sub.save()

        result = braintree.PaymentMethod.create({
            "customer_id": sub.customer_id,
            "payment_method_nonce": request.POST["payment_method_nonce"]
        })
        assert result.is_success
        sub.payment_method_token = result.payment_method.token
        sub.save()

        result = braintree.Subscription.create({
            "payment_method_token": sub.payment_method_token,
            "plan_id": "pww",
            "price": 5
        })

        sub.subscription_id = result.subscription.id
        sub.save()

        return redirect("hc-subscription-status")

    ctx = {
        "page": "pricing",
        "client_token": braintree.ClientToken.generate()
    }
    return render(request, "payments/create_subscription.html", ctx)


@login_required
def status(request):
    setup_braintree()

    sub = Subscription.objects.get(user=request.user)
    subscription = braintree.Subscription.find(sub.subscription_id)

    ctx = {
        "page": "pricing",
        "subscription": subscription
    }

    return render(request, "payments/status.html", ctx)
