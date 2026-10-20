import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import AbstractBaseUser
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.generic import View

from django_web_utils.emails_utils import send_emails, send_template_emails
from django_web_utils.magic_login.forms import RequestMagicLoginForm
from django_web_utils.magic_login.tokens import generate_token

logger = logging.getLogger(__name__)


class MagicLoginView(View):
    """
    View for the magic login feature.
    """

    # The `users_json_path` value must be the path to the file containing the allowed users.
    # For example: `{"magic@example.com": {"username": "magic-user", "is_admin": true}}`
    users_json_path: Path = Path('/etc/magic-login/users.json')

    # The `template_view` value must be defined in your view.
    # Arguments given to the template:
    #   `magic_login_form` (Django form object)
    template_view: str

    # The `template_email` value is optional and can be used to send an email using a template.
    # Arguments given to the template:
    #   `subject` (str)
    #   `body` (str)
    #   `user` (AbstractBaseUser)
    template_email: str | None = None

    # Minimum delay in seconds between two link requests for the same email address.
    # The Django cache is used to store the date of the last request. Set to 0 to disable the limit.
    request_cooldown: int = 60

    @classmethod
    def get_users(cls) -> dict[str, AbstractBaseUser]:
        """
        Retrieve all users related to the magic login feature.
        It should return a dict with email as keys and user objects as values.
        This function is used for cleaning actions.
        """
        raise NotImplementedError()

    @classmethod
    def create_user(cls, info: dict) -> AbstractBaseUser:
        """
        Function to create a user account from the information of the JSON file.
        If the account already exists, nothing should be done.
        """
        raise NotImplementedError()

    @classmethod
    def is_available(cls):
        return cls.users_json_path.exists()

    @classmethod
    def get_users_info(cls) -> dict:
        """
        Read the users json file and return its decoded content.
        """
        try:
            content = cls.users_json_path.read_text()
        except FileNotFoundError:
            return {}
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError('A dict is expected.')
        except (json.JSONDecodeError, ValueError) as err:
            logger.warning('Failed to parse content of "%s" file: %s', cls.users_json_path, err)
            return {}
        return data

    @classmethod
    def delete_unregistered_users(cls):
        """
        Delete all user accounts related to magic login that do not exist in the json file.
        """
        users_info = cls.get_users_info()
        for email, user in cls.get_users().items():
            if email not in users_info:
                logger.info(
                    'Deleting user account %r because it is tagged as a magic login user and '
                    'it does not exist in the json file "%s"',
                    user, cls.users_json_path
                )
                user.delete()

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle get requests.
        """
        if 't' in request.GET and self.authenticate_user(request):
            return HttpResponseRedirect(self.get_next_url(request))
        return render(request, self.template_view, {
            'magic_login_form': RequestMagicLoginForm()
        })

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle post requests.
        """
        form = RequestMagicLoginForm(request.POST)
        if not form.is_valid():
            messages.error(request, _('The submitted form is incorrect. Please correct all errors and send it again.'))
        elif self.process_email(request, form.get_email()):
            return HttpResponseRedirect(request.get_full_path())
        return render(request, self.template_view, {
            'magic_login_form': form
        })

    def process_email(self, request: HttpRequest, email: str) -> bool:
        """
        Send a login link if the email is allowed.
        The response is the same whether the email is allowed or not to avoid disclosing allowed addresses.
        """
        ip = request.META.get('REMOTE_ADDR')
        cache_key = None
        if self.request_cooldown > 0:
            cache_key = 'djwutils-magic-login-' + hashlib.sha256(email.lower().encode('utf-8')).hexdigest()
            if not cache.add(cache_key, True, timeout=self.request_cooldown):
                logger.warning('Too many requests for magic login link. IP: "%s", email: %r.', ip, email)
                messages.warning(request, _(
                    'A link has already been requested recently for this email address, '
                    'please wait a moment before retrying.'
                ))
                return False
        users_info = self.get_users_info()
        info = users_info.get(email)
        sent_msg = _('If this email address is allowed, an email has been sent to it with the link to log in.')
        if not info:
            logger.warning('Invalid request for magic login link. IP: "%s", email: %r.', ip, email)
            messages.success(request, sent_msg)
            return True
        info['email'] = email
        user = self.create_user(info)
        if not request.session.session_key or not request.session.exists(request.session.session_key):
            request.session.create()
        request.session['magic_login_id'] = user.id
        token = generate_token(user, request.session.session_key)
        next_url = self.get_next_url(request)
        host = request.get_host()
        subject = _('Link to authenticate on %s') % host
        link = f'{request.scheme}://{host}{request.path}?{urlencode({"t": token, "next": next_url})}'
        body = format_html(
            '{}<br/>\n<a href="{}" target="_blank">{}</a><br/>\n{}',
            _('Here is the link to log in on the site:'),
            link,
            host,
            _('If you did not request this link, ignore this email.'),
        )
        logger.info('A magic login link has been generated for IP: "%s", email: %r.', ip, email)
        if self.template_email:
            success, data = send_template_emails(self.template_email, context={
                'subject': subject,
                'body': body,
                'user': user,
            }, recipients={email: user})
        else:
            success, data = send_emails(subject=subject, content=body, recipients={email: user})
        if not success:
            logger.error('Failed to send magic login link to %r: %s', email, data)
            if cache_key:
                # Allow the user to retry immediately
                cache.delete(cache_key)
            messages.error(request, _('Failed to send the email. Please try again later.'))
        else:
            messages.success(request, sent_msg)
        return success

    def authenticate_user(self, request: HttpRequest) -> bool:
        if not request.session or not isinstance(request.session.get('magic_login_id'), int):
            messages.error(request, _('Your session has expired, please get a new link to retry.'))
            return False
        user = authenticate(request, magic_login_id=request.session['magic_login_id'])
        if not user:
            messages.error(request, _('Your request is invalid.'))
            return False
        ip = request.META.get('REMOTE_ADDR')
        logger.info('A magic login link was used to authenticate user %s (IP: %s).', user, ip)
        login(request, user)
        return True

    def get_next_url(self, request: HttpRequest) -> str:
        """
        Get the next URL to redirect the user after login.
        """
        next_page = request.GET.get('next', '')
        if not self.is_safe_url(request, next_page):
            next_page = ''
        if not next_page:
            referer = request.META.get('HTTP_REFERER')
            site_url = f'{request.scheme}://{request.get_host()}'
            if referer and referer.startswith(site_url + '/'):
                relative_url = referer[len(site_url):]
                if self.is_safe_url(request, relative_url) and not relative_url.startswith('/login'):
                    next_page = relative_url
        return next_page or settings.LOGIN_REDIRECT_URL

    @staticmethod
    def is_safe_url(request: HttpRequest, url: str) -> bool:
        """
        Check that the URL is a local path (URLs with a scheme or a host are refused).
        """
        return (
            url.startswith('/')
            and url_has_allowed_host_and_scheme(url, allowed_hosts=None, require_https=request.is_secure())
        )
