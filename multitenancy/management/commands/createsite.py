"""
Management utility to create a non-root site.
"""
import sys

from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS
from django.utils.text import capfirst

from multitenancy.models import Site
from multitenancy.management import get_default_domain


class NotRunningInTTYException(Exception):
    pass


class Command(BaseCommand):
    help = 'Used to create a the multitenancy root site.'
    requires_migrations_checks = True
    stealth_options = ('stdin',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.domain_field = Site._meta.get_field(Site.DOMAIN_FIELD)

    def add_arguments(self, parser):
        parser.add_argument(
            '--{}'.format(Site.DOMAIN_FIELD),
            help='Specifies the domain for the site.',
        )
        parser.add_argument(
            '--noinput', '--no-input', action='store_false', dest='interactive',
            help=(
                'Tells Django to NOT prompt the user for input of any kind. '
                'You must use --domain with --noinput, along with an option for '
                'any other required field.'
            ),
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".',
        )
        for field in Site.REQUIRED_FIELDS:
            parser.add_argument(
                '--%s' % field,
                help='Specifies the %s for the site.' % field,
            )

    def execute(self, *args, **options):
        self.stdin = options.get('stdin', sys.stdin)  # Used for testing
        return super().execute(*args, **options)

    def handle(self, *args, **options):
        domain = options[Site.DOMAIN_FIELD]
        database = options['database']
        is_root_site = options.get('is_root_site', False)
        command_name = "createsite" if not is_root_site else "createrootsite"
        site_data = {}
        verbose_field_name = self.domain_field.verbose_name
        try:
            if options['interactive']:
                # Same as user_data but with foreign keys as fake model
                # instances instead of raw IDs.
                fake_site_data = {}
                if hasattr(self.stdin, 'isatty') and not self.stdin.isatty():
                    raise NotRunningInTTYException
                default_domain = get_default_domain()
                if domain:
                    error_msg = self._validate_domain(domain, verbose_field_name, database)
                    if error_msg:
                        self.stderr.write(error_msg)
                        username = None
                elif domain == '':
                    raise CommandError('%s cannot be blank.' % capfirst(verbose_field_name))
                # Prompt for username.
                while domain is None:
                    message = self._get_input_message(self.domain_field, default_domain)
                    username = self.get_input_data(self.domain_field, message, default_domain)
                    if username:
                        error_msg = self._validate_domain(domain, verbose_field_name, database)
                        if error_msg:
                            self.stderr.write(error_msg)
                            username = None
                            continue
                site_data[Site.DOMAIN_FIELD] = domain
                fake_site_data[Site.DOMAIN_FIELD] = (
                    self.domain_field.remote_field.model(domain)
                    if self.domain_field.remote_field else domain
                )
                # Prompt for required fields.
                for field_name in Site.REQUIRED_FIELDS:
                    field = Site._meta.get_field(field_name)
                    site_data[field_name] = options[field_name]
                    while site_data[field_name] is None:
                        message = self._get_input_message(field)
                        input_value = self.get_input_data(field, message)
                        site_data[field_name] = input_value
                        fake_site_data[field_name] = input_value

                        # Wrap any foreign keys in fake model instances
                        if field.remote_field:
                            fake_site_data[field_name] = field.remote_field.model(input_value)

            else:
                # Non-interactive mode.
                if username is None:
                    raise CommandError('You must use --%s with --noinput.' % Site.DOMAIN_FIELD)
                else:
                    error_msg = self._validate_username(username, verbose_field_name, database)
                    if error_msg:
                        raise CommandError(error_msg)

                site_data[Site.DOMAIN_FIELD] = domain
                for field_name in Site.REQUIRED_FIELDS:
                    if options[field_name]:
                        field = Site._meta.get_field(field_name)
                        site_data[field_name] = field.clean(options[field_name], None)
                    else:
                        raise CommandError('You must use --%s with --noinput.' % field_name)

            if is_root_site:
                Site._default_manager.db_manager(database).create_root_site(**site_data)
            else:
                Site._default_manager.db_manager(database).create_site(**site_data)
            if options['verbosity'] >= 1:
                self.stdout.write("Site created successfully.")
        except KeyboardInterrupt:
            self.stderr.write('\nOperation cancelled.')
            sys.exit(1)
        except exceptions.ValidationError as e:
            raise CommandError('; '.join(e.messages))
        except NotRunningInTTYException:
            self.stdout.write(
                'Site creation skipped due to not running in a TTY. '
                f'You can run `manage.py {command_name}` in your project '
                'to create one manually.'
            )

    def get_input_data(self, field, message, default=None):
        """
        Override this method if you want to customize data inputs or
        validation exceptions.
        """
        raw_value = input(message)
        if default and raw_value == '':
            raw_value = default
        try:
            val = field.clean(raw_value, None)
        except exceptions.ValidationError as e:
            self.stderr.write("Error: %s" % '; '.join(e.messages))
            val = None

        return val

    def _get_input_message(self, field, default=None):
        return '%s%s%s: ' % (
            capfirst(field.verbose_name),
            " (leave blank to use '%s')" % default if default else '',
            ' (%s.%s)' % (
                field.remote_field.model._meta.object_name,
                field.remote_field.field_name,
            ) if field.remote_field else '',
        )

    def _validate_domain(self, domain, verbose_field_name, database):
        """Validate domain. If invalid, return a string error message."""
        if self.domain_field.unique:
            try:
                Site._default_manager.db_manager(database).get_by_natural_key(domain)
            except Site.DoesNotExist:
                pass
            else:
                return 'Error: That %s is already taken.' % verbose_field_name
        if not domain:
            return '%s cannot be blank.' % capfirst(verbose_field_name)
        try:
            self.domain_field.clean(domain, None)
        except exceptions.ValidationError as e:
            return '; '.join(e.messages)
