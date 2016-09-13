from django.conf import settings


def payments(request):

    show_pricing = settings.USE_PAYMENTS
    if show_pricing and request.user.is_authenticated:
        profile = request.user.profile
        if profile.current_team_id and profile.current_team_id != profile.id:
            show_pricing = False

    return {'show_pricing': show_pricing}
