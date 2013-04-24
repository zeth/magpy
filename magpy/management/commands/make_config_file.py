"""Make a config file, or update a cookie secret in a settings file,
or just print out a cookie secret.
"""
from __future__ import print_function

import os
from magpy.management import BaseCommand
from magpy.server.utils import make_cookie_secret
from magpy.server.config import MagpyConfigParser


class Command(BaseCommand):
    """Make new config file, or update a cookie secret in a settings file."""
    help = (
        'Provide a new filepath, and you will create a new config file.\n'
        'Provide an existing filepath, '
        'and you will update the cookie secret.\n'
        'Provide no arguments, and you will just print out '
        'a new cookie secret.')
    args = '[filelocation]'

    def handle(self, *args, **kwargs):
        cookie_secret = make_cookie_secret()
        if not args:
            print (cookie_secret)
            return

        filename = args[0]

        if os.path.exists(filename):
            config = MagpyConfigParser(filename)
        else:
            print ("Settings file does not exist at that location, creating.")
            config = MagpyConfigParser()
            config.config_file_path = filename

        config.cookie_secret = cookie_secret
        config.write()
