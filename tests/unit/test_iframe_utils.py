from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import Http404, HttpResponse
from django.test import RequestFactory
import pytest

from django_web_utils.iframe_utils import iframe_view


def fake_render(request, template_name, context=None, status=200):
    return HttpResponse(template_name, status=status)


@pytest.fixture(autouse=True)
def patch_render():
    with mock.patch('django_web_utils.iframe_utils.render', fake_render):
        yield


def _get_request(method='get', path='/iframe/'):
    request = getattr(RequestFactory(), method)(path)
    request.user = AnonymousUser()
    return request


@pytest.mark.parametrize('methods', ['GET, PUT', ['GET', 'PUT'], 'get,put'])
@pytest.mark.parametrize('method, expected', [
    ('get', 200),
    ('put', 200),
    ('post', 405),
])
def test_methods(methods, method, expected):
    @iframe_view(methods=methods)
    def view(request):
        return HttpResponse('ok')

    response = view(_get_request(method))
    assert response.status_code == expected
    if expected == 405:
        assert response['Allow'] == 'GET, PUT'
    # Iframe views must be embeddable
    assert response.xframe_options_exempt is True


def test_methods__partial_name():
    # The "T" method must not be accepted because it is a substring of "GET"
    @iframe_view(methods='GET')
    def view(request):
        return HttpResponse('ok')

    request = _get_request()
    request.method = 'T'
    assert view(request).status_code == 405


def test_wraps():
    @iframe_view
    def my_view(request):
        """My doc."""
    assert my_view.__name__ == 'my_view'
    assert my_view.__doc__ == 'My doc.'


@pytest.mark.parametrize('error, expected_status, expected_template', [
    (BadRequest, 400, 'iframe/400.html'),
    (PermissionDenied, 403, 'iframe/403.html'),
    (Http404, 404, 'iframe/404.html'),
    (ValueError, 500, 'iframe/500.html'),
])
def test_errors(error, expected_status, expected_template):
    @iframe_view
    def view(request):
        raise error()

    response = view(_get_request())
    assert response.status_code == expected_status
    assert response.content.decode() == expected_template


@pytest.mark.parametrize('login_url, expected_status, expected_location', [
    (None, 401, None),
    ('/login/', 302, '/login/?next=/iframe/%3Fa%3D1'),
])
def test_login_required(login_url, expected_status, expected_location):
    @iframe_view(login_required=True, login_url=login_url)
    def view(request):
        return HttpResponse('ok')

    response = view(_get_request(path='/iframe/?a=1'))
    assert response.status_code == expected_status
    if expected_location:
        assert response['Location'] == expected_location
