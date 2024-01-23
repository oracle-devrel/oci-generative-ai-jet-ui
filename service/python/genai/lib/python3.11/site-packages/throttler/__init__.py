"""Zero-dependency Python package for easy throttling with asyncio support"""
from .execution_timer import ExecutionTimer
from .throttler import Throttler
from .throttler_simultaneous import ThrottlerSimultaneous
from .timer import Timer

from .decorators import execution_timer, execution_timer_async, throttle, throttle_simultaneous, timer, timer_async

__author__ = 'uburuntu'
__email__ = 'github@rmbk.me'

__license__ = 'MIT'
__version__ = '1.2.2'
