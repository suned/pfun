from abc import ABC, abstractmethod
from typing import Callable, Any


class Functor(ABC):
    @abstractmethod
    def map(self, f: Callable[[Any], Any]) -> 'Functor':
        pass
