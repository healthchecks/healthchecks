from django.db.models import Q
from hc.accounts.models import Profile, Project


class TeamAccessMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        is_owner = Q(owner=request.user)
        is_member = Q(member__user_id=request.user.id)
        projects_q = Project.objects.filter(is_owner | is_member)
        projects_q = projects_q.select_related("owner")
        request.get_projects = lambda: list(projects_q)

        profile = Profile.objects.for_user(request.user)
        if profile.current_project is None:
            profile.current_project = profile.get_own_project()
            profile.save()

        request.profile = profile
        request.project = profile.current_project

        return self.get_response(request)
