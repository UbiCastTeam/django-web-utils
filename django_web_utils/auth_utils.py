"""
Authentication utility functions
"""
import base64
import re
# Django
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext as _


def login_required_basicauth(function):
    """
    Decorator to handle login through basicauth.
    Check that user is authenticated and if not, return a basic http authentication request.
    """
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return function(request, *args, **kwargs)

        msg = None
        if request.META.get('HTTP_AUTHORIZATION'):
            to_decode = request.META['HTTP_AUTHORIZATION']
            to_decode = to_decode.split(' ')[-1]
            try:
                decoded = base64.b64decode(to_decode).decode('utf-8')
            except Exception:
                pass
            else:
                if ':' in decoded:
                    username, password = decoded.split(':', 1)
                    # login user
                    user = authenticate(username=username, password=password)
                    if user:
                        if user.is_active:
                            login(request, user)
                            return function(request, *args, **kwargs)
                        else:
                            msg = _('Your account is disabled.')
                    else:
                        msg = _('Your username and password do not match.')
        if msg is None:
            msg = _('Authentication required.')

        response = HttpResponse(msg, status=401)
        response['WWW-Authenticate'] = 'Basic realm="%s"' % _('Access authentication')
        return response
    return _wrapped_view


@login_required_basicauth
def login_basicauth(request, redirect_to=None):
    """
    Function to log users in using basicauth.
    """
    rt = request.GET.get('next')
    if not rt:
        rt = redirect_to
        if not rt:
            rt = '/'
    return HttpResponseRedirect(rt)


class CharactersTypesValidator:
    """
    Password validator to check that passwords contain at least 3 types of characters.
    Types are lower case letters, upper case letters, digits and special characters.
    """

    def validate(self, password, user=None):
        letter_types = 0
        if re.search(r'\d', password):
            letter_types += 1
        if re.search(r'[a-z]', password):
            letter_types += 1
        if re.search(r'[A-Z]', password):
            letter_types += 1
        if re.search(r'[^a-zA-Z\d]', password):
            letter_types += 1
        if letter_types < 3:
            raise ValidationError(
                _('The password must contain at least 3 types of characters (types are lower case letters, upper case letters, digits and special characters).'),
                code='password_characters_types',
            )

    def get_help_text(self):
        return _('The password must contain at least 3 types of characters (types are lower case letters, upper case letters, digits and special characters).')
