#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from django.db.models import Exists, OuterRef, Q
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission

from .models import Tenant


User = get_user_model()


class TenantModelBackend(ModelBackend):

    def _get_group_permissions(self, user_obj):
        """
        We're overriding ModelBackend._get_group_permissions here so we can
        return the permissions we get through both of the `Group` and
        `TenantGroup` memberships for `user_obj`.
        """
        # First get base Django groups that the user is a member ofj
        user_groups_field = get_user_model()._meta.get_field('groups')
        user_groups_query = 'group__%s' % user_groups_field.related_query_name()
        base_groups_q = Q(**{user_groups_query: user_obj})
        # Now look at the tenant groups for our site and see if the user is a member of
        # any of those
        tenant_groups_q = Q(
            group__tenant_group__users=user_obj,
            group__tenant_group__tenant=Tenant.objects.get_current()
        )
        return Permission.objects.filter(base_groups_q | tenant_groups_q).distinct()

    def _get_permissions(self, user_obj, obj, from_name):
        """
        Return the permissions of `user_obj` from `from_name`. `from_name` can
        be either "group" or "user" to return permissions from
        `_get_group_permissions` or `_get_user_permissions` respectively.

        We're overriding `ModelBackend._get_permissions` here so we can do
        per-Tenant caching of permissions.
        """
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()

        tenant = Tenant.objects.get_current()
        if tenant is None:
            tenant_name = 'base'
        else:
            tenant_name = tenant.site.domain.replace('-.', '_')
        perm_cache_name = '_%s_%s_perm_cache' % (from_name, tenant_name)
        if not hasattr(user_obj, perm_cache_name):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            else:
                perms = getattr(self, '_get_%s_permissions' % from_name)(user_obj)
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            setattr(user_obj, perm_cache_name, {"%s.%s" % (ct, name) for ct, name in perms})
        return getattr(user_obj, perm_cache_name)

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        tenant = Tenant.objects.get_current()
        if tenant is None:
            tenant_name = 'base'
        else:
            tenant_name = re.sub(r'[-.]', '_', tenant.site.domain)
        perm_cache_name = '_%s_perm_cache' % tenant_name
        if not hasattr(user_obj, perm_cache_name):
            setattr(user_obj, perm_cache_name, super().get_all_permissions(user_obj))
        return getattr(user_obj, perm_cache_name)

    def with_perm(self, perm, is_active=True, include_superusers=True, obj=None,
                  include_super_admins=True, tenant=None):
        """
        Return users that have permission "perm". By default, filter out
        inactive users and include superusers and super_admins.
        """
        if isinstance(perm, str):
            try:
                app_label, codename = perm.split('.')
            except ValueError:
                raise ValueError(
                    'Permission name should be in the form '
                    'app_label.permission_codename.'
                )
        elif not isinstance(perm, Permission):
            raise TypeError(
                'The `perm` argument must be a string or a permission instance.'
            )

        UserModel = get_user_model()
        if obj is not None:
            return UserModel._default_manager.none()

        if not tenant:
            tenant = Tenant.objects.get_current()

        # Super admins are members of the Django Group
        permission_q = Q(
            group__tenant_membership__user=OuterRef('pk'),
            group__tenant_membership__tenant=tenant
        )
        permission_q |= Q(user=OuterRef('pk'))
        if include_super_admins:
            # Super admins are members of the Django Group
            permission_q |= Q(group__user=OuterRef('pk'))
        if isinstance(perm, Permission):
            permission_q &= Q(pk=perm.pk)
        else:
            permission_q &= Q(codename=codename, content_type__app_label=app_label)

        user_q = Exists(Permission.objects.filter(permission_q))
        if include_superusers:
            user_q |= Q(is_superuser=True)
        if is_active is not None:
            user_q &= Q(_is_active=is_active)
            user_q &= Q(
                tenant_membership__is_active=is_active,
                tenant_members__tenant=tenant
            )

        return UserModel._default_manager.filter(user_q)
