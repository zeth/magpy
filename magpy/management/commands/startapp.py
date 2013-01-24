"""Start an app - i.e. create a basic directory structure for a mag app."""

import os
import sys
import re
import stat
import errno
import shutil
from optparse import make_option
from importlib import import_module

# Pylint says string is deprecated
# but only some of it is
# www.logilab.org/2481
# pylint: disable=W0402
from string import Template

from magpy.management import BaseCommand, CommandError
import magpy


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
                    '-n multiple times.'),)
    valid_extensions = ('md', 'py', '.html')

    def handle(self, app_name=None, target=None, **options):
        verbosity = int(options.get('verbosity'))
        context = {'app_name': app_name}

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

        # Find the template directory
        template_dir = os.path.join(magpy.__path__[0], 'conf', 'app_template')
        prefix_length = len(template_dir) + 1

        for root, dirs, files in os.walk(template_dir):

            # Make a target directory
            path_rest = root[prefix_length:]
            relative_dir = path_rest.replace('app_name', app_name)
            if relative_dir:
                target_dir = os.path.join(top_dir, relative_dir)
                if not os.path.exists(target_dir):
                    os.mkdir(target_dir)

            # Ignore private and cache subdirectories
            for dirname in dirs[:]:
                if dirname.startswith('.') or dirname == '__pycache__':
                    dirs.remove(dirname)
            # Files
            for filename in files:
                if filename.endswith(('.pyo', '.pyc', '.py.class')):
                    # Ignore some files as they cause various breakages.
                    continue
                old_path = os.path.join(root, filename)
                new_path = os.path.join(top_dir, relative_dir,
                                     filename.replace('app_name', app_name))
                if os.path.exists(new_path):
                    raise CommandError("%s already exists, overlaying an "
                                       "app into an existing "
                                       "directory won't replace conflicting "
                                       "files" % new_path)
                # Get the content from template file
                with open(old_path, 'rb') as template_file:
                    content = template_file.read()
                    if filename.endswith(self.valid_extensions):
                        content = content.decode('utf-8')
                        template = Template(content)
                        content = template.safe_substitute(context)
                        content = content.encode('utf-8')
                    with open(new_path, 'wb') as new_file:
                        new_file.write(content)

                if verbosity >= 2:
                    self.stdout.write("Creating %s\n" % new_path)
                try:
                    shutil.copymode(old_path, new_path)
                    self.make_writeable(new_path)
                except OSError:
                    self.stderr.write(
                        "Notice: Couldn't set permission bits on %s. You're "
                        "probably using an uncommon filesystem setup. No "
                        "problem." % new_path, self.style.NOTICE)

    @staticmethod
    def make_writeable(filename):
        """
        Make sure that the file is writeable.
        Useful if our source is read-only.
        """
        if sys.platform.startswith('java'):
            # On Jython there is no os.access()
            return
        if not os.access(filename, os.W_OK):
            stt = os.stat(filename)
            new_permissions = stat.S_IMODE(stt.st_mode) | stat.S_IWUSR
            os.chmod(filename, new_permissions)
