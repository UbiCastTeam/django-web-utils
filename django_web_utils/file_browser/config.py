# Django
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings


# Take a look at the readme file for settings descriptions

view_decorator = getattr(settings, 'FILE_BROWSER_DECORATOR', None)
if view_decorator:
    if '.' in view_decorator:
        element = view_decorator.split('.')[-1]
        _tmp = __import__(view_decorator[:-len(element) - 1], fromlist=[element])
        view_decorator = getattr(_tmp, element)
    else:
        view_decorator = __import__(view_decorator)
else:
    view_decorator = user_passes_test(lambda user: user.is_staff)

BASE_TEMPLATE = getattr(settings, 'FILE_BROWSER_BASE_TEMPLATE', None)


def clean_namespace(namespace):
    return namespace or 'file_browser'


def get_base_path(namespace):
    nsp = clean_namespace(namespace)
    return getattr(settings, 'FILE_BROWSER_DIRS')[nsp][0]


def get_base_url(namespace):
    nsp = clean_namespace(namespace)
    url = getattr(settings, 'FILE_BROWSER_DIRS')[nsp][1].rstrip('/')
    return url
