
from django import forms

from .utils import get_current_site
from .models import SiteSpecificModel


class SiteSpecificModelForm(forms.ModelForm):
    """
    Use this class instead of ModelForm for any model that subclasses
    SiteSpecifcModel.

    SiteSpecificModelForm has two useful features:

    1. All ModelChoiceFields and ModelMultipleChoiceFields have their querysets
       filtered to show only the values for the current site.  This happens during
       form class instantiation.
    2. The form's clean() method sets the instance's site field to that of the
       current site, if instance.site is not None.

    Example::

        class StuffForm(SiteSpecificModelForm):

            class Meta:
                model = Stuff
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        site = get_current_site()
        if site:
            for field in self.fields.values():
                if isinstance(field, (
                    forms.ModelChoiceField,
                    forms.ModelMultipleChoiceField
                )):
                    if issubclass(field.queryset.model, SiteSpecificModel):
                        field.queryset = field.queryset.in_site(site)

    def clean(self):
        cleaned_data = super().clean()
        if hasattr(self.instance, 'site_id') and not self.instance.site_id:
            self.instance.site = get_current_site()
        return cleaned_data

    class Meta:
        exclude = ['site']
