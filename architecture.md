# django-site-multitenancy architecture

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

## Definitions

* **mulittenanted system**: the install of the multitenanted codebase
* **superadmin**: a user that can manage creation and deletion of tenants
* **root site**: a special console in the multitenanted systems which allows superadmins to manage tenants, users and
per-tenants permissions and settings!

## Requirements

* Implement this in the most Django native way possible
* Supported models
  * Website: admins login to manage tenants content but visitors are anonmymoous and content is publically viewable
  * Web application: some portions of the tenant are restricted to users admins grant appropriate rights to
    * Examples: e-commerce app; data management app
    * It would be nice in this case if those users did not realize that they were in a multitenanted system and could login directly to the tenant
* Sites
  * The multitenanted system itself has a domain, e.g. foo.example.org
  * Implement two methods for sending tenant visitors to the sandboxed portion of the overall multitentanted system
    * **hostname**: tenants are accessed as subdomains of the system domain, e.g. bar.foo.example.org
    * **path**: tenants are accessed as sub paths of the system domain, e.g. foo.example.org/bar
  * Extend Site objects 
  * Offer an `AbstractTenantSettings` model as an example of how to do per-tenant settings
  * Tenant objects are sandboxed -- one tenant should not "see" or have access to tenant objects from other tenants.  In practice, this means
    * Site visitors using the tenant cannot 
* Root site
  * The root site is a management console that allows tenant management 
    * Superadmins
      * Can create tenants
      * Can delete tenants
      * 
* Users
  * **Common user pool**: A single pool of users which have many-to-many relationships on Tenant.  
    * Admin users log into your account on the root site, and then select which tenant you want to work on.  
    * If an admin user has only one tenant, they are automatically configured to work on that tenant.
    * All users can login like to the root site to see all the tenants they have access to, as well as their roles within those tenants
    * Pros: 
      * This is how the big boys do it (e.g. SquareSpace, WordPress.com)
      * Thus people should be familiar with this model for managing their tenants
      * This also allows for (say you were doing for-pay hosting) one payment method for all tenants
* Authentication
  * Authentication mechanism is left up to the implementor, and is implemented with the normal Django ways (via settings.py)
  * Authentication workflow
    * Admin hsers can login to either the root site
* Authorization
  * Users associated with tenants independently from their permissions
  * User permissions are granted per tenants
* 

