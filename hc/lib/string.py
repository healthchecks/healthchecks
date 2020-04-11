def replace(template, ctx):
    """Replace placeholders with their values and return the result.

    Example:

    >>> replace("$NAME is down", {"$NAME": "foo"})
    foo is down

    This function explicitly ignores "variable variables".
    In this example, placeholder's value itself contains a placeholder:

    >>> replace("Hello $FOO", {"$FOO": "$BAR", "$BAR": "World"})
    Wrong: Hello World
    Correct: Hello $BAR

    >>> replace("Hello $$FOO", {"$FOO": "BAR", "$BAR": "World"})
    Wrong: Hello World
    Correct: Hello $BAR

    In other words, this function only replaces placeholders that appear
    in the original template. It ignores any placeholders that "emerge"
    during string substitutions. This is done mainly to avoid unexpected
    behavior when check names or tags contain dollar signs.

    """

    parts = template.split("$")

    result = [parts.pop(0)]
    for part in parts:
        part = "$" + part
        for placeholder, value in ctx.items():
            if part.startswith(placeholder):
                part = part.replace(placeholder, value, 1)
                break
        result.append(part)

    return "".join(result)
