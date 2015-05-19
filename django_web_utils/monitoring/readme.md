# Daemons monitoring Django app

This app allows you to monitor daemons statuses.
The daemons can be built from the BaseDaemon class or not.


## Optional settings

``MONITORING_VIEWS_DECORATOR``:
Function python path to be used as decorator.
Something like "a.module.decorator".

``MONITORING_BASE_TEMPLATE``:
The template to use for the browser base page.
This template must import jquery.js, utils.js, odm.css and odm.js.
It must contain this include tag:

    {% include monitoring_body %} (somewhere in page's body)

``MONITORING_DAEMONS_INFO``:
The module in which daemons informations can be found.
Something like "a.module".
TODO: add groups declaration help.
