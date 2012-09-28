"""Remove an app_name(s) from installed apps."""

from magpy.management import BaseCommand, CommandError
from magpy.server.database import Database

class Command(BaseCommand):
    """Remove an app_name(s) from installed apps."""
    help = ('Remove an app_name(s) from installed apps.')
    args = '[app_name ...]'

    def handle(self, *args, **kwargs):
        database = Database()
        for arg in args:
            database.remove_app(arg)
