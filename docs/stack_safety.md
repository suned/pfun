Its common to use recursion rather than looping in pure functional programming to avoid mutating a local variable.

Consider e.g the following implementation of the factorial function:

```python
def factorial(n: int) -> int:
    if n == 1:
        return 1
    return n * factorial(n - 1)
```
Called with a large enough value for `n`, the recursive calls will overflow the python stack.

A common solution to this problem in other languages that perform tail-call-optimization is to rewrite the function
to put the recursive call in tail-call position.

```python
def factorial(n: int) -> int:

    def factorial_acc(n: int, acc: int) -> int:
        if n == 1:
            return acc
        return factorial_acc(n - 1, n * acc)

    return factorial_acc(n, 1)
```
In Python however, this is not enough to solve the problem because Python does not perform tail-call-optimization.

Because Python doesn't optimize tail calls, we need to use a data structure called a trampoline
to wrap the recursive calls into objects that can be interpreted in constant stack space, by letting the function
return immediately at each recursive step.

```python
from pfun.trampoline import Trampoline, Done, Call


def factorial(n: int) -> int:

    def factorial_acc(n: int, acc: int) -> Trampoline[int]:
        if n == 1:
            return Done(acc)
        return Call(lambda: factorial_acc(n - 1, n * acc))

    return factorial_acc(n, 1).run()
```
However note that in most cases a recursive function can be rewritten into an iterative one
that looks completely pure to the caller because it only mutates local variables:

```python
def factorial(n: int) -> int:
    acc = 1
    for i in range(1, n + 1):
        acc *= i
    return acc
```
This is the recommended
way of solving recursive problems (when it doesn't break [referential transparency](https://en.wikipedia.org/wiki/Referential_transparency)), because it avoids overflowing the stack, and
is often easier to understand.
