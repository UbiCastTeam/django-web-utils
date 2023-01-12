import time

from django.conf import settings

from django_web_utils.settings_utils import reload_settings


def test_reload_settings():
    old_value = settings.TIME_NOW
    time.sleep(0.0001)
    # reload_settings() doesn't return a new instance
    reload_settings() is None
    # Global settings have been updated
    assert old_value != settings.TIME_NOW
