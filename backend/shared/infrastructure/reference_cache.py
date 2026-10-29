"""Best-effort JSON cache for non-sensitive reference lists, never command policies."""

import json
import logging
from collections.abc import Callable
from time import monotonic
from uuid import uuid4

from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
_unavailable_until = 0.0


def _available() -> bool:
    return settings.REFERENCE_CACHE_ENABLED and monotonic() >= _unavailable_until


def _failed(error: Exception) -> None:
    global _unavailable_until
    _unavailable_until = monotonic() + 5
    # Do not include endpoints, credentials, cached values or the exception message.
    logger.warning("Reference cache unavailable (%s); using database", type(error).__name__)


def reference_list(resource: str, load: Callable[[], list], *, using: str = "default") -> list:
    if not _available():
        return load()
    cache = caches["reference"]
    generation_key = f"{resource}:generation"
    try:
        generation = cache.get(generation_key)
        if generation is None:
            cache.add(generation_key, uuid4().hex, timeout=None)
            generation = cache.get(generation_key)
        key = f"{resource}:{generation}"
        payload = cache.get(key) if isinstance(generation, str) else None
    except (RedisError, OSError) as error:
        _failed(error)
        return load()
    if not isinstance(generation, str):
        return load()
    if isinstance(payload, str):
        try:
            result = json.loads(payload)
            if isinstance(result, list):
                return result
        except ValueError:
            pass
    # Loader failures propagate. They must never be converted to a cached success.
    result = load()
    payload = json.dumps(result, ensure_ascii=False)

    def store() -> None:
        if not _available():
            return
        try:
            # An invalidation during loading changes the generation, making this fill unreachable.
            cache.set(key, payload, timeout=settings.REFERENCE_CACHE_TTL)
        except (RedisError, OSError) as error:
            _failed(error)

    transaction.on_commit(store, using=using)
    return result


def invalidate_reference(resource: str, *, using: str = "default") -> None:
    if not settings.REFERENCE_CACHE_ENABLED:
        return

    def invalidate() -> None:
        # Attempt invalidation even during the read circuit breaker's cooldown.
        try:
            caches["reference"].set(f"{resource}:generation", uuid4().hex, timeout=None)
        except (RedisError, OSError) as error:
            _failed(error)

    transaction.on_commit(invalidate, using=using)
