from abc import ABC, abstractmethod


class FunctorTest(ABC):

    @abstractmethod
    def test_equality(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def test_inequality(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def test_identity_law(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def test_composition_law(self, *args):
        raise NotImplementedError()
