import time
import json
import hashlib
from functools import wraps
import asyncio

_CACHE = {}

def get_cache_key(func_name, *args, **kwargs):
    key_dict = {"func": func_name, "args": args, "kwargs": kwargs}
    key_str = json.dumps(key_dict, default=str, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

def apply_cache_annotation(res):
    if isinstance(res, dict):
        res = res.copy()
        if "source" in res:
            if isinstance(res["source"], str):
                if " (cached)" not in res["source"]:
                    res["source"] += " (cached)"
            elif isinstance(res["source"], dict):
                res["source"] = res["source"].copy()
                for k, v in res["source"].items():
                    if isinstance(v, str) and " (cached)" not in v:
                        res["source"][k] = v + " (cached)"
    return res

def with_cache(ttl: int = 300):
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = get_cache_key(func.__name__, *args, **kwargs)
                now = time.time()
                if key in _CACHE and now - _CACHE[key]['time'] < ttl:
                    return apply_cache_annotation(_CACHE[key]['data'])
                
                res = await func(*args, **kwargs)
                _CACHE[key] = {'time': now, 'data': res}
                return res
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = get_cache_key(func.__name__, *args, **kwargs)
                now = time.time()
                if key in _CACHE and now - _CACHE[key]['time'] < ttl:
                    return apply_cache_annotation(_CACHE[key]['data'])
                
                res = func(*args, **kwargs)
                _CACHE[key] = {'time': now, 'data': res}
                return res
            return sync_wrapper
    return decorator
