"""
Daemon base class
Useful to create daemons which can use Django easily.
"""
import argparse
import datetime
import logging
import logging.config
import os
from pathlib import Path
import subprocess
import sys
import traceback

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

    LOG_DIR = Path('/tmp/djwutils-daemon')
    PID_DIR = Path('/tmp/djwutils-daemon')
    # Django settings module (for example: `'myproject.settings'`). Django is not loaded if set to `None`.
    SETTINGS_MODULE = None

    DEFAULTS = dict(LOGGING_LEVEL='INFO')

    def __init__(self, args=None):
        # Set env
        # Get daemon script path before changing dir
        self.daemon_path = Path.cwd() / sys.argv[0]
        os.environ['LANG'] = 'C.UTF-8'
        os.environ['LC_ALL'] = 'C.UTF-8'
        os.chdir(self.daemon_path.parent)

        # Parse args
        parser = argparse.ArgumentParser(
            description=(self.__class__.__doc__ or 'Daemon').strip(),
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            '-f', '--foreground', action='store_true',
            help='Launch daemon in current thread and not in background. '
                 'Enabling this will set the log output ot standard output.'
        )
        parser.add_argument(
            '-s', '--simultaneous', action='store_true',
            help='Allow simultaneous execution.'
        )
        parser.add_argument(
            '-l', '--log', action='store_true',
            help='Force log to file and not the standard output.'
        )
        parser.add_argument(
            '-v', '--verbose', action='store_true',
            help='Set logging level to debug.'
        )
        parser.add_argument(
            'action', choices=['start', 'stop', 'restart', 'clear_log'],
            help='Action to run.'
        )
        parser.add_argument(
            'extra', nargs=argparse.REMAINDER,
            help='Extra arguments for the action.'
        )
        args = parser.parse_args(args)

        self._should_daemonize = not args.foreground
        self._simultaneous = args.simultaneous
        self._log_in_file = self._should_daemonize or args.log
        self._logging_available = False
        self._verbose = args.verbose
        self._extra_args = args.extra

        # Run command
        try:
            self._run_command(args.action)
        except Exception as err:
            self._log_error(err)
            self.exit(134)

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

    def _run_command(self, command):
        if command in ('restart', 'stop'):
            # Check if daemon is already launched
            pid = self._look_for_existing_process()
            if pid:
                print(f'Stopping {self.get_name()}... ', file=sys.stdout)
                # Kill process and its children
                p = subprocess.run(f"kill -- -$(ps hopgid {pid} | sed 's/^ *//g')", shell=True)
                if p.returncode != 0:
                    print(f'Cannot stop {self.get_name()}.', file=sys.stderr)
                    self.exit(129)
                self.get_pid_path().unlink(missing_ok=True)
                print(f'{self.get_name()} stopped.', file=sys.stdout)
            else:
                print(f'{self.get_name()} is not running.', file=sys.stdout)
        elif command == 'start':
            # Check if daemon is already launched
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
            if self._should_daemonize:
                daemonize(redirect_to=str(self.get_log_path()) if self._log_in_file else None)
            if not self._simultaneous:
                self._write_pid()
            if self.SETTINGS_MODULE:
                self._setup_django()
            self._setup_logging()
        else:
            self.exit(0)

    def _setup_django(self):
        # Set django settings, so that django modules can be imported
        if os.environ.get('DJANGO_SETTINGS_MODULE') != self.SETTINGS_MODULE:
            # If the DJANGO_SETTINGS_MODULE is already set,
            # the logging will not be changed to avoid possible
            # impact on the server which called this script.
            os.environ['DJANGO_SETTINGS_MODULE'] = self.SETTINGS_MODULE
        import django
        django.setup()

    def _setup_logging(self):
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

        loggers = logging.Logger.manager.loggerDict

        # Configure logging and disable all existing loggers
        logging_conf = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '%(asctime)s.%(msecs)03d pid:%(process)d %(name)s %(levelname)s %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S',
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
                'level': 'DEBUG' if self._verbose else 'INFO',
                'propagate': False,
            }
        }
        logging.config.dictConfig(logging_conf)
        if self._log_in_file:
            logging.captureWarnings(False)

        # Reset all loggers config
        for lg in loggers.values():
            lg.handlers = []
            lg.propagate = True

        self._logging_available = True
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
        Write pid into pid file
        """
        pid_path = self.get_pid_path()
        try:
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(str(os.getpid()))
        except OSError:
            print(f'Cannot write pid into pidfile {pid_path}', file=sys.stderr)
            raise
        else:
            self._pid_written = True

    def _clear_pid(self):
        """
        Remove pid file if written
        """
        if not getattr(self, '_pid_written', False):
            return
        pid_path = self.get_pid_path()
        try:
            pid_path.unlink(missing_ok=True)
        except OSError as err:
            logger.warning(
                'Error when trying to remove the pid file "%s": %s\n'
                '  As the pid file cannot be removed, the restart will probably kill the daemon itself.',
                pid_path, err
            )

    def _log_error(self, err):
        if self._logging_available:
            logger.error(
                'Error when running %s: %s\n%s',
                self.get_name(), err, traceback.format_exc(),
                exc_info=err
            )
        elif self._log_in_file:
            try:
                with open(self.get_log_path(), 'a') as fo:
                    fo.write(
                        f'Date: {datetime.datetime.now()} (local time): '
                        f'Error when running {self.get_name()}: {err}\n'
                        f'{traceback.format_exc()}\n'
                    )
            except OSError as err:
                print(str(err), file=sys.stderr)
        else:
            print(str(err), file=sys.stderr)

    def start(self, args=None):
        args = self._extra_args if args is None else args
        try:
            if args:
                logger.info('Starting daemon %s with arguments: %s.', self.get_name(), args)
            else:
                logger.info('Starting daemon %s without arguments.', self.get_name())
            self.run(*args)
        except Exception as err:
            self._log_error(err)
            self.exit(140)
        except KeyboardInterrupt:
            logger.info('Daemon %s interrupted by KeyboardInterrupt', self.get_name())
            self.exit(141)
        self.exit(0)

    def restart(self, args=None):
        # Function to restart daemon itself
        args = self._extra_args if args is None else args
        # Remove pid file to avoid kill command when restarting
        self._clear_pid()

        # Execute restart command (if the daemon was not daemonized it will become so)
        cmd = ['python3', str(self.daemon_path), 'restart']
        if args:
            cmd.extend(args)
        p = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8'
        )
        out = p.stdout.strip()
        logger.debug('Restarting daemon %s:\n  Command: %s\n  Out: %s', self.get_name(), cmd, out)
        if p.returncode != 0:
            logger.error('Error when restarting daemon %s:\n  %s', self.get_name(), out)
        sys.exit(0)

    def exit(self, code=0):
        self._clear_pid()
        logger.debug('Daemon %s ended (return code: %s).', self.get_name(), code)
        sys.exit(code)
