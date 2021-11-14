from django.conf import settings
from django.utils.http import urlencode
from django.http.request import split_domain_port
from django.http.response import Http404, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

from .exceptions import MissingHostException
from .models import Tenant


def match_tenant_to_request(request):
    """
    Find the Tenant object responsible for responding to this HTTP request object.
    Try in this order:

    * unique Site.domain
    * unique SiteAlias.domain

    If there is no matching hostname or alias for any Tenant, a 404 is thrown.

    This function returns a tuple of (<match-type>, Tenant), where <match-type>
    can be 'hostname' or 'alias'.  It also pre-selects as much as it can from
    the Tenant and Settings, to avoid needless separate queries for things that
    will be looked at on most requests.

    This function may throw either MissingHostException or Tenant.DoesNotExist.
    Callers must handle those appropriately.
    """
    query = Tenant.objects.prefetch_related('aliases')

    if 'HTTP_HOST' not in request.META:
        # If the HTTP_HOST header is missing, this is an improperly configured a
        # test, because any on-spec HTTP client must include it.

        # The spec says to return a 400 if that rule is violated, so we throw a
        # custom exception here to let the middleware know that it has to return
        # a Repsonse object with status code 400.
        raise MissingHostException()

    hostname = request.get_host()
    if ':' in hostname:
        hostname, _ = hostname.split(':')
    try:
        # Find a Tenant matching this specific hostname.
        return ['domain', query.get(site__domain=hostname)]
    except Tenant.DoesNotExist:
        # This except clause catches "no Tenant exists with this hostname", in
        # which case we check if the hostname matches an alias.
        # Tenant.DoesNotExist may be raised by get().
        return ['alias', query.get(tenant__aliases__domain=hostname)]


class TenantSelectingMiddleware(MiddlewareMixin):

    def process_request(self, request):
        try:
            request.tenant = Tenant.objects.get_current(request)
        except Tenant.DoesNotExist:
            # This will trigger if no Tenant matches the request. We raise a 404
            # so that the user gets a useful message.
            raise Http404()

        # WHen a user is on the root site and tries to get to /admin/,
        # send them to the /root/ admin interface instead

        # FIXME: the admin site may not start with /admin/
        if request.site.is_root_site and request.path.startswith('/admin/'):
            path = '/root/'
        else:
            path = request.path

        # When a user visits an admin page via an alias or a non-https URL, we
        # need to redirect them to the https version of the Tenant's canonical
        # domain (so the SSL cert will work).

        domain, port = split_domain_port(request.get_host())
        # FIXME: the admin site may not start with /admin/
        if request.path.startswith('/admin/') and not request.is_secure():
            url = f'https://{request.site.public_domain}{path}'
            if request.GET:
                # If there are GET args, pass them on in the redirect.
                url += f'?{urlencode(request.GET, True)}'
            return HttpResponseRedirect(url)
