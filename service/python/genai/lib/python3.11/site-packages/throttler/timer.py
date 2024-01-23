from datetime import datetime
from typing import Callable


class Timer:
    """
    Context manager for pretty printing start, end, elapsed and average times.

    Example usage:
        - https://github.com/uburuntu/throttler/blob/master/examples/example_timer.py
    """

    def __init__(self, name: str = None, verbose: bool = False, print_func: Callable = None):
        self.iteration = 1
        self.start_dt = None
        self.elapsed_all = 0.

        self.name = name
        self.verbose = verbose
        self.print = print_func or print

    def __enter__(self):
        self.start_dt = datetime.now()
        if self.verbose:
            self.print(f'{f"#{self.iteration}":>5} | {self.name or "Timer"} | begin: {self.start_dt}')

    def __exit__(self, exc_type, exc_val, exc_tb):
        curr_dt = datetime.now()
        elapsed = (curr_dt - self.start_dt).total_seconds()

        self.elapsed_all += elapsed
        average = self.elapsed_all / self.iteration

        if self.verbose:
            self.print(f'{f"#{self.iteration}":>5} | {self.name or "Timer"} |   end: {curr_dt}, elapsed: {elapsed:.2f} sec, '
                       f'average: {average:.2f} sec\n')
        else:
            self.print(f'{self.name or "Timer"} | elapsed: {elapsed:.2f} sec')

        self.iteration += 1
