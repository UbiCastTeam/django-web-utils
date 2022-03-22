"""
Settings utils tests.
"""
import time

from django.conf import settings
from django.test import TestCase

from django_web_utils.settings_utils import reload_settings


class SettingsUtilsTests(TestCase):
    databases = []

    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    def test_reload_settings(self):
        old_value = settings.TIME_NOW
        time.sleep(0.0001)
        # reload_settings() doesn't return a new instance
        self.assertIsNone(reload_settings())
        # Global settings have been updated
        self.assertNotEqual(old_value, settings.TIME_NOW)
