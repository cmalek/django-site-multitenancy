from django.db import models

from ..managers import (
    SiteAwareQuerySet,
    SiteSpecificManager
)
from .tenant import Tenant


class TenantSpecificModel(models.Model):
    """
    Subclass this abstract Model to turn your model into a site-specific one.

    Example::

        from multitenancy.models import SiteSpecificModel

        class Stuff(SiteSpecificModel)
            description = models.CharField(max_length=200)

    ``SiteSpecificModel`` models have a Site-aware manager called ``site_objects``:

        site_stuff = Stuff.site_objects.all()

    This will bring up all instances owned by the current site.
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
    # the un-site filtered version so that.
    # https://docs.djangoproject.com/en/2.2/topics/db/managers/
    objects = SiteAwareQuerySet().as_manager()
    site_objects = SiteSpecificManager()

    def clean(self):
        """
        Override clean() to setting the "site" for the model, if the site
        is not already set.  This allows apps to not have to handle this bit.

        .. note::
            We do this here instead of save() because clean() gets called
            automatically when you save a form, but not when you create
            instances programatically - in that case you must call clean()
            yourself.

            In some cases, you might want to set or change the site on an
            existing object. all you need to do is avoid calling clean() after
            setting the value and it won't be overwritten.
        """

        if (hasattr(self, 'site_id') and not self.site_id):
            self.site = Site.objects.get_current()
        super().clean()

    class Meta:
        abstract = True
