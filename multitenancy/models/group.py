from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from .mixins import SiteSpecificModel


class MultitenancyGroup(SiteSpecificModel, Group):
    """
    This subclass of django.contrib.auth.models.Group allows us to add a
    ForeignKey on our Site object.

    We do this so that we can easily determine which groups belong to a site,
    and through Group membership, determine which Users are allowed to login and
    act within asite.
    """

    # Need Validator here to enforce site, group__name unique_together
    # https://stackoverflow.com/questions/3866770/error-using-a-base-class-field-in-subclass-unique-together-meta-option/3866966#3866966

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')
