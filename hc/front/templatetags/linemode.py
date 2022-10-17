from __future__ import annotations

from django import template
from django.template import Node, TemplateSyntaxError

register = template.Library()


class LineModeNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        context["__lines__"] = []
        self.nodelist.render(context)
        return "\n".join(context["__lines__"])


@register.tag
def linemode(parser, token):
    """Skip content outside {% line %} blocks.

    Intended to be used for precise control of whitespace and newlines.
    Example usage::

        {% linemode %}
            {% line %}Line one.{% endline %}
            This content will be ignored.
            {% if True %}
                {% line %}Line two.{% endline %}
            {% endif %}
        {% endlinemode %}

    This example returns this text::

        Line one.
        Line two.

    """

    nodelist = parser.parse(("endlinemode",))
    parser.delete_first_token()
    return LineModeNode(nodelist)


class LineNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        if "__lines__" not in context:
            raise TemplateSyntaxError("The line tag used without outer linemode tags")

        context["__lines__"].append(self.nodelist.render(context))
        return ""


@register.tag
def line(parser, token):
    """For use with {% linemode %}.

    Renders the enclosed content and appends it to context["__lines__"]
    instead of returning it.

    """

    nodelist = parser.parse(("endline",))
    parser.delete_first_token()
    return LineNode(nodelist)
