from functools import wraps
from typing import Callable

from throttler import ExecutionTimer, Throttler, ThrottlerSimultaneous, Timer


def throttle(rate_limit: int, period: float = 1.0):
    def decorator(func):
        throttler = Throttler(rate_limit, period)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with throttler:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def throttle_simultaneous(count: int):
    def decorator(func):
        throttler = ThrottlerSimultaneous(count)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with throttler:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def execution_timer(period: float = 60., align_sleep: bool = False):
    def decorator(func):
        et = ExecutionTimer(period, align_sleep)

        @wraps(func)
        def wrapper(*args, **kwargs):
            with et:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def execution_timer_async(period: float = 60., align_sleep: bool = False):
    def decorator(func):
        et = ExecutionTimer(period, align_sleep)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with et:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def timer(name: str = None, verbose: bool = False, print_func: Callable = None):
    def decorator(func):
        t = Timer(name, verbose, print_func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            with t:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def timer_async(name: str = None, verbose: bool = False, print_func: Callable = None):
    def decorator(func):
        t = Timer(name, verbose, print_func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            with t:
                return await func(*args, **kwargs)

        return wrapper

    return decorator
