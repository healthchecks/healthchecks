class TeamAccessMiddleware(object):
    def process_request(self, request):
        if not request.user.is_authenticated():
            return

        profile = request.user.profile
        if profile.current_team:
            request.team = profile.current_team
        else:
            request.team = profile
