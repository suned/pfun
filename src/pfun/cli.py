import inspect
from typing import Type, Union, NoReturn
from typing_extensions import Protocol, get_type_hints
from argparse import ArgumentParser, Action, ArgumentTypeError

import os
from enum import Enum
from typing import Any, List, Tuple, TypeVar

import docstring_parser
import stringcase

from .effect import Effect, Try, error, success, catch
from .functions import curry
from .console import HasConsole, Console, print_line
from .files import HasFiles, Files
import sys


T = TypeVar('T')


class ParseError(Exception):
    def __init__(self, message: str):
        self.message = message


class BadCliSpec(ValueError):
    pass


class HasFilesAndConsole(Protocol):
    console: Console
    files: Files


class Parser(ArgumentParser):
    def exit(self, status, message):
        if status != 0:
            raise ParseError(message)
    
    def print_help(self, file):
        pass

    def print_usage(self, file):
        pass


class _EnumValueGetter:
    def __init__(self, t):
        self.t = t

    def __repr__(self):
        return '{' + ','.join([m.name for m in self.t]) + '}'

    def __call__(self, v):
        try:
            return self.t[v]
        except KeyError:
            choices = '{' + ','.join([m.name for m in self.t]) + '}'
            raise ArgumentTypeError('"%s" is not a valid choice, must be one of %s' % (v, choices))


class _EnumWrapper:
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return other == self.v

    def hash(self):
        return hash(self.v)

    def __str__(self):
        return self.v.name


class _TupleConverter:
    def __init__(self, types):
        self.types = types
        self.type_count = 0

    def __call__(self, v):
        try:
            t = self.types[self.type_count](v)
            self.type_count += 1
            return t
        except IndexError:
            raise ArgumentTypeError('number of arguments (%i) is too many, %i are required' % (self.type_count + 1, len(self.types)))


class _TupleAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, tuple(values))


def _is_type(t1, t2):
    try:
        return t1.__base__ == t2[Any].__base__
    except AttributeError:
        return False


def _is_enum(t):
    try:
        return issubclass(t, Enum)
    except TypeError:
        return False


def _is_builtin_type(t, type_):
    try:
        return issubclass(t, type_)
    except TypeError:
        return False


