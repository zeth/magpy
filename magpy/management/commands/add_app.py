"""Add an app_name(s) to installed apps."""

from magpy.management import BaseCommand, CommandError
from magpy.server.database import Database

class Command(BaseCommand):
    """Add an app_name(s) to installed apps."""
    help = ('Add an app_name(s) to installed apps.')
    args = '[app_name ...]'

    def handle(self, *args, **kwargs):
        database = Database()
        for arg in args:
            database.add_app(arg)
