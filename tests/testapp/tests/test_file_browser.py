import json

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture()
def staff_client(client):
    from django.contrib.auth.models import User
    user = User(username='fb_admin', is_staff=True)
    user.set_password('test')
    user.save()
    response = client.post(reverse('login'), {'username': user.username, 'password': 'test'})
    assert response.status_code == 302
    return client


def test_anonymous(client):
    response = client.get(reverse('storage:file_browser_base'))
    assert response.status_code == 302

    response = client.get(reverse('storage:file_browser_dirs'))
    assert response.status_code == 302

    response = client.get(reverse('storage:file_browser_content'), {'path': '/'})
    assert response.status_code == 302


def test_logged(staff_client):
    response = staff_client.get(reverse('storage:file_browser_base'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    response = staff_client.get(reverse('storage:file_browser_dirs'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    assert content == {'dirs': [{'dir_name': 'Root folder', 'sub_dirs': [{'dir_name': 'a dir', 'sub_dirs': []}]}]}

    response = staff_client.get(reverse('storage:file_browser_content'), {'path': '/'})
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    content['files'][1]['mdate'] = 'test'
    assert content == {'files': [{'name': 'a dir', 'size': 3, 'size_h': '3 B', 'is_dir': True, 'nb_files': 1, 'nb_dirs': 0}, {'name': 'image.png', 'size': 103, 'size_h': '103 B', 'is_dir': False, 'nb_files': 0, 'nb_dirs': 0, 'ext': 'png', 'preview': True, 'mdate': 'test'}], 'path': '/', 'total_size': '106 B', 'total_nb_dirs': 1, 'total_nb_files': 2}

    response = staff_client.get(reverse('storage:file_browser_img_preview'), {'path': '/image.png'})
    assert response.status_code == 200
    assert response['Content-Type'] == 'image/png; charset=utf-8'
    assert len(response.content) > 0
