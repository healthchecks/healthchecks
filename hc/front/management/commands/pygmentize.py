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
            self.stdout.write("This command requires Pygments package.")
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
        _process("python_urllib2", lexers.PythonLexer())
        _process("python_requests", lexers.PythonLexer())
        _process("python_requests_fail", lexers.PythonLexer())
        _process("python_requests_start", lexers.PythonLexer())
        _process("python_requests_payload", lexers.PythonLexer())
        _process("php", lexers.PhpLexer())
        _process("powershell", lexers.shell.PowerShellLexer())
        _process("powershell_inline", lexers.shell.BashLexer())
        _process("ruby", lexers.RubyLexer())

        # API examples
        _process("list_checks_request", lexers.BashLexer())
        _process("list_checks_response", lexers.JsonLexer())
        _process("list_checks_response_readonly", lexers.JsonLexer())
        _process("list_channels_request", lexers.BashLexer())
        _process("list_channels_response", lexers.JsonLexer())
        _process("create_check_request_a", lexers.BashLexer())
        _process("create_check_request_b", lexers.BashLexer())
        _process("update_check_request_a", lexers.BashLexer())
        _process("update_check_request_b", lexers.BashLexer())
        _process("create_check_response", lexers.JsonLexer())
        _process("pause_check_request", lexers.BashLexer())
        _process("pause_check_response", lexers.JsonLexer())
        _process("delete_check_request", lexers.BashLexer())
