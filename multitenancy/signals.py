from django.dispatch import Signal

pre_site_create = Signal(providing_args=['site'])
post_site_create = Signal(providing_args=['site'])
