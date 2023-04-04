# Django web utils

A collection of utilities for web projects based on Django.

This library is only compatible with Python 3.9+.


## Usage

Add in your `settings`:

``` python
INSTALLED_APPS = [
    # [...]
    'django_web_utils',  # to get translations of utils files
    # 'django_web_utils.file_browser',
    # 'django_web_utils.monitoring',
    # [...]
]
```


## Sub applications documentations

* [File browser](/django_web_utils/file_browser/README.md)
* [Monitoring](/django_web_utils/monitoring/README.md)


## Development

All dependencies are required for the following commands (django, bleach and pillow).

### Code check

``` bash
make lint
make deadcode
```

### Translations

``` bash
make generate_po
make generate_mo
```

### Tests

To run all tests:

``` bash
make test
```

To run a single test:

``` bash
make test PYTEST_ARGS='-x tests/testapp/tests/test_csv_utils.py'
```

### Run test server

``` bash
make run
```

With antivirus:

``` bash
make run NEED_CLAMAV=1
```

### Remove Python compiled files

``` bash
make clean
```
