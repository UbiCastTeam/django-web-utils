#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging

logger = logging.getLogger('djwutils.logging_utils')


def get_generic_logging_config(logs_dir, debug):
    os.makedirs(logs_dir, exist_ok=True)

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
                'filename': os.path.join(logs_dir, 'django.log'),
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
        warnings.simplefilter('always')
        warnings.simplefilter('ignore', ResourceWarning)  # Hide unclosed files warnings
        os.environ['PYTHONWARNINGS'] = 'always'  # Also affect subprocesses
    else:
        logging.captureWarnings(False)
    return logging_config


class IgnoreTimeoutErrors(logging.Filter):

    def filter(self, record):
        '''
        Ignore WSGI connection errors (UnreadablePostError)
        Like:
            UnreadablePostError: error during read(---) on wsgi.input
        '''
        try:
            err_class = record.exc_info[0].__name__
        except Exception as e:
            logger.error('Failed to parse error type: %s', e)
            return True
        else:
            return err_class != 'UnreadablePostError'


class IgnoreDatabaseErrors(logging.Filter):

    def filter(self, record):
        '''
        Ignore database connection errors (OperationalError)
        Like:
            OperationalError: could not connect to server: Connection refused
            OperationalError: server closed the connection unexpectedly
            OperationalError: SSL SYSCALL error: EOF detected
        '''
        try:
            err_class = record.exc_info[0].__name__
        except Exception as e:
            logger.error('Failed to parse error type: %s', e)
            return True
        else:
            return err_class != 'OperationalError'


class IgnoreNoSpaceLeftErrors(logging.Filter):

    def filter(self, record):
        '''
        Ignore no space left errors (OSError)
        Like:
            OSError [Errno 28] No space left on device: ...
        '''
        try:
            err_class = record.exc_info[0].__name__
            if err_class == 'OSError':
                import errno
                error = record.exc_info[1]
                return error.errno != errno.ENOSPC
            return True
        except Exception as e:
            logger.error('Failed to parse error type: %s', e)
            return True
