import re

import pytest
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.urls import reverse

from testapp.views import CustomMagicLoginView

pytestmark = pytest.mark.django_db


@pytest.fixture()
def filled_file(tmp_dir):
    path = CustomMagicLoginView.users_json_path
    path.write_text(
        '{"magic@example.com": '
        '{"username": "magic-user", "first_name": "Magic", "last_name": "User", "is_staff": true}}'
    )
    return path


@pytest.fixture()
def invalid_file(tmp_dir):
    path = CustomMagicLoginView.users_json_path
    path.write_text('["invalid"]')
    return path


@pytest.fixture()
def corrupted_file(tmp_dir):
    path = CustomMagicLoginView.users_json_path
    path.write_text('nope')
    return path


@pytest.fixture()
def user():
    return User.objects.create(email='magic@example.com', password='nope')


@pytest.fixture()
def with_email_template():
    CustomMagicLoginView.template_email = 'emails/email_magic_login.html'
    yield
    CustomMagicLoginView.template_email = None


def test_not_available():
    assert CustomMagicLoginView.is_available() is False


@pytest.mark.usefixtures('filled_file')
def test_available():
    assert CustomMagicLoginView.is_available() is True


def test_user_info__no_json():
    assert CustomMagicLoginView.get_users_info() == {}


@pytest.mark.usefixtures('corrupted_file')
def test_user_info__corrupted_json():
    assert CustomMagicLoginView.get_users_info() == {}


@pytest.mark.usefixtures('invalid_file')
def test_user_info__invalid_json():
    assert CustomMagicLoginView.get_users_info() == {}


@pytest.mark.usefixtures('filled_file')
def test_user_info__valid():
    assert CustomMagicLoginView.get_users_info() == {
        'magic@example.com': {
            'username': 'magic-user',
            'first_name': 'Magic',
            'last_name': 'User',
            'is_staff': True,
        }
    }


def test_get_form(client):
    response = client.get(reverse('testapp:magic_login'))
    assert response.status_code == 200


def test_invalid_email(client):
    response = client.post(reverse('testapp:magic_login'), {'email': 'nope'})
    content = response.content.decode('utf-8')
    assert response.status_code == 200, content
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].message == 'The submitted form is incorrect. Please correct all errors and send it again.'
    assert 'Invalid email address.' in content


@pytest.mark.usefixtures('filled_file')
def test_invalid_token(client):
    response = client.get(reverse('testapp:magic_login'), {'t': 'nope-invalid'})
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].message == 'Your session has expired, please get a new link to retry.'


@pytest.mark.usefixtures('filled_file')
def test_non_allowed_email(client):
    response = client.post(reverse('testapp:magic_login'), {'email': 'nope@example.com'})
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].message == 'The requested email address is not allowed.'


@pytest.mark.usefixtures('filled_file')
@pytest.mark.parametrize('with_template', [
    pytest.param(False, id='regular'),
    pytest.param(True, id='template'),
])
@pytest.mark.parametrize('already_exist', [
    pytest.param(False, id='new account'),
    pytest.param(True, id='existing account'),
])
@pytest.mark.parametrize('next_url, referrer, expected_next', [
    pytest.param(None, '', '/', id='no next & no referrer'),
    pytest.param(None, 'http://testserver/test/', '/test/', id='no next & referrer'),
    pytest.param('http://elsewhere', '', '/', id='forbidden next & no referrer'),
    pytest.param('/admin/', '', '/admin/', id='next & no referrer'),
    pytest.param('/admin/', 'http://testserver/test/', '/admin/', id='next & referrer'),
])
def test_allowed_email(request, client, with_template, already_exist, next_url, referrer, expected_next):
    if with_template:
        request.getfixturevalue('with_email_template')
    if already_exist:
        request.getfixturevalue('user')

    response = client.post(
        reverse('testapp:magic_login') + (f'?next={next_url}' if next_url else ''),
        {'email': 'magic@example.com'},
        HTTP_REFERER=referrer
    )
    assert response.status_code == 302
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].message == 'An email has been sent to you with the link to log in.'
    assert User.objects.all().count() == 1

    response = client.get(response['Location'])
    assert response.status_code == 200

    assert [m.to[0] for m in mail.outbox] == ['"Magic User" <magic@example.com>']
    match = re.match(
        r'.*<a href="http://testserver(/magic/\?t=[0-9a-z]+-[0-9a-f]+&next=[a-z/]+)" target="_blank">.*',
        mail.outbox[0].body, re.DOTALL
    )
    assert match
    url = match.groups()[0]

    response = client.get(url)
    assert response.status_code == 302
    assert response['Location'] == expected_next
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 0
    assert User.objects.all().count() == 1
    user = User.objects.all()[0]
    assert user.email == 'magic@example.com'
    assert user.password == ''
    assert user.username == 'magic-user'
    assert user.first_name == 'Magic'
    assert user.last_name == 'User'
    assert user.is_staff is True
    assert user.is_superuser is False


def test_delete_users__no_file():
    User.objects.create(username='magic-user')

    CustomMagicLoginView.delete_unregistered_users()

    assert not User.objects.filter(username='magic-user').exists()


@pytest.mark.usefixtures('filled_file')
def test_delete_users__with_file():
    User.objects.create(username='magic-user', email='magic@example.com')

    CustomMagicLoginView.delete_unregistered_users()

    assert User.objects.filter(username='magic-user').exists()


@pytest.mark.usefixtures('filled_file')
def test_delete_users__with_file__no_email():
    User.objects.create(username='magic-user')

    CustomMagicLoginView.delete_unregistered_users()

    assert not User.objects.filter(username='magic-user').exists()


@pytest.mark.usefixtures('filled_file')
def test_delete_users__with_file__multiple():
    User.objects.create(username='magic-user', email='magic@example.com')
    User.objects.create(username='magic-1', email='magic1@example.com')
    User.objects.create(username='magic-2', email='magic2@example.com')

    CustomMagicLoginView.delete_unregistered_users()

    assert User.objects.filter(username='magic-user').exists()
    assert not User.objects.filter(username='magic-1').exists()
    assert not User.objects.filter(username='magic-2').exists()
