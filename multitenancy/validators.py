from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_text


def get_domain_validators():
    """
    Returns the list of validators that ensure the hostname is correctly
    formatted and not in use by another Site.

    :rtype: a list of validator classes
    """
    regex_validator = RegexValidator(
        r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)+([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$",
        'Please enter a valid domain name, e.g. example.com.'
    )
    return [regex_validator, HostnameValidator(), AliasValidator()]


@deconstructible
class HostnameValidator:
    """
    Validates that the input doesn't match any existing Site's hostname.
    """

    def __call__(self, value):
        text_value = force_text(value)
        # We do this to avoid circular imports on Site
        Site = apps.get_model('multitenancy', 'Site')
        if Site.objects.filter(domain=text_value).exists():
            raise ValidationError(
                'This domain name is already in use by another Site.',
                'invalid'
            )
        return True


@deconstructible
class PreferredHostnameValidator:
    """
    Validates that the input matches one of the Site's aliases.
    """

    def __call__(self, value):
        text_value = force_text(value)
        Site = apps.get_model('multitenancy', 'Site')
        site = Site.objects.get_current()
        if text_value not in [alias.domain for alias in site.alias_set.all()]:
            raise ValidationError(
                'You must first save a Domain Name Alias, then set this field '
                'to match one of those Aliases.',
                'invalid'
            )
        return True


@deconstructible
class AliasValidator:
    """
    The Alias model has its domain field set to unique, so it can validate
    correctly when adding aliases.  But when adding a new Site, its hostname
    field isn't checked against SiteAlias's domain field.
    """

    def __call__(self, value):
        text_value = force_text(value)
        Site = apps.get_model('multitenancy', 'Site')
        for site in Site.objects.all():
            if text_value in [alias.domain for alias in site.alias_set.all()]:
                raise ValidationError(
                    'This domain name is already in use by another Site.',
                    'invalid'
                )
        return True
