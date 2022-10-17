from __future__ import annotations

from django.template import Context, Template, TemplateSyntaxError

from hc.test import BaseTestCase


class LinemodeTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_it_works(self):
        t = Template(
            """{% load linemode %}{% linemode %}
            {% line %}Line one.{% endline %}
            This content will be ignored.
            {% if True %}
                {% line %}Line two.{% endline %}
            {% endif %}
        {% endlinemode %}"""
        )

        ctx = Context()
        self.assertEqual(t.render(ctx), "Line one.\nLine two.")

    def test_it_handles_line_without_linemode(self):
        t = Template("""{% load linemode %}{% line %}Text{% endline %}""")

        with self.assertRaises(TemplateSyntaxError):
            t.render(Context())
