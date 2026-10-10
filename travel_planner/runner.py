import asyncio
import threading

_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


def run_async(coro, timeout: float = 900):
    """Run an async coroutine on one long-lived loop and wait for the result."""
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout)
