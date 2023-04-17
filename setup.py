#!/usr/bin/env python3
import os
import re
from setuptools import setup


INSTALL_REQUIRES = [
    'bleach[css] >= 5.0, < 5.1',
    'pillow >= 9.3, < 9.4',
]

EXTRAS_REQUIRE = {
    'dev': [
        'django >= 4.1, < 4.2',
        'flake8',
        'psycopg2-binary',
        'pytest',
        'pytest-cov',
        'pytest-django',
        'vulture',
    ],
}

root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)


def get_version():
    init_file = os.path.join('django_web_utils', '__init__.py')
    if os.path.exists(init_file):
        with open(init_file) as fo:
            version_file = fo.read()
        version = re.search(r'^__version__ = [\'"]([\d\.]+)[\'"]', version_file, re.M).group(1)
    else:
        version = '?'
    return version


def fullsplit(path, result=None):
    # Split a pathname into components (the opposite of os.path.join) in a platform-neutral way.
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)


# Compile the list of packages available, because setuptools doesn't have an easy way to do this.
packages, package_data = [], {}
for dirpath, dirnames, filenames in os.walk('django_web_utils', followlinks=True):
    # Ignore PEP 3147 cache dirs, tests dirs and those whose names start with '.'
    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__' and d != 'tests']

    parts = fullsplit(dirpath)
    package_name = '.'.join(parts)
    if '__init__.py' in filenames:
        packages.append(package_name)
        filenames = [f for f in filenames if not f.endswith('.py') and not f.endswith('.pyc')]
    if filenames:
        relative_path = []
        while '.'.join(parts) not in packages:
            relative_path.append(parts.pop())
        if relative_path:
            relative_path.reverse()
            path = os.path.join(*relative_path)
        else:
            path = ''
        package_files = package_data.setdefault('.'.join(parts), [])
        package_files.extend([os.path.join(path, f) for f in filenames])

setup(
    name='django_web_utils',
    version=get_version(),
    description='A collection of utilities for web projects based on Django.',
    author='Stéphane Diemer',
    author_email='stephane.diemer@ubicast.eu',
    url='https://github.com/UbiCastTeam/django-web-utils',
    license='LGPLv3',
    packages=packages,
    package_data=package_data,
    scripts=[],
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
)
