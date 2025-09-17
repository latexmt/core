from itertools import chain
import sys

from latexmt_core.context_logger import ContextLogger, logger_from_kwargs
import latexmt_core.glossary.align as gloss_align
import latexmt_core.glossary.srcrepl as gloss_srcrepl
from latexmt_core.parsing.to_text import is_space_or_masked, mask_str_default
from latexmt_core.parsing.unpack import latex_to_nodelist, get_textitems
from latexmt_core.parsing.repack import nodelist_to_latex, replace_nodes
from latexmt_core.parsing.parsplit import parsplit
from latexmt_core.parsing.latex_context import get_latex_context

from latexmt_core.unicode_helpers import to_unicode_latex

from .helpers import ensure_dir, textitem_flatlist_to_nodelist

# type imports
from typing import Literal, TextIO
from pathlib import Path
import pylatexenc.latexnodes.nodes as lw
from latexmt_core.alignment import Aligner, words_spans_to_markupstr
from latexmt_core.glossary import GlossaryMethod
from latexmt_core.markup_string import MarkupStartMarker, MarkupEndMarker
from latexmt_core.parsing.text_item import TextItem
from latexmt_core.translation import Translator


class DocumentTranslator:
    __translator: Translator
    __aligner: Aligner

    __root_document: Path
    __output_dir: Path

    __recurse_input: bool
    __input_queue: list[Path]

    __processed_files: list[Path]

    __logger: ContextLogger

    glossary: dict[str, str]
    glossary_method: Literal['builtin'] | GlossaryMethod

    mask_str: str

    def clear_processed(self):
        '''
        clear the list of processed files
        '''
        self.__processed_files.clear()

    @property
    def __root_document_dir(self) -> Path:
        return self.__root_document.parent

    def __init__(
        self,
        translator: Translator,
        aligner: Aligner,
        recurse_input: bool = True,
        glossary: dict[str, str] = {},
        glossary_method: Literal['auto'] | GlossaryMethod = 'auto',
        glossary_fallback: GlossaryMethod = 'align',
        mask_str: str = mask_str_default,
        **kwargs
    ):
        self.__logger = logger_from_kwargs(**kwargs)
        self.__logger.debug('Initialising %s' % (self.__class__.__name__, ),
                            extra={'translator': translator, 'aligner': aligner, 'mask_str': mask_str})

        self.__translator = translator
        self.__aligner = aligner
        self.__recurse_input = recurse_input
        self.__input_queue = list()
        self.__processed_files = list()
        self.glossary = glossary
        self.glossary_method = (('builtin' if self.__translator.supports_glossary else glossary_fallback)
                                if glossary_method == 'auto' else glossary_method)
        self.mask_str = mask_str

    def __get_input_path(self, filename: Path) -> Path:
        return self.__root_document_dir.joinpath(filename)

    def __get_output_path(self, filename: Path) -> Path:
        return self.__output_dir.joinpath(filename)

    def __translate_textitem(self, textitem: TextItem) -> list[lw.LatexNode]:
        initial_whitespace, paragraphs, final_whitespace = parsplit(textitem.text)  # nopep8

        # TODO: this should be a type
        translated_flatlist: list[str | MarkupStartMarker | MarkupEndMarker]\
            = [initial_whitespace]

        for in_text in paragraphs:
            try:
                if is_space_or_masked(in_text, textitem.mask_str):
                    out_text_flatlist = in_text.to_markup_list()
                else:
                    if self.glossary_method == 'srcrepl':
                        in_text = gloss_srcrepl.apply(in_text, self.glossary)
                    self.__translator.translate(
                        in_text, self.glossary if self.glossary_method == 'builtin' else {})
                    self.__aligner.align(
                        in_text, self.__translator.output_text)

                    if self.glossary_method == 'align':
                        out_text = words_spans_to_markupstr(
                            *gloss_align.apply(self.__aligner, self.glossary),
                        )
                    else:
                        out_text = self.__aligner.target_text

                    out_text_flatlist = out_text.to_markup_list()
            except Exception as e:
                self.__logger.warning('Translation of paragraph failed',
                                      extra={'error': e, 'in_text': in_text})
                translated_flatlist.extend([
                    '\n\n',
                    f'\textbf{{NOTE}}: Translation of the following paragraph failed: {e}',
                    '\n\n'
                ])
                out_text_flatlist = in_text.to_markup_list()

            translated_flatlist.extend(
                chain(out_text_flatlist, ('\n\n',)))
        # for in_text

        translated_flatlist[-1] = final_whitespace

        # while tmp_idx
        # concatenate adjacent strings in `translated_flatlist`
        tmp_idx = 0
        while tmp_idx < len(translated_flatlist) - 1:
            if (type(translated_flatlist[tmp_idx]), type(translated_flatlist[tmp_idx+1])) == (str, str):
                translated_flatlist[tmp_idx] += \
                    translated_flatlist[tmp_idx+1]  # type: ignore
                translated_flatlist.pop(tmp_idx+1)
            else:
                tmp_idx += 1
        # while tmp_idx
        del tmp_idx

        return textitem_flatlist_to_nodelist(textitem, translated_flatlist)

    def __process_file(self, input_file: TextIO, output_file: TextIO):
        '''
        translate a LaTeX document and direct the output to `output_file`
        '''

        self.__logger.info(f'Processing file \'{input_file.name}\'')

        # TODO: get list of LaTeX packages to be used here
        input_text = to_unicode_latex(input_file.read(), [])

        self.__logger.debug('Parsing LaTeX')

        out_included_files = list[str]()
        latex_context = get_latex_context(out_included_files)
        nodelist = latex_to_nodelist(input_text, latex_context)
        textitems = get_textitems(nodelist, latex_context, self.mask_str)

        for index, textitem in enumerate(textitems):
            with self.__logger.frame({'textitem_index': index}):
                self.__logger.debug(f'Translating textitem {index+1}/{len(textitems)}')  # nopep8

                translated_nodelist = self.__translate_textitem(textitem)

                original = nodelist_to_latex(textitem.nodelist)
                translated = nodelist_to_latex(translated_nodelist)

                self.__logger.debug(f'Finished translating textitem {index+1}/{len(textitems)}',
                                    extra=({'original': original, 'translated': translated}))

                # delete original nodes and insert newly created nodes holding translated text
                self.__logger.debug('Reinserting modified nodelist')
                replace_nodes(textitem.parent_nodelist,
                              textitem.nodelist, translated_nodelist)
        # for index, textitem

        print(nodelist_to_latex(nodelist).rstrip(), file=output_file)

        if self.__recurse_input:
            for new_in_filename in out_included_files:
                if not new_in_filename.endswith('.tex'):
                    new_in_filename += '.tex'

                new_in_path = Path(new_in_filename)
                if new_in_path not in self.__input_queue:
                    self.__input_queue.append(new_in_path)
                    self.__logger.info(f'Adding input file to queue: {new_in_path}')  # nopep8
            # for new_in_filename
        # if self.__recurse_input

        self.__logger.debug('Finished processing file')

    def process_document(self, root_document: Path, output_dir: Path):
        with self.__logger.frame({
            'root_document': str(root_document),
            'output_dir': str(output_dir),
        }):
            self.__logger.info('Started processing document')
            ensure_dir(output_dir)

            self.__root_document = root_document
            self.__output_dir = output_dir

            # stdin
            if str(self.__root_document) == '-':
                self.__process_file(sys.stdin, sys.stdout)
                self.__logger.info(
                    f'See \'{self.__output_dir}/\' for supplemental (`\\input`) files')

            else:
                self.__input_queue.append(
                    self.__root_document.relative_to(self.__root_document_dir))

                while len(self.__input_queue) > 0:
                    input_filename = self.__input_queue.pop(0)
                    input_path = self.__get_input_path(input_filename)

                    output_path = self.__get_output_path(input_filename)

                    if input_path.resolve() in self.__processed_files:
                        self.__logger.info('Already processed, skipping')
                        return
                    self.__processed_files.append(input_path.resolve())

                    with self.__logger.frame({
                        'input_path': str(input_path),
                        'output_path': str(output_path)
                    }):
                        ensure_dir(output_path.parent)
                        try:
                            with open(input_path, 'r') as input_file, open(output_path, 'w') as output_file:
                                self.__process_file(input_file, output_file)
                        except OSError as os_err:
                            self.__logger.warning(
                                f'Could not open input or output file: {os_err}')
                # while len(self.__input_queue)

            self.__logger.info('Finished processing document')
