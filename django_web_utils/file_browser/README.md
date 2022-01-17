# File browser Django app

This app allows you to manipulate files in a specific directory.


## Mandatory settings

`FILE_BROWSER_DIRS`:
Dict with tuple composed of base path and base url.
Use different namespaces to allow browsing in several base path.

Settings example:

``` python
FILE_BROWSER_DIRS = {'storage': ('/home/test/dir', '/storage')}
```

Urls example:

``` python
from django.conf.urls import include
from django.urls import re_path

# ...
re_path(r'^storage/', include(('django_web_utils.file_browser.urls', 'storage'), namespace='storage'), {'namespace': 'storage'}),
```



## Optional settings

`FILE_BROWSER_DECORATOR`:
Function python path to be used as decorator.
Something like "a.module.decorator".

`FILE_BROWSER_BASE_TEMPLATE`:
The template to use for the browser base page.
This template must import jsu.min.js, odm.min.css and odm.min.js.
It must contain two include tags:

```
    {% include "file_browser/script.html" %}
    {% include "file_browser/body.html" %}
```
