"""
HTTP utility functions
"""


def parse_methods(methods):
    """
    Get a set of uppercase HTTP methods from a string like "GET, PUT" or from an iterable.
    Returns None if no methods are given.
    """
    if not methods:
        return None
    if isinstance(methods, str):
        methods = methods.split(',')
    return {method.strip().upper() for method in methods if method.strip()}
