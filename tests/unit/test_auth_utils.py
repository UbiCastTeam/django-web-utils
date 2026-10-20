import base64

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.test import RequestFactory
import pytest

from django_web_utils.auth_utils import CharactersTypesValidator, login_basicauth, login_required_basicauth

pytestmark = pytest.mark.django_db


def _get_request(params=None, credentials=None):
    headers = {}
    if credentials:
        headers['HTTP_AUTHORIZATION'] = 'Basic ' + base64.b64encode(credentials.encode('utf-8')).decode('ascii')
    request = RequestFactory().get('/login-basic/', params or {}, **headers)
    SessionMiddleware(lambda _request: None).process_request(request)
    request.user = AnonymousUser()
    return request


@pytest.fixture()
def user():
    user = User(username='basic-user')
    user.set_password('test')
    user.save()
    return user


def test_basicauth__no_credentials():
    response = login_basicauth(_get_request())
    assert response.status_code == 401
    assert response['WWW-Authenticate'] == 'Basic realm="Access authentication"'


@pytest.mark.usefixtures('user')
def test_basicauth__invalid_credentials():
    response = login_basicauth(_get_request(credentials='basic-user:nope'))
    assert response.status_code == 401
    assert response.content == b'Your username and password do not match.'


@pytest.mark.usefixtures('user')
@pytest.mark.parametrize('next_url, expected', [
    pytest.param(None, '/', id='no next'),
    pytest.param('/admin/', '/admin/', id='local next'),
    pytest.param('http://testserver/admin/', 'http://testserver/admin/', id='same host'),
    pytest.param('//evil.example/', '/', id='protocol relative'),
    pytest.param('https://evil.example/', '/', id='other host'),
    pytest.param('javascript:alert(1)', '/', id='javascript'),
])
def test_basicauth__redirect(next_url, expected):
    params = {'next': next_url} if next_url else None
    response = login_basicauth(_get_request(params, credentials='basic-user:test'))
    assert response.status_code == 302
    assert response['Location'] == expected


def test_basicauth__wraps():
    @login_required_basicauth
    def my_view(request):
        """My doc."""
    assert my_view.__name__ == 'my_view'
    assert my_view.__doc__ == 'My doc.'


@pytest.mark.parametrize('password, valid', [
    ('abcdefgh', False),
    ('abcdEFGH', False),
    ('abcdEF12', True),
    ('abcd12!!', True),
])
def test_characters_types_validator(password, valid):
    validator = CharactersTypesValidator()
    if valid:
        validator.validate(password)
    else:
        with pytest.raises(ValidationError):
            validator.validate(password)
    assert validator.get_help_text()
