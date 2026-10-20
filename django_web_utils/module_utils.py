from importlib import import_module

from django.utils.module_loading import import_string


def import_module_by_python_path(module):
    """
    Import a module or an attribute of a module (function, class, etc.) from its Python path.
    Values which are not strings are returned as is.
    """
    if not isinstance(module, str):
        return module
    try:
        return import_module(module)
    except ModuleNotFoundError as err:
        # The path is probably pointing to an attribute of a module
        if '.' not in module or err.name != module:
            raise
    return import_string(module)
