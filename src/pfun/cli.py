from typing import TypeVar, Type, Union, NoReturn
from typing_extensions import Protocol
from argparse import ArgumentParser, Namespace

from .effect import Effect, Try, Depends, error, success, catch
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


def map_parser(t: Type[T]) -> Try[BadCliSpec, Parser]:
    p = Parser()
    p.add_argument('file')
    p.add_argument('-l', action='store_true')
    return success(p)


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
