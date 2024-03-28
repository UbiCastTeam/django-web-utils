from functools import cached_property
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest

from django_web_utils.magic_login.tokens import check_token


class MagicLoginBackend(BaseBackend):
    """
    Authentication backend for the magic login feature.
    """

    def authenticate(self, request: HttpRequest, magic_login_id: Optional[int]) -> Optional[AbstractBaseUser]:
        if not magic_login_id:
            return
        user = self.get_user(user_id=magic_login_id)
        if not user:
            return
        if not check_token(user, request.session.session_key, request.GET.get('t', '')):
            return
        if user.password:
            # Users using the magic link feature are not allowed to log in using a password
            user.password = ''
            user.save(update_fields=['password'])
        return user

    def get_user(self, user_id: int) -> Optional[AbstractBaseUser]:
        try:
            return self.user_model.objects.get(pk=user_id)
        except self.user_model.DoesNotExist:
            return None

    @cached_property
    def user_model(self) -> type[AbstractBaseUser]:
        return get_user_model()
