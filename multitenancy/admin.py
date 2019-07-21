"""
By default, django-admin will show you all model instances.  In a multitenant
project, you might want to "visit" a site's account, and see just the instances
that belong to them.  If you use MultitenantAdmin as your ModelAdmin class, you
will see only the instances for the Site you are currently logged into.

You can then visit any tenant you please, by changing the Tenant linked to your
own user profile.

example:

    from django.contrib import admin
    from multitenancy.admin import MultitenantAdmin
    from myapp.models import *

    admin.site.register(BugReport, MultitenantAdmin)
"""

from django.contrib import admin, messages
from django.contrib.sites.models import Site as DjangoSite
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.models import Group
from django.utils.html import format_html

from .forms import SiteSpecificModelForm
from .models import Site, MultitenancyGroup

from django.core.exceptions import MultipleObjectsReturned
from django.shortcuts import redirect

try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse


class SiteSpecificSingleModelAdmin(admin.ModelAdmin):

    """
    Django ModelAdmin for models that should show only one model, that
    for the current site.

    This is useful for a site-wide settings model, among other things.

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
            instance = self.model.objects.get(site=Site.objects.get_current())
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


class SuperAdminSite(admin.AdminSite):
    """
    This will be the Admin site that super admins log into in order
    to manage multiteanancy sites, groups and users.
    """
    site_header = "Super Admin"
    site_title = "Super Admin Portal"
    index_title = "Welcome to the Super Admin Site"


super_admin = SuperAdminSite(name="super_admin")


class MultitenancyGroupAdmin(auth_admin.GroupAdmin):
    search_fields = ('name', 'site__domain')
    ordering = ('site__domain', 'name')
    list_display = ('site__domain', 'site__name')
    filter_horizontal = ('permissions',)


# Ensure that this one only gets shown to install admins
super_admin.register(Site)
super_admin.register(MultitenancyGroup, MultitenancyGroupAdmin)


# ---------------------------------------------------------------
# Normal site specific admin interface.
#
# Only SiteSpecificModelAdmin classes should show up here.
# ---------------------------------------------------------------


class SpecificSiteAdmin(admin.ModelAdmin):
    list_display = ('domain', 'preferred_domain', 'alias_domains')

    def alias_domains(self, obj):
        return format_html("<br />".join([alias.domain for alias in obj.aliases.all()]))
    alias_domains.short_description = "Domain Aliases attached to this site"


admin.site.unregister(Group)
admin.site.unregister(DjangoSite)


class SiteSpecificModelAdmin(admin.ModelAdmin):
    """
    Use this with models that subclass SiteSpecificModel.
    """

    exclude = ('site',)

    # Filter all relation fields' querysets by site
    form = SiteSpecificModelForm

    def queryset(self, request):
        qs = super().queryset(request)
        return qs.filter(site=Site.objects.get_current())


admin.site.register(MultitenancyGroup, SiteSpecificModelAdmin)
