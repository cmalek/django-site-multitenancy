from django.apps import AppConfig

import logging

logger = logging.getLogger('multitenancy')


class MultitenancyConfig(AppConfig):
    name = 'multitenancy'
    verbose_name = 'Multitenancy'
    initialized = False

    def ready(self):
        if not self.initialized:
            # https://docs.djangoproject.com/en/2.1/topics/signals/#connecting-receiver-functions
            self.initialized = True
        else:
            logger.warning(
                "app.config.ready.error msg='f{self.__class__.__name__}.ready() executed more than once!'"
            )
