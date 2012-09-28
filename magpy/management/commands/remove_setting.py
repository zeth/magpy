"""Remove a setting from the database."""

from magpy.management import BaseCommand, CommandError
from magpy.server.database import Database

class Command(BaseCommand):
    """Remove a setting from the database."""
    help = ('Remove a setting from the given setting category.')
    args = '[category setting]'

    def handle(self, *args, **kwargs):
        database = Database()
        if len(args) != 2:
            raise CommandError
        database.remove_setting(args[0], args[1])
