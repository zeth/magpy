"""Collect static files into the public web directory."""

import os
from pkgutil import get_loader
from magpy.server.database import Database
from magpy.management import BaseCommand, CommandError
from optparse import make_option
#from tempfile import mkdtemp
from shutil import copy

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
                    "just overwrite all files."),
        )

    def handle(self, *args, **options):
        """Collect the static files of an application."""
        database = Database()

        # 0. Get the target directory
        target = database.get_setting('static', 'root')
        if not target:
            raise CommandError(
                'No static root setting. Set static root with:\n'
                'mag.py add_setting static root <directory-name>\n'
                'E.g.\n'
                'mag.py add_setting static root /var/www/static')

        # 1. Get the list of applications
        apps = database.get_app_list()
        apps.append('magpy')

        # 2. Build a dictionary of static file names
        static_files = []
        for app in apps:
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
            print "source", source
            print "target", target
            # Make sure the target directory exist
            target_dir = os.path.dirname(target)
            print "dir", target_dir
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            # Copy the file
            copy(source, target)

    def check_newer(self, file_tuple):
        """Check if the source is newer than the target."""
        source, target = file_tuple
        # if target does not exist, then the source is newer
        if not os.path.exists(target):
            return True
        # Check the modification time
        if os.path.getmtime(source) > os.path.getmtime(target):
            return True
        return False

    def get_path(self, app):
        """Get the static files path of an application."""
        try:
            loader = get_loader(app)
        except ImportError:
            return
        if not loader:
            return
        return os.path.join(loader.filename, 'static')

    def get_filenames(self, path, target, app, appify):
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
