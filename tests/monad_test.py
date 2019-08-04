from abc import ABC, abstractmethod
from .functor_test import FunctorTest


class MonadTest(FunctorTest, ABC):

    @abstractmethod
    def test_right_identity_law(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def test_left_identity_law(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def test_associativity_law(self, *args):
        raise NotImplementedError()
