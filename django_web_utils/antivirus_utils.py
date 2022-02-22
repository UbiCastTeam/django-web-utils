#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Antivirus utility functions
Requires:
 clamav-daemon

The ClamAVDaemon code is coming from clammy repository:
https://github.com/ranguli/clammy
It was greatly modified to fit this lib needs and to be able to scan large file as chunks.

Settings:
- ANTIVIRUS_ENABLED
    Boolean to enable or not antivirus scan.
    If no value is set (None), the antivirus scan will be enabled if the clamAV socket file exists.
    This setting impacts top level functions:
    antivirus_path_validator, antivirus_stream_validator and antivirus_file_validator
    Default: None
- ANTIVIRUS_SOCKET_PATH
    The clamd socket path can be set in Django settings.
    Default: '/var/run/clamav/clamd.ctl'
- ANTIVIRUS_REPORTS_RECIPIENTS
    The recipients for infected file upload report emails.
    Can be a list of email addresses or a python module path to a callable returning the list.
    Default: email adresses of settings.ADMINS
'''
from pathlib import Path
import contextlib
import logging
import re
import shutil
import socket
import struct
import sys
import traceback
# Django
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
# Django web utils
from django_web_utils.emails_utils import send_error_report_emails
from django_web_utils.module_utils import import_module_by_python_path

logger = logging.getLogger('djwutils.antivirus_utils')

MIDDLEWARE_MODULE = 'django_web_utils.antivirus_utils.ReportInfectedFileUploadMiddleware'

BAN_WARNING_MESSAGE = _('Your request was reported and if you send again infected files, you will be banned.')
COMMAND_ERROR_MESSAGE = _('Failed to run antivirus scanner.')
DOES_NOT_EXIST_MESSAGE = _('Cannot scan file because it does not exist.')
INFECTED_MESSAGE = _('Your file was rejected because it is infected.')
INVALID_FILE_MESSAGE = _('Cannot scan file because it is not a file.')
INVALID_PATH_MESSAGE = _('Cannot scan file because it is neither a file nor a directory.')
SCAN_FAILED_MESSAGE = _('Failed to scan your file with the antivirus.')


class ClamdError(Exception):
    '''
    Generic Clamd error class.
    '''


class ClamdResponseError(ClamdError):
    '''
    Class for response errrors.
    '''


class ClamdBufferTooLongError(ClamdResponseError):
    '''
    Class for errors with clamd using INSTREAM with a buffer lenght > StreamMaxLength in /etc/clamav/clamd.conf.
    '''


class ClamdConnectionError(ClamdError):
    '''
    Class for communication errors with clamd.
    '''


class ClamAVDaemon:
    '''
    Class for using clamd with a network socket.
    '''
    SCAN_RESPONSE = re.compile(r'^(?P<path>.*): ((?P<virus>.+) )?(?P<status>(FOUND|OK|ERROR))$')

    def __init__(self, host='127.0.0.1', port=3310, unix_socket=None, timeout=None):
        '''
        Args:
            host (string): The hostname or IP address (if connecting to a network socket)
            port (int): TCP port (if connecting to a network socket)
            unix_socket (str):
            timeout (float or None) : socket timeout
        '''
        self.host = host
        self.port = port
        self.unix_socket = unix_socket
        self.socket_type = socket.AF_UNIX if unix_socket else socket.AF_INET
        self.timeout = timeout

        self._init_socket()

    def _init_socket(self):
        try:
            clamd_socket = socket.socket(self.socket_type, socket.SOCK_STREAM)

            # Set timeout prior to connecting to ensure that an initial
            # connection timeout will respect the setting regardless of OS.
            # https://docs.python.org/3/library/socket.html#timeouts-and-the-connect-method
            clamd_socket.settimeout(self.timeout)

            if self.socket_type == socket.AF_INET:
                clamd_socket.connect((self.host, self.port))
            elif self.socket_type == socket.AF_UNIX:
                clamd_socket.connect(self.unix_socket)

        except socket.error as error:
            if self.socket_type == socket.AF_UNIX:
                error_message = f'Error connecting to Unix socket "{self.unix_socket}"'
            elif self.socket_type == socket.AF_INET:
                error_message = f'Error connecting to network socket with host "{self.host}" and port "{self.port}"'
            raise ClamdConnectionError(error_message) from error

        self.socket = clamd_socket

    def ping(self):
        '''
        Sends the ping command to the ClamAV daemon.
        '''
        return self._basic_command('PING')

    def version(self):
        '''
        Sends the version command to the ClamAV daemon.
        '''
        return self._basic_command('VERSION')

    def reload(self):
        '''
        Sends the reload command to the ClamAV daemon.
        '''
        return self._basic_command('RELOAD')

    def shutdown(self):
        '''
        Force Clamd to shutdown and exit.

        return: nothing

        May raise:
          - ClamdConnectionError: in case of communication problem
        '''
        try:
            self._send_command('SHUTDOWN')
            # result = self._recv_response()
        finally:
            self._close_socket()

    def scan(self, filename):
        '''
        Scan a file.
        '''
        return self._file_system_scan('SCAN', filename)

    def cont_scan(self, filename):
        '''
        Scan a file but don't stop if a virus is found.
        '''
        return self._file_system_scan('CONTSCAN', filename)

    def multi_scan(self, filename):
        '''
        Scan a file using multiple threads.
        '''
        return self._file_system_scan('MULTISCAN', filename)

    def _basic_command(self, command):
        '''
        Send a command to the clamav server, and return the reply.
        '''
        try:
            self._send_command(command)
            response = self._recv_response().rsplit('ERROR', 1)
            if len(response) > 1:
                raise ClamdResponseError(response[0])
            return response[0]
        finally:
            self._close_socket()

    def _file_system_scan(self, command, filename):
        '''
        Scan a file or directory given by filename using multiple threads (faster on SMP machines).
        Do not stop on error or virus found.
        Scan with archive support enabled.

        filename (string): filename or directory (MUST BE ABSOLUTE PATH !)

        return:
          - (dict): {FOUND: 1, ERROR: 1, files: {filename1: ('FOUND', 'virusname'), filename2: ('ERROR', 'reason')}}

        May raise:
          - ClamdConnectionError: in case of communication problem
        '''
        try:
            self._send_command(command, filename)

            report = {'files': {}}
            for result in self._recv_response_multiline().split('\n'):
                if result:
                    filename, reason, status = self.parse_response(result)
                    report['files'][filename] = (status, reason)
                    if status not in report:
                        report[status] = 1
                    else:
                        report[status] += 1

            return report

        finally:
            self._close_socket()

    def instream(self, buff, max_chunk_size=1048576, max_stream_size=26214400):
        '''
        Scan a buffer.

        buff  filelikeobj: buffer to scan
        max_chunk_size int: Maximum size of chunk to send to clamd in bytes
          MUST be < StreamMaxLength in /etc/clamav/clamd.conf
          Default 1 MiB
        max_stream_size int: Maximum size of stream to send to clamd in bytes
          MUST be <= StreamMaxLength in /etc/clamav/clamd.conf
          Used to segment scan for large stream
          When segmented, the last chunk is always resend
          Default 25 MiB

        return:
          - (dict): {FOUND: 1, files: {filename1: ('FOUND', 'virusname')}}

        May raise :
          - ClamdBufferTooLongError: if the buffer size exceeds clamd limits
          - ClamdConnectionError: in case of communication problem
        '''
        try:
            self._send_command('INSTREAM')

            stream_size = 0
            last_chunk = None
            chunk = buff.read(max_chunk_size)
            range_start, range_end = 0, 0
            while chunk:
                if stream_size + len(chunk) >= max_stream_size:
                    # Scan sent data
                    self.socket.sendall(struct.pack(b'!L', 0))
                    logger.debug('Instream scan range: %s-%s', range_start, range_end)

                    result = self._recv_response()

                    if len(result) > 0:
                        if result == 'INSTREAM size limit exceeded. ERROR':
                            raise ClamdBufferTooLongError(result)

                        filename, reason, status = self.parse_response(result)
                        if status != 'OK':
                            report = {status: 1, 'files': {filename: (status, reason)}}
                            return report

                    # Initiate new instream scan
                    self._close_socket()
                    self._init_socket()
                    self._send_command('INSTREAM')

                    # Resend last chunk to scan content between two instream
                    range_start = range_end - len(last_chunk)
                    size = struct.pack(b'!L', len(last_chunk))
                    self.socket.sendall(size + last_chunk)
                    stream_size = len(last_chunk)
                    last_chunk = None

                # Send chunk
                range_end += len(chunk)
                size = struct.pack(b'!L', len(chunk))
                self.socket.sendall(size + chunk)
                stream_size += len(chunk)
                last_chunk = chunk

                # Get next chunk
                chunk = buff.read(max_chunk_size)

            # Scan sent data
            self.socket.sendall(struct.pack(b'!L', 0))
            logger.debug('Instream scan range: %s-%s', range_start, range_end)

            result = self._recv_response()

            if len(result) > 0:
                if result == 'INSTREAM size limit exceeded. ERROR':
                    raise ClamdBufferTooLongError(result)

                filename, reason, status = self.parse_response(result)
                report = {status: 1, 'files': {filename: (status, reason)}}
            else:
                report = {'files': {}}
            return report
        finally:
            self._close_socket()

    def stats(self):
        '''
        Get Clamscan stats.

        return: (string) clamscan stats

        May raise:
          - ClamdConnectionError: in case of communication problem
        '''
        try:
            self._send_command('STATS')
            return self._recv_response_multiline()
        finally:
            self._close_socket()

    def _send_command(self, cmd, *args):
        '''
        Sends a command to the ClamAV daemon.

        `man clamd` recommends to prefix commands with z, but we will use \n
        terminated strings, as python<->clamd has some problems with \0x00
        '''
        concat_args = ''
        if args:
            concat_args = ' ' + ' '.join(args)

        # cmd = 'n{cmd}{args}\n'.format(cmd=cmd, args=concat_args).encode('utf-8')
        cmd = f'n{cmd}{concat_args}\n'.encode('utf-8')
        self.socket.sendall(cmd)

    def _recv_response(self):
        '''
        Receive line from clamd.
        '''
        try:
            with contextlib.closing(self.socket.makefile('rb')) as file_object:
                return file_object.readline().decode('utf-8').strip()
        except (socket.error, socket.timeout) as error:
            raise ClamdConnectionError(
                f'Error while reading from socket: {sys.exc_info()[1].args}'
            ) from error

    def _recv_response_multiline(self):
        '''
        Receive multiple line response from clamd and strip all whitespace characters.
        '''
        try:
            with contextlib.closing(self.socket.makefile('rb')) as file_object:
                return file_object.read().decode('utf-8')
        except (socket.error, socket.timeout) as error:
            raise ClamdConnectionError(
                f'Error while reading from socket: {sys.exc_info()[1]}'
            ) from error

    def _close_socket(self):
        '''
        Close clamd socket.
        '''
        self.socket.close()

    def parse_response(self, msg):
        '''
        Parses responses for SCAN, CONTSCAN, MULTISCAN and STREAM commands.
        '''
        try:
            return self.SCAN_RESPONSE.match(msg).group('path', 'virus', 'status')
        except AttributeError:
            raise ClamdResponseError(
                msg.rsplit('ERROR', 1)[0]
            ) from AttributeError


class FileInfectedError(Exception):
    '''
    Class for infected file errrors.
    Used only if the `ReportInfectedFileUploadMiddleware` middleware is enabled.
    '''
    def __init__(self, message):
        # The message attribute is used to have the same format as ValidationError.
        self.message = message
        super().__init__(message)


def on_file_infected_error(request):
    '''
    Function to log and report infected file upload.
    '''
    # Prepare message
    if request.user.is_authenticated:
        user_repr = 'user #' + str(request.user.id)
        if hasattr(request.user, 'username'):
            user_repr += ' "' + request.user.username + '"'
        if hasattr(request.user, 'email'):
            user_repr += ' <' + request.user.email + '>'
    else:
        user_repr = 'anonymous user'
    log_subject = 'An infected file was uploaded'
    log_msg = log_subject + '. IP: "' + request.META.get('REMOTE_ADDR', '') + '", ' + user_repr + '.'
    log_msg += '\nThe file was uploaded on this URL: ' + ('https://' if request.is_secure() else 'http://') + request.get_host() + request.get_full_path()
    logger.warning(log_msg)
    # Get recipients
    # Recipients can be a list of email addresses or a python module path to a callable returning the list.
    recipients_val = getattr(settings, 'ANTIVIRUS_REPORTS_RECIPIENTS', None)
    if isinstance(recipients_val, str):
        fct = import_module_by_python_path(recipients_val)
        recipients = fct()
    elif isinstance(recipients_val, (list, tuple, dict)):
        recipients = recipients_val
    else:
        recipients = [adm[1] for adm in settings.ADMINS]
    # Send email if ricipients
    if recipients:
        send_error_report_emails(log_subject, log_msg, recipients=recipients, show_traceback=False)
    return str(INFECTED_MESSAGE) + '\n' + str(BAN_WARNING_MESSAGE)


class ReportInfectedFileUploadMiddleware:
    '''
    This middleware logs request information and returns a 451 HTTP code
    (unavailable for legal reasons) response when an infected file is uploaded.
    The purpose of this middleware is to be able to ban the IP with fai2ban.
    '''
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_exception(self, request, exception):
        if isinstance(exception, FileInfectedError):
            msg = on_file_infected_error(request)
            return HttpResponse(msg, content_type='text/plain; charset=utf-8', status=451)


def get_antivirus_socket_path():
    return getattr(settings, 'ANTIVIRUS_SOCKET_PATH', None) or '/var/run/clamav/clamd.ctl'


def is_antivirus_enabled():
    enabled = getattr(settings, 'ANTIVIRUS_ENABLED', None)
    if enabled is None:
        socket_exists = Path(get_antivirus_socket_path()).exists()
        settings.ANTIVIRUS_ENABLED = socket_exists  # Avoid checking again socket existence
        return socket_exists
    return bool(enabled)


def _remove_infected_file(path):
    '''
    Remove path (file or directory) if it exists.
    '''
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()


def antivirus_path_validator(path, remove=True):
    '''
    Check given path (file or directory) and raise ValidationError if invalid or infected.
    The `path` argument must be a Path or a str.
    Warning: The clamav unix user must be able to read the data to be able to scan it.
    Use the `antivirus_file_validator` function to avoid this constraint.
    '''
    if not is_antivirus_enabled():
        logger.info('Skipped scan of path "%s" because scan is disabled.', path)
        return
    if isinstance(path, str):
        path = Path(path)
    elif not isinstance(path, Path):
        raise ValueError('Invalid argument type, a Path or a str is expected.')
    if not path.exists():
        logger.info('Cannot scan path "%s" because it does not exist.', path)
        raise ValidationError(DOES_NOT_EXIST_MESSAGE)
    if not path.is_file() and not path.is_dir():
        logger.info('Cannot scan path "%s" because it is neither a file nor a directory.', path)
        raise ValidationError(INVALID_PATH_MESSAGE)
    try:
        sp = get_antivirus_socket_path()
        clamav = ClamAVDaemon(unix_socket=sp)
        report = clamav.multi_scan(str(path))
        logger.debug('Scanned with antivirus path "%s": %s', path, report)
    except Exception:
        logger.error('Scan failed for path "%s":\n%s', path, traceback.format_exc())
        if remove:
            _remove_infected_file(path)
        raise ValidationError(COMMAND_ERROR_MESSAGE)
    else:
        if report.get('FOUND'):
            logger.warning('Path "%s" is infected%s:\n%s', path, (', it will be removed' if remove else ''), report['files'])
            if remove:
                _remove_infected_file(path)
            if MIDDLEWARE_MODULE in settings.MIDDLEWARE:
                raise FileInfectedError(INFECTED_MESSAGE)
            raise ValidationError(INFECTED_MESSAGE)
        elif report.get('ERROR'):
            logger.error('Path "%s" cannot be scanned%s:\n%s', path, (', it will be removed' if remove else ''), report['files'])
            raise ValidationError(SCAN_FAILED_MESSAGE)
        logger.debug('Path "%s" is not infected:\n%s', path, report['files'])


def antivirus_stream_validator(stream, remove=True):
    '''
    Check given file stream (for example in a model FileField) and raise ValidationError if invalid or infected.
    The `stream` argument must be a file object.
    '''
    if not is_antivirus_enabled():
        logger.info('Skipped scan of stream "%s" because scan is disabled.', stream.name)
        return
    initial_pos = stream.tell()
    try:
        sp = get_antivirus_socket_path()
        clamav = ClamAVDaemon(unix_socket=sp)
        report = clamav.instream(stream)
        logger.debug('Scanned with antivirus file "%s": %s', stream.name, report)
    except Exception:
        logger.error('Scan failed for stream "%s":\n%s', stream.name, traceback.format_exc())
        if remove and getattr(stream, 'path', None):
            _remove_infected_file(Path(stream.path))
        raise ValidationError(COMMAND_ERROR_MESSAGE)
    else:
        if report.get('FOUND'):
            logger.warning('Stream "%s" is infected%s:\n%s', stream.name, (', it will be removed' if remove else ''), report['files'])
            if remove and getattr(stream, 'path', None):
                _remove_infected_file(Path(stream.path))
            if MIDDLEWARE_MODULE in settings.MIDDLEWARE:
                raise FileInfectedError(INFECTED_MESSAGE)
            raise ValidationError(INFECTED_MESSAGE)
        elif report.get('ERROR'):
            logger.error('Stream "%s" cannot be scanned%s:\n%s', stream.name, (', it will be removed' if remove else ''), report['files'])
            raise ValidationError(SCAN_FAILED_MESSAGE)
        logger.debug('Stream "%s" is not infected:\n%s', stream.name, report['files'])
    finally:
        # Move file stream pointer to the initial position
        stream.seek(initial_pos)


def antivirus_file_validator(path, remove=True):
    '''
    Check given file path and raise ValidationError if invalid or infected.
    The `path` argument must be a Path or a str.
    This function allows to check paths inaccessible for the clamav user.
    '''
    if not is_antivirus_enabled():
        logger.info('Skipped scan of file "%s" because scan is disabled.', path)
        return
    if isinstance(path, str):
        path = Path(path)
    elif not isinstance(path, Path):
        raise ValueError('Invalid argument type, a Path or a str is expected.')
    if not path.is_file():
        logger.info('Cannot scan path "%s" because it is not a file.', path)
        raise ValidationError(INVALID_FILE_MESSAGE)
    with open(path, 'rb') as fo:
        fo.path = path
        antivirus_stream_validator(fo)
