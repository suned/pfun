from string import printable
from typing import Any, Callable, Iterable, NoReturn, Tuple, TypeVar, Union

from . import Dict, List, aio_trampoline, effect, either, maybe, trampoline

try:
    from hypothesis.strategies import (
        booleans,
        builds,
        composite,
        dictionaries,
        floats,
        integers,
        just,
        lists as lists_,
        one_of,
        recursive,
        text,
        SearchStrategy
    )
except ImportError:
    raise ImportError(
        'Could not import hypothesis. To use pfun.hypothesis_strategies, '
        'install pfun with \n\n\tpip install pfun[test]'
    )

A = TypeVar('A')


def _everything(allow_nan: bool = False) -> Tuple[SearchStrategy[int],
                                                  SearchStrategy[bool],
                                                  SearchStrategy[str],
                                                  SearchStrategy[float]]:
    return integers(), booleans(), text(), floats(allow_nan=allow_nan)


def anything(allow_nan: bool = False
             ) -> SearchStrategy[Union[int, bool, str, float]]:
    """
    Create a search strategy that produces one of int, bool, str or floats.

    Args:
        Allow_nan: whether to allow nan values
    Return:
        Search strategy that produces ints, bools, str or floats
    """
    return one_of(*_everything(allow_nan))


def unaries(return_strategy: SearchStrategy[A]
            ) -> SearchStrategy[Callable[[object], A]]:
    """
    Create a search strategy that produces functions of 1 argument

    Example:
        >>> f = unaries(integers()).example()
        >>> f
        <function ...>
        >>> f(None)
        2
    Args:
        return_strategy: strategy used to draw return values
    Return:
        Search strategy that produces callables of 1 argument
    """
    @composite
    def _(draw):
        a: A = draw(return_strategy)
        return lambda _: a

    return _()


def maybes(value_strategy: SearchStrategy[A]
           ) -> SearchStrategy[maybe.Maybe[A]]:
    """
    Create a search strategy that produces `pfun.maybe.Maybe` values

    Example:
        >>> maybes(integers()).example()
        Just(1)
    Args:
        value_strategy: search strategy to draw values from
    Return:
        search strategy that produces `pfun.maybe.Maybe` values
    """
    justs = builds(maybe.Just, value_strategy)
    nothings = just(maybe.Nothing())
    return one_of(justs, nothings)


def rights(value_strategy: SearchStrategy[A]
           ) -> SearchStrategy[either.Right[A]]:
    """
    Create a search strategy that produces `pfun.either.Right` values

    Args:
        value_strategy: search strategy to draw values from
    Example:
        >>> rights(integers()).example()
        Right(0)
    Return:
        search strategy that produces `pfun.either.Right` values
    """
    return builds(either.Right, value_strategy)


def lefts(value_strategy: SearchStrategy[A]) -> SearchStrategy[either.Left[A]]:
    """
    Create a search strategy that produces `pfun.either.Left` values

    Args:
        value_strategy: search strategy to draw values from
    Example:
        >>> lefts(integers()).example()
        Left(0)
    Return:
        search strategy that produces `pfun.either.Left` values
    """
    return builds(either.Left, value_strategy)


def eithers(value_strategy: SearchStrategy[A]
            ) -> SearchStrategy[either.Either[A, A]]:
    """
    Create a search strategy that produces `pfun.either.Either` values

    Args:
        value_strategy: search strategy to draw values from
    Example:
        >>> s = eithers(integers())
        >>> s.example()
        Right(0)
        >>> s.example()
        Left(0)
    Return:
        search strategy that produces `pfun.either.Either` values
    """
    return one_of(lefts(value_strategy), rights(value_strategy))


