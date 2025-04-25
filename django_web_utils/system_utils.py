"""
System utility functions
"""
import os
import pwd


def get_unix_user():
    uid = os.getuid()
    if uid == 0:
        return 'root'
    return pwd.getpwuid(uid).pw_name
