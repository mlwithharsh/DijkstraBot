import asyncio
import time

class RateLimiter:
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.interval = 60.0 / calls_per_minute
        self.tokens = calls_per_minute
        self.max_tokens = calls_per_minute
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self._lock:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                
                # Calculate wait time
                wait_time = (1 - self.tokens) * self.interval
            
            # Sleep outside the lock
            await asyncio.sleep(max(0.1, wait_time))

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        refill_amount = elapsed * (self.calls_per_minute / 60.0)
        if refill_amount > 0:
            self.tokens = min(self.max_tokens, self.tokens + refill_amount)
            self.last_refill = now
