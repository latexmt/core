import inspect
from contextlib import contextmanager
import logging
from typing import cast

# type imports
from typing import Any, Iterable, Mapping, Optional


class ContextLogger(logging.Logger):
    __log_context: dict[str, Any]
    __log_frames: list[Iterable[str]]

    def __init__(self, name, level=0):
        super().__init__(name, level)

        self.__log_context = dict()
        self.__log_frames = list()

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra: Optional[dict[str, Any]] = None, sinfo=None):
        extra = dict[str, Any]() if extra is None else extra
        return super().makeRecord(name, level, fn, lno, msg, args, exc_info,
                                  func=func,
                                  extra={'context': self.__log_context | extra},
                                  sinfo=sinfo)

    @contextmanager
    def frame(self, frame: Mapping[str, Any]):
        try:
            self.__log_frames.append(frame.keys())
            self.__log_context |= frame
            yield
        finally:
            keys = self.__log_frames.pop()
            for key in keys:
                self.__log_context.pop(key)


def logger_from_kwargs(**kwargs) -> ContextLogger:
    if 'logger' in kwargs and kwargs['logger'] is not None:
        _logger = cast(logging.Logger, kwargs['logger'])
        if not issubclass(_logger.__class__, ContextLogger):
            raise TypeError(
                f'`{_logger.__class__.__name__}` is not a subclass of `ContextLogger`')
    else:
        logging.setLoggerClass(ContextLogger)

        if 'parent_logger' in kwargs:
            parent = cast(logging.Logger, kwargs['parent_logger'])
        else:
            parent = logging.getLogger()

        if 'logger_name' in kwargs:
            name = cast(str, kwargs['logger_name'])
        else:
            caller_module = inspect.getmodule(inspect.stack()[1][0])
            if caller_module is not None:
                name = caller_module.__name__
            else:
                raise Exception('could not determine caller from stack')

        if name in logging.Logger.manager.loggerDict \
                and not issubclass(logging.Logger.manager.loggerDict[name].__class__, ContextLogger):
            del logging.Logger.manager.loggerDict[name]

        _logger = parent.getChild(name)

    return cast(ContextLogger, _logger)
