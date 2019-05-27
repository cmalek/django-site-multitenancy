from django.utils.http import urlencode
from django.http.request import split_domain_port
from django.http.response import HttpResponseBadRequest, Http404, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

from .exceptions import MissingHostException
from .models import Site


def match_site_to_request(request):
    """
    Find the Site object responsible for responding to this HTTP request object.
    Try in this order:

    * unique hostname
    * unique site alias

    If there is no matching hostname or alias for any Site, a 404 is thrown.

    This function returns a tuple of (<match-type>, Site), where <match-type>
    can be 'hostname' or 'alias'.  It also pre-selects as much as it can from
    the Site and Settings, to avoid needless separate queries for things that
    will be looked at on most requests.

    This function may throw either MissingHostException or Site.DoesNotExist.
    Callers must handle those appropriately.
    """
    query = Site.objects.prefetch_related('alias_set')

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
        # Find a Site matching this specific hostname.
        return ['domain', query.get(domain=hostname)]
    except Site.DoesNotExist:
        # This except clause catches "no Site exists with this hostname", in
        # which case we check if the hostname matches an alias.
        # Site.DoesNotExist may be raised by get().
        return ['alias', query.get(site__alias_set__domain=hostname)]


class SiteSelectingMiddleware(MiddlewareMixin):

    def process_request(self, request):
        """
        Set request.site to the Site object responsible for handling this
        request.

        For this, we look at both the site's hostname and the site's aliases.

        This middleware also denies access to users who have valid accounts, but
        aren't members of the current Site.
        """
        try:
            match_type, request.site = match_site_to_request(request)
        except Site.DoesNotExist:
            # This will trigger if no Site matches the request. We raise a 404
            # so that the user gets a useful message.
            raise Http404()
        except MissingHostException:
            # If no hostname was specified, we return a 400 error. This is only
            # able to happen in tests.
            return HttpResponseBadRequest(
                "No HTTP_HOST header detected. Site cannot be determined without one."
            )

        # When a user visits an admin page via an alias or a non-https URL, we
        # need to redirect them to the https version of the Site's canonical
        # domain (so the SSL cert will work).

        domain, port = split_domain_port(request.get_host())
        if request.path.startswith('/admin/') and (
            not request.is_secure()
            or (match_type == 'alias' and domain != request.site.preferred_domain)
        ):
            url = f'https://{request.site.public_domain}{request.path}'
            if request.GET:
                # If there are GET args, pass them on in the redirect.
                url += f'?{urlencode(request.GET, True)}'
            return HttpResponseRedirect(url)
