'''
Django web utils daemon tests.
'''
import logging
import unittest

from django_web_utils.daemon.base import BaseDaemon

logger = logging.getLogger('djwutils.tests.testapp.tests.test_daemon')


class DaemonTests(unittest.TestCase):

    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))

    def test_daemons_attrs(self):
        self.assertEqual(BaseDaemon.get_name(), 'base')

    def test_daemon_start(self):
        logger.info('////!\\\\\\\\ A traceback will be displayed after this line, this is intended so you can ignore it.')

        class TestDaemon(BaseDaemon):
            NEED_DJANGO = False

            def exit(self, code=0):
                # Override exit function to check expected code
                if code != 140:
                    raise Exception('Unexpected error code (expected 140, got %s).' % code)
                raise RuntimeError('Canceled exit with expected code (%s).' % code)

        # Logging will be displayed twice because of logging init in the daemon class
        daemon = TestDaemon(argv=['notused', 'start', '-n'])
        with self.assertRaises(RuntimeError):
            daemon.start()


if __name__ == '__main__':
    unittest.main()
