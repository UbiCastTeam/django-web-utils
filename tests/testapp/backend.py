from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User


class SettingsBackend(BaseBackend):
    '''
    Authenticate against the settings AUTHENTICATION_USERS.
    '''

    def _get_user_object(self, username, user_id, **info):
        user = User(id=user_id, username=username, **info)
        user.save = lambda *args, **kwargs: user
        user.delete = lambda *args, **kwargs: user
        return user

    def authenticate(self, request, username=None, password=None):
        user_dict = settings.AUTHENTICATION_USERS.get(username)
        if not user_dict or not user_dict.get('password'):
            return None
        pwd_valid = password == user_dict['password']
        if pwd_valid:
            user_id = list(settings.AUTHENTICATION_USERS.keys()).index(username) + 1
            user = self._get_user_object(username, user_id, **user_dict)
            return user
        return None

    def get_user(self, user_id):
        users = list(settings.AUTHENTICATION_USERS.keys())
        try:
            username = users[user_id - 1]
        except IndexError:
            return None
        else:
            user_dict = settings.AUTHENTICATION_USERS[username]
            user = self._get_user_object(username, user_id, **user_dict)
            return user
