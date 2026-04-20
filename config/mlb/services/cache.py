from datetime import timedelta

from django.utils import timezone

from mlb.models import ApiCache


def get_cached(key, max_age_minutes):
    """
    Return cached JSON data for a given key if it is still fresh.

    Each cache row stores:
    - key: unique name for the cached payload
    - data: JSON response we want to reuse
    - updated_at: last time this cache entry was written

    If the row does not exist, or if it is older than max_age_minutes,
    return None so the caller knows it should fetch fresh data.
    """
    try:
        row = ApiCache.objects.get(key=key)

        # Only use the cache if it is still within the allowed age window.
        age = timezone.now() - row.updated_at
        if age <= timedelta(minutes=max_age_minutes):
            return row.data

    except ApiCache.DoesNotExist:
        # No cache entry yet for this key.
        pass

    return None


def set_cached(key, data):
    """
    Create or update a cache entry.

    update_or_create lets us handle both cases in one call:
    - if the key already exists, replace its JSON data
    - if the key does not exist, insert a new row

    updated_at is refreshed automatically because the model uses auto_now=True.
    """
    ApiCache.objects.update_or_create(
        key=key,
        defaults={"data": data},
    )
