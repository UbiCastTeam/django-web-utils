# Django web utils

A collection of utilities for web projects based on Django.

This library is only compatible with Python 3.7+.


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
make po
make mo
```

### Tests

``` bash
make test
```

### Run test server

``` bash
make run
```

### Remove Python compiled files

``` bash
make clean
```
