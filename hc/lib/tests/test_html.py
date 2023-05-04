from __future__ import annotations

from unittest import TestCase

from hc.lib.html import html2text


class HtmlTestCase(TestCase):
    def test_it_works(self):
        sample = """
            <style>css goes here</style>
            <h1 class="foo">Hello</h1>
            World
            <script>js goes here</script>
            """

        self.assertEqual(html2text(sample), "Hello World")

    def test_it_does_not_inject_whitespace(self):
        sample = """<b>S</b>UCCESS"""
        self.assertEqual(html2text(sample), "SUCCESS")
