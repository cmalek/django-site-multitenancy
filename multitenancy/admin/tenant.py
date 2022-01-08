#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.utils.html import format_html

from ..forms import TenantSpecificModelForm
from ..models import (
    Tenant,
    TenantGroup,
)

from django.core.exceptions import MultipleObjectsReturned
from django.shortcuts import redirect

try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse


class TenantSpecificSingleModelAdmin(admin.ModelAdmin):

    """
    Django ModelAdmin for models that should show only one model instance, that
    for the current tenant.

    This is useful for a tenant-wide settings model, among other things.

    * If there is only one object, the changelist will redirect to that object.
    * If there are no objects, the changelist will redirect to the add form.
    * If there are multiple objects, the changelist is displayed with a warning.

    Attempting to add a new record when there is already one will result in a
    warning and a redirect away from the add form.
    """

    def _get_model_name(self):
        try:
            return self.model._meta.model_name
        except AttributeError:
            return self.model._meta.module_name

    def changelist_view(self, request, extra_context=None):
        app_and_model = '{0}_{1}'.format(
            self.model._meta.app_label,
            self._get_model_name()
        )
        try:
            instance = self.model.objects.get(tenant=Tenant.objects.get_current())
        except self.model.DoesNotExist:
            return redirect(reverse('admin:{0}_add'.format(app_and_model)))
        except MultipleObjectsReturned:
            warning = ('There are multiple instances of {0}. There should only'
                       ' be one.').format(self._get_model_name())
            messages.warning(request, warning, fail_silently=True)
            return super().changelist_view(
                request,
                extra_context=extra_context
            )
        else:
            return redirect(
                reverse('admin:{0}_change'.format(app_and_model), args=[instance.pk])
            )

    def add_view(self, request, form_url='', extra_context=None):
        if self.model.objects.count():
            warning = ('Do not add additional instances of {0}. Only one is'
                       ' needed.').format(self._get_model_name())
            messages.warning(request, warning, fail_silently=True)
            return redirect(
                reverse('admin:{0}_{1}_changelist'.format(
                    self.model._meta.app_label,
                    self._get_model_name()
                ))
            )
        return super().add_view(
            request,
            form_url=form_url,
            extra_context=extra_context
        )

    def has_add_permission(self, request):
        try:
            self.model.objects.get()
        except self.model.DoesNotExist:
            return super().has_add_permission(request)
        except MultipleObjectsReturned:
            pass
        return False


class TenantSpecificModelAdmin(admin.ModelAdmin):
    """
    Use this with models that subclass TenantSpecificModel.
    """

    exclude = ('tenant',)

    # This is the form that will get subclassed by modelform_factory
    # in ModelAdmin.get_form()
    form = TenantSpecificModelForm

    def queryset(self, request):
        qs = super().queryset(request)
        return qs.filter(tenant=Tenant.objects.get_current())


# FIXME: this should be a SingleModelAdmin
class TenantAdmin(admin.ModelAdmin):
    """
    This allows a Tenant owner to manage the configs for their site.
    """
    list_display = ('get_domain', 'get_name', 'preferred_domain',)

    @admin.display(ordering='site__domain', description="Domain")
    def get_domain(self, obj):
        return obj.site.domain

    @admin.display(ordering='site__name', description="Site Name")
    def get_name(self, obj):
        return obj.site.name

    def alias_domains(self, obj):
        return format_html("<br />".join([alias.domain for alias in obj.aliases.all()]))
    alias_domains.short_description = "Domain Aliases attached to this tenant"


admin.site.unregister(Group)
admin.site.register(Tenant, TenantAdmin)
admin.site.register(TenantGroup, TenantSpecificModelAdmin)
