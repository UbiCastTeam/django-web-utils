"""
Daemon base class
Useful to create daemons which can use Django easily.
"""
import argparse
import datetime
import importlib.util
import logging
import logging.config
import os
import socket
import subprocess
import sys
import traceback
from pathlib import Path

from django_web_utils.daemon.daemonization import daemonize

logger = logging.getLogger('djwutils.daemon.base')


class BaseDaemon:
    """
    Class to initialize daemons.

    To create a daemon, just create a class which inherits
    from this one and implement the run function.

    Log file will be located in `LOG_DIR/<daemon_file_name>.log`.
    PID file is located in `PID_DIR/<daemon_file_name>.pid`.
    """

    CONF_DIR = Path('/tmp/djwutils-daemon')
    LOG_DIR = Path('/tmp/djwutils-daemon')
    PID_DIR = Path('/tmp/djwutils-daemon')
    WORK_DIR = Path('/')
    # Dir to append in `sys.path`. Ignored if set to `None`.
    SERVER_DIR = None
    # Django settings module (for example: `'myproject.settings'`). Django is not loaded if set to `None`.
    SETTINGS_MODULE = None

    DEFAULTS = dict(LOGGING_LEVEL='INFO')

    def __init__(self, args=None):
        # Set env
        # get daemon script path before changing dir
        self.daemon_path = Path.cwd() / sys.argv[0]
        os.environ['LANG'] = 'C.UTF-8'
        os.environ['LC_ALL'] = 'C.UTF-8'
        os.chdir(self.WORK_DIR)

        # Get config
        self.config = {}
        self.load_config()

        # Parse args
        parser = argparse.ArgumentParser(
            description=(self.__class__.__doc__ or 'Daemon').strip(),
            formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument(
            '-f', '--foreground', action='store_true',
            help='Launch daemon in current thread and not in background. Enabling this will set the log output ot standard output.')
        parser.add_argument(
            '-s', '--simultaneous', action='store_true',
            help='Allow simultaneous execution.')
        parser.add_argument(
            '-l', '--log', action='store_true',
            help='Force log to file and not the standard output.')
        parser.add_argument(
            'action', choices=['start', 'stop', 'restart', 'clear_log'],
            help='Action to run.')
        parser.add_argument(
            'extra', nargs=argparse.REMAINDER,
            help='Extra arguments for the action.')
        args = parser.parse_args(args)

        self._should_daemonize = not args.foreground
        self._simultaneous = args.simultaneous
        self._log_in_file = self._should_daemonize or args.log
        self._extra_args = args.extra

        # Run command
        try:
            self._run_command(args.action)
        except Exception:
            self._exit_with_error('Error when initializing base daemon.')

    def run(self, *args):
        msg = f'Function "run" is not implemented in daemon "{self.get_name()}".'
        logger.error(msg)
        raise NotImplementedError(msg)

    @classmethod
    def get_name(cls):
        if not hasattr(cls, '_file_name'):
            cls._file_name = Path(sys.modules[cls.__module__].__file__).name[:-3]
        return cls._file_name

    @classmethod
    def get_pid_path(cls):
        if not hasattr(cls, '_pid_path'):
            cls._pid_path = cls.PID_DIR / f'{cls.get_name()}.pid'
        return cls._pid_path

    @classmethod
    def get_log_path(cls):
        if not hasattr(cls, '_log_path'):
            cls._log_path = cls.LOG_DIR / f'{cls.get_name()}.log'
        return cls._log_path

    @classmethod
    def get_conf_path(cls):
        if not hasattr(cls, '_conf_path'):
            cls._conf_path = cls.CONF_DIR / f'{cls.get_name()}.py'
        return cls._conf_path

    def get_config(self, option, default=None):
        return self.config.get(option, default)

    def load_config(self):
        self.config = dict(self.DEFAULTS)
        if not self.get_conf_path().exists():
            return False
        spec = importlib.util.spec_from_file_location('cfg', str(self.get_conf_path()))
        cfg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cfg)
        for key in list(cfg.__dict__.keys()):
            if not key.startswith('__'):
                self.config[key] = cfg.__dict__[key]
        return True

    def _run_command(self, command):
        if command in ('restart', 'stop'):
            # check if daemon is already launched
            pid = self._look_for_existing_process()
            if pid:
                print(f'Stopping {self.get_name()}... ', file=sys.stdout)
                # kill process and its children
                p = subprocess.run(f'kill -- -$(ps hopgid {pid} | sed \'s/^ *//g\')', shell=True)
                if p.returncode != 0:
                    print(f'Cannot stop {self.get_name()}.', file=sys.stderr)
                    self.exit(129)
                self.get_pid_path().unlink(missing_ok=True)
                print(f'{self.get_name()} stopped.', file=sys.stdout)
            else:
                print(f'{self.get_name()} is not running.', file=sys.stdout)
        elif command == 'start':
            # check if daemon is already launched
            pid = self._look_for_existing_process()
            if pid and not self._simultaneous:
                print(f'{self.get_name()} is already running.', file=sys.stderr)
                self.exit(130)
        elif command == 'clear_log':
            if self.get_log_path().exists():
                self.get_log_path().write_text('')
            print(f'Log file cleared for {self.get_name()}.', file=sys.stdout)
        else:
            print(self.USAGE % self.daemon_path, file=sys.stderr)
            self.exit(128)

        if command in ('start', 'restart'):
            print(f'Starting {self.get_name()}...', file=sys.stdout)
            sys.stdout.flush()
            try:
                if self._should_daemonize:
                    daemonize(redirect_to=str(self.get_log_path()) if self._log_in_file else None)
                if not self._simultaneous:
                    self._write_pid()
                self._setup_sys_path()
                if self.SETTINGS_MODULE:
                    self._setup_django()
                self._setup_logging()
            except Exception:
                self._exit_with_error(f'Error when starting {self.get_name()}.', code=134)
        else:
            self.exit(0)

    def _setup_sys_path(self):
        if self.SERVER_DIR and self.SERVER_DIR.is_dir():
            # Remove current file directory from sys.path to avoid incorrect imports
            if '.' in sys.path:
                sys.path.remove('.')
            if '' in sys.path:
                sys.path.remove('')
            if str(self.SERVER_DIR) not in sys.path:
                sys.path.append(str(self.SERVER_DIR))

    def _setup_django(self):
        # set django settings, so that django modules can be imported
        if os.environ.get('DJANGO_SETTINGS_MODULE') != self.SETTINGS_MODULE:
            # if the DJANGO_SETTINGS_MODULE is already set,
            # the logging will not be changed to avoid possible
            # impact on the server which called this script.
            os.environ['DJANGO_SETTINGS_MODULE'] = self.SETTINGS_MODULE
        import django
        django.setup()

    def _setup_logging(self):
        try:
            self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print('Cannot create log directory %s: %s' % (self.LOG_DIR, e), file=sys.stderr)
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
        """
        Check if the daemon is already launched and return its pid if it is, else None
        """
        try:
            pid = int(self.get_pid_path().read_text())
        except (OSError, ValueError):
            return None
        p = subprocess.run(
            ['ps', '-p', str(pid), '-f'], encoding='utf-8',
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if self.get_name() not in p.stdout:
            self.get_pid_path().unlink(missing_ok=True)
            pid = None
        return pid

    def _write_pid(self):
        """
        Write pid into pidfile
        """
        pid_path = self.get_pid_path()
        try:
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(str(os.getpid()))
        except OSError as e:
            print(f'Cannot write pid into pidfile {pid_path}', file=sys.stderr)
            raise e
        else:
            self._pid_written = True

    def _exit_with_error(self, msg=None, code=-1):
        if self._log_in_file:
            try:
                with open(self.get_log_path(), 'a') as fo:
                    fo.write('Date: %s (local time).\n' % datetime.datetime.now())
                    if msg:
                        fo.write(msg + '\n')
                    fo.write(traceback.format_exc())
            except Exception as err:
                print(err, file=sys.stderr)
        try:
            self.send_error_email(msg, tb=True)
        except Exception as e:
            print(e, file=sys.stderr)
        self.exit(code)

    def start(self, args=None):
        args = self._extra_args if args is None else args
        # Run daemon
        try:
            if args:
                logger.info('Starting daemon %s with arguments: %s.', self.get_name(), args)
            else:
                logger.info('Starting daemon %s without arguments.', self.get_name())
            self.run(*args)
        except Exception:
            self._exit_with_error(f'Error when running {self.get_name()}.', code=140)
        except KeyboardInterrupt:
            logger.info('Daemon %s interrupted by KeyboardInterrupt', self.get_name())
            self.exit(141)
        self.exit(0)

    def restart(self, args=None):
        # function to restart daemon itself
        args = self._extra_args if args is None else args
        # remove pid file to avoid kill command when restarting
        try:
            self.get_pid_path().unlink(missing_ok=True)
        except OSError as err:
            logger.error('Error when trying to remove pid file.\n    Error: %s\nAs the pid file cannot be removed, the restart will probably kill daemon itself.', err)

        # execute restart command (if the daemon was not daemonized it will become so)
        cmd = ['python3', str(self.daemon_path), 'restart']
        if args:
            cmd.extend(args)
        p = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        out = p.stdout.strip()
        err = p.stderr.strip()
        logger.debug('Restarting daemon.\n    Command: %s\n    Stdout: %s\n    Stderr: %s', cmd, out, err)
        if p.returncode != 0:
            logger.error('Error when restarting daemon:\n    %s', err)
        sys.exit(0)

    def exit(self, code=0):
        if getattr(self, '_pid_written', False):
            self.get_pid_path().unlink(missing_ok=True)
        logger.debug('Daemon %s ended (return code: %s).', self.get_name(), code)
        sys.exit(code)

    def send_error_email(self, msg, tb=False, recipients=None):
        logger.error('%s\n%s', msg, traceback.format_exc() if tb else msg)
        if not self.SETTINGS_MODULE:
            self._setup_django()
        from django_web_utils import emails_utils
        emails_utils.send_error_report_emails(
            title='%s - %s' % (self.get_name(), socket.gethostname()),
            error='%s\n\nThe daemon was started with the following arguments:\n%s' % (msg, sys.argv),
            recipients=recipients,
        )
