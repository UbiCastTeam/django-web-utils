# Restarter Django app

This app allows you to restart a service (Django site) from the service itself.


## Installation

Add in your `settings`:

``` python
INSTALLED_APPS = [
    # [...]
    'django_web_utils',  # to get translations of utils files
    'django_web_utils.restarter',
    # [...]
]
```

Add in your `urls.py`:

``` python
urlpatterns = [
    # [...]
    re_path(r'^restart/', include(('django_web_utils.restarter.urls', 'restarter'), namespace='restarter')),
    # [...]
]
```


## Mandatory settings

`RESTART_COMMAND`:
The command to restart the service. Can be a list or a string. The value will be called with `subprocess.run` so a list is recommended.
For example:
`RESTART_COMMAND = ['systemctl', 'restart', 'myservice']`


## Optional settings

`FRONT_SERVERS_IPS`:
List of IP adresses of all servers hosting the same service. If only one server is hosting the service, no value has to be defined.
For example:
`FRONT_SERVERS_IPS = ['192.168.24.5', '192.168.24.6']`
Default:
`FRONT_SERVERS_IPS = ['127.0.0.1']`
