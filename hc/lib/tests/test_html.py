from __future__ import annotations

from unittest import TestCase

from hc.lib.html import extract_signal_styles, html2text


class Html2TextTestCase(TestCase):
    def test_it_works(self) -> None:
        sample = """
            <style>css goes here</style>
            <h1 class="foo">Hello</h1>
            World
            <script>js goes here</script>
            """

        self.assertEqual(html2text(sample), "Hello World")

    def test_it_does_not_inject_whitespace(self) -> None:
        sample = """<b>S</b>UCCESS"""
        self.assertEqual(html2text(sample), "SUCCESS")


class ExtractSignalTestCase(TestCase):
    def test_b_works(self) -> None:
        text, styles = extract_signal_styles("<b>foo</b> bar")
        self.assertEqual(text, "foo bar")
        self.assertEqual(styles, ["0:3:BOLD"])

    def test_code_works(self) -> None:
        text, styles = extract_signal_styles("foo <code>bar</code>")
        self.assertEqual(text, "foo bar")
        self.assertEqual(styles, ["4:3:MONOSPACE"])

    def test_it_rejects_mismatched_tags(self) -> None:
        with self.assertRaises(AssertionError):
            extract_signal_styles("<b>foo</code>")

    def test_it_unescapes_html(self) -> None:
        text, styles = extract_signal_styles("<b>5 &lt; 10</b>")
        self.assertEqual(text, "5 < 10")
        self.assertEqual(styles, ["0:6:BOLD"])
