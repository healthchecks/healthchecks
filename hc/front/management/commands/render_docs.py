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

        extensions = [
            "fenced_code",
            "codehilite",
            "tables",
            "def_list",
            "attr_list",
        ]
        extension_configs = {
            "codehilite": {"css_class": "highlight", "startinline": True}
        }

        def process_directory(path):
            for src_path in path.glob("*.md"):
                print(f"Rendering {src_path.name}")

                text = src_path.open("r", encoding="utf-8").read()
                html = markdown.markdown(
                    text, extensions=extensions, extension_configs=extension_configs
                )

                dst_path = src_path.with_suffix(".html-fragment")
                with dst_path.open("w", encoding="utf-8") as f:
                    f.write(html)

        process_directory(settings.BASE_DIR / "templates/docs")
