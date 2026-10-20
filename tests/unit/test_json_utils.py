import datetime
import json

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import Http404, JsonResponse
from django.test import RequestFactory
import pytest

from django_web_utils import json_utils


def _get_request(method='get'):
    request = getattr(RequestFactory(), method)('/json/')
    request.user = AnonymousUser()
    return request


def test_dates():
    date = datetime.datetime(2026, 1, 2, 3, 4, 5)
    assert json_utils.get_date_display(date) == '2026-01-02 03:04:05'
    assert json_utils.get_date_object('2026-01-02 03:04:05') == date
    assert json_utils.get_date_object('nope') is None


@pytest.mark.parametrize('methods', ['GET, PUT', ['GET', 'PUT']])
@pytest.mark.parametrize('method, expected', [
    ('get', 200),
    ('put', 200),
    ('post', 405),
])
def test_methods(methods, method, expected):
    @json_utils.json_view(methods=methods)
    def view(request):
        return JsonResponse({})

    response = view(_get_request(method))
    assert response.status_code == expected
    if expected == 405:
        assert response['Allow'] == 'GET, PUT'


def test_methods__partial_name():
    @json_utils.json_view(methods='GET')
    def view(request):
        return JsonResponse({})

    request = _get_request()
    request.method = 'T'
    assert view(request).status_code == 405


def test_login_required():
    @json_utils.json_view(login_required=True)
    def view(request):
        return JsonResponse({})

    response = view(_get_request())
    assert response.status_code == 401
    assert json.loads(response.content) == {'error': 'Authentication required (401)'}


def test_wraps():
    @json_utils.json_view
    def my_view(request):
        """My doc."""
    assert my_view.__name__ == 'my_view'
    assert my_view.__doc__ == 'My doc.'


@pytest.mark.parametrize('error, expected_status', [
    (BadRequest('bad'), 400),
    (PermissionDenied('denied'), 403),
    (Http404('missing'), 404),
    (ValueError('internal'), 500),
])
def test_middleware(error, expected_status):
    middleware = json_utils.JsonErrorResponseMiddleware(lambda request: None)
    request = _get_request()
    assert middleware.process_exception(request, error) is None

    request.is_json_request = True
    response = middleware.process_exception(request, error)
    assert response.status_code == expected_status
    content = json.loads(response.content)
    if expected_status == 500:
        # The details of internal errors must not be disclosed
        assert content == {'error': 'Internal server error (500)'}
    else:
        assert str(error) in content['error']
