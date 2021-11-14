from crequest.middleware import CrequestMiddleware
from django.apps import apps
from django.contrib.sites.models import Site
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import Group
from django.contrib.sites.managers import CurrentSiteManager
from django.http.request import split_domain_port
from django.http.response import HttpResponseBadRequest

from .exceptions import MissingHostException
from .signals import (
    pre_tenant_create,
    post_tenant_create
)


TENANT_CACHE = {}


class TenantSpecificManager(CurrentSiteManager):

    def get_queryset(self):
        Tenant = apps.get_model('multitenancy', 'Tenant')
        tenant = Tenant.objects.get_current()
        if tenant:
            return super().get_queryset().filter(**{self._get_field_name() + '__id': tenant.id})
        else:
            return super().get_queryset()


class TenantAwareQuerySet(models.QuerySet):

    def in_tenant(self, tenant):
        return self.get_query_set().filter(tenant=tenant)


class TenantManager(models.Manager):
    use_in_migrations = True

    def _get_tenant_by_id(self, tenant_id):
        if tenant_id not in TENANT_CACHE:
            tenant = self.get(pk=tenant_id)
            TENANT_CACHE[tenant_id] = tenant
        return TENANT_CACHE[tenant_id]

    def _get_tenant_by_request(self, request):
        try:
            host = request.get_host()
        except MissingHostException:
            # If no hostname was specified, we return a 400 error. This is only
            # able to happen in tests.
            return HttpResponseBadRequest(
                "No HTTP_HOST header detected. Tenant cannot be determined without one."
            )

        if ':' in host:
            domain, port = split_domain_port(host)
        else:
            domain = host
        if domain not in TENANT_CACHE:
            TENANT_CACHE[domain] = self.get(
                Q(site__domain__iexact=domain) | Q(aliases__domain__iexact=domain)
            )
        return TENANT_CACHE[domain]

    def get_current(self, request=None):
        """
        Return the current Tenant based on the HTTP_HOST header.  The ``Tenant``
        object is cached the first time it's retrieved from the database.
        """
        if request:
            return self._get_tenant_by_request(request)
        else:
            request = CrequestMiddleware.get_request()

    def clear_cache(self):
        """Clear the ``Site`` object cache."""
        global TENANT_CACHE
        TENANT_CACHE = {}

    def get_by_natural_key(self, domain):
        return self.get(site__domain=domain)

    def _create_site(self, domain, site_name, **extra_fields):
        """
        Create and save a site with the given domain and site_name.
        """
        if not domain:
            raise ValueError('domain is required')
        if not site_name:
            raise ValueError('site_name is required')
        Tenant = apps.get_model('multitenancy', 'Tenant')
        site = Site(domain=domain, name=site_name)
        site.save(using=self._db)
        tenant = Tenant(
            site=site,
            is_root_site=extra_fields['is_root_site']
        )
        pre_tenant_create.send(self.__class__, tenant=tenant)
        tenant.save(using=self._db)
        post_tenant_create.send(self.__class__, site=site)
        return site

    def create_site(self, domain, site_name, **extra_fields):
        extra_fields.setdefault('is_root_site', False)
        return self._create_site(domain, site_name, **extra_fields)

    def create_root_site(self, domain, site_name, **extra_fields):
        extra_fields.setdefault('is_root_site', True)
        if extra_fields.get('is_root_site') is not True:
            raise ValueError('Root sites must have is_root_site=True.')
        return self._create_site(domain, site_name, **extra_fields)


class TenantGroupManager(models.Manager):

    def django_groups(self):
        return Group.objects.filter(tenant_group__isnull=False)


def clear_tenant_cache(sender, **kwargs):
    """
    Clear the cache (if primed) each time a site is saved or deleted.
    """
    instance = kwargs['instance']
    using = kwargs['using']
    Tenant = apps.get_model('multitenancy', 'Tenant')
    try:
        del TENANT_CACHE[instance.pk]
    except KeyError:
        pass
    try:
        del TENANT_CACHE[Tenant.objects.using(using).get(pk=instance.pk).domain]
    except (KeyError, Tenant.DoesNotExist):
        pass
