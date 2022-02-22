'''
Antivirus utils tests.
'''
from io import BytesIO
from os import chmod
from pathlib import Path

from django.conf import settings
from django.core import mail as dj_mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, TestCase
from django.urls import reverse

from django_web_utils import antivirus_utils as avu


EICAR_TEST_CONTENT = 'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

DEFAULT_MIDDLEWARES = settings.MIDDLEWARE


class AntivirusUtilsConfigTests(TestCase):
    databases = []

    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    def test_socket_path(self):
        sp = avu.get_antivirus_socket_path()
        self.assertTrue(Path(sp).exists())

    def test_is_enabled(self):
        enabled = getattr(settings, 'ANTIVIRUS_ENABLED', None)
        self.assertIsNone(enabled)
        enabled = avu.is_antivirus_enabled()
        self.assertTrue(enabled)


@override_settings(ANTIVIRUS_ENABLED=True)
class AntivirusUtilsScanTests(TestCase):
    databases = []

    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()
        self.test_path = Path('/tmp/djwutils-antivirus-test.txt')

    def tearDown(self):
        super().tearDown()
        if self.test_path.exists():
            self.test_path.unlink()

    def test_clean_file(self):
        with open(self.test_path, 'w') as fo:
            fo.write('Test content')
        # Should not raise any error
        avu.antivirus_path_validator(self.test_path)

    def test_infected_file(self):
        with open(self.test_path, 'w') as fo:
            # Write eicar test content
            fo.write(EICAR_TEST_CONTENT)
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(avu.INFECTED_MESSAGE)):
            avu.antivirus_path_validator(self.test_path)

    def test_non_existent_path(self):
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(avu.DOES_NOT_EXIST_MESSAGE)):
            avu.antivirus_path_validator('/doesnotexist')

    def test_non_existent_file(self):
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(avu.INVALID_FILE_MESSAGE)):
            avu.antivirus_file_validator('/doesnotexist')

    def test_restricted_file_denied(self):
        with open(self.test_path, 'w') as fo:
            # Write eicar test content
            fo.write('Test content')
        chmod(self.test_path, 0o400)
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(avu.SCAN_FAILED_MESSAGE)):
            avu.antivirus_path_validator(self.test_path)

    def test_restricted_file_ok(self):
        with open(self.test_path, 'w') as fo:
            # Write eicar test content
            fo.write('Test content')
        chmod(self.test_path, 0o400)
        # Should not raise any error
        avu.antivirus_file_validator(self.test_path)

    def test_clean_uploaded_file(self):
        upload_file = SimpleUploadedFile('test-clean.txt', b'Test content')
        upload_file.path = '/doesnotexist'
        # Should not raise any error
        avu.antivirus_stream_validator(upload_file)

    def test_infected_uploaded_file(self):
        upload_file = SimpleUploadedFile('test-eicar.txt', EICAR_TEST_CONTENT.encode('utf-8'))
        upload_file.path = '/doesnotexist'
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(avu.INFECTED_MESSAGE)):
            avu.antivirus_stream_validator(upload_file)

    @override_settings(MIDDLEWARE=DEFAULT_MIDDLEWARES + (
        'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware',
    ))
    def test_form_get_request(self):
        response = self.client.get(reverse('testapp:upload'))
        self.assertEqual(response.status_code, 200)

    @override_settings(MIDDLEWARE=DEFAULT_MIDDLEWARES + (
        'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware',
    ))
    def test_form_post_request(self):
        file = BytesIO(EICAR_TEST_CONTENT.encode('utf-8'))
        response = self.client.post(reverse('testapp:upload'), data={'file': file})
        self.assertEqual(response.status_code, 451)

        mailinbox = [m.to[0] for m in dj_mail.outbox]
        expected = [settings.ADMINS[0][1]]
        self.assertListEqual(mailinbox, expected)

    @override_settings(MIDDLEWARE=DEFAULT_MIDDLEWARES + (
        'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware',
        'django_web_utils.json_utils.JsonErrorResponseMiddleware',
    ))
    def test_form_post_request_json(self):
        file = BytesIO(EICAR_TEST_CONTENT.encode('utf-8'))
        response = self.client.post(reverse('testapp:upload-json'), data={'file': file})
        self.assertEqual(response.status_code, 451)

        mailinbox = [m.to[0] for m in dj_mail.outbox]
        expected = [settings.ADMINS[0][1]]
        self.assertListEqual(mailinbox, expected)
