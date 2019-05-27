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
 
Add `crequest.middleware.CrequestMiddleware` and
`multitenancy.middleware.SiteSelectingMiddleware` to your `settings.MIDDLEWARE`:

```
MIDDLEWARE = [
    # Django middleware goes here
    ...

    # Enables the use of the multitenancy.utils.get_current_site() function
    'crequest.middleware.CrequestMiddleware',
    # Our middleware
    'multitenancy.middleware.SiteSelectingMiddleware',
]
```

## How to use

### Sites

`multitenancy.models.Site` is a model that ... TBD.

### Request-based Site determination

The current site for each request is determined by `SiteSelectingMiddleware`, a
Django middleware that compares the `HTTP_HOST` header for the request to the
domain name and domain aliases for each site in the system, and choosing the one
that matches, and attaching it to the current request as `request.site`.

### Models

To make a site-aware model, simply subclass django-site-multitenancy's
`SiteSpecificModel`.  This has a `django.models.ForeignKey` on
`multitenancy.models.Site`, and provides some special Managers.

Example:

```
from django.db import models
from multitenancy.models import SiteSpecificModel

class Stuff(SiteSpecificModel)

    description = models.CharField(max_length=200)
```

`SiteSpecificModel` subclasses have a Manager called `site_objects` which
automatically filters model records to only those in the current site:

```
site_specific_things = Stuff.site_objects.all()
```

For those times when you want to operate on all records for a model,
`SiteSpecificModel.objects` does not filter objects to only those in the current
site.  It does, however, have an additional `.in_site(site)` filter, which will
allow you to easily filter objects to only those in that site, where site is a
`multitenancy.models.Site` object.

```
site_specific_things = Stuff.objects.in_site(site).all()
```

### Forms

For any model that subclasses `SiteSpecificModel`, you'll want to use a
`SiteSpecificModelForm` instead of django's `ModelForm`.  The
`SiteSpecificModelForm` has two useful features:

1. All `ModelChoiceField` and `ModelMultipleChoiceField` fields on the form have
   their querysets filtered to show only the values for the current site.  This
   happens during form class instantiation.
1. The form's `clean()` method sets the instance's "site" field to that of the
   site chosen by `SiteSelectingMiddleware`, if "site" was not already set.  

Example:

```
class StuffForm(SiteSpecificModelForm):

   class Meta:
       model = Stuff
```

Note that we don't need to worry about filtering the options available for each
form field.  You should exclude the tenant form field as above, not out of
security concerns but rather to avoid complications while cleaning the form.
    

### Django Admin 

If you use `SiteSpecificModelAdmin` as your `ModelAdmin` class for your
`SiteSpecificModel` subclass, you will see only the instances for the site
chosen by `SiteSelectingMiddleware` when you login to the Django admin interface
for that site.

Example:

```
from django.contrib import admin
from multitenancy.admin import SiteSpecificModelAdmin
from myapp.models import Stuff

admin.site.register(Stuff, SiteSpecificModelAdmin)    
```

### Utilities

A site-aware version of Django's `get_object_or_404` shortcut:

```
from multitenancy.utils import get_site_specific_object_or_404

get_site_specific_object_or_404(Stuff, id=1)
```

To get the `Site` instance for the current request:

```
from multitenancy.middleware import get_current_site

site = get_current_site()
```


## Special Considerations and Warnings

### Uniqueness constraints

Add the "site" field to any uniqueness constraints for site-aware models; 

```
unique_together = (("name", "site"), ("code", "site"),)
```

