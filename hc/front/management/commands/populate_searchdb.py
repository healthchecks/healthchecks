from __future__ import annotations

import os
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand

from hc.front.views import _replace_placeholders
from hc.lib.html import html2text


class Command(BaseCommand):
    help = "Renders Markdown to HTML"

    def handle(self, *args, **options):
        con = sqlite3.connect(os.path.join(settings.BASE_DIR, "search.db"))
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS docs")
        cur.execute(
            """CREATE VIRTUAL TABLE docs USING FTS5(slug, title, body, tokenize="porter unicode61")"""
        )

        docs_path = os.path.join(settings.BASE_DIR, "templates/docs")
        for filename in os.listdir(docs_path):
            if not filename.endswith(".html"):
                continue
            if filename == "apiv1.html":
                continue

            slug = filename[:-5]  # cut ".html"
            print("Processing %s" % slug)

            html = open(os.path.join(docs_path, filename), "r").read()
            html = _replace_placeholders(slug, html)

            lines = html.split("\n")
            title = html2text(lines[0])
            text = html2text("\n".join(lines[1:]), skip_pre=True)

            cur.execute("INSERT INTO docs VALUES (?, ?, ?)", (slug, title, text))

        con.commit()
