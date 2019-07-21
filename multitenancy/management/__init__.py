from django.core import exceptions


def get_default_domain(check_db=True):
    """
    Try to determine a site domain to use as a default.
    :param check_db: If ``True``, requires that the domain does not match an
        existing ``multitenancy.Site`` (otherwise returns an empty string).
    :returns: The domain, or an empty string if no domain can be
        determined.
    """
    # This file is used in apps.py, it should not trigger models import.
    from multitenancy import models as multitenancy_app

    # If the Site model has been swapped out, we can't make any assumptions
    # about the default user name.
    if multitenancy_app.Site._meta.swapped:
        return ''

    default_domain = 'localhost'

    # Run the domain validator
    try:
        multitenancy_app.Site._meta.get_field('domain').run_validators(default_domain)
    except exceptions.ValidationError:
        return ''

    # Don't return the default domain if it is already taken.
    if check_db and default_domain:
        try:
            multitenancy_app.Site._default_manager.get(domain=default_domain)
        except multitenancy_app.Site.DoesNotExist:
            pass
        else:
            return ''
    return default_domain
