import os

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test

from django_web_utils.module_utils import import_module_by_python_path

# Take a look at the readme file for settings descriptions

view_decorator = getattr(settings, 'FILE_BROWSER_DECORATOR', None)
if view_decorator:
    view_decorator = import_module_by_python_path(view_decorator)
else:
    view_decorator = user_passes_test(lambda user: user.is_staff)

BASE_TEMPLATE = getattr(settings, 'FILE_BROWSER_BASE_TEMPLATE', None)


def clean_namespace(namespace):
    return namespace or 'file_browser'


def get_base_path(namespace):
    nsp = clean_namespace(namespace)
    return settings.FILE_BROWSER_DIRS[nsp][0]


def get_base_url(namespace):
    nsp = clean_namespace(namespace)
    url = settings.FILE_BROWSER_DIRS[nsp][1].rstrip('/')
    return url


def get_safe_path(base_path, *parts):
    """
    Join the given parts to the base path and return the resulting path (str).
    None is returned if the resulting path is not inside the base path (for example
    if a part is an absolute path or if it contains "..").
    The check is lexical: symbolic links inside the base path are not resolved.
    """
    if any('\0' in part for part in parts):
        return None
    base = os.path.normpath(base_path)
    path = os.path.normpath(os.path.join(base, *parts))
    if path != base and not path.startswith(base.rstrip(os.sep) + os.sep):
        return None
    return path


def is_valid_name(name):
    """
    Check that the given name is a single path component (no "/", not "." or "..").
    """
    return bool(name) and name not in ('.', '..') and '/' not in name and '\0' not in name
