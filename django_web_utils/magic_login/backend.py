from functools import cached_property
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest


class MagicLoginBackend(BaseBackend):

    def authenticate(
        self, request: HttpRequest, magic_login_user: Optional[AbstractBaseUser] = None
    ) -> Optional[AbstractBaseUser]:
        if not magic_login_user:
            return
        if magic_login_user.password:
            # Users using the magic link feature are not allowed to log in using a password
            magic_login_user.password = ''
            magic_login_user.save(update_fields=['password'])
        return magic_login_user

    def get_user(self, user_id: int) -> Optional[AbstractBaseUser]:
        try:
            return self.user_model.objects.get(pk=user_id)
        except self.user_model.DoesNotExist:
            return None

    @cached_property
    def user_model(self) -> type[AbstractBaseUser]:
        return get_user_model()
