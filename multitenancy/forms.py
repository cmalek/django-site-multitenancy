from django import forms

from .models import TenantSpecificModel, Tenant


class TenantSpecificModelForm(forms.ModelForm):
    """
    Use this class instead of ModelForm for any model that subclasses
    TenantSpecifcModel.

    TenantSpecificModelForm has two useful features:

    1. All ModelChoiceFields and ModelMultipleChoiceFields have their querysets
       filtered to show only the values for the current tenant if the model
       referenced is a subclass of TenantSpecificModel.  This happens during
       form class instantiation.
    2. The form's clean() method sets the instance's tenant field to that of the
       current tenant, if instance.tenant is not None.

    Example::

        class StuffForm(TenantSpecificModelForm):

            class Meta:
                model = Stuff
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tenant = Tenant.objects.get_current()
        if tenant:
            for field in self.fields.values():
                if isinstance(field, (
                    forms.ModelChoiceField,
                    forms.ModelMultipleChoiceField
                )):
                    if issubclass(field.queryset.model, TenantSpecificModel):
                        field.queryset = field.queryset.in_tenant(tenant)

    def clean(self):
        cleaned_data = super().clean()
        if hasattr(self.instance, 'tenant_id') and not self.instance.tenant_id:
            self.instance.tenant = Tenant.objects.get_current()
        return cleaned_data

    class Meta:
        exclude = ['tenant']
