import asyncio
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

@dataclass
class RateLimit:
    """Represents GitHub API rate limit information."""
    limit: int          # Total points available
    remaining: int      # Points remaining
    reset_at: datetime  # When the limit resets
    cost: int = 1       # Cost of the last query
    
    @property
    def is_exhausted(self) -> bool:
        """Check if rate limit is exhausted."""
        return self.remaining < 100  # Keep a buffer
    
    @property
    def seconds_until_reset(self) -> float:
        """Calculate seconds until rate limit resets."""
        delta = self.reset_at - datetime.now()
        return max(0, delta.total_seconds())


class RateLimiter:
    """
    Manages GitHub API rate limiting.
    Ensures we don't hit rate limits and handles waiting when necessary.
    """
    
    def __init__(self):
        self.current_limit: Optional[RateLimit] = None
        self._lock = asyncio.Lock()
    
    def update(self, rate_limit_data: dict) -> None:
        """
        Update rate limit information from GitHub API response.
        
        Args:
            rate_limit_data: Dict containing 'limit', 'remaining', 'resetAt', 'cost'
        """
        self.current_limit = RateLimit(
            limit=rate_limit_data['limit'],
            remaining=rate_limit_data['remaining'],
            reset_at=datetime.fromisoformat(rate_limit_data['resetAt'].replace('Z', '+00:00')),
            cost=rate_limit_data.get('cost', 1)
        )
    
    async def wait_if_needed(self) -> None:
        """
        Wait if rate limit is exhausted.
        This prevents us from hitting the rate limit.
        """
        async with self._lock:
            if self.current_limit and self.current_limit.is_exhausted:
                wait_time = self.current_limit.seconds_until_reset
                if wait_time > 0:
                    print(f"⏳ Rate limit low ({self.current_limit.remaining} remaining). "
                          f"Waiting {wait_time:.0f} seconds until reset...")
                    await asyncio.sleep(wait_time + 5)  # Add 5 second buffer
                    print("✅ Rate limit reset. Continuing...")
    
    def get_status(self) -> str:
        """Get current rate limit status as a string."""
        if not self.current_limit:
            return "Rate limit: Unknown"
        
        return (f"Rate limit: {self.current_limit.remaining}/{self.current_limit.limit} "
                f"(resets in {self.current_limit.seconds_until_reset:.0f}s)")