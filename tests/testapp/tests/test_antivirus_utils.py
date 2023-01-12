import subprocess
from io import BytesIO
from os import chmod
from pathlib import Path

import pytest
from django.conf import settings
from django.core import mail as dj_mail
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from django_web_utils import antivirus_utils as avu

pytestmark = pytest.mark.usefixtures('clamav_daemon')

EICAR_TEST_CONTENT = 'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

DEFAULT_MIDDLEWARES = settings.MIDDLEWARE


@pytest.fixture(scope='session')
def clamav_daemon():
    # Start ClamAV daemon if not running
    if not Path('/var/run/clamav/clamd.ctl').exists():
        # The systemctl command is not available here because of docker
        subprocess.run(['sudo', 'service', 'clamav-daemon', 'start'], stdin=subprocess.DEVNULL, check=True)


@pytest.fixture()
def test_path(tmp_dir):
    path = tmp_dir / 'djwutils-antivirus-test.txt'
    path.unlink(missing_ok=True)

    yield path

    path.unlink(missing_ok=True)


def test_socket_path():
    sp = avu.get_antivirus_socket_path()
    assert Path(sp).exists()


def test_is_enabled():
    enabled = getattr(settings, 'ANTIVIRUS_ENABLED', None)
    assert enabled is None
    enabled = avu.is_antivirus_enabled()
    assert enabled


@override_settings(ANTIVIRUS_ENABLED=True)
def test_file__clean(test_path):
    with open(test_path, 'w') as fo:
        fo.write('Test content')
    # Should not raise any error
    avu.antivirus_path_validator(test_path)
    assert test_path.exists()


@override_settings(ANTIVIRUS_ENABLED=True)
def test_file__infected(test_path):
    with open(test_path, 'w') as fo:
        # Write eicar test content
        fo.write(EICAR_TEST_CONTENT)
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.INFECTED_MESSAGE)):
        avu.antivirus_path_validator(test_path)
    assert not test_path.exists()


@override_settings(ANTIVIRUS_ENABLED=True)
def test_file__infected__without_remove(test_path):
    with open(test_path, 'w') as fo:
        # Write eicar test content
        fo.write(EICAR_TEST_CONTENT)
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.INFECTED_MESSAGE)):
        avu.antivirus_path_validator(test_path, remove=False)
    assert test_path.exists()


@override_settings(ANTIVIRUS_ENABLED=True)
def test_stream__clean(test_path):
    with open(test_path, 'w') as fo:
        # Write eicar test content
        fo.write('Test content')
    # Should raise ValidationError
    with open(test_path, 'rb') as fo:
        avu.antivirus_stream_validator(fo)
    assert test_path.exists()


@override_settings(ANTIVIRUS_ENABLED=True)
def test_stream__infected(test_path):
    with open(test_path, 'w') as fo:
        # Write eicar test content
        fo.write(EICAR_TEST_CONTENT)
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.INFECTED_MESSAGE)):
        with open(test_path, 'rb') as fo:
            avu.antivirus_stream_validator(fo)
    assert test_path.exists()  # Because the stream path is not set


@override_settings(ANTIVIRUS_ENABLED=True)
def test_stream__infected__closed(test_path):
    with open(test_path, 'w') as fo:
        # Write eicar test content
        fo.write(EICAR_TEST_CONTENT)
    # Should not raise any error because scan should be skipped (closed file)
    fo = open(test_path, 'rb')
    fo.close()
    avu.antivirus_stream_validator(fo)
    assert test_path.exists()


@override_settings(ANTIVIRUS_ENABLED=True)
def test_stream__infected__reopen():
    # Use ContentFile to handle re-opening
    fo = ContentFile(EICAR_TEST_CONTENT.encode('utf-8'))
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.INFECTED_MESSAGE)):
        fo.close()
        avu.antivirus_stream_validator(fo, skip_closed=False)


@override_settings(ANTIVIRUS_ENABLED=True)
def test_non_existent__path():
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.DOES_NOT_EXIST_MESSAGE)):
        avu.antivirus_path_validator('/doesnotexist')


@override_settings(ANTIVIRUS_ENABLED=True)
def test_non_existent__file():
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.INVALID_FILE_MESSAGE)):
        avu.antivirus_file_validator('/doesnotexist')


@override_settings(ANTIVIRUS_ENABLED=True)
def test_restricted_file__denied(test_path):
    with open(test_path, 'w') as fo:
        # Write eicar test content
        fo.write('Test content')
    chmod(test_path, 0o400)
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.SCAN_FAILED_MESSAGE)):
        avu.antivirus_path_validator(test_path)


@override_settings(ANTIVIRUS_ENABLED=True)
def test_restricted_file__ok(test_path):
    with open(test_path, 'w') as fo:
        # Write eicar test content
        fo.write('Test content')
    chmod(test_path, 0o400)
    # Should not raise any error
    avu.antivirus_file_validator(test_path)


@override_settings(ANTIVIRUS_ENABLED=True)
def test_uploaded_file__clean():
    upload_file = SimpleUploadedFile('test-clean.txt', b'Test content')
    upload_file.path = '/doesnotexist'
    # Should not raise any error
    avu.antivirus_stream_validator(upload_file)


@override_settings(ANTIVIRUS_ENABLED=True)
def test_uploaded_file__infected():
    upload_file = SimpleUploadedFile('test-eicar.txt', EICAR_TEST_CONTENT.encode('utf-8'))
    upload_file.path = '/doesnotexist'
    # Should raise ValidationError
    with pytest.raises(ValidationError, match=str(avu.INFECTED_MESSAGE)):
        avu.antivirus_stream_validator(upload_file)


@pytest.mark.django_db()
@override_settings(ANTIVIRUS_ENABLED=True, MIDDLEWARE=DEFAULT_MIDDLEWARES + (
    'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware',
))
def test_form_request__get(client):
    response = client.get(reverse('testapp:upload'))
    assert response.status_code == 200


@pytest.mark.django_db()
@override_settings(ANTIVIRUS_ENABLED=True, MIDDLEWARE=DEFAULT_MIDDLEWARES + (
    'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware',
))
def test_form_request__post(client):
    dj_mail.outbox = []

    file = BytesIO(EICAR_TEST_CONTENT.encode('utf-8'))
    response = client.post(reverse('testapp:upload'), data={'file': file})
    assert response.status_code == 451

    mailinbox = [m.to[0] for m in dj_mail.outbox]
    expected = [settings.ADMINS[0][1]]
    assert mailinbox == expected


@pytest.mark.django_db()
@override_settings(ANTIVIRUS_ENABLED=True, MIDDLEWARE=DEFAULT_MIDDLEWARES + (
    'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware',
    'django_web_utils.json_utils.JsonErrorResponseMiddleware',
))
def test_form_request__post_json(client):
    dj_mail.outbox = []

    file = BytesIO(EICAR_TEST_CONTENT.encode('utf-8'))
    response = client.post(reverse('testapp:upload-json'), data={'file': file})
    assert response.status_code == 451

    mailinbox = [m.to[0] for m in dj_mail.outbox]
    expected = [settings.ADMINS[0][1]]
    assert mailinbox == expected
