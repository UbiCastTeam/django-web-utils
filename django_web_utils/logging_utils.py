import logging
import re
import traceback

from django.conf import settings
from django.utils.log import AdminEmailHandler
from django.core.cache import cache

try:
    import pygments
    from pygments.lexers import SqlLexer
    from pygments.formatters import Terminal256Formatter, TerminalTrueColorFormatter
except ImportError:
    pygments = SqlLexer = Terminal256Formatter = TerminalTrueColorFormatter = None
try:
    import sqlparse
except ImportError:
    sqlparse = None

logger = logging.getLogger('djwutils.logging_utils')


class ThrottledAdminEmailHandler(AdminEmailHandler):
    """
    Modification of Django builtin class AdminEmailHandler
    to add a rate limit for sending emails.
    """
    PERIOD_LENGTH_IN_SECONDS = getattr(settings, 'ADMIN_EMAIL_THROTTLING_PERIOD_LENGTH', 24 * 3600)
    MAX_EMAILS_IN_PERIOD = getattr(settings, 'ADMIN_EMAIL_THROTTLING_MAX_EMAILS', 10)
    COUNTER_CACHE_KEY = getattr(settings, 'ADMIN_EMAIL_THROTTLING_CACHE_KEY', 'email_admin_counter')

    def increment_counter(self):
        try:
            value = cache.incr(self.COUNTER_CACHE_KEY)
        except ValueError:
            cache.set(self.COUNTER_CACHE_KEY, 1, timeout=self.PERIOD_LENGTH_IN_SECONDS)
            value = 1
        return value

    def emit(self, record):
        try:
            counter = self.increment_counter()
        except Exception as err:
            logger.warning(
                'Failed to increment counter of error report emails, no email will be sent. Details: %s',
                err
            )
        else:
            if counter > self.MAX_EMAILS_IN_PERIOD:
                logger.warning(
                    'Error report emails reached limit (%s emails in %s seconds), no email will be sent.',
                    self.MAX_EMAILS_IN_PERIOD, self.PERIOD_LENGTH_IN_SECONDS
                )
                return
            super().emit(record)


class IgnoreTimeoutErrors(logging.Filter):

    def filter(self, record):
        """
        Ignore WSGI connection errors (UnreadablePostError)
        Like:
            UnreadablePostError: error during read(---) on wsgi.input
        """
        try:
            err_class = record.exc_info[0].__name__ if record.exc_info is not None else 'None'
        except Exception as e:
            logger.warning('IgnoreTimeoutErrors: Failed to parse error type: %s (record: %s).', e, record)
            return True
        else:
            return err_class != 'UnreadablePostError'


class IgnoreDatabaseErrors(logging.Filter):

    def filter(self, record):
        """
        Ignore database connection errors (OperationalError)
        Like:
            OperationalError: could not connect to server: Connection refused
            OperationalError: server closed the connection unexpectedly
            OperationalError: SSL SYSCALL error: EOF detected
        """
        try:
            err_class = record.exc_info[0].__name__ if record.exc_info is not None else 'None'
        except Exception as e:
            logger.warning('IgnoreDatabaseErrors: Failed to parse error type: %s (record: %s).', e, record)
            return True
        else:
            return err_class != 'OperationalError'


class IgnoreNoSpaceLeftErrors(logging.Filter):

    def filter(self, record):
        """
        Ignore no space left errors (OSError)
        Like:
            OSError [Errno 28] No space left on device: ...
        """
        try:
            err_class = record.exc_info[0].__name__ if record.exc_info is not None else 'None'
            if err_class == 'OSError':
                import errno
                error = record.exc_info[1]
                return error.errno != errno.ENOSPC
            return True
        except Exception as e:
            logger.warning('IgnoreNoSpaceLeftErrors: Failed to parse error type: %s (record: %s).', e, record)
            return True


