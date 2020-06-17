from pfun import Immutable, either
from typing import TypeVar, Callable, Generic, Any, NoReturn, Union


R = TypeVar('R', contravariant=True)
E = TypeVar('E', covariant=True)
A = TypeVar('A', covariant=True)
B = TypeVar('B')


class Effect(Immutable, Generic[R, E, A]):
    pass

    def run(self, r: R):
        effect = self
        while not isinstance(self, Done) or isinstance(self, Error):
            effect = effect.next()
        
    def next(self) -> Effect[R, E, A]:
        pass
    
    def __call__(self, r: R) -> either.Either[E, A]:
        pass

class Done(Effect[Any, NoReturn, A]):
    a: A

class Error(Effect[Any, E, NoReturn]):
    reason: E


class Thunk(Generic[R, E, A], Immutable):
    effect: Effect[R, E, A]

    def __call__(self) -> Effect[R, E, A]:
        return self.effect


class Call(Effect[R, E, A]):
    thunk: Thunk[R, E, A]

    def next(self):
        return self.thunk()
    
    def __call__(self, r: R) -> either.Either[E, A]:
        return self.thunk()(r)

class Map(Effect[R, E, A], Generic[R, E, A, B]):
    f: Callable[[B], A]
    effect: Effect[R, E, B]

    def __call__(self, r: R) -> either.Either[E, A]:
        e = self.effect(r)
        if isinstance(e, either.Left):
            return e
        return either.Right(self.f(e.get))
    
    def next(self):
        return Call(Thunk(self))
        


