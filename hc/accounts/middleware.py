from hc.accounts.models import Profile


class TeamAccessMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            teams_q = Profile.objects.filter(member__user_id=request.user.id)
            teams_q = teams_q.select_related("user")
            request.teams = list(teams_q)

            try:
                profile = request.user.profile
            except Profile.DoesNotExist:
                profile = Profile(user=request.user)
                profile.save()

            if profile.current_team:
                request.team = profile.current_team
            else:
                request.team = profile

        return self.get_response(request)
