from django.contrib.auth.models import User
from hc.accounts.models import Profile


class BasicBackend(object):
    def get_user(self, user_id):
        try:
            q = User.objects.select_related("profile", "profile__current_project")

            return q.get(pk=user_id)
        except User.DoesNotExist:
            return None


# Authenticate against the token in user's profile.
class ProfileBackend(BasicBackend):
    def authenticate(self, request=None, username=None, token=None):
        try:
            profiles = Profile.objects.select_related("user")
            profile = profiles.get(user__username=username)
        except Profile.DoesNotExist:
            return None

        if not profile.check_token(token, "login"):
            return None

        return profile.user


class EmailBackend(BasicBackend):
    def authenticate(self, request=None, username=None, password=None):
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user
