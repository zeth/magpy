"""Start an app - i.e. create a basic directory structure for a mag app."""

from importlib import import_module
import re
import os
from optparse import make_option
import errno

# Pylint says string is deprecated
# but only some of it is
# www.logilab.org/2481
# pylint: disable=W0402
from string import Template

from magpy.management import BaseCommand, CommandError


class Command(BaseCommand):
    """Command to start a new Mag application."""
    help = ("Creates a Mag app directory structure for the given app "
            "name in the current directory or optionally in the given "
            "directory.")

    args = "[name] [optional destination directory]"
    option_list = BaseCommand.option_list + (
        make_option('--name', '-n', dest='files',
                    action='append', default=[],
                    help='The file name(s) to render. '
                    'Separate multiple extensions with commas, or use '
                    '-n multiple times.'))

    def handle(self, app_name=None, target=None, **options):
        if app_name is None:
            raise CommandError("you must provide an app name")

        # Check that the app_name cannot be imported.
        try:
            import_module(app_name)
        except ImportError:
            pass
        else:
            raise CommandError("%r conflicts with the name of an existing "
                               "Python module and cannot be used as an app "
                               "name. Please try another name." % app_name)

        #super(Command, self).handle('app', app_name, target, **options)

        # If it's not a valid directory app_name.
        if not re.search(r'^[_a-zA-Z]\w*$', app_name):
            # Provide a smart error message, depending on the error.
            if not re.search(r'^[_a-zA-Z]', app_name):
                message = ('make sure the app_name begins '
                           'with a letter or underscore')
            else:
                message = 'use only numbers, letters and underscores'
            raise CommandError("%r is not a valid app name. Please %s." %
                               (app_name, message))

        # if some directory is given, make sure it's nicely expanded
        if target is None:
            top_dir = os.path.join(os.getcwd(), app_name)
            try:
                os.makedirs(top_dir)
            except OSError as err:
                if err.errno == errno.EEXIST:
                    message = "'%s' already exists" % top_dir
                else:
                    message = err
                raise CommandError(message)
        else:
            top_dir = os.path.abspath(os.path.expanduser(target))
            if not os.path.exists(top_dir):
                raise CommandError("Destination directory '%s' does not "
                                   "exist, please create it first." % top_dir)
