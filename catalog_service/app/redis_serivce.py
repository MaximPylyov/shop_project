import aioredis

async def get_redis():
    redis = aioredis.from_url("redis://redis:6379", encoding="utf-8", decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()