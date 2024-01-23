import asyncio


class ThrottlerSimultaneous:
    """
    Context manager for limiting simultaneous count of accessing to context block.

    Should be created inside of async loop.

    Example usages:
        - https://github.com/uburuntu/throttler/blob/master/examples/example_throttlers.py
        - https://github.com/uburuntu/throttler/blob/master/examples/example_throttlers_aiohttp.py
    """

    __slots__ = ('_semaphore',)

    def __init__(self, count: int):
        self._semaphore = asyncio.Semaphore(count)

    async def __aenter__(self):
        await self._semaphore.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._semaphore.release()
