from django.dispatch import Signal

pre_tenant_create = Signal(providing_args=['tenant'])
post_tenant_create = Signal(providing_args=['tenant'])
