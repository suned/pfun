from abc import ABC, abstractmethod


class MonoidTest(ABC):
    @abstractmethod
    def test_left_append_identity_law(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def test_right_append_identity_law(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def test_append_associativity_law(self, *args):
        raise NotImplementedError()
