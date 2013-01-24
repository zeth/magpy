"""Make a cookie secret file.
"""

import base64
import uuid
from magpy.management import BaseCommand, CommandError


class Command(BaseCommand):
    """Make a cookie secret file."""
    help = ('Make a cookie secret file.')
    args = '[filelocation]'

    def handle(self, *args, **kwargs):
        if args:
            filename = args[0]
        else:
            filename = 'cookie.txt'
        cookie_secret = base64.b64encode(
            uuid.uuid4().bytes + uuid.uuid4().bytes)
        with open(filename, 'wb') as cookie_file:
            cookie_file.write(cookie_secret)
