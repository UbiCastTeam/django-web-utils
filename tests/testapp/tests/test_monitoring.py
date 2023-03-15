import json

import pytest
from django.urls import reverse

import django_web_utils
from django_web_utils.monitoring.sysinfo import get_system_info

pytestmark = pytest.mark.django_db


def test_anonymous(client):
    response = client.get(reverse('monitoring:monitoring-panel'))
    assert response.status_code == 302

    response = client.get(reverse('monitoring:monitoring-check_password'))
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

    response = client.get(reverse('monitoring:monitoring-check_password'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    assert content == {'pwd_ok': False}

    response = client.get(reverse('monitoring:monitoring-status'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    content['hosts']['log_mtime'] = 'test'
    content['hosts']['log_size'] = 'test'
    assert content == {
        'hosts': {'running': None, 'need_password': False, 'log_size': 'test', 'log_mtime': 'test'},
        'fake': {'running': False, 'need_password': False, 'log_size': '', 'log_mtime': ''},
        'dummy': {'running': False, 'need_password': False, 'log_size': '', 'log_mtime': ''},
    }

    response = client.get(reverse('monitoring:monitoring-status'), {'name': 'fake'})
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    assert content == {'fake': {'running': False, 'need_password': False, 'log_size': '', 'log_mtime': ''}}

    response = client.get(reverse('monitoring:monitoring-config', args=['hosts']))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    response = client.get(reverse('monitoring:monitoring-log', args=['fake']))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    response = client.get(reverse('monitoring:monitoring-command'))
    assert response.status_code == 405

    response = client.post(reverse('monitoring:monitoring-command'), {})
    assert response.status_code == 404

    response = client.post(reverse('monitoring:monitoring-command'), {'daemon': 'fake', 'cmd': 'clear_log'})
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    assert content == {'messages': [{'level': 'success', 'name': 'fake', 'out': 'Log file cleared.', 'text': 'Command "clear_log" on "fake" successfully executed.'}]}


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
        'info_network']
