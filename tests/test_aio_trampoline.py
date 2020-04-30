from hypothesis import given, assume
from pfun.aio_trampoline import Done
from pfun import identity, compose
import pytest

from .strategies import aio_trampolines, unaries, anything
from .monad_test import MonadTest
from .utils import recursion_limit


class TestTrampoline(MonadTest):
    @pytest.mark.asyncio
    @given(aio_trampolines())
    async def test_right_identity_law(self, trampoline):
        assert (await
                trampoline.and_then(Done).run()) == (await trampoline.run())

    @pytest.mark.asyncio
    @given(anything(), unaries(aio_trampolines()))
    async def test_left_identity_law(self, value, f):
        assert (await Done(value).and_then(f).run()) == (await f(value).run())

    @pytest.mark.asyncio
    @given(
        aio_trampolines(),
        unaries(aio_trampolines()),
        unaries(aio_trampolines())
    )
    async def test_associativity_law(self, trampoline, f, g):
        assert (await trampoline.and_then(f).and_then(g).run(
        )) == (await trampoline.and_then(lambda x: f(x).and_then(g)).run())

    @given(anything())
    def test_equality(self, value):
        assert Done(value) == Done(value)

    @given(anything(), anything())
    def test_inequality(self, first, second):
        assume(first != second)
        assert Done(first) != Done(second)

    @pytest.mark.asyncio
    @given(anything())
    async def test_identity_law(self, value):
        assert (await
                Done(value).map(identity).run()) == (await Done(value).run())

    @pytest.mark.asyncio
    @given(unaries(), unaries(), anything())
    async def test_composition_law(self, f, g, value):
        h = compose(f, g)
        assert (await Done(value).map(g).map(f).run()
                ) == (await Done(value).map(h).run())
