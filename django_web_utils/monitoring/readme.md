# Daemons monitoring Django app

This app allows you to monitor daemons statuses.
The daemons can be built from the BaseDaemon class or not.


## Optional settings

``MONITORING_BASE_TEMPLATE``:
The template to use for the browser base page.
This template must import jquery.js, utils.js, odm.css and odm.js.
It must contain this include tag:

    {% include monitoring_body %} (somewhere in page's body)

``MONITORING_TEMPLATE_DATA``:
Some extra data to give to the template.
This setting must be either a dict or None.

``MONITORING_DAEMONS_INFO``:
The module in which daemons informations can be found.
Something like "a.module".
Content example:

    DAEMONS = [
        dict(group='base', name='django', label=_('Django'),
            no_commands=True, only_log=True,
            log_path=os.path.expanduser('~/.logs/django.log'),
            pid_path=os.path.join(settings.BASE_DIR, 'django.pid'),
            help_text=_('This daemon handles all basic requests.')),
    ]
    GROUPS = [
        dict(name='base', label=_('Base daemons')),
    ]


``MONITORING_DATE_ADJUST_FCT``:
The function to use to convert system locale date to user date.
For example:

    lambda request: request.user.get_locale_date
