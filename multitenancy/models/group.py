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

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')
        unique_together = ('site', 'name',)
