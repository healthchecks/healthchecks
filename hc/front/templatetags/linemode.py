from __future__ import annotations

from django import template
from django.template import Context, Node, NodeList, TemplateSyntaxError
from django.template.base import Parser, Token

register = template.Library()


class LineModeNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        context["__lines__"] = []
        self.nodelist.render(context)
        return "\n".join(context["__lines__"])


@register.tag
def linemode(parser: Parser, token: Token) -> LineModeNode:
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


@register.simple_block_tag(takes_context=True)
def line(context: Context, content: str) -> str:
    if "__lines__" not in context:
        raise TemplateSyntaxError("The line tag used without outer linemode tags")

    context["__lines__"].append(content)
    return ""
