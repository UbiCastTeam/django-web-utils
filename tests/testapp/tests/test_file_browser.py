'''
File browser app tests.
'''
import json

from django.test import TestCase
from django.urls import reverse


class FileBrowserTests(TestCase):

    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    def test_anonymous(self):
        response = self.client.get(reverse('storage:file_browser_base'))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('storage:file_browser_dirs'))
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('storage:file_browser_content'), {'path': '/'})
        self.assertEqual(response.status_code, 302)

    def test_logged(self):
        from django.contrib.auth.models import User
        user = User(username='fb_admin', is_staff=True)
        user.set_password('test')
        user.save()
        response = self.client.post(reverse('login'), {'username': user.username, 'password': 'test'})
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('storage:file_browser_base'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

        response = self.client.get(reverse('storage:file_browser_dirs'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content, {'dirs': [{'dir_name': 'Root folder', 'sub_dirs': [{'dir_name': 'a dir', 'sub_dirs': []}]}]})

        response = self.client.get(reverse('storage:file_browser_content'), {'path': '/'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        content = json.loads(response.content.decode('utf-8'))
        content['files'][1]['mdate'] = 'test'
        self.assertEqual(content, {'files': [{'name': 'a dir', 'size': 3, 'size_h': '3 B', 'is_dir': True, 'nb_files': 1, 'nb_dirs': 0}, {'name': 'image.png', 'size': 103, 'size_h': '103 B', 'is_dir': False, 'nb_files': 0, 'nb_dirs': 0, 'ext': 'png', 'preview': True, 'mdate': 'test'}], 'path': '/', 'total_size': '106 B', 'total_nb_dirs': 1, 'total_nb_files': 2})

        response = self.client.get(reverse('storage:file_browser_img_preview'), {'path': '/image.png'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png; charset=utf-8')
        self.assertGreater(len(response.content), 0)
