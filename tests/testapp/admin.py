from django_web_utils.admin_utils import register_module
# App models
from . import models

# Automatic admin configuration
register_module(models)
