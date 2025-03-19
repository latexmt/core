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
        'package-commands',
        prepend=True,
        macros=[MacroSpec('enquote', '{'), MacroSpec('caption', '{')]
    )

    newenvironment_parser = CharsArgumentParser('{')
    latex_context.add_context_category(
        'newenvironment',
        prepend=True,
        macros=[
            MacroSpec('newenvironment', arguments_spec_list=[
                '*', LatexArgumentSpec('{', argname='env_name'), '[', '[',
                LatexArgumentSpec(newenvironment_parser, argname='env_begin'),
                LatexArgumentSpec(newenvironment_parser, argname='env_end'),
            ])
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
