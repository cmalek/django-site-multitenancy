from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q
from django.contrib.sites.managers import CurrentSiteManager
from django.http.request import split_domain_port
from django.http.response import HttpResponseBadRequest

from .exceptions import MissingHostException
from .signals import (
    pre_site_create,
    post_site_create
)


SITE_CACHE = {}


class SiteSpecificManager(CurrentSiteManager):

    def get_queryset(self):
        Site = apps.get_model('multitenancy', 'Site')
        site = Site.objects.get_current()
        if site:
            return super().get_queryset().filter(**{self._get_field_name() + '__id': site.id})
        else:
            return super().get_queryset()


class SiteAwareQuerySet(models.QuerySet):

    def in_site(self, site):
        return self.get_query_set().filter(site=site)


class SiteManager(models.Manager):
    use_in_migrations = True

    def _get_site_by_id(self, site_id):
        if site_id not in SITE_CACHE:
            site = self.get(pk=site_id)
            SITE_CACHE[site_id] = site
        return SITE_CACHE[site_id]

    def _get_site_by_request(self, request):
        try:
            host = request.get_host()
        except MissingHostException:
            # If no hostname was specified, we return a 400 error. This is only
            # able to happen in tests.
            return HttpResponseBadRequest(
                "No HTTP_HOST header detected. Site cannot be determined without one."
            )

        if ':' in host:
            domain, port = split_domain_port(host)
        else:
            domain = host
        if domain not in SITE_CACHE:
            SITE_CACHE[domain] = self.get(
                Q(domain__iexact=domain) | Q(aliases__domain__iexact=domain)
            )
        return SITE_CACHE[domain]

    def get_current(self, request=None):
        """
        Return the current Site based on the HTTP_HOST header.  The ``Site``
        object is cached the first time it's retrieved from the database.
        """
        if not request:
            try:
                from crequest.middleware import CrequestMiddleware
            except ImportError:
                pass
            else:
                request = CrequestMiddleware.get_request()

        if request:
            return self._get_site_by_request(request)

        raise ImproperlyConfigured(
            "You're using \"django-sites-multitenancy\" without having "
            "a current request. Pass a request object to Site.objects.get_current() "
            "to fix this error, or install django-crequest and use CrequestMiddleare."
        )

    def clear_cache(self):
        """Clear the ``Site`` object cache."""
        global SITE_CACHE
        SITE_CACHE = {}

    def get_by_natural_key(self, domain):
        return self.get(domain=domain)

    def _create_site(self, domain, site_name, **extra_fields):
        """
        Create and save a site with the given domain and site_name.
        """
        if not domain:
            raise ValueError('The given domain must be set')
        site = self.model(domain=domain, site_name=site_name, **extra_fields)
        pre_site_create.send(self.__class__, site=site)
        site.save(using=self._db)
        post_site_create.send(self.__class__, site=site)
        return site

    def create_site(self, domain, site_name, **extra_fields):
        extra_fields.setdefault('is_root_site', False)
        return self._create_site(domain, site_name, **extra_fields)

    def create_root_site(self, domain, site_name, **extra_fields):
        extra_fields.setdefault('is_root_site', True)
        if extra_fields.get('is_root_site') is not True:
            raise ValueError('Root sites must have is_root_site=True.')
        return self._create_site(domain, site_name, **extra_fields)


def clear_site_cache(sender, **kwargs):
    """
    Clear the cache (if primed) each time a site is saved or deleted.
    """
    instance = kwargs['instance']
    using = kwargs['using']
    Site = apps.get_model('multitenancy', 'Site')
    try:
        del SITE_CACHE[instance.pk]
    except KeyError:
        pass
    try:
        del SITE_CACHE[Site.objects.using(using).get(pk=instance.pk).domain]
    except (KeyError, Site.DoesNotExist):
        pass
