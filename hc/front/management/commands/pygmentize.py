from django.core.management.base import BaseCommand


def _process(fin, fout, lexer):
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    source = open("templates/front/snippets/" + fin).read()
    processed = highlight(source, lexer, HtmlFormatter())
    processed = processed.replace("PING_URL", "{{ ping_url }}")
    with open("templates/front/snippets/" + fout, "w") as out:
        out.write(processed)


class Command(BaseCommand):
    help = 'Compiles snippets with Pygments'

    def handle(self, *args, **options):

        try:
            from pygments import lexers
        except ImportError:
            self.stdout.write("This command requires Pygments package.")
            self.stdout.write("Please install it with:\n\n")
            self.stdout.write("  pip install Pygments\n\n")
            return

        _process("bash.txt", "bash.html", lexers.BashLexer())
        _process("browser.txt", "browser.html", lexers.JavascriptLexer())
        _process("crontab.txt", "crontab.html", lexers.BashLexer())
        _process("python.txt", "python.html", lexers.PythonLexer())
        _process("php.txt", "php.html", lexers.PhpLexer())
        _process("powershell.txt", "powershell.html",
                 lexers.shell.PowerShellLexer())
        _process("node.txt", "node.html", lexers.JavascriptLexer())
