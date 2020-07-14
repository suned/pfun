from typing import Type

from typing_extensions import Protocol


class Middleware(Protocol):
    def __init__(self, app):
        pass


def effect_http_middleware(environment) -> Type[Middleware]:
    class EffectHTTPMiddleware(Middleware):
        def __init__(self, app):
            self.app = app
            self.environment = environment

        async def __call__(self, scope, receive, send):
            if scope['type'] != 'http':
                await self.app(scope, receive, send)
                return

            async def send_wrapper(event):
                print(event)
                await send(event)

            await self.app(scope, receive, send_wrapper)

    return EffectHTTPMiddleware
