from django.apps import apps as django_apps
from django.http import Http404
from django.shortcuts import get_object_or_404


def get_tenant_specific_object_or_404(klass, *args, **kwargs):
    """
    A site-aware version of django's get_object_or_404 shortcut.

    Example:

        get_site_specific_object_or_404(Stuff, id=1)
    """
    obj = get_object_or_404(klass, *args, **kwargs)
    Tenant = django_apps.get_model('multitenancy', 'Tenant')
    if obj and hasattr(obj, 'tenant'):
        if obj.tenant != Tenant.objects.get_current():
            raise Http404
    return obj
