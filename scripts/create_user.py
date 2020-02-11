from django.contrib.auth.models import User

# Args: Username, password, email
def run(*args):
  user=User.objects.create_user(args[0], password=args[1], email=args[2])
  user.is_superuser=False
  user.is_staff=True
  user.save()