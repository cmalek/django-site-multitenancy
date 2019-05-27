from django.db import models
from django.contrib.sites.managers import CurrentSiteManager

from .utils import get_current_site


class SiteSpecificManager(CurrentSiteManager):

    def get_queryset(self):
        site = get_current_site()
        if site:
            return super().get_queryset().filter(**{self._get_field_name() + '__id': site.id})
        else:
            return super().get_queryset()


class SiteAwareQuerySet(models.QuerySet):

    def in_site(self, site):
        return self.get_query_set().filter(site=site)
