'''
Antivirus utils tests.
'''
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, TestCase
from django.urls import reverse

from django_web_utils.antivirus_utils import antivirus_path_validator, antivirus_file_validator, INFECTED_MESSAGE, DOES_NOT_EXIST_MESSAGE


EICAR_TEST_CONTENT = 'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

DEFAULT_MIDDLEWARES = settings.MIDDLEWARE


class AntivirusUtilsTests(TestCase):
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
        antivirus_path_validator(self.test_path)

    def test_infected_file(self):
        with open(self.test_path, 'w') as fo:
            # Write eicar test content
            fo.write(EICAR_TEST_CONTENT)
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(INFECTED_MESSAGE)):
            antivirus_path_validator(self.test_path)

    def test_non_existent_file(self):
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(DOES_NOT_EXIST_MESSAGE)):
            antivirus_path_validator('/doesnotexist')

    def test_clean_uploaded_file(self):
        upload_file = SimpleUploadedFile('test-clean.txt', b'Test content')
        upload_file.path = '/doesnotexist'
        # Should not raise any error
        antivirus_file_validator(upload_file)

    def test_infected_uploaded_file(self):
        upload_file = SimpleUploadedFile('test-eicar.txt', EICAR_TEST_CONTENT.encode('utf-8'))
        upload_file.path = '/doesnotexist'
        # Should raise ValidationError
        with self.assertRaisesMessage(ValidationError, str(INFECTED_MESSAGE)):
            antivirus_file_validator(upload_file)

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

    @override_settings(MIDDLEWARE=DEFAULT_MIDDLEWARES + (
        'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware',
        'django_web_utils.json_utils.JsonErrorResponseMiddleware',
    ))
    def test_form_post_request_json(self):
        file = BytesIO(EICAR_TEST_CONTENT.encode('utf-8'))
        response = self.client.post(reverse('testapp:upload-json'), data={'file': file})
        self.assertEqual(response.status_code, 451)
