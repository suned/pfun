`pfun` provides a mirror version of the `operator` module found in the standard library, with operators that support partial application:

```python
from pfun.operator import mul

double = mul(2)
assert double(4) == 8
```
Moreover, `pfun.operator` provide more accutare typing than its standard library counterpart (if the `pfun` MyPy plugin is enabled).

Note that for some operators, such as `contains`, the argument order is flipped compared to its counterpart in the builtin `operators` module to better support [tacit programming](https://en.wikipedia.org/wiki/Tacit_programming).

To see all available operators, check out the [API reference](operators_api.md).
