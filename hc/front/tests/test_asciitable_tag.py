from __future__ import annotations

from django.template import Context, Template, TemplateSyntaxError
from hc.test import BaseTestCase


class AsciiTableTestCase(BaseTestCase):
    def test_it_works(self) -> None:
        t = Template(
            """{% load asciitable %}{% table %}
            {% row %}
                {% cell %}Header{% endcell %}
            {% endrow %}
            {% row %}
                {% cell %}Value{% endcell %}
            {% endrow %}
        {% endtable %}"""
        )

        expected = """
+--------+
| Header |
+========+
| Value  |
+--------+
""".strip()

        self.assertEqual(t.render(Context()), expected)

    def test_it_handles_row_without_table(self) -> None:
        t = Template("""{% load asciitable %}{% row %}{% endrow %}""")

        with self.assertRaises(TemplateSyntaxError):
            t.render(Context())

    def test_it_handles_cell_without_row(self) -> None:
        t = Template(
            """{% load asciitable %}{% table %}{% cell %}Text{% endcell %}{% endtable %}"""
        )

        with self.assertRaises(TemplateSyntaxError):
            t.render(Context())
