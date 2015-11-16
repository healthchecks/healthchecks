from django.conf import settings


def payments(request):
    return {'USE_PAYMENTS': settings.USE_PAYMENTS}
