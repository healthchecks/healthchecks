from django.conf import settings


def payments(request):

    show_pricing = settings.USE_PAYMENTS
    if show_pricing and request.user.is_authenticated():
        profile = request.user.profile
        if profile.id != profile.current_team_id:
            show_pricing = False

    return {'show_pricing': show_pricing}
