from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser


class TextOnlyParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active = True
        self.buf = []
        self.skiplist = set(["script", "style"])

    def handle_starttag(self, tag, attrs):
        if tag in self.skiplist:
            self.active = False

    def handle_endtag(self, tag):
        if tag in self.skiplist:
            self.active = True

    def handle_data(self, data):
        if self.active and data:
            self.buf.append(data)

    def get_text(self):
        messy = "".join(self.buf)
        return " ".join(messy.split())


def html2text(html, skip_pre=False):
    parser = TextOnlyParser()
    if skip_pre:
        parser.skiplist.add("pre")

    parser.feed(html)
    return parser.get_text()


def extract_signal_styles(markup: str) -> tuple[str, list[str]]:
    """Convert HTML syntax to Signal text styles.

    This implementation has limited functionality, and only supports the features
    we do use:
    * only supports <b> and <code> tags
    * does not support nested (<b><code>text</code></b>) tags

    Example:

    >>> extract_signal_styles("<b>foo</b> bar")
    "foo bar", ["0:3:BOLD"]

    """
    text = ""
    styles: list[str] = []
    tag, tag_idx = "", 0

    for part in re.split(r"(</?(?:b|code)>)", markup):
        if part == "<b>":
            tag = "BOLD"
            tag_idx = len(text)
        elif part == "</b>":
            assert tag == "BOLD"
            len_tagged = len(text) - tag_idx
            styles.append(f"{tag_idx}:{len_tagged}:{tag}")
        elif part == "<code>":
            tag = "MONOSPACE"
            tag_idx = len(text)
        elif part == "</code>":
            assert tag == "MONOSPACE"
            len_tagged = len(text) - tag_idx
            styles.append(f"{tag_idx}:{len_tagged}:{tag}")
        else:
            text += unescape(part)

    return text, styles
