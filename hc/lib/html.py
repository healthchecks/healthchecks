from html.parser import HTMLParser


class TextOnlyParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active = True
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.active = False

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.active = True

    def handle_data(self, data):
        if self.active and data:
            self.buf.append(data)

    def get_text(self):
        messy = "".join(self.buf)
        return " ".join(messy.split())


def html2text(html):
    parser = TextOnlyParser()
    parser.feed(html)
    return parser.get_text()
