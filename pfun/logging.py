import logging
from types import TracebackType
from typing import Optional, Tuple, Type, Union

from typing_extensions import Protocol

from .effect import Depends, Success, add_repr, depend, from_callable, io_bound
from .either import Right
from .functions import curry
from .immutable import Immutable

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
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.debug`

        Example:
            >>> import logging
            >>> Logger(logging.getLogger('foo')).debug('hello!').run(None)
            DEBUG:foo:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.debug` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            self.logger.debug(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def info(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.info`

        Example:
            >>> import logging
            >>> Logger(logging.getLogger('foo')).info('hello!').run(None)
            INFO:foo:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.info` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            self.logger.info(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def warning(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.warning`

        Example:
            >>> import logging
            >>> Logger(logging.getLogger('foo')).warning('hello!').run(None)
            WARNING:foo:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.warning` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            self.logger.warning(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def error(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.error`

        Example:
            >>> import logging
            >>> Logger(logging.getLogger('foo')).error('hello!').run(None)
            ERROR:foo:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.error` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            self.logger.error(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def critical(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.critical`

        Example:
            >>> import logging
            >>> Logger(logging.getLogger('foo')).critical('hello!').run(None)
            CRITICAL:foo:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
        `Effect` that calls `logging.critical` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            self.logger.critical(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def exception(
        self,
        msg: str,
        stack_info: bool = True,
        exc_info: Union[bool, ExcInfo] = True
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.exception`

        Example:
            >>> import logging
            >>> Logger(logging.getLogger('foo')).exception('hello!').run(None)
            EXCEPTION:foo:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.exception` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            self.logger.exception(
                msg, stack_info=stack_info, exc_info=exc_info
            )
            return Right(None)

        return from_callable(f)


class Logging:
    """
    Module providing logging capability
    """
    def get_logger(self, name: Optional[str] = None) -> Logger:
        """
        Create an effect that produces a `Logger` by calling built-in
        logging.getLogger

        Example:
            >>> Logging().get_logger('foo').and_then(
            ...     lambda logger: logger.info('hello!')
            ... ).run(None)
            INFO:foo:hello!

        Args:
            name: name of logger
        Return:
            `Effect` that produces a `Logger`

        """
        return Logger(logging.getLogger(name))

    def debug(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.debug`

        Example:
            >>> Logging().debug('hello!').run(None)
            DEBUG:root:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.debug` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            logging.debug(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def info(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.info`

        Example:
            >>> Logging().info('hello!').run(None)
            INFO:root:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.info` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            logging.info(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def warning(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.warning`

        Example:
            >>> Logging().warning('hello!').run(None)
            WARNING:root:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.warning` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            logging.warning(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def error(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.error`

        Example:
            >>> Logging().error('hello!').run(None)
            ERROR:root:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.error` with `msg`
        """
        @io_bound
        def f(_: object):
            logging.error(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def critical(
        self,
        msg: str,
        stack_info: bool = False,
        exc_info: Union[bool, ExcInfo] = False
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.info`

        Example:
            >>> Logging().critical('hello!').run(None)
            CRITICAL:root:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.critical` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            logging.critical(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)

    def exception(
        self,
        msg: str,
        stack_info: bool = True,
        exc_info: Union[bool, ExcInfo] = True
    ) -> Success[None]:
        """
        Create an effect that calls built-in `logging.exception`

        Example:
            >>> Logging().exception('hello!').run(None)
            ERROR:root:hello!

        Args:
            msg: the log message
            stack_info: whether to include stack information in the \
                log message
            exc_info: whether to include exception info in the log message

        Return:
            `Effect` that calls `logging.exception` with `msg`
        """
        @io_bound
        def f(_: object) -> Right[None]:
            logging.exception(msg, stack_info=stack_info, exc_info=exc_info)
            return Right(None)

        return from_callable(f)


class HasLogging(Protocol):
    """
    Module provider for logging capability

    :type logging: Logging
    :attribute logging: The logging instance
    """
    logging: Logging


@add_repr
def get_logger(name: Optional[str] = None) -> Depends[HasLogging, Logger]:
    """
    Create an effect that produces a `Logger` by calling built-in
    logging.getLogger

    Example:
        >>> class Env:
        ...     logging = Logging()
        >>> get_logger('foo').and_then(
        ...     lambda logger: logger.info('hello!')
        ... ).run(None)
        INFO:foo:hello!

    Args:
        name: name of logger
    Return:
        `Effect` that produces a `Logger`

    """
    return depend().map(lambda env: env.logging.get_logger(name))


@curry
@add_repr
def debug(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Depends[HasLogging, None]:
    """
    Create an effect that calls built-in `logging.debug`

    Example:
        >>> class Env:
        ...     logging = Logging()
        >>> debug('hello!').run(Env())
        DEBUG:root:hello!

    Args:
        msg: the log message
        stack_info: whether to include stack information in the log message
        exc_info: whether to include exception info in the log message

    Return:
        `Effect` that calls `logging.debug` with `msg`
    """
    return depend().and_then(
        lambda env: env.logging.
        debug(msg, stack_info=stack_info, exc_info=exc_info)
    )


@curry
@add_repr
def info(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Depends[HasLogging, None]:
    """
    Create an effect that calls built-in `logging.info`

    Example:
        >>> class Env:
        ...     logging = Logging()
        >>> info('hello!').run(Env())
        INFO:root:hello!

    Args:
        msg: the log message
        stack_info: whether to include stack information in the log message
        exc_info: whether to include exception info in the log message

    Return:
        `Effect` that calls `logging.info` with `msg`
    """
    return depend().and_then(
        lambda env: env.logging.
        info(msg, stack_info=stack_info, exc_info=exc_info)
    )


@curry
@add_repr
def warning(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Depends[HasLogging, None]:
    """
    Create an effect that calls built-in `logging.warning`

    Example:
        >>> class Env:
        ...     logging = Logging()
        >>> warning('hello!').run(Env())
        WARNING:root:hello!

    Args:
        msg: the log message
        stack_info: whether to include stack information in the log message
        exc_info: whether to include exception info in the log message

    Return:
        `Effect` that calls `logging.warning` with `msg`
    """
    return depend().and_then(
        lambda env: env.logging.
        warning(msg, stack_info=stack_info, exc_info=exc_info)
    )


@curry
@add_repr
def error(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Depends[HasLogging, None]:
    """
    Create an effect that calls built-in `logging.error`

    Example:
        >>> class Env:
        ...     logging = Logging()
        >>> error('hello!').run(Env())
        ERROR:root:hello!

    Args:
        msg: the log message
        stack_info: whether to include stack information in the log message
        exc_info: whether to include exception info in the log message

    Return:
        `Effect` that calls `logging.error` with `msg`
    """
    return depend().and_then(
        lambda env: env.logging.
        error(msg, stack_info=stack_info, exc_info=exc_info)
    )


@curry
@add_repr
def critical(
    msg: str, stack_info: bool = False, exc_info: Union[bool, ExcInfo] = False
) -> Depends[HasLogging, None]:
    """
    Create an effect that calls built-in `logging.critical`

    Example:
        >>> class Env:
        ...     logging = Logging()
        >>> critical('hello!').run(Env())
        CRITICAL:root:hello!

    Args:
        msg: the log message
        stack_info: whether to include stack information in the log message
        exc_info: whether to include exception info in the log message

    Return:
        `Effect` that calls `logging.critical` with `msg`
    """
    return depend().and_then(
        lambda env: env.logging.
        critical(msg, stack_info=stack_info, exc_info=exc_info)
    )


@curry
@add_repr
def exception(
    msg: str, stack_info: bool = True, exc_info: Union[bool, ExcInfo] = True
) -> Depends[HasLogging, None]:
    """
    Create an effect that calls built-in `logging.exception`

    Example:
        >>> class Env:
        ...     logging = Logging()
        >>> exception('hello!').run(Env())
        ERROR:root:hello!

    Args:
        msg: the log message
        stack_info: whether to include stack information in the log message
        exc_info: whether to include exception info in the log message

    Return:
        `Effect` that calls `logging.exception` with `msg`
    """
    return depend().and_then(
        lambda env: env.logging.
        exception(msg, stack_info=stack_info, exc_info=exc_info)
    )
