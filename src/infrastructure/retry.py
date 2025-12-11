import asyncio
from typing import TypeVar, Callable, Any
from functools import wraps
import random

T = TypeVar('T')

class RetryException(Exception):
    """Exception raised when all retry attempts are exhausted."""
    pass


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Don't retry on certain errors (like authentication errors)
                    error_message = str(e).lower()
                    if any(x in error_message for x in ['unauthorized', 'forbidden', 'bad credentials']):
                        print(f"❌ Authentication error, not retrying: {e}")
                        raise
                    
                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                        
                        # Add jitter (randomness) to prevent all clients retrying at once
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        
                        print(f"⚠️  Attempt {attempt + 1}/{max_attempts} failed: {e}")
                        print(f"   Retrying in {delay:.2f} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        print(f"❌ All {max_attempts} attempts failed")
            
            raise RetryException(f"Failed after {max_attempts} attempts. Last error: {last_exception}")
        
        return wrapper
    return decorator