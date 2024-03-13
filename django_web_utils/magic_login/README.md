# Magic login for Django

This feature allows a list of predefined users to log in using their email address.
It is based on the Django mecanism to reset account passwords.


## Workflow

- A user goes to the magic login page.
- The user enters his email address.
- An email is sent to the user with a link to log in.
- The user clicks on the link.
- The user is logged in in the site.

Note: The link can be used only once and its validity duration can be configured with the Django setting `PASSWORD_RESET_TIMEOUT`.


## Setup

In your project `AUTHENTICATION_BACKENDS` setting, add `django_web_utils.magic_login.backend.MagicLoginBackend`.

Create a sub class of the view `django_web_utils.magic_login.views.MagicLoginView` and:
- Configure the class attributes:
    - `users_json_path: Path`
    - `template_view: str`
    - `template_email: Optional[str]`
- Implement the functions:
    - `create_user(self, info: dict) -> AbstractBaseUser`

More details are available in the [source file](./views.py).

Add the view sub class in your `urls.py`, for example:

```python
from django.urls import path

from myproject.views import MyMagicLoginView

urlpatterns = [
    # ...
    path('login-magic/', MyMagicLoginView.as_view(), name='login-magic'),
]
```
