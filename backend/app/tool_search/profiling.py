# Copyright (C) 2026 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import functools
import asyncio
from typing import Callable, Any


def profiling(func: Callable) -> Callable:
    """
    Function execution time profiling decorator.
    Prints function name and execution time (milliseconds, 2 decimal places).
    Supports both synchronous and asynchronous functions.
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        print(f"[{func.__name__}] execution time: {elapsed_ms:.2f} ms")
        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        print(f"[{func.__name__}] execution time: {elapsed_ms:.2f} ms")
        return result

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def test():
    """Test profiling decorator"""
    
    @profiling
    def sync_task(n: int) -> int:
        """Synchronous task: calculate sum from 1 to n"""
        total = sum(range(1, n + 1))
        time.sleep(0.05)  # Simulate time-consuming operation
        return total

    @profiling
    async def async_task(n: int) -> int:
        """Asynchronous task: calculate sum from 1 to n"""
        total = sum(range(1, n + 1))
        await asyncio.sleep(0.05)  # Simulate time-consuming operation
        return total

    print("=== Test synchronous function ===")
    result1 = sync_task(100)
    print(f"Result: {result1}\n")

    print("=== Test asynchronous function ===")
    result2 = asyncio.run(async_task(100))
    print(f"Result: {result2}\n")

    print("=== Tests complete ===")


if __name__ == "__main__":
    test()
