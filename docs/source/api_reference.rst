API Reference
====
Maybe
-----
.. autofunction:: pfun.maybe.maybe
.. autoclass:: pfun.maybe.Maybe
    :members:
    :special-members:
    :exclude-members: __repr__,__setattr__,__init__,__weakref__

.. autoclass:: pfun.maybe.Just
    :members: __init__,__eq__

.. autoclass:: pfun.maybe.Nothing
    :members: __init__,__eq__

Either
------
.. autofunction:: pfun.either.either


.. autoclass:: pfun.result.either
    :members:
    :special-members:
    :exclude-members: __init__,__setattr__,__weakref__

.. autoclass:: pfun.result.Right
    :members: __init__,__eq__

.. autoclass:: pfun.result.Left
    :members: __init__,__eq__

Reader
------

.. automodule:: pfun.reader
    :members:
    :special-members:
    :exclude-members: __weakref__,__setattr__

Writer
------

.. automodule:: pfun.writer
    :members:
    :special-members:
    :exclude-members: __weakref__,__setattr__,__repr__


State
-----

.. automodule:: pfun.state
    :members:
    :special-members:
    :exclude-members: __weakref__,__setattr__,__repr__


Cont
----

.. automodule:: pfun.cont
    :members:
    :special-members:
    :exclude-members: __weakref__,__setattr__,__repr__


Immutable
---------

.. autoclass:: pfun.Immutable
    :members:


Dict
----
.. autoclass:: pfun.Dict
    :members:
    :special-members:
    :exclude-members: __weakref__,clear,__setitem__,__delitem__
List
----
.. autoclass:: pfun.List
    :members:
    :special-members:
    :exclude-members: __weakref__,clear,__setitem__,__delitem__


Unit
----
.. class:: pfun.Unit

    Type alias for the empty tuple ``()``. Used to
    represent a computation that doesn't have a result (i.e is purely
    an effect).

curry
-----
.. autofunction:: pfun.curry
.. autofunction:: pfun.curry2
.. autofunction:: pfun.curry3
.. autofunction:: pfun.curry4
.. autofunction:: pfun.curry5
.. autofunction:: pfun.curry6
.. autofunction:: pfun.curry7
.. autofunction:: pfun.curry8
.. autofunction:: pfun.curry9
.. autofunction:: pfun.curry10
.. autofunction:: pfun.curry11
.. autofunction:: pfun.curry12

identity
--------

.. autofunction:: pfun.identity


