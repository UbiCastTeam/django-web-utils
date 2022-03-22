"""
Time utils tests.
"""
from django.test import TestCase

from django_web_utils.time_utils import get_hms_tuple, get_hms_str


class TimeUtilsTests(TestCase):
    databases = []

    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    def test_get_hms_tuple(self):
        self.assertRaises(ValueError, lambda: get_hms_tuple(-1))
        self.assertEqual(get_hms_tuple(0), (0, 0, 0))
        self.assertEqual(get_hms_tuple(50), (0, 0, 50))
        self.assertEqual(get_hms_tuple(130), (0, 2, 10))
        self.assertEqual(get_hms_tuple(4250), (1, 10, 50))

    def test_get_hms_str(self):
        self.assertEqual(get_hms_str(0), '0s')
        self.assertEqual(get_hms_str(40), '40s')
        self.assertEqual(get_hms_str(150), '2m 30s')
        self.assertEqual(get_hms_str(3670), '1h 1m 10s')
