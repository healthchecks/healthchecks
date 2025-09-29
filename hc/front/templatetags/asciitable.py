from django import template
from django.template import Context, Node, NodeList, TemplateSyntaxError
from django.template.base import Parser, Token
from tabulate import tabulate

register = template.Library()


class TableNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        context["__rows__"] = []
        self.nodelist.render(context)

        header = context["__rows__"][0]
        rows = context["__rows__"][1:]
        return tabulate(rows, header, tablefmt="grid")


class RowNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        if "__rows__" not in context:
            raise TemplateSyntaxError("The row tag used without outer table tag")

        context["__cells__"] = []
        self.nodelist.render(context)
        context["__rows__"].append(context["__cells__"])
        return ""


class CellNode(Node):
    def __init__(self, nodelist: NodeList) -> None:
        self.nodelist = nodelist

    def render(self, context: Context) -> str:
        if "__cells__" not in context:
            raise TemplateSyntaxError("The cell tag used without outer row tag")

        context["__cells__"].append(self.nodelist.render(context))
        return ""


@register.tag
def table(parser: Parser, token: Token) -> TableNode:
    nodelist = parser.parse(("endtable",))
    parser.delete_first_token()
    return TableNode(nodelist)


@register.tag
def row(parser: Parser, token: Token) -> RowNode:
    nodelist = parser.parse(("endrow",))
    parser.delete_first_token()
    return RowNode(nodelist)


@register.tag
def cell(parser: Parser, token: Token) -> CellNode:
    nodelist = parser.parse(("endcell",))
    parser.delete_first_token()
    return CellNode(nodelist)