def nullaries(return_strategy: SearchStrategy[A]
              ) -> SearchStrategy[Callable[[], A]]:
    """
    Create a search strategy that produces functions of 0 arguments

    Args:
        return_strategy: strategy used to draw return values
    Example:
        >>> f = unaries(integers()).example()
        >>> f
        <function ...>
        >>> f()
        2
    Return:
        Search strategy that produces callables of 0 arguments
    """
    def f(v):
        return lambda: v

    return builds(f, return_strategy)


def trampolines(value_strategy: SearchStrategy[A]
                ) -> SearchStrategy[trampoline.Trampoline[A]]:
    """
    Create a strategy that produces `pfun.trampoline.Trampoline` instances

    Args:
        value_strategy: strategy used to draw result values
    Example:
        >>> trampolines(integers()).example()
        Call(thunk=<function ... at 0x1083d2d40>)
    Return:
        search strategy that produces `pfun.trampoline.Trampoline` instances
    """
    dones = builds(trampoline.Done, value_strategy)

    @composite
    def call(draw):
        t = draw(trampolines(value_strategy))
        return trampoline.Call(lambda: t)

    @composite
    def and_then(draw):
        t = draw(trampolines(value_strategy))
        cont = lambda _: t
        return trampoline.AndThen(draw(trampolines(value_strategy)), cont)

    return one_of(dones, call(), and_then())


def aio_trampolines(value_strategy: SearchStrategy[A]
                    ) -> SearchStrategy[trampoline.Trampoline[A]]:
    """
    Create a strategy that produces `pfun.aio_trampoline.Trampoline` instances

    Args:
        value_strategy: strategy used to draw result values
    Example:
        >>> aio_trampolines(integers()).example()
        Call(thunk=<function ... at 0x1083d2d40>)
    Return:
        search strategy that produces \
            `pfun.aio_trampoline.Trampoline` instances
    """
    dones = builds(aio_trampoline.Done, value_strategy)

    @composite
    def call(draw):
        t = draw(aio_trampolines(value_strategy))

        async def f():
            return t

        return aio_trampoline.Call(f)

    @composite
    def and_then(draw):
        t = draw(aio_trampolines(value_strategy))
        cont = lambda _: t
        return aio_trampoline.AndThen(
            draw(aio_trampolines(value_strategy)), cont
        )

    return one_of(dones, call(), and_then())


def lists(elements: SearchStrategy[A], min_size=0):
    """
    Create a search strategy that produces `pfun.list.List` instances

    Args:
        elements: strategy used to draw elements of the list
        min_size: minimum size of the lists
    Example:
        >>> lists(integers()).example()
        List((0,))
    Return:
        search strategy that produces `pfun.list.List` instances
    """
    return builds(List, lists_(elements, min_size=min_size))


B = TypeVar('B')


def dicts(
    keys: SearchStrategy[A],
    values: SearchStrategy[B],
    min_size: int = 0,
    max_size: int = None
) -> SearchStrategy[Dict[A, B]]:
    """
    Create a search strategy that produces `pfun.dict.Dict` instances

    Args:
        keys: search strategy used to draw keys for the Dict instances
        values: search strategy used to draw values for the Dict instances
        min_size: minimum size of the Dicts
        max_size: max size of the Dicts
    Example:
        >>> dicts(text(), integers()).example()
        Dict({'0': 0})
    Return:
        search strategy that produces `pfun.dict.Dict` instances
    """
    return builds(
        Dict, dictionaries(keys, values, min_size=min_size, max_size=max_size)
    )


TestEffect = effect.Effect[object, Any, A]


