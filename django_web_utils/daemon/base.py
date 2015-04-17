#!/usr/bin/env python
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
logger = logging.getLogger('djwutils.daemon.base')
# django_web_utils
from django_web_utils.daemon.daemonization import daemonize


class BaseDaemon(object):
    '''
    Class to initialize daemons.
    
    To create a daemon, just create a class which
    herits from this one and implement the run function.
    Also, you will have to set the var DAEMON_NAME with the name of the file.
    
    Log file will be located in LOG_DIR/<daemon_name>.log
    PID file is located in PID_DIR/<daemon_name>.pid
    '''
    
    SERVER_DIR = os.path.expanduser('~/server')
    LOG_DIR = os.path.join(SERVER_DIR, 'logs')
    CONF_DIR = os.path.join(SERVER_DIR, 'conf')
    PID_DIR = os.path.join(SERVER_DIR, 'temporary')
    ALLOWED_COMMANDS = ('start', 'restart', 'stop', 'clear_log')
    SETTINGS_MODULE = 'settings'
    
    USAGE = '''USAGE: %s start|restart|stop|clear_log [-n] [-f] [*options]
    -n: launch daemon in current thread and not in background
    -s: allow simultaneous execution
    -f: force log to use a file and not the standard output'''
    DAEMON_NAME = 'unamed_daemon'
    NEED_GOBJECT = False
    NEED_DJANGO = True
    DEFAULTS = dict(LOGGING_LEVEL='INFO')
    
    def __init__(self, argv=None):
        object.__init__(self)
        try:
            # get daemon script path before changing dir
            self.daemon_path = os.path.join(os.getcwd(), sys.argv[0])
            self.usage = self.USAGE % self.daemon_path
            
            os.environ['LANG'] = 'C'
            os.chdir('/')  # to avoid wrong imports
            
            self._should_daemonize = False
            self._simultaneous = False
            self._log_in_file = False
            self._command = None
            self._cleaned_args = list()
            self._parse_args(argv)
            
            self._pid_written = False
            self._pid_file_path = os.path.join(self.PID_DIR, '%s.pid' % self.DAEMON_NAME)
            self._log_file_path = os.path.join(self.LOG_DIR, '%s.log' % self.DAEMON_NAME)
            
            self.config = dict()
            self.config_file = os.path.join(self.CONF_DIR, '%s.py' % self.DAEMON_NAME)
            self.load_config()
            
            self._run_command()
        except Exception:
            msg = 'Error when initializing base daemon.'
            self._dump_error_in_tmp(msg)
            print >>sys.stderr, '%s\n%s' % (msg, traceback.format_exc())
            self.send_error_email(msg, tb=True)
            sys.exit(-1)
    
    def run(self, *args):
        msg = 'Function "run" is not implemented in daemon "%s"' % self.DAEMON_NAME
        logger.error(msg)
        raise NotImplementedError(msg)
    
    def get_config(self, option, default=None):
        return self.config.get(option, default)
    
    def load_config(self):
        self.config = dict(self.DEFAULTS)
        if not os.path.exists(self.config_file):
            return False
        cfg = imp.load_source('cfg', self.config_file)
        for key in cfg.__dict__.keys():
            if not key.startswith('__'):
                self.config[key] = cfg.__dict__[key]
        return True
    
    def save_config(self):
        if not os.path.exists(os.path.dirname(self.config_file)):
            try:
                os.makedirs(os.path.dirname(self.config_file))
            except Exception:
                return False
        
        try:
            conf_file = open(self.config_file, 'w+')
        except Exception:
            return False
        
        # get modified keys
        content = u''
        for key, value in self.config.iteritems():
            if value != self.DEFAULTS.get(key):
                content += key + u' = ' + self.config[key] + u'\n'
        
        try:
            conf_file.write(content)
        except Exception:
            conf_file.close()
            return False
        else:
            conf_file.close()
            return True
    
    def _parse_args(self, argv=None):
        if argv:
            args = list(argv)
        else:
            args = list(sys.argv)
        
        daemonize = True
        if '-n' in args:
            daemonize = False
            args.remove('-n')
        self._should_daemonize = daemonize
        
        simultaneous = False
        if '-s' in args:
            simultaneous = True
            args.remove('-s')
        self._simultaneous = simultaneous
        
        log_in_file = daemonize
        if '-f' in args:
            log_in_file = True
            args.remove('-f')
        self._log_in_file = log_in_file
        
        if len(args) > 0 and args[0] not in self.ALLOWED_COMMANDS:
            args.pop(0)  # this script path
        
        command = None
        if len(args) > 0 and args[0] in self.ALLOWED_COMMANDS:
            command = args.pop(0)
        self._command = command
        
        self._cleaned_args = args
    
    def _run_command(self):
        if self._command in ('restart', 'stop'):
            # check if daemon is already launched
            pid = self._look_for_existing_process()
            if pid:
                print >>sys.stdout, 'Stopping %s... ' % self.DAEMON_NAME
                # kill process and its children
                result = os.system('kill -- -$(ps hopgid %s | sed \'s/^ *//g\')' % pid)
                if result != 0:
                    print >>sys.stderr, 'Cannot stop %s' % self.DAEMON_NAME
                    self.exit(129)
                os.remove(self._pid_file_path)
                print >>sys.stdout, '%s stopped' % self.DAEMON_NAME
            else:
                print >>sys.stdout, '%s is not running' % self.DAEMON_NAME
        elif self._command == 'start':
            # check if daemon is already launched
            pid = self._look_for_existing_process()
            if pid and not self._simultaneous:
                print >>sys.stderr, '%s is already running' % self.DAEMON_NAME
                self.exit(130)
        elif self._command == 'clear_log':
            if os.path.exists(self._log_file_path):
                f = open(self._log_file_path, 'w')
                f.write('')
                f.close()
            print >>sys.stdout, 'Log file cleared for %s.' % self.DAEMON_NAME
        else:
            print >>sys.stderr, self.usage
            self.exit(128)
        
        if self._command in ('start', 'restart'):
            print >>sys.stdout, 'Starting %s...' % self.DAEMON_NAME
            try:
                if self._should_daemonize:
                    daemonize(redirect_to=self._log_file_path if self._log_in_file else None)
                if not self._simultaneous:
                    self._write_pid()
            except Exception:
                print >>sys.stderr, 'Error when starting %s:\n%s' % (self.DAEMON_NAME, traceback.format_exc())
                self.exit(134)
            try:
                if self.NEED_DJANGO and self.SETTINGS_MODULE:
                    self._setup_django()
                self._setup_logging()
            except Exception:
                msg = 'Error when starting %s.' % self.DAEMON_NAME
                self._dump_error_in_tmp(msg)
                print >>sys.stderr, '%s\n%s' % (msg, traceback.format_exc())
                self.send_error_email(msg, tb=True)
                self.exit(135)
        else:
            self.exit(0)
    
    def _setup_django(self):
        # set django settings, so that django modules can be imported
        sys.path.append(self.SERVER_DIR)
        if not os.environ.get('DJANGO_SETTINGS_MODULE') or os.environ.get('DJANGO_SETTINGS_MODULE') != self.SETTINGS_MODULE:
            # if the DJANGO_SETTINGS_MODULE is already set,
            # the logging will not be changed to avoid possible
            # impact on the server which called this script.
            os.environ['DJANGO_SETTINGS_MODULE'] = self.SETTINGS_MODULE
        import django
        try:
            django.setup()
        except Exception:
            pass
    
    def _setup_logging(self):
        if not os.path.exists(self.LOG_DIR):
            try:
                os.makedirs(self.LOG_DIR)
            except Exception:
                pass
        if not os.path.isdir(self.LOG_DIR):
            print >>sys.stderr, 'Cannot create log directory %s' % self.LOG_DIR
            self.exit(131)

        loggers = logging.Logger.manager.loggerDict
        if loggers.keys():
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
                    'filename': self._log_file_path,
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
        for key, lg in loggers.iteritems():
            lg.handlers = []
            lg.propagate = 1
        logger.debug('Logging configured.')
    
    def _look_for_existing_process(self):
        '''check if the daemon is already launched and return its pid if it is, else None'''
        pid = None
        try:
            pidfile = open(self._pid_file_path, 'r')
        except Exception:
            pass
        else:
            try:
                pid = int(pidfile.read())
            except Exception:
                pass
            finally:
                pidfile.close()
        if pid and os.system('ps -p %s > /dev/null' % pid) != 0:
            pid = None
        return pid

    def _write_pid(self):
        '''write pid into pidfile'''
        pid_dir = os.path.dirname(self._pid_file_path)
        if not os.path.exists(pid_dir):
            try:
                os.makedirs(pid_dir)
            except Exception:
                pass
        if not os.path.isdir(pid_dir):
            print >>sys.stderr, 'Cannot create pidfile directory %s' % pid_dir
            self.exit(132)
        
        try:
            pidfile = open(self._pid_file_path, 'w')
        except Exception:
            print >>sys.stderr, 'Cannot write pid into pidfile %s' % self._pid_file_path
            self.exit(133)
        else:
            pidfile.write('%s' % os.getpid())
            pidfile.close()
            self._pid_written = True
    
    def _dump_error_in_tmp(self, msg=None):
        if self._should_daemonize:
            # sys.stderr is not visible if daemonized
            fd = open('/tmp/daemon-error_%s' % self.DAEMON_NAME, 'w+')
            fd.write('Date: %s (local time).\n\n' % datetime.datetime.now())
            if msg:
                fd.write(msg + '\n\n')
            fd.write(traceback.format_exc())
            fd.close()

    def start(self, argv=None):
        argv = self._cleaned_args if not argv else argv
        # launch service
        try:
            if argv:
                logger.info('Staring daemon %s with arguments:\n    %s.' % (self.DAEMON_NAME, argv))
            else:
                logger.info('Staring daemon %s without arguments.' % self.DAEMON_NAME)
            self.run(*argv)
        except Exception:
            msg = 'Error when running %s.' % self.DAEMON_NAME
            self._dump_error_in_tmp(msg)
            logger.error('%s\n%s' % (msg, traceback.format_exc()))
            self.send_error_email(msg, tb=True)
            self.exit(140)
        except KeyboardInterrupt:
            logger.info('%s interrupted by KeyboardInterrupt' % (self.DAEMON_NAME))
            self.exit(141)
        
        # Gobject main loop
        if self.NEED_GOBJECT:
            import gobject
            #gobject.threads_init()
            ml = gobject.MainLoop()
            print >>sys.stdout, '%s started' % self.DAEMON_NAME
            try:
                ml.run()
            except Exception:
                msg = 'Daemon %s mainloop interrupted by error.' % self.DAEMON_NAME
                self._dump_error_in_tmp(msg)
                logger.error('%s\n%s' % (msg, traceback.format_exc()))
                self.send_error_email(msg, tb=True)
                self.exit(142)
            except KeyboardInterrupt:
                logger.info('Daemon %s mainloop interrupted by KeyboardInterrupt.' % (self.DAEMON_NAME))
                self.exit(143)
    
    def restart(self, argv=None):
        # function to restart daemon itself
        argv = self._cleaned_args if not argv else argv
        # remove pid file to avoid kill command when restarting
        try:
            os.remove(self._pid_file_path)
        except Exception, e:
            logger.error('Error when trying to remove pid file.\n    Error: %s\nAs the pid file cannot be removed, the restart will probably kill daemon itself.' % e)
        
        # execute restart command (if the daemon was not daemonized it will become so)
        cmd = 'python %s restart %s' % (self.daemon_path, ' '.join(argv))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        logger.debug('Restarting daemon.\n    Command: %s\n    Stdout: %s\n    Stderr: %s', cmd, out, err)
        if p.returncode != 0:
            logger.error('Error when restarting daemon:\n    %s' % err)
        sys.exit(0)
    
    def exit(self, code=0):
        if self._pid_written:
            try:
                os.remove(self._pid_file_path)
            except Exception:
                pass
        logger.debug('Daemon %s ended (return code: %s).\n' % (self.DAEMON_NAME, code))
        sys.exit(code)
    
    def send_error_email(self, msg, tb=False, recipients=None):
        from django_web_utils import emails_utils
        message = msg.decode('utf-8')
        logger.error(u'%s\n%s' % (message, traceback.format_exc().decode('utf-8')) if tb else message)
        emails_utils.send_error_report_emails(
            title=u'%s - %s' % (self.DAEMON_NAME, socket.gethostname()),
            error=u'%s\n\nThe daemon was started with the following arguments:\n%s' % (message, sys.argv),
            recipients=recipients,
        )
