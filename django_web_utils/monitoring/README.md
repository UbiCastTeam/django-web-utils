# Daemons monitoring Django app

This app allows you to monitor daemons statuses.
The daemons can be built from the BaseDaemon class or not.


## Optional settings

`MONITORING_NAMESPACE`:
The namespace to use to build links.
Default is `monitoring`.

To include urls, add this line to your `urls.py`:

``` python
from django.conf.urls import include
from django.urls import re_path

# ...
re_path(r'^monitoring/', include(('django_web_utils.monitoring.urls', 'monitoring'), namespace='monitoring')),
```

`MONITORING_BASE_TEMPLATE`:
The template to use for the browser base page.
This template must import jquery.js, jsu.js, odm.css and odm.js.
It must contain this include tag:

```
{% include monitoring_body %} (somewhere in page's body)
```

`MONITORING_TEMPLATE_DATA`:
Some extra data to give to the template.
This setting must be either a dict or None.

`MONITORING_DAEMONS_INFO`:
The module in which daemons informations can be found.
Something like "a.module".
Content example of this module:

``` python
from django.utils.translation import gettext_lazy as _

DAEMONS = [
    dict(
        group='base', name='django', label=_('Django'),
        no_commands=True, only_log=True,
        log_path='/var/logs/your-service/django.log',
        pid_path='/var/run/your-service/django.pid',
        help_text=_('This daemon handles all basic requests.')),
]
GROUPS = [
    dict(name='base', label=_('Base daemons')),
]
```


`MONITORING_DATE_ADJUST_FCT`:
The function to use to convert system locale date to user date.
The returned object must be a callable.
For example:

``` python
def MONITORING_DATE_ADJUST_FCT(request):
    return request.user.get_locale_date
```
