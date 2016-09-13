from django.conf import settings
from django.core.signing import base64_hmac
from django.template.loader import render_to_string
from django.urls import reverse

WIDTHS = {"a": 7, "b": 7, "c": 6, "d": 7, "e": 6, "f": 4, "g": 7, "h": 7,
          "i": 3, "j": 3, "k": 7, "l": 3, "m": 10, "n": 7, "o": 7, "p": 7,
          "q": 7, "r": 4, "s": 6, "t": 5, "u": 7, "v": 7, "w": 9, "x": 6,
          "y": 7, "z": 7, "0": 7, "1": 6, "2": 7, "3": 7, "4": 7, "5": 7,
          "6": 7, "7": 7, "8": 7, "9": 7, "A": 8, "B": 7, "C": 8, "D": 8,
          "E": 7, "F": 6, "G": 9, "H": 8, "I": 3, "J": 4, "K": 7, "L": 6,
          "M": 10, "N": 8, "O": 9, "P": 6, "Q": 9, "R": 7, "S": 7, "T": 7,
          "U": 8, "V": 8, "W": 11, "X": 7, "Y": 7, "Z": 7, "-": 4, "_": 6}

COLORS = {
    "up": "#4c1",
    "late": "#fe7d37",
    "down": "#e05d44"
}


def get_width(s):
    total = 0
    for c in s:
        total += WIDTHS.get(c, 7)
    return total


def get_badge_svg(tag, status):
    w1 = get_width(tag) + 10
    w2 = get_width(status) + 10
    ctx = {
        "width": w1 + w2,
        "tag_width": w1,
        "status_width": w2,
        "tag_center_x": w1 / 2,
        "status_center_x": w1 + w2 / 2,
        "tag": tag,
        "status": status,
        "color": COLORS[status]
    }

    return render_to_string("badge.svg", ctx)


def check_signature(username, tag, sig):
    ours = base64_hmac(str(username), tag, settings.SECRET_KEY)
    ours = ours[:8].decode("utf-8")
    return ours == sig


def get_badge_url(username, tag):
    sig = base64_hmac(str(username), tag, settings.SECRET_KEY)
    url = reverse("hc-badge", args=[username, sig[:8], tag])
    return settings.SITE_ROOT + url
