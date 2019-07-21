from django.apps import apps
from django.conf import settings
from django.core import checks


def check_site_model(app_configs=None, **kwargs):
    if app_configs is None:
        cls = apps.get_model(settings.MULTITENANCY_SITE_MODEL)
    else:
        app_label, model_name = settings.MULTITENANCY_SITE_MODEL.split('.')
        for app_config in app_configs:
            if app_config.label == app_label:
                cls = app_config.get_model(model_name)
                break
        else:
            # Checks might be run against a set of app configs that don't
            # include the specified user model. In this case we simply don't
            # perform the checks defined below.
            return []

    errors = []

    # Check that REQUIRED_FIELDS is a list
    if not isinstance(cls.REQUIRED_FIELDS, (list, tuple)):
        errors.append(
            checks.Error(
                "'REQUIRED_FIELDS' must be a list or tuple.",
                obj=cls,
                id='multitenancy.E001',
            )
        )

    # Check that the DOMAIN_FIELD isn't included in REQUIRED_FIELDS.
    if cls.DOMAIN_FIELD in cls.REQUIRED_FIELDS:
        errors.append(
            checks.Error(
                "The field named as the 'DOMAIN_FIELD' "
                "for a custom user model must not be included in 'REQUIRED_FIELDS'.",
                obj=cls,
                id='multitenancy.E002',
            )
        )

    # Check that the domain field is unique
    if not cls._meta.get_field(cls.DOMAIN_FIELD).unique:
        errors.append(
            checks.Error(
                "'%s.%s' must be unique because it is named as the 'USERNAME_FIELD'." % (
                    cls._meta.object_name, cls.USERNAME_FIELD
                ),
                obj=cls,
                id='auth.E003',
            )
        )

    return errors
