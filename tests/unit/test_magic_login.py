import html
import re
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.urls import reverse
import pytest
from testproject.testapp.views import CustomMagicLoginView

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


SENT_MSG = 'If this email address is allowed, an email has been sent to it with the link to log in.'


@pytest.mark.usefixtures('filled_file')
def test_non_allowed_email(client):
    # The response must be the same as for an allowed email to avoid disclosing allowed addresses
    response = client.post(reverse('testapp:magic_login'), {'email': 'nope@example.com'})
    assert response.status_code == 302
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].message == SENT_MSG
    assert len(mail.outbox) == 0
    assert User.objects.all().count() == 0


@pytest.mark.usefixtures('filled_file')
def test_request_cooldown(client):
    response = client.post(reverse('testapp:magic_login'), {'email': 'magic@example.com'})
    assert response.status_code == 302
    assert len(mail.outbox) == 1

    response = client.post(reverse('testapp:magic_login'), {'email': 'magic@example.com'})
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert [m.message for m in messages] == [
        SENT_MSG,
        'A link has already been requested recently for this email address, please wait a moment before retrying.'
    ]
    assert len(mail.outbox) == 1



@pytest.mark.usefixtures('filled_file')
def test_request_cooldown__reset_on_send_failure(client):
    with mock.patch('django_web_utils.magic_login.views.send_emails', return_value=(False, 'SMTP error')):
        response = client.post(reverse('testapp:magic_login'), {'email': 'magic@example.com'})
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert [m.message for m in messages] == ['Failed to send the email. Please try again later.']
    assert len(mail.outbox) == 0

    # The user can retry immediately
    response = client.post(reverse('testapp:magic_login'), {'email': 'magic@example.com'})
    assert response.status_code == 302
    assert len(mail.outbox) == 1

def _get_link(email):
    match = re.match(r'.*<a href="([^"]+)" target="_blank">.*', email.body, re.DOTALL)
    assert match
    return html.unescape(match.groups()[0])


@pytest.mark.usefixtures('filled_file')
@pytest.mark.parametrize('next_url', [
    '//evil.example/x',
    '/\\evil.example/x',
    'https://evil.example/x',
    'javascript:alert(1)',
    'evil.example',
])
def test_next_url__open_redirect(client, next_url):
    response = client.post(
        reverse('testapp:magic_login') + '?' + urlencode({'next': next_url}),
        {'email': 'magic@example.com'},
    )
    assert response.status_code == 302
    url = _get_link(mail.outbox[0])
    assert url.endswith('&next=%2F')

    response = client.get(url.removeprefix('http://testserver'))
    assert response.status_code == 302
    assert response['Location'] == '/'


@pytest.mark.usefixtures('filled_file')
def test_next_url__html_injection(client):
    next_url = '/"><a href="https://evil.example">click</a>'
    response = client.post(
        reverse('testapp:magic_login') + '?' + urlencode({'next': next_url}),
        {'email': 'magic@example.com'},
    )
    assert response.status_code == 302
    body = mail.outbox[0].body
    assert 'evil.example">' not in body
    assert body.count('<a ') == 1
    url = _get_link(mail.outbox[0])
    assert parse_qs(urlsplit(url).query)['next'] == [next_url]


@pytest.mark.usefixtures('filled_file')
def test_inactive_user(client):
    User.objects.create(username='magic-user', email='magic@example.com', is_active=False)
    response = client.post(reverse('testapp:magic_login'), {'email': 'magic@example.com'})
    assert response.status_code == 302
    url = _get_link(mail.outbox[0])

    response = client.get(url.removeprefix('http://testserver'))
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert [m.message for m in messages] == [SENT_MSG, 'Your request is invalid.']
    assert '_auth_user_id' not in client.session


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
    assert messages[0].message == SENT_MSG
    assert User.objects.all().count() == 1

    response = client.get(response['Location'])
    assert response.status_code == 200

    assert [m.to[0] for m in mail.outbox] == ['"Magic User" <magic@example.com>']
    match = re.match(
        r'.*<a href="http://testserver(/magic/\?t=[0-9a-z]+-[0-9a-f]+&amp;next=[0-9A-Za-z%]+)" target="_blank">.*',
        mail.outbox[0].body, re.DOTALL
    )
    assert match
    url = html.unescape(match.groups()[0])

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
