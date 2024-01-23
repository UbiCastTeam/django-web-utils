"""
Emails utility functions

Optional settings:
    - EMAIL_CONTEXT_PROCESSOR:
        This var should point to a function. The object returned by the
        function must be a dict and should contain a valid sender field
        (something like '"name" <sender@address.com>').
    - EMAIL_ERROR_TEMPLATE:
        The template to use to prepare error report emails.

The template should contain a subject tag.
For example, a valid template could look like this:
<subject>The email subject</subject>
The email content
"""
import datetime
import logging
import os
import socket
import sys
import traceback
# Django
from django.conf import settings
from django.core import mail
from django.db.models.query import QuerySet
from django.template import Context, Engine
from django.utils import translation
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
# utils
from django_web_utils import html_utils
from django_web_utils.logging_utils import IgnoreTimeoutErrors, IgnoreDatabaseErrors

logger = logging.getLogger('djwutils.emails_utils')


class Recipient:
    def __init__(self, user=None, **info):
        self.name = (user.get_full_name() if user else info.pop('name', '')).replace('"', '”').replace('\'', '’')
        self.email = user.email if user else info.pop('email', None)
        self.lang = (
            getattr(user, 'emails_lang', None) if user else info.pop('lang', None)
        ) or settings.LANGUAGE_CODE[:2]
        self.user = user
        self.info = info

    def is_valid(self):
        return (self.email or '').count('@') == 1


def _get_context():
    # Get context processor function
    if '_context_processor' not in globals():
        ctx_processor = None
        if getattr(settings, 'EMAIL_CONTEXT_PROCESSOR', None):
            fct_path = settings.EMAIL_CONTEXT_PROCESSOR
            try:
                module_name = fct_path.rsplit('.', 1)[-1]
                module_path = fct_path[:-len(module_name) - 1]
                if not module_path:
                    module_path = '.'
                module = __import__(module_path, fromlist=[module_name])
                ctx_processor = getattr(module, module_name)
            except Exception as err:
                raise RuntimeError(f'Failed to import emails context processor: {err}') from err
            if not hasattr(ctx_processor, '__call__'):
                ctx_processor = None
        globals()['_context_processor'] = ctx_processor
    else:
        ctx_processor = globals()['_context_processor']

    # Generate context
    ctx = {}
    if ctx_processor is not None:
        data = ctx_processor()
        if not isinstance(data, dict):
            raise RuntimeError(
                f'Emails context processor returned an invalid object for context (must be a dict): {data}'
            )
        else:
            ctx = data
    if (not ctx or not ctx.get('sender')) and getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        ctx['sender'] = settings.DEFAULT_FROM_EMAIL
    return ctx


def _get_recipients_list(recipients):
    if recipients is None:
        # Send emails to managers if no email is given
        recipients = {a[1]: {'name': a[0]} for a in settings.MANAGERS}
    elif isinstance(recipients, dict):
        # Convert dict to list
        as_list = list()
        for key, value in recipients.items():
            if isinstance(value, dict):
                value['email'] = key
                as_list.append(value)
            elif hasattr(value, 'email'):
                # User model
                as_list.append(value)
            else:
                as_list.append(dict(email=key, info=value))
        recipients = as_list
    elif not isinstance(recipients, (tuple, list, QuerySet)):
        recipients = [recipients]
    # Clean recipients list (get a list of Recipient objects)
    cleaned_rcpts = list()
    for recipient in recipients:
        if hasattr(recipient, 'email'):
            # User model
            rcpt = Recipient(user=recipient)
        elif isinstance(recipient, dict):
            rcpt = Recipient(**recipient)
        else:
            rcpt = Recipient(email=str(recipient))
        if rcpt.is_valid():
            cleaned_rcpts.append(rcpt)
    return cleaned_rcpts


def send_template_emails(template, context=None, recipients=None, content_subtype='html', attachments=None):
    """
    Function to send emails with a template.
    Arguments:
        template: template path.
        context: can be a dict or None.
        recipients: can be a dict, a list, a str or None.
            dict format: {'test@test.com': {'lang': 'en', 'name': ''}}
            list format: [{'email': 'test@test.com', 'lang': 'en', 'name': ''}]
            str format: test@test.com
            (user objects can be given as recipient)
        content_subtype: email content type.
        attachments: list of attachments.
    """
    # Get common context
    base_ctx = _get_context()
    if context:
        base_ctx.update(context)
    sender = base_ctx.get('sender') or '"Default sender name" <sender@address.com>'

    # Clean recipients list (get a list of User model or dict with at least email in keys)
    cleaned_rcpts = _get_recipients_list(recipients)
    if not cleaned_rcpts:
        msg = 'No emails have been sent: no valid recipients given.'
        logger.error('%s Recipients: %s.', msg, recipients)
        return False, msg

    # Get template
    engine = Engine.get_default()
    if template.startswith('/'):
        with open(template, 'r') as file_obj:
            template = file_obj.read()
        tplt = engine.from_string(template)
    else:
        tplt = engine.get_template(template)

    # Prepare emails messages
    connection = None
    sent = []
    error = 'unknown'
    cur_lang = translation.get_language()
    last_lang = cur_lang
    for recipient in cleaned_rcpts:
        # Activate correct lang
        lang = recipient.lang
        if lang != last_lang:
            last_lang = lang
            translation.activate(lang)
        # Get subject and content
        ctx = dict(base_ctx)
        ctx['recipient'] = recipient
        ctx['LANGUAGE_CODE'] = lang
        content = tplt.render(Context(ctx))
        subject_start = content.index('<subject>') + 9
        subject_end = subject_start + content[subject_start:].index('</subject>')
        subject = content[subject_start:subject_end].replace('\r', '').replace('\n', ' ').strip()
        content = content[:subject_start - 9] + content[subject_end + 10:]
        # Prepare email
        address_with_name = f'"{recipient.name}" <{recipient.email}>' if recipient.name else recipient.email
        msg = mail.EmailMessage(subject, content, sender, [address_with_name])
        if attachments:
            for attachment in attachments:
                msg.attach_file(attachment)
        msg.content_subtype = content_subtype  # by default, set email content type to html
        # Send email
        try:
            if not connection:
                connection = mail.get_connection()
            connection.send_messages([msg])
        except Exception as err:
            error = err
            logger.error('Error when trying to send email to: %s.\n%s', recipient.email, traceback.format_exc())
        else:
            sent.append(recipient.email)
            logger.info('Email with subject "%s" sent to "%s" (tplt).', subject, recipient.email)
    if last_lang != cur_lang:
        translation.activate(cur_lang)
    if not sent:
        return False, f'No emails have been sent. Last error when trying to send email: {error}'
    return True, sent


