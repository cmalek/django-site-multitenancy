from django.db import models

from ..managers import (
    TenantAwareQuerySet,
    TenantSpecificManager
)
from .tenant import Tenant


class TenantSpecificModel(models.Model):
    """
    Subclass this abstract Model to turn your model into a tenant-specific one.

    Example::

        from multitenancy.models import TenantSpecificModel

        class Stuff(TenantSpecificModel)
            description = models.CharField(max_length=200)

    ``TenantSpecificModel`` models have a Tenant-aware manager called ``tenant_objects``:

        tenant_stuff = Stuff.tenant_objects.all()

    This will bring up all instances owned by the current tenant.
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)ss",
        related_query_name="%(app_label)s_%(class)ss",
        null=False
    )

    # Django gives special treatment to the first Manager declared within a
    # Model; it becomes the default manager.  Thus we set objects to
    # the un-tenant filtered version so that.
    # https://docs.djangoproject.com/en/2.2/topics/db/managers/
    objects = TenantAwareQuerySet().as_manager()
    tenant_objects = TenantSpecificManager()

    def clean(self):
        """
        Override clean() to setting the "tenant" for the model, if the tenant
        is not already set.  This allows apps to not have to handle this bit.

        .. note::
            We do this here instead of save() because clean() gets called
            automatically when you save a form, but not when you create
            instances programatically - in that case you must call clean()
            yourself.

            In some cases, you might want to set or change the tenant on an
            existing object. all you need to do is avoid calling clean() after
            setting the value and it won't be overwritten.
        """

        if (hasattr(self, 'tenant_id') and not self.tenant_id):
            self.tenant = Tenant.objects.get_current()
        super().clean()

    class Meta:
        abstract = True
