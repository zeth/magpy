"""Add a setting to the database."""

from magpy.management import BaseCommand, CommandError
from magpy.server.database import Database

class Command(BaseCommand):
    """Add a setting to the database."""
    help = ('Add a key and a value to the given setting category.')
    args = '[category setting value]'

    def handle(self, *args, **kwargs):
        database = Database()
        if len(args) != 3:
            raise CommandError
        database.add_setting(args[0], args[1], args[2])