def send_emails(subject, content, recipients=None, content_subtype='html', attachments=None):
    """
    Function to send emails without template.
    Arguments:
        subject: email subject.
        content: email content.
        recipients: can be a dict, a list, a str or None.
            dict format: {'test@test.com': {'lang': 'en', 'name': ''}}
            list format: [{'email': 'test@test.com', 'lang': 'en', 'name': ''}]
            str format: test@test.com
            (user objects can be given as recipient)
        content_subtype: email content type.
        attachments: list of attachments.
    """
    # Get sender
    ctx = _get_context()
    sender = ctx.get('sender') or '"Default sender name" <sender@address.com>'

    # Clean recipients list (get a list of User model or dict with at least email in keys)
    cleaned_rcpts = _get_recipients_list(recipients)
    if not cleaned_rcpts:
        msg = 'No emails have been sent: no valid recipients given.'
        logger.error('%s Recipients: %s.', msg, recipients)
        return False, msg

    # Prepare emails messages
    subject = subject.replace('\r', '').replace('\n', ' ').strip()
    connection = None
    sent = []
    error = 'no recipient'
    for recipient in cleaned_rcpts:
        # Prepare email
        address_with_name = f'"{recipient.name}" <{recipient.email}>' if recipient.name else recipient.email
        msg = mail.EmailMessage(subject, content, sender, [address_with_name])
        if attachments:
            for attachment in attachments:
                msg.attach_file(attachment)
        msg.content_subtype = content_subtype  # by default, set email content type to html
        # Send email
        try:
            if not connection:
                connection = mail.get_connection()
            connection.send_messages([msg])
        except Exception as err:
            error = err
            logger.error('Error when trying to send email to: %s.\n%s', recipient.email, traceback.format_exc())
        else:
            sent.append(recipient.email)
            logger.info('Email with subject "%s" sent to "%s".', subject, recipient.email)
    if not sent:
        return False, f'No emails have been sent. Last error when trying to send email: {error}'
    return True, sent


def send_error_report_emails(title=None, error=None, recipients=None, filter_error=True, show_traceback=True):
    """
    Function to send last error traceback.
    Arguments:
        title: label to add to subject.
        error: can be a dict or None.
        recipients: can be a dict, a list, a str or None.
            dict format: {'test@test.com': {'lang': 'en', 'name': ''}}
            list format: [{'email': 'test@test.com', 'lang': 'en', 'name': ''}]
            str format: test@test.com
            (user objects can be given as recipient)
        filter_error: filter error type with default filters.
    """
    title = f'Error report - {title}' if title else 'Error report'

    no_sending_msg = None
    if settings.DEBUG:
        no_sending_msg = 'Error report will not be sent because the debug mode is enabled.'
    elif filter_error:
        # Check that last error is passing filters
        class Record:
            exc_info = sys.exc_info()
        if Record.exc_info[0] is not None:
            filters = (IgnoreTimeoutErrors(), IgnoreDatabaseErrors())
            for ft in filters:
                if not ft.filter(Record):
                    no_sending_msg = 'Error report will not be sent because the error is matching an exclusion filter.'
                    break

    if no_sending_msg:
        logger.info(
            '%s\nSubject: %s\nTo: %s\nContent:\n%s\n%s',
            no_sending_msg, title, recipients, error, traceback.format_exc())
        return True, no_sending_msg

    fieldset_style = 'style="margin-bottom: 8px; border: 1px solid #888; border-radius: 4px;"'
    content = (
        '<div style="margin-bottom: 8px;">'
        f'Message sent at: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br/>\n'
        f'Unix user: {conditional_escape(os.environ.get("USER"))}<br/>\n'
        f'System hostname: {conditional_escape(socket.gethostname())}'
        '</div>\n'
    )
    # Error information
    if error:
        err_repr = conditional_escape(error).replace('\n', '<br/>\n')
        content += (
            f'<fieldset {fieldset_style}>\n'
            '<legend><b> Error </b></legend>\n'
            f'<div>{err_repr}</div>\n'
            '</fieldset>\n'
        )
    # Traceback information
    if show_traceback:
        content += (
            f'<fieldset {fieldset_style}>\n'
            '<legend><b> Traceback </b></legend>\n'
            f'<div>{html_utils.get_html_traceback()}</div>\n'
            '</fieldset>\n'
        )
    # Send emails
    content = mark_safe(content)
    tplt = getattr(settings, 'EMAIL_ERROR_TEMPLATE', None)
    if tplt:
        return send_template_emails(tplt, dict(
            title=title,
            error=error,
            content=content,
        ), recipients=recipients)
    else:
        return send_emails(title, content, recipients)
