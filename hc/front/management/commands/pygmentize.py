from django.core.management.base import BaseCommand


def _process(name, lexer):
    from pygments import highlight
    from pygments.formatters import HtmlFormatter

    source = open("templates/front/snippets/%s.txt" % name).read()
    processed = highlight(source, lexer, HtmlFormatter())
    processed = processed.replace("PING_URL", "{{ ping_url }}")
    processed = processed.replace("SITE_ROOT", "{{ SITE_ROOT }}")
    processed = processed.replace("PING_ENDPOINT", "{{ PING_ENDPOINT }}")
    with open("templates/front/snippets/%s.html" % name, "w") as out:
        out.write(processed)


class Command(BaseCommand):
    help = "Compiles snippets with Pygments"

    def handle(self, *args, **options):

        try:
            from pygments import lexers
        except ImportError:
            self.stdout.write("This command requires the Pygments package.")
            self.stdout.write("Please install it with:\n\n")
            self.stdout.write("  pip install Pygments\n\n")
            return

        # Invocation examples
        _process("bash_curl", lexers.BashLexer())
        _process("bash_wget", lexers.BashLexer())
        _process("browser", lexers.JavascriptLexer())
        _process("crontab", lexers.BashLexer())
        _process("cs", lexers.CSharpLexer())
        _process("node", lexers.JavascriptLexer())
        _process("go", lexers.GoLexer())
        _process("python_urllib2", lexers.PythonLexer())
        _process("python_requests", lexers.PythonLexer())
        _process("python_requests_fail", lexers.PythonLexer())
        _process("python_requests_start", lexers.PythonLexer())
        _process("python_requests_payload", lexers.PythonLexer())
        _process("php", lexers.PhpLexer())
        _process("powershell", lexers.shell.PowerShellLexer())
        _process("powershell_inline", lexers.shell.BashLexer())
        _process("ruby", lexers.RubyLexer())
