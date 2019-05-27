
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site as DjangoSite
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .managers import SiteSpecificManager, SiteAwareQuerySet
from .utils import get_current_site
from .validators import PreferredHostnameValidator, get_domain_validators


class SiteAlias(models.Model):
    """
    This is a class to hold other domains by which a Site is also known.

    For example, your site might have these hostnames:

        foo.example.com
        www.foo.example.com
        m.foo.example.com

    Then on your ``Site`` object, you would set the 'domain' to
    "foo.example.com" and add SiteAliases (through the
    ``Site.aliases`` many-to-many relationship) for "www.foo.example.com"
    and "m.foo.example.com".
    """

    domain = models.CharField(
        max_length=100,
        unique=True,
        blank=False,
        validators=get_domain_validators(),
        error_messages={
            'unique': 'This domain name is already in use by another Site.'
        }
    )

    def __str__(self):
        return self.domain

    class Meta:
        verbose_name = _('site alias')
        verbose_name_plural = _('site aliases')


class Site(DjangoSite):
    """
    Make this a subclass of the django.contrib.sites.models.Site model.  This
    way, 3rd party modules that have django.contrib.sites support still work
    without modification.
    """

    preferred_domain = models.CharField(
        verbose_name='Preferred Domain',
        max_length=100,
        default='',
        blank=True,
        validators=[PreferredHostnameValidator()],
        help_text=mark_safe(
            "What domain name do you prefer people use for this site? <br>"
            "If set, this value must match a previously saved Site Alias. "
            "If left blank, this Site's canonical domain will be used, instead."
        )
    )
    permissions = models.ManyToManyField(
        SiteAlias,
        verbose_name=_('aliases'),
        blank=True
    )

    @property
    def public_domain(self):
        """
        Returns the public-facing domain for this site, which is the
        preferred_domain setting if it's set. Otherwise, it's the canonical domain.
        """
        return self.preferred_domain or self.domain


class SiteSpecificModel(models.Model):
    """
    Subclass this abstract Model to turn your model into a site-specific one.

    Example::

        from multitenancy.models import SiteSpecificModel

        class Stuff(SiteSpecificModel)
            description = models.CharField(max_length=200)

    SiteSpecificModel models have a Site-aware manager called site_objects:

        site_stuff = Stuff.site_objects.all()

    This will bring up all instances owned by the current site.
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
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
            self.site = get_current_site()
        super().clean()

    class Meta:
        abstract = True


class MultitenancyGroup(SiteSpecificModel, Group):
    """
    This subclass of django.contrib.auth.models.Group allows us to add a
    ForeignKey on our Site object.

    We do this so that we can easily determine which groups belong to a site,
    and through Group membership, determine which Users are allowed to login and
    act within asite.
    """
    pass

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')
