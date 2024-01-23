import pytest
from django.contrib.auth.models import User
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture()
def super_client(client):
    user = User(username='admin', is_staff=True, is_superuser=True)
    user.set_password('test')
    user.save()
    response = client.post(reverse('login'), {'username': user.username, 'password': 'test'})
    assert response.status_code == 302
    return client


def test_admin_ui(super_client):
    response = super_client.get('/admin/testapp/settingsmodel/')
    assert response.status_code == 200
