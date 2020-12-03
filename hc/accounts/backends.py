from django.contrib.auth.models import User
from hc.accounts.models import Profile
from django.contrib.auth.backends import RemoteUserBackend
from hc.accounts import views
from django.conf import settings


class BasicBackend(object):
    def get_user(self, user_id):
        try:
            q = User.objects.select_related("profile")

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

class CustomHeaderBackend(RemoteUserBackend):
    def clean_username(self, username):
        if settings.REMOTE_USER_HEADER_TYPE == None: return None
        elif settings.REMOTE_USER_HEADER_TYPE == "ID": return username

        #else, it's the email address
        try:
            return User.objects.get(email=username).username
        except User.DoesNotExist:
            return views._make_user(username).username