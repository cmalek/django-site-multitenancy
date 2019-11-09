from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from ..managers import (
    SiteManager,
    clear_site_cache
)
from ..validators import PreferredHostnameValidator, get_domain_validators


class Site(models.Model):

    domain = models.CharField(
        _('Domain Name'),
        max_length=255,
        validators=get_domain_validators(),
        unique=True,
    )

    site_name = models.CharField(
        verbose_name=_('Site Name'),
        max_length=255,
        help_text=_("Human-readable name for the site.")
    )

    preferred_domain = models.CharField(
        verbose_name='Preferred Domain',
        max_length=100,
        default='',
        blank=True,
        validators=[PreferredHostnameValidator],
        help_text=mark_safe(
            "What domain name do you prefer people use for this site? <br>"
            "If set, this value must match a previously saved Site Alias. "
            "If left blank, this Site's canonical domain will be used, instead."
        )
    )

    is_root_site = models.BooleanField(
        verbose_name=_('Is Root Site'),
        default=False,
        help_text=_(
            "If true, this site will host only the admin interface for managing other sites."
        )
    )

    # Keep track of when things were last created or modified.  We always wanted to know this, and regretted on our own
    # implementation that we didn't have it.
    created_at = models.DateTimeField('Created At', auto_now_add=True)
    updated_at = models.DateTimeField('Last Modified At', auto_now=True)

    objects = SiteManager()

    DOMAIN_FIELD = 'domain'
    REQUIRED_FIELDS = ['site_name']

    @property
    def public_domain(self):
        """
        Returns the public-facing domain for this site, which is the
        preferred_domain setting if it's set. Otherwise, it's the canonical domain.
        """
        return self.preferred_domain or self.domain

    class Meta:
        db_table = 'multitenancy_site'
        verbose_name = _('site')
        verbose_name_plural = _('sites')
        ordering = ('domain',)

    def get_domain(self):
        """Return the domain for this Site."""
        return getattr(self, self.DOMAIN_FIELD)

    def __str__(self):
        return self.get_domain()

    def natural_key(self):
        return (self.get_domain(),)

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude)
        # Only one site can have the is_root_site flag set
        Site = type(self)
        try:
            root = Site.objects.get(is_root_site=True)
        except Site.DoesNotExist:
            pass
        except Site.MultipleObjectsReturned:
            raise
        else:
            if self.is_root_site and self.pk != root.pk:
                raise ValidationError(
                    {'is_root_site': [
                        _(
                            "%(hostname)s is already configured as the root site."
                            " You cannot create a second root site."
                        )
                        % {'hostname': root.hostname}
                    ]}
                )


pre_save.connect(clear_site_cache, sender=Site)
pre_delete.connect(clear_site_cache, sender=Site)


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

    site = models.ForeignKey(
        Site,
        verbose_name=_('Site'),
        related_name='aliases',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.domain

    class Meta:
        verbose_name = _('Site Alias')
        verbose_name_plural = _('Site Aliases')

