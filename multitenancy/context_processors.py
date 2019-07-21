from .models import Site


def multitenancy(request):
    """
    Return context variables required by apps that use django-site-multitenancy.

    If there is no 'site' attribute in the request, extract one from the request.
    """
    if hasattr(request, 'site'):
        site = request.site
    else:
        site = Site.objects.get_current(request)

    return {'site': site}
