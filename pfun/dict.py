from typing import Dict as Dict_, TypeVar, Optional

from .maybe import Maybe, Nothing, Just, maybe

K = TypeVar('K')
V = TypeVar('V')


class Dict(Dict_[K, V]):
    """
    Immutable dictionary class with functional helper methods
    """
    def __setitem__(self, key, value):
        raise TypeError("'Dict' object does not support item assignment. "
                        "Use '.set' instead")

    def __delitem__(self, key):
        raise TypeError("'Dict' object does not support item deletion")

    def clear(self):
        raise TypeError("'Dict' object does not support clear method")

    def __repr__(self):
        mapping_repr = ', '.join(
            [f'{repr(key)}: {repr(value)}' for key, value in self.items()]
        )
        return f'{{{mapping_repr}}}'

    def __getitem__(self, key: K) -> Maybe[V]:  # type: ignore
        """
        get the value associated with a key

        :example:
        >>> Dict(key='value')['key']
        Just('value')

        :param key: the key to retrieve
        :return: value associated with key
        """
        return self.get(key)

    def set(self, key: K, value: V) -> 'Dict[K, V]':
        """
        Combine keys and values from this dictionary
        with a new dictionary that includes key and value

        :example:
        >>> Dict().set('key', 'value')
        {'key': 'value'}

        :param key: key to add to the new dictionary
        :param value: value to associate with key
        :return: new dictionary with existing keys and values
                 in addition to key and value
        """
        copy = self.copy()
        copy[key] = value
        return Dict(copy)

    def get(self, key: K) -> Maybe[V]:  # type: ignore
        """
        get the value associated with a key

        :example:
        >>> Dict().get('key', 'default')
        Just('default')
        >>> Dict(key='value').get('key', 'default')
        Just('value')

        :param key: the key to retrieve
        :param default: value to return if the key is not found
        :return: :class:`Just` if key is found in dictionary or default is given,
                 :class:`Nothing` otherwise
        """
        v = super().get(key)  # type: ignore
        if v is None:
            return Nothing()
        return Just(v)

    def update(self, other: 'Dict[K, V]', **kwargs) -> 'Dict[K, V]':
        d = {}
        d.update(self)
        d.update(other)
        d.update(kwargs)
        return Dict(d)


