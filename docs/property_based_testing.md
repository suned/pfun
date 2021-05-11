Pure functional programming lends itself well to [property-based testing](https://hypothesis.works/articles/what-is-property-based-testing/). To make property based testing easy, `pfun` comes with a number of test case generators for the excellent [hypothesis](https://hypothesis.readthedocs.io/en/latest/) library.

For example, if you're testing a function that takes `pfun.list.List` value as an argument, you can use the `pfun.hypothesis_strategies.lists` search strategy:

```python
from hypothesis import given
from hypothesis.strategies import integers

from pfun.hypothesis_strategies import lists
from pfun.list import List


def increment_all(l: List[int]) -> List[int]:
    return l.map(lambda v: v + 1)


@given(lists(integers()))
def test_increment_all(l: List[int]) -> None:
    assert sum(increment_all(l)) == sum(l) + len(l)
```
To see all search strategies that comes with `pfun` check out the [API reference](hypothesis_strategies_api.md).

To use the version of hypothesis that `pfun` is tested against, you can install `pfun` along with `hypothesis` using `pip install pfun[test]`
