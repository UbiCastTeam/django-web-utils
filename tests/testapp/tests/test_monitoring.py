import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

import django_web_utils
from django_web_utils.monitoring.sysinfo import get_system_info

pytestmark = pytest.mark.django_db

with open(Path(settings.BASE_DIR, 'storage/logs/sample.log'), 'r') as fo:
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

    response = client.get(reverse('monitoring:monitoring-config', args=['hosts']))
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
        'sample': {'running': None, 'log_size': '<val>', 'log_mtime': '<val>'},
        'hosts': {'running': None, 'log_size': '<val>', 'log_mtime': '<val>'},
        'fake': {'running': False, 'log_size': '', 'log_mtime': ''},
        'dummy': {'running': False, 'log_size': '', 'log_mtime': ''},
    }

    response = client.get(reverse('monitoring:monitoring-status'), {'name': 'fake'})
    content = response.json()
    assert response.status_code == 200, content
    assert response['Content-Type'] == 'application/json'
    assert content == {'fake': {'running': False, 'log_size': '', 'log_mtime': ''}}

    response = client.get(reverse('monitoring:monitoring-config', args=['hosts']))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

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
            'out': 'No output from command.',
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
