"""
Management utility to create the root site.
"""
from multitenancy.management.commands.createsite import Command as SiteCreateCommand


class Command(SiteCreateCommand):

    def handle(self, *args, **options):
        options['is_root_site'] = True
        super().handle(*args, **options)
