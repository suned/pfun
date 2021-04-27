`pfun` provides a mirror version of the `operator` module found in the standard library, with operators that support partial application:

```python
from pfun.operator import mul

double = mul(2)
assert double(4) == 8
```
Moreover, `pfun.operator` provide more accutare typing than its standard library counterpart (if the `pfun` MyPy plugin is enabled).

To see all available operators, check out the [API reference](operators_api.md).