class SQLFormatter(logging.Formatter):
    """Pretty logger for SQL queries with optional indentation and syntax highlighting."""
    def __init__(self, *args, **kwargs):
        self.indent = kwargs.pop('indent', False)
        self.true_color = kwargs.pop('true_color', False)
        self.color_style = kwargs.pop('color_style', 'default')
        self.truncate_sql = kwargs.pop('truncate_sql', -1)
        self.traceback_filter = kwargs.pop('traceback_filter', None)
        if self.traceback_filter:
            self.traceback_filter = re.compile(self.traceback_filter)
        self.traceback_lines = kwargs.pop('traceback_lines', 1)
        self.only_slow_queries = kwargs.pop('only_slow_queries', False)
        super().__init__(*args, **kwargs)

    def format(self, record):
        # Remove leading and trailing whitespaces
        sql = record.sql.strip()

        if self.truncate_sql > 0:
            if len(sql) > self.truncate_sql:
                sql = f'{sql[:self.truncate_sql]}...'
        elif self.truncate_sql == 0:
            sql = ''
        else:
            if self.indent and sqlparse:
                # Indent the SQL query
                sql = sqlparse.format(sql, reindent=True)

            if self.color_style != 'none' and all((pygments, SqlLexer, Terminal256Formatter, TerminalTrueColorFormatter)):
                # Highlight the SQL query
                terminal_formatter_cls = TerminalTrueColorFormatter if self.true_color else Terminal256Formatter
                sql = pygments.highlight(sql, SqlLexer(), terminal_formatter_cls(style=self.color_style))

        # Set the record's statement
        prefix = 'SLOW SQL' if self.only_slow_queries else 'SQL'
        duration = f'{record.duration * 1000:.1f}ms'
        sql = sql.strip()
        if sql:
            record.statement = f'[{prefix} - {duration}]: {sql} [{duration}]'
        else:
            record.statement = f'[{prefix} - {duration}]:'

        # Set the record's statement to the formatted query
        if self.traceback_lines != 0:
            stack = traceback.extract_stack()
            if self.traceback_filter and self.traceback_lines > 0:
                for i, frame_summary in enumerate(stack):
                    if 'django/db/models/query.py' in frame_summary.filename:
                        stack = stack[:i]
                        break
            if self.traceback_filter:
                stack = [line for line in stack if self.traceback_filter.search(line.filename)]
            if self.traceback_lines > 0:
                stack = stack[-self.traceback_lines:]
            if stack:
                tb = '\n'.join([
                    f'{frame_summary.filename}:{frame_summary.lineno} in {frame_summary.name}\n\t{frame_summary.line}'
                    for frame_summary in stack
                ])
            else:
                tb = 'Unable to find query location in the stack.'
            record.statement += f'\n{tb}'

        if (self.truncate_sql < 0 and self.indent) or self.traceback_lines != 0:
            record.statement += '\n'

        return super().format(record)


class RegexFilter(logging.Filter):
    """Ignores SQL queries that don't match the provided regex."""
    def __init__(self, *args, **kwargs):
        self.regex_filter = kwargs.pop('regex_filter', None)
        if self.regex_filter:
            self.regex_filter = re.compile(self.regex_filter)
        super().__init__(*args, **kwargs)

    def filter(self, record):
        if not self.regex_filter:
            return True
        return bool(self.regex_filter.search(record.sql))


class OnlySlowSQLQueries(logging.Filter):
    """Ignores SQL queries that execute in less than the provided threshold."""
    def __init__(self, *args, **kwargs):
        self.slow_query_threshold = kwargs.pop('slow_query_threshold_ms', 100) / 1000
        super().__init__(*args, **kwargs)

    def filter(self, record):
        return record.duration >= self.slow_query_threshold


def enable_sql_logging(
    logging_config: dict,
    indent=True, color_style='default', true_color=False,
    truncate_sql=-1, traceback_filter=None, traceback_lines=1,
    regex_filter=None, only_slow_queries=False, slow_query_threshold_ms=100,
):
    # Formatters
    formatters = logging_config.setdefault('formatters', {})
    formatters['sql'] = {
        '()': 'django_web_utils.logging_utils.SQLFormatter',
        'format': '%(statement)s',
        'indent': indent,
        'color_style': color_style,
        'true_color': true_color,
        'truncate_sql': truncate_sql,
        'traceback_filter': traceback_filter,
        'traceback_lines': traceback_lines,
        'only_slow_queries': only_slow_queries,
    }

    # Filters
    filters = logging_config.setdefault('filters', {})
    if regex_filter:
        filters['regex_filter'] = {
            '()': 'django_web_utils.logging_utils.RegexFilter',
            'regex_filter': regex_filter,
        }
    if only_slow_queries:
        filters['only_slow_sql_queries'] = {
            '()': 'django_web_utils.logging_utils.OnlySlowSQLQueries',
            'slow_query_threshold_ms': slow_query_threshold_ms,
        }

    # Handlers
    handlers = logging_config.setdefault('handlers', {})
    handlers['sql'] = {
        'class': 'logging.StreamHandler',
        'formatter': 'sql',
        'level': 'DEBUG',
    }
    handlers['sql']['filters'] = []
    if regex_filter:
        handlers['sql']['filters'].append('regex_filter')
    if only_slow_queries:
        handlers['sql']['filters'].append('only_slow_sql_queries')

    # Loggers
    loggers = logging_config.setdefault('loggers', {})
    loggers['django.db.backends'] = {
        'handlers': ['sql'],
        'level': 'DEBUG',
        'propagate': False,
    }
    loggers['django.db.backends.schema'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False,
    }
