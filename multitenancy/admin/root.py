#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.auth import admin as auth_admin

from ..models import (
    Tenant,
    TenantGroup,
    SiteAlias
)


class SuperAdminSite(admin.AdminSite):
    """
    This will be the Admin site that super admins log into in order
    to manage tenants, groups and users.
    """
    site_header = "Super Admin"
    site_title = "Super Admin Portal"
    index_title = "Welcome to the Super Admin Site"


class SuperTenantGroupAdmin(auth_admin.GroupAdmin):
    search_fields = ('name', 'tenant__site__domain',)
    ordering = ('tenant__site__domain', 'group__name',)
    list_display = ('tenant', 'get_name',)
    # FIXME: figure out how to filter tenant groups based on permissions on the associated django group
    filter_horizontal = ()

    @admin.display(ordering='group__name', description="Site Name")
    def get_name(self, obj):
        return obj.group.name


class SiteAliasInline(admin.TabularInline):
    model = SiteAlias


class SuperTenantAdmin(admin.ModelAdmin):
    inlines = [SiteAliasInline]
    search_fields = ('site__domain', 'site__name', 'aliases__domain')
    ordering = ('site__domain', 'site__name',)
    list_display = (
        'get_domain',
        'get_name',
        'preferred_domain',
        'created_at',
    )
    fields = (
        'site',
        'preferred_domain',
        ('created_at', 'updated_at'),
    )
    readonly_fields = ('created_at', 'updated_at',)

    @admin.display(ordering='site__domain', description="Domain")
    def get_domain(self, obj):
        return obj.site.domain

    @admin.display(ordering='site__name', description="Site Name")
    def get_name(self, obj):
        return obj.site.name

    def get_queryset(self, request):
        """
        This filters out the root site.  Make people edit the root site with
        ./manage.py updaterootsite.
        """
        return super().get_queryset(request).exclude(is_root_site=True)


# Ensure that this one only gets shown to super admins
super_admin = SuperAdminSite(name="super_admin")
super_admin.register(Tenant, SuperTenantAdmin)
super_admin.register(TenantGroup, SuperTenantGroupAdmin)
