# Django
from django.db import models


class AbstractSettingsModel(models.Model):
    """
    Key/value table for site settings. This model is for storage and retrieval
    only. It is not meant to be exposed to the rest of your application. Use
    a `SettingsStoreBase` subclass for that.
    """
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True
