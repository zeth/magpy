"""Let's go!
Run the Magpy site backend.
Use --port to specify the port.
"""

from magpy.server import base
from magpy.server.urls import URLS
from magpy.server.urlloader import URLLoader
from magpy.management import BaseCommand, CommandError

class Command(BaseCommand):
    """Add a setting to the database."""
    help = ('Add a key and a value to the given setting category.')
    args = '[category setting value]'

    def handle(self, *args, **kwargs):
        loader = URLLoader()
        urls = loader.get_urls()
        base.main(urls)
