import re
from typing import Optional

from django import forms
from django.utils.translation import gettext_lazy as _


class RequestMagicLoginForm(forms.Form):
    EMAIL_REGEX = r'[\w\-\_\.\+]+(\+[\w\-\_\.]+){0,1}@[\w\-\_\.]+'

    email = forms.CharField(label=_('Email address'), max_length=254, required=True)

    def clean_email(self) -> str:
        email = self.cleaned_data.get('email', '')
        if not re.match(self.EMAIL_REGEX, email):
            raise forms.ValidationError(_('Invalid email address.'))
        return email

    def get_email(self) -> Optional[str]:
        if hasattr(self, 'cleaned_data'):
            return self.cleaned_data.get('email')
