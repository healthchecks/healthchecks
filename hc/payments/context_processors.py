from django.conf import settings


def payments(request):

    show_pricing = settings.USE_PAYMENTS
    if show_pricing and request.user.is_authenticated:
        if request.profile != request.team:
            # Hide "Pricing" tab when user is not working on their
            # own team
            show_pricing = False

    return {'show_pricing': show_pricing}
