"""
By default, django-admin will show you all model instances.  In a multitenant
project, you might want to "visit" a site's account, and see just the instances
that belong to them.  If you use MultitenantAdmin as your ModelAdmin class, you
will see only the instances for the Site you are currently logged into.

You can then visit any tenant you please, by changing the Tenant linked to your
own user profile.

example:

    from django.contrib import admin
    from multitenancy.admin import MultitenantAdmin
    from myapp.models import *

    admin.site.register(BugReport, MultitenantAdmin)
"""

from django.contrib import admin

from .forms import SiteSpecificModelForm
from .utils import get_current_site
from .models import Site

admin.site.register(Site)


class SiteSpecificModelAdmin(admin.ModelAdmin):
    exclude = ('site',)

    # Filter all relation fields' querysets by site
    form = SiteSpecificModelForm

    def queryset(self, request):
        qs = super().queryset(request)
        return qs.filter(site=get_current_site())
