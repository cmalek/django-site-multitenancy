from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_text


def get_domain_validators():
    """
    Returns the list of validators that ensure the hostname is correctly
    formatted and not in use by another Tenant.

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
    Validates that the input doesn't match any existing Tenant's hostname.
    """

    def __call__(self, value):
        text_value = force_text(value)
        # We do this to avoid circular imports on Tenant
        Tenant = apps.get_model('multitenancy', 'Tenant')
        if Tenant.objects.filter(site__domain=text_value).exists():
            raise ValidationError(
                'This domain name is already in use by another Tenant.',
                'invalid'
            )
        return True


@deconstructible
class PreferredHostnameValidator:
    """
    Validates that the input matches one of the Tenant's aliases or the Tenant's
    domain
    """

    def __call__(self, value):
        text_value = force_text(value)
        Tenant = apps.get_model('multitenancy', 'Tenant')
        tenant = Tenant.objects.get_current()
        if (text_value not in [alias.domain for alias in tenant.aliases.all()] and
                text_value != tenant.site.domain):
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
    correctly when adding aliases.  But when adding a new Tenant, its hostname
    field isn't checked against SiteAlias's domain field.
    """

    def __call__(self, value):
        text_value = force_text(value)
        SiteAlias = apps.get_model('multitenancy', 'SiteAlias')
        try:
            SiteAlias.object.get(domain=text_value)
        except SiteAlias.DoesNotExist:
            pass
        else:
            raise ValidationError(
                'This domain name is already in use by another Tenant.',
                'invalid'
            )
        return True
