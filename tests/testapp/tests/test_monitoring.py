'''
Monitoring app tests.
'''
import json

from django.test import TestCase
from django.urls import reverse

from django_web_utils.monitoring.sysinfo import get_system_info
import django_web_utils


class MonitoringTests(TestCase):
    databases = []

    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    def test_anonymous(self):
        response = self.client.get(reverse('monitoring:monitoring-panel'))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('monitoring:monitoring-check_password'))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('monitoring:monitoring-status'))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('monitoring:monitoring-config', args=['hosts']))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('monitoring:monitoring-log', args=['fake']))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('monitoring:monitoring-command'))
        self.assertEqual(response.status_code, 405)

        response = self.client.post(reverse('monitoring:monitoring-command'))
        self.assertEqual(response.status_code, 302)

    def test_logged(self):
        response = self.client.post(reverse('login'), {'username': 'admin', 'password': 'test'})
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('monitoring:monitoring-panel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

        response = self.client.get(reverse('monitoring:monitoring-check_password'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content, {'pwd_ok': False})

        response = self.client.get(reverse('monitoring:monitoring-status'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        content = json.loads(response.content.decode('utf-8'))
        content['hosts']['log_mtime'] = 'test'
        content['hosts']['log_size'] = 'test'
        self.assertEqual(content, {'hosts': {'running': None, 'need_password': False, 'log_size': 'test', 'log_mtime': 'test'}, 'fake': {'running': False, 'need_password': False, 'log_size': '', 'log_mtime': ''}})

        response = self.client.get(reverse('monitoring:monitoring-status'), {'name': 'fake'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content, {'fake': {'running': False, 'need_password': False, 'log_size': '', 'log_mtime': ''}})

        response = self.client.get(reverse('monitoring:monitoring-config', args=['hosts']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

        response = self.client.get(reverse('monitoring:monitoring-log', args=['fake']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

        response = self.client.get(reverse('monitoring:monitoring-command'))
        self.assertEqual(response.status_code, 405)

        response = self.client.post(reverse('monitoring:monitoring-command'), {})
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('monitoring:monitoring-command'), {'daemon': 'fake', 'cmd': 'clear_log'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content, {'messages': [{'level': 'success', 'name': 'fake', 'out': 'Log file cleared.', 'text': 'Command "clear_log" on "fake" successfully executed.'}]})

    def test_sysinfo(self):
        info = get_system_info(module=django_web_utils)
        self.assertIn('info_sections', info)
        keys = list(info.keys())
        self.assertListEqual(keys[:-1], [
            'info_sections',
            'local_repo',
            'version',
            'revision',
            'info_package',
            'info_os',
            'info_hdd',
            'info_cpu',
            'info_gpu',
            'info_memory',
            'info_network'])
