import gzip
from pathlib import Path
import re
import types

from django.conf import settings
from django.urls import reverse
import pytest

import django_web_utils
from django_web_utils.monitoring.sysinfo import get_system_info

pytestmark = pytest.mark.django_db

with open(Path(settings.BASE_DIR, 'storage/logs/sample.log')) as fo:
    LOG_CONTENT = fo.read()


@pytest.fixture()
def logged_client(client):
    from django.contrib.auth.models import User
    user = User(username='mn_admin', is_superuser=True)
    user.set_password('test')
    user.save()
    response = client.post(reverse('login'), {'username': user.username, 'password': 'test'})
    assert response.status_code == 302
    return client


def test_anonymous(client):
    response = client.get(reverse('monitoring:monitoring-panel'))
    assert response.status_code == 302

    response = client.get(reverse('monitoring:monitoring-status'))
    assert response.status_code == 302

    response = client.get(reverse('monitoring:monitoring-log', args=['fake']))
    assert response.status_code == 302

    response = client.get(reverse('monitoring:monitoring-command'))
    assert response.status_code == 405

    response = client.post(reverse('monitoring:monitoring-command'))
    assert response.status_code == 302


def test_authentified(logged_client):
    client = logged_client

    response = client.get(reverse('monitoring:monitoring-panel'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    response = client.get(reverse('monitoring:monitoring-status'))
    content = response.json()
    assert response.status_code == 200, content
    assert response['Content-Type'] == 'application/json'
    content['sample']['log_mtime'] = '<val>'
    content['sample']['log_size'] = '<val>'
    content['hosts']['log_mtime'] = '<val>'
    content['hosts']['log_size'] = '<val>'
    assert content == {
        'sample': {'running': False, 'log_size': '<val>', 'log_mtime': '<val>'},
        'hosts': {'running': False, 'log_size': '<val>', 'log_mtime': '<val>'},
        'fake': {'running': False, 'log_size': '', 'log_mtime': ''},
        'dummy': {'running': False, 'log_size': '', 'log_mtime': ''},
    }

    response = client.get(reverse('monitoring:monitoring-status'), {'name': 'fake'})
    content = response.json()
    assert response.status_code == 200, content
    assert response['Content-Type'] == 'application/json'
    assert content == {'fake': {'running': False, 'log_size': '', 'log_mtime': ''}}

    response = client.get(reverse('monitoring:monitoring-log', args=['dummy']))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'
    content = response.content.decode('utf-8')
    results = re.findall(r'href="\?suffix[^&"]+"', content)
    assert results == ['href="?suffix="']

    response = client.get(reverse('monitoring:monitoring-command'))
    assert response.status_code == 405

    response = client.post(reverse('monitoring:monitoring-command'), {})
    assert response.status_code == 404

    response = client.post(reverse('monitoring:monitoring-command'), {'daemon': 'fake', 'cmd': 'start'})
    content = response.json()
    assert response.status_code == 200, content
    assert response['Content-Type'] == 'application/json'
    assert content == {'messages': [
        {
            'level': 'error',
            'name': 'fake',
            'out': 'The daemon name is invalid: "fake"',
            'text': 'The command "start" on "fake" has failed.'
        }
    ]}

    response = client.post(reverse('monitoring:monitoring-command'), {'daemon': 'dummy', 'cmd': 'stop'})
    content = response.json()
    assert response.status_code == 200, content
    assert response['Content-Type'] == 'application/json'
    assert content == {'messages': [
        {
            'level': 'success',
            'name': 'dummy',
            'out': '',
            'text': 'The command "stop" on "dummy" was successfully executed.'
        }
    ]}


@pytest.mark.parametrize('suffix, is_gz, expected', [
    pytest.param('', False, '', id='empty'),
    pytest.param('.1', False, 'Test\n', id='1'),
    pytest.param('.2.gz', True, 'Test\n', id='2'),
    pytest.param('invalid', False, '', id='invalid'),
])
def test_log_view__suffixes(logged_client, suffix, is_gz, expected):
    client = logged_client

    response = client.get(reverse('monitoring:monitoring-log', args=['sample']) + '?suffix=' + suffix)
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'
    content = response.content.decode('utf-8')
    results = re.findall(r'href="\?suffix[^&"]+"', content)
    assert results == [
        'href="?suffix="',
        'href="?suffix=.1"',
        'href="?suffix=.2.gz"',
    ]
    assert f'<pre class="log-block">{LOG_CONTENT}{expected}</pre>' in content
    if is_gz:
        assert ' (gz)' in content
    else:
        assert ' (gz)' not in content


def test_sysinfo():
    info = get_system_info(module=django_web_utils)
    assert 'info_sections' in info
    keys = list(info.keys())
    assert keys[:-1] == [
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
        'info_network'
    ]


@pytest.mark.parametrize('limit, expected', [
    pytest.param(1000, 'Test\n' * 100, id='under limit'),
    pytest.param(100, 'File too large once decompressed.\nOnly the raw file is accessible.', id='over limit'),
])
def test_log_view__gz_decompressed_limit(monkeypatch, tmp_path, limit, expected):
    from django.test import RequestFactory

    from django_web_utils.monitoring import utils
    monkeypatch.setattr(utils, 'FILE_SIZE_LIMIT_GZ_DECOMPRESSED', limit)
    path = tmp_path / 'test.log.gz'
    path.write_bytes(gzip.compress(b'Test\n' * 100))

    result = utils.log_view(RequestFactory().get('/'), path=path)
    assert result['file_content'] == expected


def test_daemons_info__str_paths(settings):
    from django_web_utils.monitoring import config
    settings.MONITORING_DAEMONS_INFO = types.SimpleNamespace(
        GROUPS=[{'name': 'base', 'label': 'Base'}],
        DAEMONS=[{'group': 'base', 'name': 'str', 'log_path': '/tmp/str.log', 'pid_path': '/tmp/str.pid'}],
    )
    config.get_daemons_info.cache_clear()
    try:
        info = config.get_daemons_info()
        assert info.DAEMONS['str']['log_path'] == Path('/tmp/str.log')
        assert info.DAEMONS['str']['pid_path'] == Path('/tmp/str.pid')
    finally:
        config.get_daemons_info.cache_clear()
