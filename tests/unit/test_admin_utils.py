from django.contrib.auth.models import User
from django.urls import reverse
import pytest

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


def test_admin_csv_export(super_client):
    from testproject.testapp.models import SettingsModel
    obj = SettingsModel.objects.create(key='=1+1', value='test')
    response = super_client.post('/admin/testapp/settingsmodel/', {
        'action': 'export_as_csv',
        '_selected_action': [obj.pk],
    })
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'
    lines = response.content.decode('utf-8').splitlines()
    # The columns order must be the model fields order
    assert lines[0] == 'id,key,value,updated_at'
    # The values are not altered
    assert lines[1].startswith(f'{obj.pk},=1+1,test,')
