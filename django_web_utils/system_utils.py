"""
System utility functions
"""
import os
from pathlib import Path
import pwd
import sys


def get_unix_user():
    uid = os.getuid()
    if uid == 0:
        return 'root'
    return pwd.getpwuid(uid).pw_name


def get_python_executable():
    """
    Get the path of the Python interpreter of the current environment (virtual environment included).
    The `sys.executable` value is not used first because it can point to the server binary in some
    contexts (for example with uWSGI).
    """
    for name in (f'python{sys.version_info.major}.{sys.version_info.minor}', f'python{sys.version_info.major}'):
        path = Path(sys.prefix) / 'bin' / name
        if path.exists():
            return str(path)
    return sys.executable or 'python3'
