import logging
from types import TracebackType
from typing import Any, NoReturn, Optional, Tuple, Type, Union

from typing_extensions import Protocol

from ..aio_trampoline import Done
from ..either import Right
from ..immutable import Immutable
from .effect import Effect, get_environment

ExcInfo = Tuple[Type[BaseException], BaseException, TracebackType]


class Logger(Immutable):
    """
    Wrapper around built-in `logging.Logger` class that
    calls logging methods as effects
    """
    logger: logging.Logger

    def debug(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.debug`

        :example:
        >>> import logging
        >>> Logger(logging.getLogger('foo')).debug('hello!').run(None)
        DEBUG:foo:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.debug` with `msg`
        """
        async def run_e(_):
            self.logger.debug(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def info(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.info`

        :example:
        >>> import logging
        >>> Logger(logging.getLogger('foo')).info('hello!').run(None)
        INFO:foo:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.info` with `msg`
        """
        async def run_e(_):
            self.logger.info(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def warning(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.warning`

        :example:
        >>> import logging
        >>> Logger(logging.getLogger('foo')).warning('hello!').run(None)
        WARNING:foo:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.warning` with `msg`
        """
        async def run_e(_):
            self.logger.warning(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def error(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.error`

        :example:
        >>> import logging
        >>> Logger(logging.getLogger('foo')).error('hello!').run(None)
        ERROR:foo:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.error` with `msg`
        """
        async def run_e(_):
            self.logger.error(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def critical(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.critical`

        :example:
        >>> import logging
        >>> Logger(logging.getLogger('foo')).critical('hello!').run(None)
        CRITICAL:foo:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.critical` with `msg`
        """
        async def run_e(_):
            self.logger.critical(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def exception(
        self,
        msg: str,
        stack_info: bool = True,
        exc_info: Union[bool, ExcInfo] = True
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.exception`

        :example:
        >>> import logging
        >>> Logger(logging.getLogger('foo')).exception('hello!').run(None)
        EXCEPTION:foo:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.exception` with `msg`
        """
        async def run_e(_):
            self.logger.exception(
                msg, stack_info=stack_info, exc_info=exc_info
            )
            return Done(Right(None))

        return Effect(run_e)


class Logging:
    """
    Module providing logging capability
    """
    def get_logger(self, name: Optional[str] = None) -> Logger:
        """
        Create an effect that produces a :class:`Logger` by calling built-in
        logging.getLogger

        :example:
        >>> Logging().get_logger('foo').and_then(
        ...     lambda logger: logger.info('hello!')
        ... ).run(None)
        INFO:foo:hello!

        :param name: name of logger
        :return: :class:`Effect` that produces a :class:`Logger`

        """
        return Logger(logging.getLogger(name))

    def debug(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.debug`

        :example:
        >>> Logging().debug('hello!').run(None)
        DEBUG:root:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.debug` with `msg`
        """
        async def run_e(_):
            logging.debug(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def info(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.info`

        :example:
        >>> Logging().info('hello!').run(None)
        INFO:root:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.info` with `msg`
        """
        async def run_e(_):
            logging.info(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def warning(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.warning`

        :example:
        >>> Logging().warning('hello!').run(None)
        WARNING:root:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.warning` with `msg`
        """
        async def run_e(_):
            logging.warning(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def error(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.error`

        :example:
        >>> Logging().error('hello!').run(None)
        ERROR:root:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.error` with `msg`
        """
        async def run_e(_):
            logging.error(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def critical(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.info`

        :example:
        >>> Logging().critical('hello!').run(None)
        CRITICAL:root:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.critical` with `msg`
        """
        async def run_e(_):
            logging.critical(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)

    def exception(
        self,
        msg: str,
        stack_info: bool = True,
        exc_info: Union[bool, ExcInfo] = True
    ) -> Effect[Any, NoReturn, None]:
        """
        Create an effect that calls built-in `logging.exception`

        :example:
        >>> Logging().exception('hello!').run(None)
        ERROR:root:hello!

        :param msg: the log message
        :param stack_info: whether to include stack information in the \
            log message
        :param exc_info: whether to include exception info in the log message

        :return: :class:`Effect` that calls `logging.exception` with `msg`
        """
        async def run_e(_):
            logging.exception(msg, stack_info=stack_info, exc_info=exc_info)
            return Done(Right(None))

        return Effect(run_e)


class HasLogging(Protocol):
    """
    Module provider for logging capability

    :type logging: Logging
    :attribute logging: The logging instance
    """
    logging: Logging


def get_logger(name: Optional[str] = None
               ) -> Effect[HasLogging, NoReturn, Logger]:
    """
    Create an effect that produces a :class:`Logger` by calling built-in
    logging.getLogger

    :example:
    >>> class Env:
    ...     logging = Logging()
    >>> get_logger('foo').and_then(
    ...     lambda logger: logger.info('hello!')
    ... ).run(None)
    INFO:foo:hello!

    :param name: name of logger
    :return: :class:`Effect` that produces a :class:`Logger`

    """
    return get_environment().map(lambda env: env.logging.get_logger(name))


def debug(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Effect[HasLogging, NoReturn, None]:
    """
    Create an effect that calls built-in `logging.debug`

    :example:
    >>> class Env:
    ...     logging = Logging()
    >>> debug('hello!').run(Env())
    DEBUG:root:hello!

    :param msg: the log message
    :param stack_info: whether to include stack information in the log message
    :param exc_info: whether to include exception info in the log message

    :return: :class:`Effect` that calls `logging.debug` with `msg`
    """
    return get_environment().and_then(
        lambda env: env.logging.
        debug(msg, stack_info=stack_info, exc_info=exc_info)
    )


def info(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Effect[HasLogging, NoReturn, None]:
    """
    Create an effect that calls built-in `logging.info`

    :example:
    >>> class Env:
    ...     logging = Logging()
    >>> info('hello!').run(Env())
    INFO:root:hello!

    :param msg: the log message
    :param stack_info: whether to include stack information in the log message
    :param exc_info: whether to include exception info in the log message

    :return: :class:`Effect` that calls `logging.info` with `msg`
    """
    return get_environment().and_then(
        lambda env: env.logging.
        info(msg, stack_info=stack_info, exc_info=exc_info)
    )


def warning(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Effect[HasLogging, NoReturn, None]:
    """
    Create an effect that calls built-in `logging.warning`

    :example:
    >>> class Env:
    ...     logging = Logging()
    >>> warning('hello!').run(Env())
    WARNING:root:hello!

    :param msg: the log message
    :param stack_info: whether to include stack information in the log message
    :param exc_info: whether to include exception info in the log message

    :return: :class:`Effect` that calls `logging.warning` with `msg`
    """
    return get_environment().and_then(
        lambda env: env.logging.
        warning(msg, stack_info=stack_info, exc_info=exc_info)
    )


def error(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Effect[HasLogging, NoReturn, None]:
    """
    Create an effect that calls built-in `logging.error`

    :example:
    >>> class Env:
    ...     logging = Logging()
    >>> error('hello!').run(Env())
    ERROR:root:hello!

    :param msg: the log message
    :param stack_info: whether to include stack information in the log message
    :param exc_info: whether to include exception info in the log message

    :return: :class:`Effect` that calls `logging.error` with `msg`
    """
    return get_environment().and_then(
        lambda env: env.logging.
        error(msg, stack_info=stack_info, exc_info=exc_info)
    )


def critical(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Effect[HasLogging, NoReturn, None]:
    """
    Create an effect that calls built-in `logging.critical`

    :example:
    >>> class Env:
    ...     logging = Logging()
    >>> critical('hello!').run(Env())
    CRITICAL:root:hello!

    :param msg: the log message
    :param stack_info: whether to include stack information in the log message
    :param exc_info: whether to include exception info in the log message

    :return: :class:`Effect` that calls `logging.critical` with `msg`
    """
    return get_environment().and_then(
        lambda env: env.logging.
        critical(msg, stack_info=stack_info, exc_info=exc_info)
    )


def exception(
    msg: str, stack_info: bool = True, exc_info: Union[bool, ExcInfo] = True
) -> Effect[HasLogging, NoReturn, None]:
    """
    Create an effect that calls built-in `logging.exception`

    :example:
    >>> class Env:
    ...     logging = Logging()
    >>> exception('hello!').run(Env())
    ERROR:root:hello!

    :param msg: the log message
    :param stack_info: whether to include stack information in the log message
    :param exc_info: whether to include exception info in the log message

    :return: :class:`Effect` that calls `logging.exception` with `msg`
    """
    return get_environment().and_then(
        lambda env: env.logging.
        exception(msg, stack_info=stack_info, exc_info=exc_info)
    )
