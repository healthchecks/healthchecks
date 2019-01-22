from hc.accounts.models import Profile


class TeamAccessMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        profile = Profile.objects.for_user(request.user)
        if profile.current_project is None:
            profile.current_project = profile.get_own_project()
            profile.save()

        request.profile = profile
        request.project = profile.current_project

        return self.get_response(request)
