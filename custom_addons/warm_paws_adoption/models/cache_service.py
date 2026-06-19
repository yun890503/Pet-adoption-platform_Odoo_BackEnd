import json
import logging
import os

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import redis
except ImportError:  # pragma: no cover - handled gracefully when dependency is unavailable.
    redis = None


class WarmPawsCacheService(models.AbstractModel):
    _name = "warm.paws.cache"
    _description = "Warm Paws Redis Cache"

    def _enabled(self):
        return bool(redis and (os.environ.get("REDIS_URL") or os.environ.get("REDIS_HOST")))

    def _client(self):
        if not self._enabled():
            return None
        try:
            redis_url = os.environ.get("REDIS_URL")
            if redis_url:
                return redis.Redis.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2, decode_responses=True)
            return redis.Redis(
                host=os.environ.get("REDIS_HOST", "localhost"),
                port=int(os.environ.get("REDIS_PORT", "6379")),
                password=os.environ.get("REDIS_PASSWORD") or None,
                db=int(os.environ.get("REDIS_DB", "0")),
                socket_timeout=2,
                socket_connect_timeout=2,
                decode_responses=True,
            )
        except Exception as error:
            _logger.info("Redis cache unavailable: %s", error)
            return None

    def get_json(self, key):
        client = self._client()
        if not client:
            return None
        try:
            value = client.get(key)
            return json.loads(value) if value else None
        except Exception as error:
            _logger.info("Redis cache get failed for %s: %s", key, error)
            return None

    def set_json(self, key, value, ttl=None):
        client = self._client()
        if not client:
            return False
        try:
            seconds = int(ttl or os.environ.get("WARM_PAWS_CACHE_TTL", "300"))
            client.setex(key, seconds, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as error:
            _logger.info("Redis cache set failed for %s: %s", key, error)
            return False

    def clear_pattern(self, pattern):
        client = self._client()
        if not client:
            return False
        try:
            keys = list(client.scan_iter(match=pattern, count=100))
            if keys:
                client.delete(*keys)
            return True
        except Exception as error:
            _logger.info("Redis cache clear failed for %s: %s", pattern, error)
            return False

    def clear_animals(self):
        return self.clear_pattern("warm_paws:animals:*")
