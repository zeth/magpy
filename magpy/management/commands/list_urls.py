"""Show all URLs from the installed apps."""

import importlib
from magpy.management import BaseCommand, CommandError
from magpy.server.database import Database
from magpy.server.urls import URLS


class Command(BaseCommand):
    """Show all URLs from the installed apps."""
    help = ('Show all URLs from the installed apps.')

    def handle(self, *args, **kwargs):
        """Get the Urls."""
        database = Database()
        apps = database.get_app_list()
        urls = URLS
        if apps:
            for app in apps:
                url_path = '%s.urls' % app
                try:
                    url_module = importlib.import_module(url_path)
                except:
                    pass
                else:
                    urls.extend(getattr(url_module, 'URLS', []))
        for url in urls:
            print url
