"""Let's go!
Run the Magpy site backend.
Use --port to specify the port.
"""
from optparse import make_option
from magpy.server import base
#from magpy.server.urls import URLS
from magpy.server.urlloader import URLLoader
from magpy.management import BaseCommand


class Command(BaseCommand):
    """Run the REST server."""
    help = ('Run the REST server.')
    args = '[port]'
    option_list = BaseCommand.option_list + (
        make_option('--port', '-p', dest='port',
                    action='store', type='int',
                    help='Server port to use.'),
        make_option('--conf', '-c', dest='config',
                    action='store',
                    type='string',
                    help='Location of config file.'),)

    def handle(self, *args, **kwargs):
        loader = URLLoader()
        urls = loader.get_urls()
        base.main(
            urls,
            kwargs['port'],
            kwargs['config'])
