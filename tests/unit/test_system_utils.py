from pathlib import Path
import re
import subprocess
import sys

import django_web_utils
from django_web_utils import module_utils, packages_utils, system_utils


def test_get_unix_user():
    assert system_utils.get_unix_user()


def test_get_python_executable():
    path = system_utils.get_python_executable()
    assert Path(path).exists()
    p = subprocess.run([path, '-c', 'import sys; print(sys.prefix)'], capture_output=True, text=True, check=True)
    assert p.stdout.strip() == sys.prefix


def test_get_version__git():
    version, revision, local_repo = packages_utils.get_version(package='djwutils-missing-pkg', module=django_web_utils)
    assert version == django_web_utils.__version__
    assert local_repo is True
    assert re.fullmatch(r'\d{8}-\d{6}-[0-9a-f]+', revision)


def test_get_version__shell_chars():
    # The package name must not be interpreted by a shell
    version, revision, local_repo = packages_utils.get_version(package="x'; touch /tmp/djwutils-injected; '")
    assert not Path('/tmp/djwutils-injected').exists()


def test_import_module_by_python_path():
    import json
    assert module_utils.import_module_by_python_path('json') is json
    assert module_utils.import_module_by_python_path('json.dumps') is json.dumps
    assert module_utils.import_module_by_python_path('django_web_utils.time_utils').__name__ == (
        'django_web_utils.time_utils'
    )
    assert module_utils.import_module_by_python_path(json) is json
