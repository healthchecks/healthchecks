from django.core.management.base import BaseCommand
from pygments import highlight, lexers
from pygments.formatters import HtmlFormatter


def _process(fin, fout, lexer):
    source = open("templates/front/snippets/" + fin).read()
    processed = highlight(source, lexer, HtmlFormatter())
    processed = processed.replace("PING_URL", "{{ ping_url }}")
    with open("templates/front/snippets/" + fout, "w") as out:
        out.write(processed)


class Command(BaseCommand):
    help = 'Compiles snippets with pygmentize'

    def handle(self, *args, **options):
        _process("bash.txt", "bash.html", lexers.BashLexer())
        _process("browser.txt", "browser.html", lexers.JavascriptLexer())
        _process("crontab.txt", "crontab.html", lexers.BashLexer())
        _process("python.txt", "python.html", lexers.PythonLexer())
        _process("php.txt", "php.html", lexers.PhpLexer())
        _process("node.txt", "node.html", lexers.JavascriptLexer())
