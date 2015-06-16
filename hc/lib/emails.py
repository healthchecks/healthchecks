from django.core.mail import send_mail


def send_status_notification(check):
    if check.status == "down":
        subject = "Alert DOWN"
        body = "Hi, the check %s has gone down" % check.code
    elif check.status == "up":
        subject = "Alert UP"
        body = "Hi, the check %s has gone up" % check.code
    else:
        raise NotImplemented("Unexpected status: %s" % check.status)

    send_mail(subject, body, 'cuu508@gmail.com', [check.user.email],
              fail_silently=False)
