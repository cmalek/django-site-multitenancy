from .models import Tenant


def multitenancy(request):
    """
    Return context variables required by apps that use django-site-multitenancy.

    If there is no 'tenant' attribute in the request, extract one from the request.
    """
    if hasattr(request, 'tenant'):
        tenant = request.tenant
    else:
        tenant = Tenant.objects.get_current(request)

    return {'tenant': tenant}
