from __future__ import annotations

import sqlite3
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from hc.front.views import _replace_placeholders
from hc.lib.html import html2text


class Command(BaseCommand):
    help = "Renders Markdown to HTML"

    def handle(self, **options: Any) -> None:
        con = sqlite3.connect(settings.BASE_DIR / "search.db")
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS docs")
        cur.execute(
            """CREATE VIRTUAL TABLE docs
            USING FTS5(slug, title, body, tokenize="porter unicode61")"""
        )

        docs_path = settings.BASE_DIR / "templates/docs"
        for doc_path in docs_path.glob("*.html-fragment"):
            if doc_path.stem == "apiv1" or doc_path.stem == "apiv2":
                continue

            slug = doc_path.stem
            print("Processing %s" % slug)

            html = doc_path.open("r").read()
            html = _replace_placeholders(slug, html)

            lines = html.split("\n")
            title = html2text(lines[0])
            text = html2text("\n".join(lines[1:]), skip_pre=True)

            cur.execute("INSERT INTO docs VALUES (?, ?, ?)", (slug, title, text))

        con.commit()