def map_parser(t: Type[T]) -> Try[BadCliSpec, Parser]:
    try:
        annotations = get_type_hints(t)
        annotations.pop('return', None)
        docs = docstring_parser.parse(t.__doc__)

        description = (docs.long_description
                       if docs.long_description
                       else docs.short_description)
        __main__ = inspect.getmodule(t)
        main_name, _ = os.path.splitext(os.path.basename(__main__.__file__))
        parser = Parser(prog=main_name, description=description)
        signature = inspect.signature(t)

        defaults = {
            k: v.default for k, v in signature.parameters.items()
            if v.default is not inspect.Parameter.empty
        }

        other = [name for name, v in signature.parameters.items()
                 if v.default is inspect.Parameter.empty]

        doc_params = {p.arg_name: p for p in docs.params}

        # args that are not annotated and have no default
        for name in other:
            if name in annotations:
                continue
            if name in doc_params:
                arg_help = doc_params[name].description
            else:
                arg_help = None
            parser.add_argument(name, help=arg_help)

        # add annotated items parameters first
        for name, t in annotations.items():
            if name in doc_params:
                arg_help = doc_params[name].description
            else:
                arg_help = None

            if name in defaults:
                formatted_name = _format_name(name)
                default = defaults[name]
            else:
                formatted_name = name
                default = None

            if _is_type(t, List):
                if t.__args__ and not isinstance(t.__args__[0], TypeVar):
                    t = annotations[name].__args__[0]
                    if issubclass(t, Enum):
                        choices = [_EnumWrapper(m) for m in t]
                        t = _EnumValueGetter(t)
                    else:
                        choices = None
                else:
                    t = None
                    choices = None
                parser.add_argument(
                    formatted_name,
                    default=default,
                    type=t,
                    nargs='+',
                    help=arg_help,
                    choices=choices
                )
            elif _is_type(t, Tuple):
                choices = None
                if t.__args__ and not isinstance(t.__args__[0], TypeVar):
                    ts = t.__args__
                    if ts[-1] is ...:
                        nargs = '+'
                        t = ts[-2]
                        if _is_enum(t):
                            choices = [_EnumWrapper(m) for m in t]
                            t = _EnumValueGetter(t)

                    else:
                        if _is_enum(ts[0]) and all(issubclass(t_, ts[0]) for t_ in ts):
                            choices = [_EnumWrapper(m) for m in ts[0]]
                        ts = [t_ if not _is_enum(t_) else _EnumValueGetter(t_) for t_ in ts]
                        t = _TupleConverter(ts)
                        nargs = len(ts)
                else:
                    t = None
                    nargs = '+'
                parser.add_argument(
                    formatted_name,
                    default=default,
                    type=t,
                    nargs=nargs,
                    choices=choices,
                    help=arg_help,
                    action=_TupleAction
                )
            elif _is_builtin_type(t, list):
                parser.add_argument(
                    formatted_name,
                    default=default,
                    nargs='+',
                    help=arg_help,
                )
            elif _is_builtin_type(t, tuple):
                parser.add_argument(
                    formatted_name,
                    default=default,
                    nargs='+',
                    help=arg_help,
                    action=_TupleAction
                )
            elif _is_enum(t):
                parser.add_argument(
                    formatted_name,
                    type=_EnumValueGetter(t),
                    default=default,
                    help=arg_help,
                    choices=[_EnumWrapper(m) for m in t]
                )
            else:
                parser.add_argument(formatted_name, type=t, default=default, help=arg_help)

        # add defaults
        for name, value in defaults.items():
            if name in annotations:
                # skip if arg was already added
                continue

            if name in doc_params:
                arg_help = doc_params[name].description
            else:
                arg_help = None
            formatted_name = _format_name(name)
            if isinstance(value, bool):
                parser.add_argument(
                    formatted_name,
                    action='store_true' if not value else 'store_false',
                    help=arg_help
                )
            elif isinstance(value, list):
                if value:
                    v = value[0]
                    if isinstance(v, Enum):
                        t = _EnumValueGetter(type(v))
                        choices = [_EnumWrapper(m) for m in type(v)]
                    else:
                        t = type(v)
                        choices = None
                else:
                    t = None
                    choices = None
                parser.add_argument(
                    formatted_name,
                    default=value,
                    type=t,
                    nargs='+',
                    help=arg_help,
                    choices=choices
                )
            elif isinstance(value, tuple):
                nargs = '+'
                choices = None
                if value:
                    vt = type(value[0])
                    if all(type(v) == vt for v in value):
                        if issubclass(vt, Enum):
                            t = _EnumValueGetter(vt)
                            choices = [_EnumWrapper(m) for m in vt]
                        else:
                            t = vt
                    else:
                        t = _TupleConverter([type(v)
                                            if not isinstance(v, Enum)
                                            else _EnumValueGetter(type(v))
                                             for v in value])
                        nargs = len(value)
                else:
                    t = None
                    choices = None
                parser.add_argument(
                    formatted_name,
                    default=value,
                    type=t,
                    nargs=nargs,
                    help=arg_help,
                    choices=choices,
                    action=_TupleAction
                )
            elif isinstance(value, Enum):
                t = type(value)
                parser.add_argument(
                    formatted_name,
                    type=_EnumValueGetter(t),
                    default=value,
                    help=arg_help,
                    choices=[_EnumWrapper(m) for m in t]
                )
            else:
                parser.add_argument(formatted_name, type=type(value), default=value, help=arg_help)

        return success(parser)
    except Exception as e:
        return error(BadCliSpec(*e.args))


def _format_name(name):
    return '--%s' % stringcase.spinalcase(name.lower())


@curry
def try_parse_as(t: Type[T], p: ArgumentParser) -> Effect[HasConsole, SystemExit, T]:
    def print_help(e: ParseError) -> Effect[HasConsole, SystemExit, NoReturn]:
        return print_line(
            p.format_help()
        ).discard_and_then(
            print_line(e.message)
        ).discard_and_then(
            error(SystemExit(2))
        )

    return catch(ParseError)(p.parse_args)().map(
        lambda args: t(**vars(args))  # type: ignore
    ).recover(print_help)


def parse_args(t: Type[T]) -> Effect[HasFilesAndConsole, Union[BadCliSpec, SystemExit], T]:
    return map_parser(t).and_then(try_parse_as(t))