def effects(
    value_strategy: SearchStrategy[A],
    include_errors: bool = False,
    max_size: int = 10,
    max_leaves: int = 10
) -> SearchStrategy[TestEffect[A]]:
    """
    Create a search strategy that produces `pfun.effect.Effect` instances

    Args:
        value_strategy: search strategy used to draw success values
        include_errors: whether to include effects that fail
        max_size: max size of effects that produces iterables \
            (such as `pfun.effect.sequence`)
        max_leaves: max number of leaf effects \
            (`pfun.effect.success`, `pfun.effect.from_callable` etc) \
            to be drawn
    Example:
        >>> e = effects(integers()).example()
        >>> e
        success(0)
        >>> e.run(None)
        0
    Return:
        search strategy that produces `pfun.effect.Effect` instances
    """
    def extend(children: SearchStrategy[TestEffect[A]]
               ) -> SearchStrategy[TestEffect[A]]:
        maps: SearchStrategy[TestEffect[A]] = children.flatmap(
            lambda e: unaries(value_strategy).map(lambda f: e.map(f))
        )
        and_then = children.flatmap(
            lambda e: unaries(children).map(lambda f: e.and_then(f))
        )
        discard_and_then = children.flatmap(
            lambda e: children.map(lambda e2: e.discard_and_then(e2))
        )
        either = children.map(lambda e: e.either())
        recover = children.flatmap(
            lambda e: children.map(lambda e2: e.recover(lambda _: e2))
        )
        memoize = children.map(lambda e: e.memoize())
        ensure = children.flatmap(
            lambda e: children.map(lambda e2: e.ensure(e2))
        )
        with_repr = children.flatmap(
            lambda e: text(printable).map(lambda s: e.with_repr(s))
        )
        sequence: SearchStrategy[TestEffect[Iterable[A]]
                                 ] = lists_(children,
                                            max_size=10).map(effect.sequence)
        sequence_async: SearchStrategy[TestEffect[Iterable[A]]] = lists_(
            children,
            max_size=max_size
        ).map(
            effect.sequence_async
        )
        lift = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.lift(f)(e))
        )
        lift_io_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.lift_io_bound(f)(e))
        )
        lift_cpu_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.lift_cpu_bound(f)(e))
        )
        combine = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.combine(e)(f))
        )
        combine_io_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.combine_io_bound(e)(f))
        )
        combine_cpu_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.combine_cpu_bound(e)(f))
        )

        return one_of(
            maps,
            and_then,
            discard_and_then,
            either,
            recover,
            memoize,
            ensure,
            with_repr,
            sequence,
            sequence_async,
            lift,
            lift_io_bound,
            lift_cpu_bound,
            combine,
            combine_io_bound,
            combine_cpu_bound
        )

    success = builds(effect.success, value_strategy)
    depends: SearchStrategy[effect.Effect[Any, NoReturn, Any]
                            ] = builds(effect.depend)
    from_callable: SearchStrategy[TestEffect[A]
                                  ] = unaries(rights(value_strategy)
                                              ).map(effect.from_callable)
    from_io_bound_callable: SearchStrategy[TestEffect[A]] = unaries(
        rights(value_strategy)
    ).map(effect.from_io_bound_callable)
    from_cpu_bound_callable: SearchStrategy[TestEffect[A]] = unaries(
        rights(value_strategy)
    ).map(effect.from_cpu_bound_callable)
    catch: SearchStrategy[TestEffect[A]] = unaries(value_strategy).flatmap(
        lambda f: value_strategy.map(lambda a: effect.catch(Exception)(f)(a))
    )
    catch_io_bound: SearchStrategy[TestEffect[A]] = unaries(
        value_strategy
    ).flatmap(
        lambda f: value_strategy.map(
            lambda a: effect.catch_io_bound(Exception)(f)(a)
        )
    )
    catch_cpu_bound: SearchStrategy[TestEffect[A]] = unaries(
        value_strategy
    ).flatmap(
        lambda f: value_strategy.map(
            lambda a: effect.catch_cpu_bound(Exception)(f)(a)
        )
    )

    base = (
        success
        | from_callable
        | from_io_bound_callable
        | from_cpu_bound_callable
        | depends
        | catch
        | catch_io_bound
        | catch_cpu_bound
    )

    if include_errors:
        errors = builds(effect.error, value_strategy)
        base = base | errors

    return recursive(base, extend, max_leaves=10)
