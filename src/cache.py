import os
import json
import time
from functools import wraps
import hashlib

CACHE_DIR = "output/cache"

def _get_cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe_key = hashlib.md5(key.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{safe_key}.json")

def cached(ttl_seconds: int = 3600):
    """
    Decorator to cache the output of a function to disk.
    Requires arguments to be stringifiable.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a deterministic key from function name and arguments
            key_data = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            key = json.dumps(key_data, sort_keys=True, default=str)
            cache_path = _get_cache_path(key)

            # Check if valid cache exists
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                    if time.time() - cached_data["timestamp"] < ttl_seconds:
                        print(f"[CACHE] Cache hit for {func.__name__}!")
                        return cached_data["result"]
                except Exception as e:
                    print(f"[CACHE] Error reading cache for {func.__name__}: {e}")

            # Run the function
            result = func(*args, **kwargs)

            # Do not cache empty or failed results
            if not result:
                return result

            # Save to cache
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "timestamp": time.time(),
                        "result": result
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[CACHE] Error saving cache for {func.__name__}: {e}")

            return result
        return wrapper
    return decorator
