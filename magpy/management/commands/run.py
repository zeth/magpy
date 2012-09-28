"""Let's go!
Run the Magpy site backend.
Use --port to specify the port.
"""

from magpy.server import base
from magpy.server.urls import URLS
from magpy.server.urlloader import URLLoader
from magpy.management import BaseCommand, CommandError

class Command(BaseCommand):
    """Run the REST server."""
    help = ('Run the REST server.')
    args = '[port]'

    def handle(self, *args, **kwargs):
        loader = URLLoader()
        urls = loader.get_urls()
        base.main(urls)
