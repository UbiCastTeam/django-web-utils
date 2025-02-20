"""
JSON utility functions
"""
import datetime
import traceback
import logging
# Django
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import JsonResponse, Http404
from django.utils.translation import gettext_lazy as _
# Django web utils
from django_web_utils.antivirus_utils import FileInfectedError, on_file_infected_error


def get_date_display(date):
    """
    Function to serialize a date object.
    """
    return date.strftime('%Y-%m-%d %H:%M:%S')


def get_date_object(date):
    """
    Function to get date object from a serialized date.
    """
    try:
        return datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def response(*args, **kwargs):
    """
    Function to get a JSON response.
    DEPRECATED function.
    """
    code = kwargs.pop('code', 200)
    if args:
        if len(args) == 1:
            data = args[0]
        else:
            data = args
        return JsonResponse(data, safe=False, status=code)
    return JsonResponse(kwargs, status=code)


def success_response(*args, **kwargs):
    """
    Function to get a classic JSON success response.
    DEPRECATED function.
    """
    code = kwargs.pop('code', 200)
    kwargs['success'] = True
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return JsonResponse(kwargs, status=code)


def failure_response(*args, **kwargs):
    """
    Function to get a classic JSON failure response.
    DEPRECATED function.
    """
    code = kwargs.pop('code', 200)
    kwargs['success'] = False
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return JsonResponse(kwargs, status=code)


def json_view(function=None, methods=None, login_required=False):
    """
    Decorator for JSON views.
    The "methods" argument can be used to allow only some methods on a particular view.
    To allow several methods, use this format: "GET, PUT".
    """
    def decorator(fct):
        def _wrapped_view(request, *args, **kwargs):
            # Tag request as json for error handling in the middleware
            request.is_json_request = True
            # Check request method
            if methods and request.method not in methods:
                response = JsonResponse({'error': '%s (405)' % _('Invalid request method')}, status=405)
                response['Allow'] = methods
                return response
            # Check login
            if login_required and not request.user.is_authenticated:
                return JsonResponse({'error': '%s (401)' % _('Authentication required')}, status=401)
            # Process view
            return fct(request, *args, **kwargs)
        return _wrapped_view
    if function:
        return decorator(function)
    return decorator


class JsonErrorResponseMiddleware:
    """
    This middleware returns errors in JSON format if request has "is_json_request" set to True.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_exception(self, request, exception):
        if getattr(request, 'is_json_request', False):
            if isinstance(exception, BadRequest):
                return JsonResponse({'error': '%s (400)\n%s' % (_('Bad request'), exception)}, status=400)
            elif isinstance(exception, PermissionDenied):
                return JsonResponse({'error': '%s (403)\n%s' % (_('Access denied'), exception)}, status=403)
            elif isinstance(exception, Http404):
                return JsonResponse({'error': '%s (404)\n%s' % (_('Page not found'), exception)}, status=404)
            elif isinstance(exception, FileInfectedError):
                # Call the function manually because all errors are catched in this decorator,
                # then the middleware from the antivirus module will be unable to see it.
                msg = on_file_infected_error(request)
                return JsonResponse({'error': '%s (451)\n%s' % (_('Infected file detected'), msg)}, status=451)
            else:
                # Trigger Django error log then return a json response.
                logger = logging.getLogger('django.request')
                logger.error(
                    'Internal server error: %s', request.get_full_path(),
                    exc_info=traceback.extract_stack(),
                    extra={'status_code': 500, 'request': request}
                )
                response = JsonResponse({'error': '%s (500)' % _('Internal server error')}, status=500)
                response._has_been_logged = True
                return response
