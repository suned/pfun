from datetime import datetime
from unittest.mock import Mock

from pfun import clock, effect, random


class MockModules:
    clock: clock.Clock
    random: random.Random

    def __init__(self):
        self.clock = Mock()
        self.clock.sleep.return_value = effect.success(None)
        self.clock.now.return_value = effect.success(datetime.fromtimestamp(0))

        self.random = Mock()
        self.random.random.return_value = effect.success(0.0)
        self.random.randint.return_value = effect.success(0)
