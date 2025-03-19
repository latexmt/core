from latexmt_core.context_logger import logger_from_kwargs

# type imports
from pathlib import Path
from typing import Literal, Optional, Sequence


# typedefs
type Glossary = dict[str, str]
type GlossaryMethod = Literal['align', 'srcrepl']


def load_glossary(csv_path: Optional[Path] = None, lines: Optional[Sequence[str]] = None, **kwargs) -> Glossary:
    logger = logger_from_kwargs(**kwargs)

    if csv_path is not None and lines is None:
        with open(csv_path, 'r') as glossary_file:
            lines = glossary_file.readlines()
    elif lines is None:
        raise ValueError('must specify *either* csv_path or lines')

    glossary = dict(tuple[str, str](map(str.strip, line.split(',')[:2]))
                    for line in lines)
    logger.info('Loaded %d glossary entries' % (len(lines),))

    return glossary
