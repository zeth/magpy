"""Collect static files into the public web directory."""

import os
from pkgutil import get_loader
from magpy.server.database import Database
from magpy.management import BaseCommand, CommandError
from optparse import make_option
#from tempfile import mkdtemp
from shutil import copy
from six.moves import filter


class Command(BaseCommand):
    """Collect static files into the public web directory."""
    help = ('Collect static files into the public web directory.')

    option_list = BaseCommand.option_list + (
        make_option("-p", "--pure",
                    action="store_false", dest="appify", default=True,
                    help="Do not modify the paths, "
                    "i.e. do not group them by application."),
        make_option("-t", "--no_time",
                    action="store_false", dest="check_time", default=True,
                    help="Do not check timestamps, "
                    "just overwrite all files."),)

    def handle(self, *args, **options):
        """Collect the static files of an application."""
        database = Database()

        # 0. Get the target directory
        target = database.get_setting('static', 'root')
        if not target:
            raise CommandError(
                u'No static root setting. Set static root with:\n'
                u'mag.py add_setting static root <directory-name>\n'
                u'E.g.\n'
                u'mag.py add_setting static root /var/www/static')

        # 1. Get the list of applications
        apps = database.get_app_list()
        if apps:
            apps.append('magpy')
        else:
            apps = ['magpy']
            
        # 2. Build a dictionary of static file names
        static_files = []
        for app in apps:
            print("Looking for static files in ", app)
            path = self.get_path(app)
            if path:
                static_files.extend(
                    self.get_filenames(
                        path, target, app, options["appify"]))

        # 3. Check if the timestamps on the static files are newer than the
        # the saved files, and cut out any that are not
        if options['check_time']:
            static_files = filter(self.check_newer, static_files)

        # 4. Copy the files
        for source, target in static_files:
            # Make sure the target directory exist
            target_dir = os.path.dirname(target)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            # Copy the file
            print("Copying %s to %s" % (source, target))
            copy(source, target)

    @staticmethod
    def check_newer(file_tuple):
        """Check if the source is newer than the target."""
        source, target = file_tuple
        # if target does not exist, then the source is newer
        if not os.path.exists(target):
            return True
        # Check the modification time
        if os.path.getmtime(source) > os.path.getmtime(target):
            return True
        return False

    @staticmethod
    def get_path(app):
        """Get the static files path of an application."""
        try:
            loader = get_loader(app)
        except ImportError:
            return
        if not loader:
            return
        path = os.path.split(loader.get_filename())[0]
        return os.path.join(path, 'static')

    @staticmethod
    def get_filenames(path, target, app, appify):
        """Get all the filenames in a path."""
        file_list = []
        for branch in os.walk(path):
            orig_path = branch[0]
            leaves = branch[2]
            if leaves:
                for leaf in leaves:
                    source_path = os.path.join(orig_path, leaf)
                    short_path = os.path.relpath(source_path, path)
                    if appify:
                        target_path = os.path.join(target, app, short_path)
                    else:
                        target_path = os.path.join(target, short_path)
                    file_list.append((source_path, target_path))
        return file_list
