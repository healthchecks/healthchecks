from hc.accounts.models import Profile


class TeamAccessMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        teams_q = Profile.objects.filter(member__user_id=request.user.id)
        teams_q = teams_q.select_related("user")
        request.teams = list(teams_q)

        request.profile = Profile.objects.for_user(request.user)
        request.team = request.profile.team()

        return self.get_response(request)
