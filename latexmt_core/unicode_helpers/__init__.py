def to_unicode_latex(tex_input: str, packages: list[str] = []) -> str:
    '''
    replaces all LaTeX-encoded umlauts (TODO: etc.) with their Unicode
    representations
    '''

    from .replacements import get_replacements

    for substrs, repl in get_replacements(packages):
        for substr in substrs:
            tex_input = tex_input.replace(substr, repl)

    return tex_input


def to_plain_latex(tex_input: str) -> str:
    from pylatexenc.latexencode import unicode_to_latex

    return unicode_to_latex(tex_input)
