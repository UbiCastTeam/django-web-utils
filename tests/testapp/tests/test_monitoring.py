import pytest
from django.urls import reverse

import django_web_utils
from django_web_utils.monitoring.sysinfo import get_system_info

pytestmark = pytest.mark.django_db


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


def test_logged(client):
    from django.contrib.auth.models import User
    user = User(username='mn_admin', is_superuser=True)
    user.set_password('test')
    user.save()
    response = client.post(reverse('login'), {'username': user.username, 'password': 'test'})
    assert response.status_code == 302

    response = client.get(reverse('monitoring:monitoring-panel'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    response = client.get(reverse('monitoring:monitoring-status'))
    content = response.json()
    assert response.status_code == 200, content
    assert response['Content-Type'] == 'application/json'
    content['apt']['log_mtime'] = '<val>'
    content['apt']['log_size'] = '<val>'
    content['hosts']['log_mtime'] = '<val>'
    content['hosts']['log_size'] = '<val>'
    assert content == {
        'apt': {'running': None, 'log_size': '<val>', 'log_mtime': '<val>'},
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

    response = client.get(reverse('monitoring:monitoring-log', args=['apt']))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    response = client.get(reverse('monitoring:monitoring-log', args=['dummy']))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

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
