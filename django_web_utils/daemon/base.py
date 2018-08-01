#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Daemon base class
To create daemon (which can use django easily).
'''
import os
import sys
import subprocess
import socket
import imp
import datetime
import traceback
import logging
import logging.config
# django_web_utils
from django_web_utils.daemon.daemonization import daemonize

logger = logging.getLogger('djwutils.daemon.base')


class BaseDaemon(object):
    '''
    Class to initialize daemons.

    To create a daemon, just create a class which
    herits from this one and implement the run function.

    Log file will be located in LOG_DIR/<daemon_file_name>.log
    PID file is located in PID_DIR/<daemon_file_name>.pid
    '''

    CONF_DIR = '/tmp/djwutils-daemon'
    LOG_DIR = '/tmp/djwutils-daemon'
    PID_DIR = '/tmp/djwutils-daemon'
    SERVER_DIR = None  # Dir to append in sys.path
    SETTINGS_MODULE = 'settings'

    USAGE = '''USAGE: %s start|restart|stop|clear_log [-n] [-f] [*options]
    -n: launch daemon in current thread and not in background
    -s: allow simultaneous execution
    -f: force log to use a file and not the standard output'''
    NEED_DJANGO = True
    DEFAULTS = dict(LOGGING_LEVEL='INFO')

    def __init__(self, argv=None):
        object.__init__(self)
        try:
            # Set env
            # get daemon script path before changing dir
            self.daemon_path = os.path.join(os.getcwd(), sys.argv[0])
            os.environ['LANG'] = 'C'
            os.chdir('/')  # to avoid wrong imports
            self._django_setup_done = False
            # Get config
            self.config = dict()
            self.load_config()
            # Parse args
            args = list(argv) if argv else list()
            self._should_daemonize = True
            if '-n' in args:
                self._should_daemonize = False
                args.remove('-n')
            self._simultaneous = False
            if '-s' in args:
                self._simultaneous = True
                args.remove('-s')
            self._log_in_file = self._should_daemonize
            if '-f' in args:
                self._log_in_file = True
                args.remove('-f')
            valid_commands = ('start', 'restart', 'stop', 'clear_log')
            if len(args) > 0 and args[0] not in valid_commands:
                args.pop(0)  # this script path
            self._command = None
            if len(args) > 0 and args[0] in valid_commands:
                self._command = args.pop(0)
            self._cleaned_args = args
            # Run command
            self._run_command()
        except Exception:
            self._exit_with_error('Error when initializing base daemon.')

    def run(self, *args):
        msg = 'Function "run" is not implemented in daemon "%s"' % self.get_name()
        logger.error(msg)
        raise NotImplementedError(msg)

    @classmethod
    def get_name(cls):
        if not hasattr(cls, '_file_name'):
            cls._file_name = os.path.basename(sys.modules[cls.__module__].__file__)[:-3]
        return cls._file_name

    @classmethod
    def get_pid_path(cls):
        if not hasattr(cls, '_pid_path'):
            cls._pid_path = os.path.join(cls.PID_DIR, '%s.pid' % cls.get_name())
        return cls._pid_path

    @classmethod
    def get_log_path(cls):
        if not hasattr(cls, '_log_path'):
            cls._log_path = os.path.join(cls.LOG_DIR, '%s.log' % cls.get_name())
        return cls._log_path

    @classmethod
    def get_conf_path(cls):
        if not hasattr(cls, '_conf_path'):
            cls._conf_path = os.path.join(cls.CONF_DIR, '%s.py' % cls.get_name())
        return cls._conf_path

    def get_config(self, option, default=None):
        return self.config.get(option, default)

    def load_config(self):
        self.config = dict(self.DEFAULTS)
        if not os.path.exists(self.get_conf_path()):
            return False
        cfg = imp.load_source('cfg', self.get_conf_path())
        for key in list(cfg.__dict__.keys()):
            if not key.startswith('__'):
                self.config[key] = cfg.__dict__[key]
        return True

    def save_config(self):
        # get modified keys
        content = ''
        for key, value in self.config.items():
            if value != self.DEFAULTS.get(key):
                content += key + ' = ' + self.config[key] + '\n'
        try:
            if not os.path.exists(os.path.dirname(self.get_conf_path())):
                os.makedirs(os.path.dirname(self.get_conf_path()))
            with open(self.get_conf_path(), 'w+') as fo:
                fo.write(content)
        except Exception:
            return False
        return True

    def _run_command(self):
        if self._command in ('restart', 'stop'):
            # check if daemon is already launched
            pid = self._look_for_existing_process()
            if pid:
                print('Stopping %s... ' % self.get_name(), file=sys.stdout)
                # kill process and its children
                result = os.system('kill -- -$(ps hopgid %s | sed \'s/^ *//g\')' % pid)
                if result != 0:
                    print('Cannot stop %s' % self.get_name(), file=sys.stderr)
                    self.exit(129)
                os.remove(self.get_pid_path())
                print('%s stopped' % self.get_name(), file=sys.stdout)
            else:
                print('%s is not running' % self.get_name(), file=sys.stdout)
        elif self._command == 'start':
            # check if daemon is already launched
            pid = self._look_for_existing_process()
            if pid and not self._simultaneous:
                print('%s is already running' % self.get_name(), file=sys.stderr)
                self.exit(130)
        elif self._command == 'clear_log':
            if os.path.exists(self.get_log_path()):
                with open(self.get_log_path(), 'w') as fo:
                    fo.write('')
            print('Log file cleared for %s.' % self.get_name(), file=sys.stdout)
        else:
            print(self.USAGE % self.daemon_path, file=sys.stderr)
            self.exit(128)

        if self._command in ('start', 'restart'):
            print('Starting %s...' % self.get_name(), file=sys.stdout)
            sys.stdout.flush()
            try:
                if self._should_daemonize:
                    daemonize(redirect_to=self.get_log_path() if self._log_in_file else None)
                if not self._simultaneous:
                    self._write_pid()
                if self.NEED_DJANGO and self.SETTINGS_MODULE:
                    self._setup_django()
                self._setup_logging()
            except Exception:
                self._exit_with_error('Error when starting %s.' % self.get_name(), code=134)
        else:
            self.exit(0)

    def _setup_django(self):
        if self._django_setup_done:
            return
        # set django settings, so that django modules can be imported
        if self.SERVER_DIR and os.path.isdir(self.SERVER_DIR) and self.SERVER_DIR not in sys.path:
            sys.path.append(self.SERVER_DIR)
        if not os.environ.get('DJANGO_SETTINGS_MODULE') or os.environ.get('DJANGO_SETTINGS_MODULE') != self.SETTINGS_MODULE:
            # if the DJANGO_SETTINGS_MODULE is already set,
            # the logging will not be changed to avoid possible
            # impact on the server which called this script.
            os.environ['DJANGO_SETTINGS_MODULE'] = self.SETTINGS_MODULE
        import django
        try:
            django.setup()
        except Exception as e:
            logger.warning('Django setup failed: %s', e)
        self._django_setup_done = True

    def _setup_logging(self):
        if not os.path.exists(self.LOG_DIR):
            try:
                os.makedirs(self.LOG_DIR)
            except Exception:
                pass
        if not os.path.isdir(self.LOG_DIR):
            print('Cannot create log directory %s' % self.LOG_DIR, file=sys.stderr)
            self.exit(131)

        loggers = logging.Logger.manager.loggerDict
        if list(loggers.keys()):
            logger.debug('Resetting loggers.')

        # configure logging and disable all existing loggers
        LOGGING_CONF = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'verbose',
                    'stream': 'ext://sys.stdout',
                },
                'log_file': {
                    'class': 'logging.FileHandler',
                    'formatter': 'verbose',
                    'filename': self.get_log_path(),
                },
            },
            'loggers': {
                'django': {
                    'level': 'WARNING',
                },
                'urllib3': {
                    'level': 'ERROR',
                },
                'requests.packages.urllib3': {
                    'level': 'ERROR',
                },
            },
            'root': {
                'handlers': ['log_file' if self._log_in_file else 'console'],
                'level': self.config.get('LOGGING_LEVEL', 'INFO'),
                'propagate': False,
            }
        }
        logging.config.dictConfig(LOGGING_CONF)
        if self._log_in_file:
            logging.captureWarnings(False)
        # reset all loggers config
        for key, lg in loggers.items():
            lg.handlers = []
            lg.propagate = 1
        logger.debug('Logging configured.')

    def _look_for_existing_process(self):
        '''check if the daemon is already launched and return its pid if it is, else None'''
        pid = None
        try:
            with open(self.get_pid_path(), 'r') as fo:
                pid = int(fo.read())
        except Exception:
            pass
        else:
            mod = sys.modules[self.__class__.__module__]
            if pid and os.system('ps -p %s -f | grep "%s" >/dev/null' % (pid, os.path.basename(mod.__file__))) != 0:
                os.remove(self.get_pid_path())
                pid = None
        return pid

    def _write_pid(self):
        '''write pid into pidfile'''
        pid_dir = os.path.dirname(self.get_pid_path())
        try:
            if not os.path.exists(pid_dir):
                os.makedirs(pid_dir)
            with open(self.get_pid_path(), 'w+') as fo:
                fo.write(str(os.getpid()))
        except Exception as e:
            print('Cannot write pid into pidfile %s' % self.get_pid_path(), file=sys.stderr)
            raise e
        else:
            self._pid_written = True

    def _exit_with_error(self, msg=None, code=-1):
        if self._should_daemonize:
            # sys.stderr is not visible if daemonized
            try:
                with open('/tmp/daemon-error_%s' % self.get_name(), 'w+') as fo:
                    fo.write('Date: %s (local time).\n\n' % datetime.datetime.now())
                    if msg:
                        fo.write(msg + '\n\n')
                    fo.write(traceback.format_exc())
            except Exception as e:
                print(e, file=sys.stderr)
        try:
            self.send_error_email(msg, tb=True)
        except Exception as e:
            print(e, file=sys.stderr)
        self.exit(code)

    def start(self, argv=None):
        argv = self._cleaned_args if not argv else argv
        # Run daemon
        try:
            if argv:
                logger.info('Starting daemon %s with arguments: "%s".', self.get_name(), '" "'.join(argv))
            else:
                logger.info('Starting daemon %s without arguments.', self.get_name())
            self.run(*argv)
        except Exception:
            self._exit_with_error('Error when running %s.' % self.get_name(), code=140)
        except KeyboardInterrupt:
            logger.info('%s interrupted by KeyboardInterrupt', self.get_name())
            self.exit(141)
        self.exit(0)

    def restart(self, argv=None):
        # function to restart daemon itself
        argv = self._cleaned_args if not argv else argv
        # remove pid file to avoid kill command when restarting
        try:
            os.remove(self.get_pid_path())
        except Exception as e:
            logger.error('Error when trying to remove pid file.\n    Error: %s\nAs the pid file cannot be removed, the restart will probably kill daemon itself.', e)

        # execute restart command (if the daemon was not daemonized it will become so)
        cmd = 'python3 %s restart %s' % (self.daemon_path, ' '.join(argv))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        out = out.decode('utf-8') if out else ''
        err = err.decode('utf-8') if err else ''
        logger.debug('Restarting daemon.\n    Command: %s\n    Stdout: %s\n    Stderr: %s', cmd, out, err)
        if p.returncode != 0:
            logger.error('Error when restarting daemon:\n    %s', err)
        sys.exit(0)

    def exit(self, code=0):
        if getattr(self, '_pid_written', False):
            try:
                os.remove(self.get_pid_path())
            except Exception:
                pass
        logger.debug('Daemon %s ended (return code: %s).\n', self.get_name(), code)
        sys.exit(code)

    def send_error_email(self, msg, tb=False, recipients=None):
        logger.error('%s\n%s', msg, traceback.format_exc() if tb else msg)
        if not self.NEED_DJANGO:
            self._setup_django()
        from django_web_utils import emails_utils
        emails_utils.send_error_report_emails(
            title='%s - %s' % (self.get_name(), socket.gethostname()),
            error='%s\n\nThe daemon was started with the following arguments:\n%s' % (msg, sys.argv),
            recipients=recipients,
        )
