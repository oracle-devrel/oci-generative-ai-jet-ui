import asyncio
import time
from collections import deque
from typing import Union


class Throttler:
    """
    Context manager for limiting rate of accessing to context block.

    Example usages:
        - https://github.com/uburuntu/throttler/blob/master/examples/example_throttlers.py
        - https://github.com/uburuntu/throttler/blob/master/examples/example_throttlers_aiohttp.py
    """
    __slots__ = ('_rate_limit', '_period', '_times',)

    def __init__(self, rate_limit: int, period: Union[int, float] = 1.0):
        if not (isinstance(rate_limit, int) and rate_limit > 0):
            raise ValueError('`rate_limit` should be positive integer')

        if not (isinstance(period, (int, float)) and period > 0.):
            raise ValueError('`period` should be positive float')

        self._rate_limit = float(rate_limit)
        self._period = float(period)

        self._times = deque(0. for _ in range(rate_limit))

    async def __aenter__(self):
        while True:
            curr_ts = time.monotonic()
            diff = curr_ts - (self._times[0] + self._period)
            if diff > 0.:
                self._times.popleft()
                break
            await asyncio.sleep(-diff)

        self._times.append(curr_ts)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
