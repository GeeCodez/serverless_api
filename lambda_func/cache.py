import os
import redis

CACHE_ENDPOINT = os.environ.get("CACHE_ENDPOINT")
CACHE_PORT = int(os.environ.get("CACHE_PORT", "6379"))

cache = redis.Redis(
    host=CACHE_ENDPOINT,
    port=CACHE_PORT,
    ssl=True,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def get(key):
    try:
        return cache.get(key)
    except Exception:
        return None


def set(key, value, ttl):
    try:
        cache.set(key, value, ex=ttl)
    except Exception:
        pass


def delete(key):
    try:
        cache.delete(key)
    except Exception:
        pass