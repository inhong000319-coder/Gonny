import os

from redis import Redis


REDIS_URL = os.getenv("REDIS_URL", "")

redis_client = Redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None
