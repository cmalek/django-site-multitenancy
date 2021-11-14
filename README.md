`django-site-multitenancy` provides multitenancy support to your Django users
and users.

## Overview

[Multitenancy](https://en.wikipedia.org/wiki/Multitenancy) in software is an
architecture that allows software running on a server to simultaneously
serve multiple, entirely separate groups of people, called tenants.   The
software is architected in such a way that each tenant gets its own sandboxed
slice of the system resources.  A tenant sees and can affect only their
resources within the system -- data, users, tenant-specific features, etc..

There are typically four solutions for solving the multitenancy problem.

* Parallel installs: each tenant gets its own instance of the software on the
  system, with their own data stores.
* Database-per-tenant: One instance of the software, but one backend data store
  per tenant, and use per-tenant data store configuration.
* Table prefixing: one instance of the software, one data store, but each tenant
  gets its own copy of the relavent tables, with table names appropriately
  prefixed.  The software applies the appropriate prefix when looking for the
  tenants' data.
* Full-multitenancy: one instance of the software, one unified data store,
  shared tables.  A main table identifies the tenants, and all other tables have
  a foreign key into that table.  The software then filters all data by the
  approprate record in the tenant table.

`django-site-multitenancy` implements this last, "full multitenancy" model by
extending the `django.contrib.sites` and `django.contrib.auth` packages
appropriately.

## Installation and Setup

The easiest way to install `django-site-multitenancy` is directly from PyPi using
pip by running the following command:

```
$ pip install -U django-site-multitenancy
```

Otherwise you can download `django-site-multitenancy` and install it directly
from source:

```
$ python setup.py install
```

Add `multitenancy` to `settings.INSTALLED_APPS`:

```
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django.contrib.admin",
    'multitenancy',
]    
```

If you're using a custom `settings.AUTH_USER_MODEL`, add `multitenancy` to
`INSTALLED_APPS` after the app that that model is in.
`django-site-multitenancy` sets up some special Django admin site bits that need
the `settings.AUTH_USER_MODEL` to be registered properly.  E.g.

```
INSTALLED_APPS = [
    'django.contrib.auth',
    ...
    'custom_auth',  # Application that our settings.AUTH_USER_MODEL is in
    'multitenancy',
]    
```
 
Add `crequest.middleware.CrequestMiddleware` and
`multitenancy.middleware.TenantSelectingMiddleware` to your `settings.MIDDLEWARE`:

```
MIDDLEWARE = [
    # Django middleware goes here
    ...

    # Enables the use of the multitenancy.utils.get_current_tenant() function
    'crequest.middleware.CrequestMiddleware',
    # Our middleware
    'multitenancy.middleware.TenantSelectingMiddleware',
]
```

## How to use

### Tenants

`multitenancy.models.Tenant is a model that ... TBD.

### Request-based Tenant determination

The current tenant for each request is determined by `TenantSelectingMiddleware`, a
Django middleware that compares the `HTTP_HOST` header for the request to the
domain name and domain aliases for each tenant in the system, and choosing the one
that matches, and attaching it to the current request as `request.tenant.

### Models

To make a tenant-aware model, simply subclass django-site-multitenancy's
`TenantSpecificModel`.  This has a `django.models.ForeignKey` on
`multitenancy.models.Tenant`, and provides some special Managers.

Example:

```
from django.db import models
from multitenancy.models import TenantSpecificModel

class Stuff(TenantSpecificModel)

    description = models.CharField(max_length=200)
```

`TenantSpecificModel` subclasses have a Manager called `tenant_objects` which
automatically filters model records to only those in the current tenant:

```
tenant_specific_things = Stuff.tenant_objects.all()
```

For those times when you want to operate on all records for a model,
`TenantSpecificModel.objects` does not filter objects to only those in the current
tenant.  It does, however, have an additional `.in_tenant(tenant)` filter, which will
allow you to easily filter objects to only those in that tenant, where tenant is a
`multitenancy.models.Tenant` object.

```
tenant_specific_things = Stuff.objects.in_tenant(tenant).all()
```

### Forms

For any model that subclasses `TenantSpecificModel`, you'll want to use a
`TenantSpecificModelForm` instead of django's `ModelForm`.  The
`TenantSpecificModelForm` has two useful features:

1. All `ModelChoiceField` and `ModelMultipleChoiceField` fields on the form have
   their querysets filtered to show only the values for the current tenant.  This
   happens during form class instantiation.
1. The form's `clean()` method sets the instance's "tenant" field to that of the
   tenant chosen by `TenantSelectingMiddleware`, if "tenant" was not already set.  

Example:

```
class StuffForm(TenantSpecificModelForm):

   class Meta:
       model = Stuff
```

Note that we don't need to worry about filtering the options available for each
form field.  You should exclude the tenant form field as above, not out of
security concerns but rather to avoid complications while cleaning the form.
    

### Django Admin 

If you use `TenantSpecificModelAdmin` as your `ModelAdmin` class for your
`TenantSpecificModel` subclass, you will see only the instances for the tenant
chosen by `TenantSelectingMiddleware` when you login to the Django admin interface
for that tenant.

Example:

```
from django.contrib import admin
from multitenancy.admin import TenantSpecificModelAdmin
from myapp.models import Stuff

admin.site.register(Stuff, TenantSpecificModelAdmin)    
```

### Utilities

A tenant-aware version of Django's `get_object_or_404` shortcut:

```
from multitenancy.utils import get_tenant_specific_object_or_404

get_tenant_specific_object_or_404(Stuff, id=1)
```

To get the `Tenant` instance for the current request:

```
from multitenancy.middleware import get_current_tenant

tenant = get_current_tenant()
```


## Special Considerations and Warnings

### Uniqueness constraints

Add the "tenant" field to any uniqueness constraints for tenant-aware models; 

```
unique_together = (("name", "tenant"), ("code", "tenant"),)
```

