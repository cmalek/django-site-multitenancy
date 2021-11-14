from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Group, PermissionsMixin, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from ..managers import TenantGroupManager
from .mixins import TenantSpecificModel
from .tenant import Tenant


User = get_user_model()


class TenantGroup(TenantSpecificModel):
    """
    This class  of django.contrib.auth.models.Group allows us to add a
    ForeignKey on our Tenant object and to have users that are in the Django
    Group only for specific tenants.
    """

    objects = TenantGroupManager()

    group = models.OneToOneField(Group, related_name="tenant_group")
    users = models.ManyToManyField(User, related_name='tenant_groups')

    def __str__(self):
        return f'{self.name}:{self.tenant.public_domain}'

    def natural_key(self):
        return (self.name, self.tenant.site.domain,)

    class Meta:
        verbose_name = _('tenant group')
        verbose_name_plural = _('tenant groups')


class TenantMembership(models.Model):

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='tenant_membership'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tenant_membership"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('tenant membership')
        verbose_name_pural = _('tenant memberships')
        unique_together = ('tenant', 'user',)


class AbstractTenantUser(AbstractBaseUser, PermissionsMixin):
    """
    Our own AbstractUser model.  We need this primarily to properly handle the
    `is_active` and `is_staff` fields, which are used often by auth backends and
    by the Django admin.
    """

    username_validator = UnicodeUsernameValidator()

    tenants = models.ManyToManyField(Tenant, through=TenantMembership)
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    _is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    _is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    @property
    def is_active(self):
        is_active = self._is_active or self._is_active is None
        return is_active and self.is_active_for_tenant()

    @is_active.setter
    def is_active(self, value):
        """
        We're just setting `self._is_active` here.  To manage a user
        for a particular `Tenant`, use `User.activate()` and `User.deactivate()`.
        """
        self._is_active = value

    @property
    def is_staff(self):
        return self._is_staff and self.is_staff_for_tenant()

    @is_staff.setter
    def is_staff(self, value):
        """
        We're just setting `self._is_staff` here.  To manage a user for a
        particular `Tenant`, use `User.make_staff()` and `User.remove_staff()`.
        """
        self._is_staff = value

    def add_to_tenant(self, tenant=None):
        if not tenant:
            tenant = Tenant.objects.get_current()
        try:
            self.tenants.get(tenant=tenant)
        except TenantMembership.DoesNotExist:
            membership = TenantMembership(tenant=tenant, user=self)
            membership.save()

    # is_staff

    @property
    def is_super_admin(self):
        """
        A user is a super admin if they are in one of the Django Groups
        associated with our TenantGroups.
        """
        group_ids = TenantGroup.objects.django_groups().values_list('id', flat=True)
        return self.groups.filter(id__in=group_ids).exists()

    def is_member(self, tenant=None):
        # First, see if this user is a super admin.  Super admins are people
        # who are  in any of the root Django Groups for our TenantGrouops
        if self.is_super_admin:
            return True
        if not tenant:
            tenant = Tenant.objects.get_current()
        try:
            TenantMembership.objects.get(tenant=tenant, user=self)
        except TenantMembership.DoesNotExist:
            return False
        return True

    def is_staff_for_tenant(self, tenant=None):
        if self.is_super_admin and self._is_staff:
            return True
        if not tenant:
            tenant = Tenant.objects.get_current()
        membership = TenantMembership.objects.get(tenant=tenant, user=self)
        return membership.is_staff

    def make_staff(self, tenant=None):
        """
        Set is_staff to True for this user on Tenant.
        """
        if not tenant:
            tenant = Tenant.objects.get_current()
        membership = TenantMembership.objects.get(tenant=tenant, user=self)
        membership.is_staff = True
        membership.save()

    def remove_staff(self, tenant=None):
        """
        Set is_staff to True for this user on Tenant.
        """
        if not tenant:
            tenant = Tenant.objects.get_current()
        membership = TenantMembership.objects.get(tenant=tenant, user=self)
        membership.is_staff = False
        membership.save()

    # is_active

    def is_active_for_tenant(self, tenant=None):
        if self.is_super_admin and self._is_active:
            return True
        if not tenant:
            tenant = Tenant.objects.get_current()
        membership = TenantMembership.objects.get(tenant=tenant, user=self)
        return membership.is_active

    def activate(self, tenant=None):
        """
        Set is_active to True for this user on Tenant.
        """
        if not tenant:
            tenant = Tenant.objects.get_current()
        membership = TenantMembership.objects.get(tenant=tenant, user=self)
        membership.is_active = True
        membership.save()

    def deactivate(self, tenant=None):
        """
        Set is_active to False for this user on Tenant.
        """
        if not tenant:
            tenant = Tenant.objects.get_current()
        membership = TenantMembership.objects.get(tenant=tenant, user=self)
        membership.is_active = False
        membership.save()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)
