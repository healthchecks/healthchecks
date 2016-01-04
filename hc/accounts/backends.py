from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from hc.accounts.models import Profile


# Authenticate against the token in user's profile.
class ProfileBackend(object):

    def authenticate(self, username=None, token=None):
        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return None

        if not check_password(token, profile.token):
            return None

        return profile.user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
