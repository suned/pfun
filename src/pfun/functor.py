from abc import ABC, abstractmethod
from typing import Any, Callable


class Functor(ABC):
    """
    Abstract base class for functors
    """
    @abstractmethod
    def map(self, f: Callable[[Any], Any]) -> 'Functor':
        """
        Map function ``f`` over the value wrapped by this functor

        :param f: The function to apply to the value wrapped by this Functor
        :return: The result of applying ``f`` to the wrapped value
        """
        pass
