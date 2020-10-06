# File browser Django app

This app allows you to manipulate files in a specific directory.


## Mandatory settings

`FILE_BROWSER_BASE_PATH`:
Base path to serve with file browser.
Should be set when no namespace is used to inlucde app urls.

`FILE_BROWSER_BASE_URL`:
Base url for served files.
Should be set when no namespace is used to inlucde app urls.

`FILE_BROWSER_DIRS`:
Dict with tuple composed of base path and base url.
Should be set when namespace is used to inlucde app urls.
Use different namespaces to allow browsing in several base path.
Example:

``` python
FILE_BROWSER_DIRS = {'namespace': ('path', 'url')}
```


## Optional settings

`FILE_BROWSER_DECORATOR`:
Function python path to be used as decorator.
Something like "a.module.decorator".

`FILE_BROWSER_BASE_TEMPLATE`:
The template to use for the browser base page.
This template must import jquery.js, utils.js, odm.css and odm.js.
It must contain two include tags:

```
    {% include "file_browser/script.html" %}
    {% include "file_browser/body.html" %}
```
