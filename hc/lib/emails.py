from djmail.template_mail import InlineCSSTemplateMail


def login(to, ctx):
    o = InlineCSSTemplateMail("login")
    o.send(to, ctx)


def alert(to, ctx):
    o = InlineCSSTemplateMail("alert")
    o.send(to, ctx)


def verify_email(to, ctx):
    o = InlineCSSTemplateMail("verify-email")
    o.send(to, ctx)


def report(to, ctx):
    o = InlineCSSTemplateMail("report")
    o.send(to, ctx)
