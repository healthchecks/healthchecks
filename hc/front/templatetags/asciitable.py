from django import template
from django.template import Context, Node, NodeList, TemplateSyntaxError
from django.template.base import Parser, Token
from tabulate import tabulate

register = template.Library()


class Table:
    def __init__(self) -> None:
        self.rows: list[list[str]] = []
        self.current_row: list[str] = []

    def add_cell(self, v: str) -> None:
        self.current_row.append(v)

    def add_row(self) -> None:
        self.rows.append(self.current_row)
        self.current_row = []

    def render(self) -> str:
        return tabulate(self.rows[1:], self.rows[0], tablefmt="grid")


class TableNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        t = context["__table__"] = Table()
        self.nodelist.render(context)

        # At this point, if the current row is not empty it means there
        # have been some cell blocks without outer row blocks
        if t.current_row:
            raise TemplateSyntaxError("The cell tag used without outer row tag")

        return t.render()


@register.tag
def table(parser: Parser, token: Token) -> TableNode:
    """Format tabular data as ASCII table.

    Example usage:

        {% table %}
            {% row %}
                {% cell %}Header 1{% endcell%}
                {% cell %}Header 2{% endcell%}
            {% endrow %}
            {% row %}
                {% cell %}Value 1{% endcell%}
                {% cell %}Value 2{% endcell%}
            {% endrow %}
        {% endtable %}

    This example returns this text:

        +------------+------------+
        | Header 1   | Header 2   |
        +============+============+
        | Value 1    | Value 2    |
        +------------+------------+

    """
    nodelist = parser.parse(("endtable",))
    parser.delete_first_token()
    return TableNode(nodelist)


@register.simple_block_tag(takes_context=True)
def row(context: Context, content: str) -> str:
    if "__table__" not in context:
        raise TemplateSyntaxError("The row tag used without outer table tag")

    context["__table__"].add_row()
    return ""


@register.simple_block_tag(takes_context=True)
def cell(context: Context, content: str) -> str:
    if "__table__" not in context:
        raise TemplateSyntaxError("The cell tag used without outer table tag")

    context["__table__"].add_cell(content)
    return ""
