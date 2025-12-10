import time
import functools
import asyncio
from typing import Callable, Any


def profiling(func: Callable) -> Callable:
    """
    函数运行时间统计装饰器。
    打印函数名和运行时间（毫秒，保留两位小数）。
    支持同步和异步函数。
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        print(f"[{func.__name__}] 运行时间: {elapsed_ms:.2f} ms")
        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        print(f"[{func.__name__}] 运行时间: {elapsed_ms:.2f} ms")
        return result

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def test():
    """测试 profiling 装饰器"""
    
    @profiling
    def sync_task(n: int) -> int:
        """同步任务：计算 1 到 n 的和"""
        total = sum(range(1, n + 1))
        time.sleep(0.05)  # 模拟耗时操作
        return total

    @profiling
    async def async_task(n: int) -> int:
        """异步任务：计算 1 到 n 的和"""
        total = sum(range(1, n + 1))
        await asyncio.sleep(0.05)  # 模拟耗时操作
        return total

    print("=== 测试同步函数 ===")
    result1 = sync_task(100)
    print(f"结果: {result1}\n")

    print("=== 测试异步函数 ===")
    result2 = asyncio.run(async_task(100))
    print(f"结果: {result2}\n")

    print("=== 测试完成 ===")


if __name__ == "__main__":
    test()
