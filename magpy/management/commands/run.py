"""Let's go!
Run the Magpy site backend.
Use --port to specify the port.
"""
from optparse import make_option
from magpy.server import base
from magpy.server.urls import URLS
from magpy.server.urlloader import URLLoader
from magpy.management import BaseCommand, CommandError

class Command(BaseCommand):
    """Run the REST server."""
    help = ('Run the REST server.')
    args = '[port]'
    option_list = BaseCommand.option_list + (
        make_option('--cookie', '-c', dest='cookie_secret_file',
                    action='store', default="cookie.txt",
                    type='string',
                    help='Location of cookie secret file.'),
        make_option('--port', '-p', dest='port',
                    action='store', default="8000",
                    type='int',
                    help='Server port to use.'),)

    def handle(self, *args, **kwargs):
        loader = URLLoader()
        urls = loader.get_urls()
        base.main(
            urls,
            kwargs['cookie_secret_file'],
            kwargs['port'])
