import json
import logging
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic import View

from django_web_utils.emails_utils import send_template_emails, send_emails
from django_web_utils.magic_login.forms import RequestMagicLoginForm
from django_web_utils.magic_login.backend import MagicLoginBackend

logger = logging.getLogger(__name__)


class MagicLoginView(View):
    """
    View to use the magic login feature.
    This feature allows users to login using a link sent to them by email.
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
    template_email: Optional[str] = None

    @classmethod
    def is_available(cls):
        return cls.users_json_path.exists()

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

    def process_email(self, request: HttpRequest, email: str) -> None:
        ip = request.META['REMOTE_ADDR']
        info = self.get_user_info(email)
        if not info:
            logger.warning('Invalid request for magic login link. IP: %s, email: "%s".', ip, email)
            messages.warning(request, _('The requested email address is not allowed.'))
            return False
        user = self.create_user(info)
        if not request.session.session_key or not request.session.exists(request.session.session_key):
            request.session.create()
        request.session['magic_login_id'] = user.id
        token = self.generate_token(user, request.session.session_key)
        next_url = self.get_next_url(request)
        subject = _('Link to authenticate on %s') % request.get_host()
        body = mark_safe(
            '%(intro)s<br/>\n'
            '<a href="%(scheme)s://%(host)s%(path)s?t=%(token)s&next=%(next)s" target="_blank">%(host)s</a><br/>\n'
            '%(warning)s'
            % {
                'scheme': request.scheme,
                'host': request.get_host(),
                'path': request.path,
                'token': token,
                'next': next_url,
                'intro': escape(_('Here is the link to log in on the site:')),
                'warning': escape(_('If you did not request this link, ignore this email.'))
            }
        )
        logger.info('A magic login link has been generated for IP: %s, email: "%s".', ip, email)
        if self.template_email:
            success, data = send_template_emails(self.template_email, context={
                'subject': subject,
                'body': body,
                'user': user,
            }, recipients={email: user})
        else:
            success, data = send_emails(subject=subject, content=body, recipients={email: user})
        if not success:
            messages.warning(request, _('Failed to send the email:') + ' ' + str(data))
        else:
            messages.success(request, _('An email has been sent to you with the link to log in.'))
        return success

    def get_user_info(self, email: str) -> dict:
        try:
            content = self.users_json_path.read_text()
        except FileNotFoundError:
            return None
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError('A dict is expected.')
        except (json.JSONDecodeError, ValueError) as err:
            logger.error('Failed to parse content of "%s" file: %s', self.users_json_path, err)
            return None
        info = data.get(email)
        if info:
            info['email'] = email
        return info

    def authenticate_user(self, request: HttpRequest) -> bool:
        if not request.session or not isinstance(request.session.get('magic_login_id'), int):
            messages.error(request, _('Your session has expired, please get a new link to retry.'))
            return False
        backend = MagicLoginBackend()
        user = backend.get_user(request.session['magic_login_id'])
        if user is None:
            messages.error(request, _('Your request is invalid.'))
            return False
        if not self.check_token(user, request.session.session_key, request.GET.get('t', '')):
            messages.error(request, _('Your request is invalid.'))
            return False
        user = authenticate(request, magic_login_user=user)
        if not user:
            messages.error(request, _('The "MagicLoginBackend" is missing from authentication backends.'))
            return False
        ip = request.META['REMOTE_ADDR']
        logger.info('A magic login link was used to authenticate user %s (IP: %s).', user, ip)
        login(request, user)
        return True

    def create_user(self, info: dict) -> AbstractBaseUser:
        """
        Function to create a user account from the information of the JSON file.
        If the account already exists, nothing should be done.
        """
        raise NotImplementedError()

    def generate_token(self, user: AbstractBaseUser, session_key: str) -> str:
        """
        Function to generate a token for a user.
        """
        generator = PasswordResetTokenGenerator()
        generator.key_salt = session_key
        return generator.make_token(user)

    def check_token(self, user: AbstractBaseUser, session_key: str, token: str) -> bool:
        """
        Function to check the token for a user.
        """
        generator = PasswordResetTokenGenerator()
        generator.key_salt = session_key
        return generator.check_token(user, token)

    def get_next_url(self, request: HttpRequest) -> str:
        """
        Function to get the next URL to redirect the user after login.
        """
        next_page = request.GET.get('next', '')
        if '://' in next_page:
            next_page = ''
        if not next_page:
            referer = request.META.get('HTTP_REFERER')
            site_url = f'{request.scheme}://{request.get_host()}'
            if referer and referer.startswith(site_url):
                relative_url = referer[len(site_url):]
                if relative_url and '://' not in relative_url and not relative_url.startswith('/login'):
                    next_page = relative_url
        return next_page or settings.LOGIN_REDIRECT_URL
