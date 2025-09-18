from pylatexenc.latexwalker import get_default_latex_context_db
from pylatexenc.latexnodes import LatexArgumentSpec, ParsingStateDeltaEnterMathMode
from pylatexenc.macrospec import MacroSpec, EnvironmentSpec

from .macro_parsers import CharsArgumentParser, InputArgumentParser
from .special_commands import math_environs


def get_latex_context(out_included_files: list[str]):
    '''
    returns a `pylatexenc.LatexContextDb` that handles custom macro processing
    and, when encountering an `\\input` or `\\include` macro, appends its contents
    to the list passed via `out_included_files`
    '''

    latex_context = get_default_latex_context_db()

    # FIXME: this should probably not be done here
    latex_context.add_context_category(
        'extra-commands',
        prepend=True,
        macros=[
            MacroSpec('enquote', '{'),
            MacroSpec('caption', '{'),
            MacroSpec('paragraph', '{'),
            MacroSpec('footnote', '{'),
        ]
    )

    plaintext_req = CharsArgumentParser('{')
    latex_context.add_context_category(
        'new-commands',
        prepend=True,
        macros=[
            MacroSpec('newenvironment', arguments_spec_list=[
                '*', LatexArgumentSpec('{', argname='env_name'), '[', '[',
                LatexArgumentSpec(plaintext_req, argname='env_begin'),
                LatexArgumentSpec(plaintext_req, argname='env_end'),
            ]),
            MacroSpec('newcommand', arguments_spec_list=[
                LatexArgumentSpec('{', argname='cmd_name'),
                LatexArgumentSpec('[', argname='cmd_argcount'),
                LatexArgumentSpec(plaintext_req, argname='cmd_content'),
            ]),
            # TODO: store and later recognise let aliases
            MacroSpec('let', arguments_spec_list=[
                LatexArgumentSpec('{', argname='let_name'),
                LatexArgumentSpec(plaintext_req, argname='let_content'),
            ]),
        ]
    )

    latex_context.add_context_category(
        'amsmath',
        prepend=True,
        environments=[EnvironmentSpec(name, arguments_spec_list='*',
                                      body_parsing_state_delta=ParsingStateDeltaEnterMathMode())
                      for name in math_environs]
    )

    input_parser = InputArgumentParser(out_included_files, '{')
    latex_context.add_context_category(
        'input',
        prepend=True,
        macros=[MacroSpec('input', arguments_spec_list=[input_parser]),
                MacroSpec('include', arguments_spec_list=[input_parser])]
    )

    return latex_context
