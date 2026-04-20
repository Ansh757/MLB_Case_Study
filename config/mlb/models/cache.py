from django.db import models


class ApiCache(models.Model):
    """
    Model used to cache external API responses in SQLite.

    Each row stores:
    - key: unique cache name
    - data: JSON payload returned from the API
    - updated_at: last refresh time
    """
    key = models.CharField(max_length=255, unique=True)
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "API Cache Entry"
        verbose_name_plural = "API Cache Entries"

    def __str__(self):
        return self.key
