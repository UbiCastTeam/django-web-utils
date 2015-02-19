# File browser Django app

This app allows you to manipulate the file in a specific directory.


## Mandatory settings

``FILE_BROWSER_BASE_PATH``:
Base path to serve with file browser.

``FILE_BROWSER_BASE_URL``:
Base url for served files.


## Optional settings

``FILE_BROWSER_DECORATOR``:
Function python path to be used as decorator.
Something like "a.module.decorator".

``FILE_BROWSER_BASE_TEMPLATE``:
The template to use for the browser base page.
This template must import jquery.js, utils.js, odm.css and odm.js.
It must contain two include tags:

    {% include "file_browser/script.html" %}
    {% include "file_browser/body.html" %}
