from django.http import Http404
from django.shortcuts import get_object_or_404

from crequest.middleware import CrequestMiddleware

from .exceptions import NoCurrentRequestException


def get_current_request(default=None, silent=True, label='__DEFAULT_LABEL__'):
    """
    Returns the current request.

    You can optonally use ``default`` to pass in a dummy request object to act as the default if there is no current
    request, e.g. when ``get_current_request()`` is called during a manage.py command.

    :param default: (optional) a dummy request object

    :param silent: If ``False``, raise an exception if CRequestMiddleware can't get us a request object.  Default: True
    :type silent: boolean

    :param label: If ``silent`` is ``False``, put this label in our exception message
    :type label: string

    :rtype: a Django request object
    """
    request = CrequestMiddleware.get_request(default)
    if not silent and request is None:
        raise NoCurrentRequestException(
            "{} failed because there is no current request. Try using djunk.utils.FakeCurrentRequest.".format(
                label
            )
        )
    return request


def get_current_user(default=None):
    """
    Returns the user responsible for the current request.

    You can optonally use ``default`` to pass in a dummy request object to act as the default if there is no current
    request, e.g. when ``get_current_user()`` is called during a manage.py command.

    :param default: (optional) a dummy request object
    :type default: an object that emulates a Django request object

    :rtype: a settings.AUTH_USER_MODEL type object
    """
    try:
        return get_current_request().user
    except AttributeError:
        # There's no current request to grab a user from.
        return default


def get_current_site(default=None):
    """
    Returns the Site for the current request.

    You can optonally use ``default`` to pass in a dummy request object to act
    as the default if there is no current request, e.g. when
    ``get_current_site()`` is called during a manage.py command.

    :param default: (optional) a dummy request object
    :type default: an object that emulates a Django request object:e

    :rtype: a multitenancy.Site model
    """
    try:
        return get_current_request().site
    except AttributeError:
        # There's no current request to grab a user from.
        return default


def get_site_specific_object_or_404(klass, *args, **kwargs):
    """
    A site-aware version of django's get_object_or_404 shortcut.

    Example:

        get_site_specific_object_or_404(Stuff, id=1)
    """
    obj = get_object_or_404(klass, *args, **kwargs)

    if obj and hasattr(obj, 'site'):
        if obj.site != get_current_site():
            raise Http404

    return obj
