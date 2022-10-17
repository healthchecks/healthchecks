from __future__ import annotations

import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Renders Markdown to HTML"

    def handle(self, *args, **options):
        try:
            import markdown

            # We use pygments for highlighting code samples
            import pygments
        except ImportError as e:
            self.stdout.write(f"This command requires the {e.name} package.")
            self.stdout.write("Please install it with:\n\n")
            self.stdout.write(f"  pip install {e.name}\n\n")
            return

        extensions = ["fenced_code", "codehilite", "tables", "def_list", "attr_list"]
        ec = {"codehilite": {"css_class": "highlight", "startinline": True}}

        docs_path = os.path.join(settings.BASE_DIR, "templates/docs")
        for doc in os.listdir(docs_path):
            if not doc.endswith(".md"):
                continue

            print("Rendering %s" % doc)

            src_path = os.path.join(docs_path, doc)
            dst_path = os.path.join(docs_path, doc[:-3] + ".html")

            text = open(src_path, "r", encoding="utf-8").read()
            html = markdown.markdown(text, extensions=extensions, extension_configs=ec)

            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(html)
