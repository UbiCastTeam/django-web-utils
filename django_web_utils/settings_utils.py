#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os


def get_generic_logging_config(tmp_dir, debug):
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    if os.environ.get('DJANGO_LOGGING') == 'none':
        return {}

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                '()': 'django.utils.log.ServerFormatter',
                'format': '%(asctime)s %(module)s %(levelname)s %(message)s',
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler',
            },
            'django_log_file': {
                'class': 'logging.FileHandler',
                'formatter': 'verbose',
                'filename': os.path.join(tmp_dir, 'django.log'),
            },
        },
        'loggers': {
            'django.request': {
                'handlers': ['mail_admins'],
                'level': 'ERROR',
                'propagate': True,
            },
        },
        'root': {
            'handlers': ['django_log_file'],
            'level': 'INFO',
            'propagate': False,
        },
    }

    if debug:
        logging_config['root']['level'] = 'DEBUG'
        logging_config['root']['handlers'] = ['console']
        import warnings
        warnings.simplefilter('always', DeprecationWarning)
    else:
        import logging
        logging.captureWarnings(False)
    return logging_config
