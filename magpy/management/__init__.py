#!/usr/bin/env python
"""Management Command Tool.
Based originally on Django's one."""

import os
import sys
import collections
import imp
import warnings
from optparse import OptionParser, NO_DEFAULT, make_option
import traceback
from importlib import import_module

from magpy.server.database import Database
from magpy.server.validators import smart_str
import magpy

# A cache of loaded commands, so that call_command
# doesn't have to reload every time it's called.
# This is how Django does it, but globals are for losers
# So lets introduce a class one day instead.
_COMMANDS = None


def execute_from_command_line(argv=None):
    """
    A simple method that runs a ManagementUtility.
    """
    utility = ManagementUtility(argv)
    utility.execute()


def find_commands(management_dir):
    """
    Given a path to a management directory, returns a list of all the command
    names that are available.

    Returns an empty list if no commands are defined.
    """
    command_dir = os.path.join(management_dir, 'commands')
    try:
        return [filename[:-3] for filename in os.listdir(command_dir)
                if not filename.startswith('_') and filename.endswith('.py')]
    except OSError:
        return []


def get_commands():
    """
    Returns a dictionary mapping command names to their callback applications.

    This works by looking for a management.commands package in magpy, and
    in each installed application -- if a commands package exists, all commands
    in that package are registered.

    The dictionary is in the format {command_name: app_name}. Key-value
    pairs from this dictionary can then be used in calls to
    load_command_class(app_name, command_name)

    If a specific version of a command must be loaded (e.g., with the
    startapp command), the instantiated module can be placed in the
    dictionary in place of the application name.

    The dictionary is cached on the first call and reused on subsequent
    calls.
    """
    global _COMMANDS  # pylint: disable-msg=W0603
    if _COMMANDS is None:
        # Find the builtin commands
        magpy_path = find_management_module('magpy')
        _COMMANDS = dict([(name, 'magpy') for \
                              name in find_commands(magpy_path)])
        # Find the installed apps
        database = Database()
        apps = database.get_app_list()
        if apps == None:
            apps = []

        # Find and load the management module for each installed app.
        for app_name in apps:
            try:
                path = find_management_module(app_name)
                _COMMANDS.update(dict([(name, app_name)
                                       for name in find_commands(path)]))
            except ImportError:
                pass  # No management module - ignore this app

    return _COMMANDS


def find_management_module(app_name):
    """
    Determines the path to the management module for the given app_name,
    without actually importing the application or the management module.

    Raises ImportError if the management module cannot be found for any reason.
    """
    parts = app_name.split('.')
    parts.append('management')
    parts.reverse()
    part = parts.pop()
    path = None

    # When using manage.py, the project module is added to the path,
    # loaded, then removed from the path. This means that
    # testproject.testapp.models can be loaded in future, even if
    # testproject isn't in the path. When looking for the management
    # module, we need look for the case where the project name is part
    # of the app_name but the project directory itself isn't on the path.

    # pylint: disable-msg=W0612
    try:
        fileobject, path, descr = imp.find_module(part, path)
    except ImportError as exception:
        if os.path.basename(os.getcwd()) != part:
            raise exception

    while parts:
        part = parts.pop()
        fileobject, path, descr = \
            imp.find_module(part, path and [path] or None)
    return path


def load_command_class(app_name, name):
    """
    Given a command name and an application name, returns the Command
    class instance. All errors raised by the import process
    (ImportError, AttributeError) are allowed to propagate.
    """
    module = import_module('%s.management.commands.%s' % (app_name, name))
    return module.Command()


class LaxOptionParser(OptionParser):  # pylint: disable-msg=R0904
    """
    An option parser that doesn't raise any errors on unknown options.

    This is needed because the --settings and --pythonpath options affect
    the commands (and thus the options) that are available to the user.
    """
    def error(self, msg):
        pass

    def print_help(self):  # pylint: disable-msg=W0221
        """Output nothing.

        The lax options are included in the normal option parser, so under
        normal usage, we don't need to print the lax options.
        """
        pass

    def print_lax_help(self):
        """Output the basic options available to every command.

        This just redirects to the default print_help() behavior.
        """
        OptionParser.print_help(self)

    def _process_args(self, largs, rargs, values):
        """
        Overrides OptionParser._process_args to exclusively handle default
        options and ignore args and other options.

        This overrides the behavior of the super class, which stop parsing
        at the first unrecognized option.
        """
        while rargs:
            arg = rargs[0]
            try:
                if arg[0:2] == "--" and len(arg) > 2:
                    # process a single long option (possibly with value(s))
                    # the superclass code pops the arg off rargs
                    self._process_long_opt(rargs, values)
                elif arg[:1] == "-" and len(arg) > 1:
                    # process a cluster of short options (possibly with
                    # value(s) for the last one only)
                    # the superclass code pops the arg off rargs
                    self._process_short_opts(rargs, values)
                else:
                    # it's either a non-default option or an arg
                    # either way, add it to the args list so we can keep
                    # dealing with options
                    del rargs[0]
                    raise Exception
            except:
                largs.append(arg)  # pylint: disable-msg=W0702


class ManagementUtility(object):
    """
    Encapsulates the logic of the django-admin.py and manage.py utilities.

    A ManagementUtility has a number of commands, which can be manipulated
    by editing the self.commands dictionary.
    """
    def __init__(self, argv=None):
        self.argv = argv or sys.argv[:]
        self.prog_name = os.path.basename(self.argv[0])

    def main_help_text(self, commands_only=False):
        """
        Returns the script's main help text, as a string.
        """
        if commands_only:
            usage = sorted(get_commands().keys())
        else:
            usage = [
                "",
                "Type '%s help <subcommand>' for help on a "
                "specific subcommand." % self.prog_name,
                "",
                "Available subcommands:",
            ]
            commands_dict = collections.defaultdict(lambda: [])
            for name, app in get_commands().iteritems():
                if app == 'django.core':
                    app = 'django'
                else:
                    app = app.rpartition('.')[-1]
                commands_dict[app].append(name)
            style = color_style()
            for app in sorted(commands_dict.keys()):
                usage.append("")
                usage.append(style.NOTICE("[%s]" % app))
                for name in sorted(commands_dict[app]):
                    usage.append("    %s" % name)
        return '\n'.join(usage)

    def fetch_command(self, subcommand):
        """
        Tries to fetch the given subcommand, printing a message with the
        appropriate command called from the command line (usually
        "django-admin.py" or "manage.py") if it can't be found.
        """
        try:
            app_name = get_commands()[subcommand]
        except KeyError:
            sys.stderr.write("Unknown command: %r\nType '%s help'"
                             " for usage.\n" % \
                (subcommand, self.prog_name))
            sys.exit(1)
        if isinstance(app_name, BaseCommand):
            # If the command is already loaded, use it directly.
            klass = app_name
        else:
            klass = load_command_class(app_name, subcommand)
        return klass

    def autocomplete(self):  # pylint: disable-msg=R0914
        """
        Output completion suggestions for BASH.

        The output of this function is passed to BASH's `COMREPLY` variable and
        treated as completion suggestions. `COMREPLY` expects a space
        separated string as the result.

        The `COMP_WORDS` and `COMP_CWORD` BASH environment variables are used
        to get information about the cli input. Please refer to the BASH
        man-page for more information about this variables.

        Subcommand options are saved as pairs. A pair consists of
        the long option string (e.g. '--exclude') and a boolean
        value indicating if the option requires arguments. When printing to
        stdout, a equal sign is appended to options which require arguments.

        Note: If debugging this function, it is recommended to write the debug
        output in a separate file. Otherwise the debug output will be treated
        and formatted as potential completion suggestions.
        """
        # Don't complete if user hasn't sourced bash_completion file.
        # This is found in django-trunk/extras/django_bash_completion
        if 'DJANGO_AUTO_COMPLETE' not in os.environ:
            return

        cwords = os.environ['COMP_WORDS'].split()[1:]
        cword = int(os.environ['COMP_CWORD'])

        try:
            curr = cwords[cword - 1]
        except IndexError:
            curr = ''

        subcommands = get_commands().keys() + ['help']
        options = [('--help', None)]

        # subcommand
        if cword == 1:
            print ' '.join(sorted(filter(lambda x: x.startswith(curr),
                                         subcommands)))
        # subcommand options
        # special case: the 'help' subcommand has no options
        elif cwords[0] in subcommands and cwords[0] != 'help':
            subcommand_cls = self.fetch_command(cwords[0])
            # special case: add the names of installed apps to options
            if cwords[0] in ('dumpdata', 'sql', 'sqlall', 'sqlclear',
                    'sqlcustom', 'sqlindexes', 'sqlsequencereset', 'test'):
                try:
                    database = Database()
                    # Get the last part of the dotted path as the app name.
                    options += [(a.split('.')[-1], 0) for \
                                    a in database.get_app_list()]
                except ImportError:
                    # Fail silently if DJANGO_SETTINGS_MODULE isn't set. The
                    # user will find out once they execute the command.
                    pass
            options += [(s_opt.get_opt_string(), s_opt.nargs) for s_opt in
                        subcommand_cls.option_list]
            # filter out previously specified options from available options
            prev_opts = [x.split('=')[0] for x in cwords[1:cword - 1]]
            options = filter(lambda (x, v): x not in prev_opts, options)

            # filter options by current input
            options = sorted([(k, v) for k, v in \
                                  options if k.startswith(curr)])
            for option in options:
                opt_label = option[0]
                # append '=' to options which require args
                if option[1]:
                    opt_label += '='
                print opt_label
        sys.exit(1)

    def execute(self):
        """
        Given the command-line arguments, this figures out which subcommand is
        being run, creates a parser appropriate to that command, and runs it.
        """
        # Preprocess options to extract --settings and --pythonpath.
        # These options could affect the commands that are available, so they
        # must be processed early.
        parser = LaxOptionParser(usage="%prog subcommand [options] [args]",
                                 version=magpy.get_version(),
                                 option_list=BaseCommand.option_list)
        self.autocomplete()
        try:
            options, args = parser.parse_args(self.argv)
            handle_default_options(options)
        except:
            # Ignore any option errors at this point.
            pass  # pylint: disable-msg=W0702

        try:
            subcommand = self.argv[1]
        except IndexError:
            subcommand = 'help'  # Display help if no arguments were given.

        if subcommand == 'help':
            if len(args) <= 2:
                parser.print_lax_help()
                sys.stdout.write(self.main_help_text() + '\n')
            elif args[2] == '--commands':
                sys.stdout.write(
                    self.main_help_text(commands_only=True) + '\n')
            else:
                self.fetch_command(args[2]).print_help(self.prog_name, args[2])
        elif subcommand == 'version':
            sys.stdout.write(parser.get_version() + '\n')
        # Special-cases: We want 'django-admin.py --version' and
        # 'django-admin.py --help' to work, for backwards compatibility.
        elif self.argv[1:] == ['--version']:
            # LaxOptionParser already takes care of printing the version.
            pass
        elif self.argv[1:] in (['--help'], ['-h']):
            parser.print_lax_help()
            sys.stdout.write(self.main_help_text() + '\n')
        else:
            self.fetch_command(subcommand).run_from_argv(self.argv)

# Base classes for writing management commands (named commands which can
# be executed through ``manage.py``).


class CommandError(Exception):
    """
    Exception class indicating a problem while executing a management
    command.

    If this exception is raised during the execution of a management
    command, it will be caught and turned into a nicely-printed error
    message to the appropriate output stream (i.e., stderr); as a
    result, raising this exception (with a sensible description of the
    error) is the preferred way to indicate that something has gone
    wrong in the execution of a command.

    """
    pass


def handle_default_options(options):
    """
    Include any default options that all commands should accept here
    so that ManagementUtility can handle them before searching for
    user commands.

    """
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    if options.pythonpath:
        sys.path.insert(0, options.pythonpath)


class BaseCommand(object):
    """
    The base class from which all management commands ultimately
    derive.

    Use this class if you want access to all of the mechanisms which
    parse the command-line arguments and work out what code to call in
    response; if you don't need to change any of that behavior,
    consider using one of the subclasses defined in this file.

    If you are interested in overriding/customizing various aspects of
    the command-parsing and -execution behavior, the normal flow works
    as follows:

    1. ``django-admin.py`` or ``manage.py`` loads the command class
       and calls its ``run_from_argv()`` method.

    2. The ``run_from_argv()`` method calls ``create_parser()`` to get
       an ``OptionParser`` for the arguments, parses them, performs
       any environment changes requested by options like
       ``pythonpath``, and then calls the ``execute()`` method,
       passing the parsed arguments.

    3. The ``execute()`` method attempts to carry out the command by
       calling the ``handle()`` method with the parsed arguments; any
       output produced by ``handle()`` will be printed to standard
       output.

    4. If ``handle()`` raised a ``CommandError``, ``execute()`` will
       instead print an error message to ``stderr``.

    Thus, the ``handle()`` method is typically the starting point for
    subclasses; many built-in commands and command types either place
    all of their logic in ``handle()``, or perform some additional
    parsing work in ``handle()`` and then delegate from it to more
    specialized methods as needed.

    Several attributes affect behavior at various steps along the way:

    ``args``
        A string listing the arguments accepted by the command,
        suitable for use in help messages; e.g., a command which takes
        a list of application names might set this to '<appname
        appname ...>'.

    ``can_import_settings``
        A boolean indicating whether the command needs to be able to
        import Django settings; if ``True``, ``execute()`` will verify
        that this is possible before proceeding. Default value is
        ``True``.

    ``help``
        A short description of the command, which will be printed in
        help messages.

    ``option_list``
        This is the list of ``optparse`` options which will be fed
        into the command's ``OptionParser`` for parsing arguments.

    """
    # Metadata about this command.
    option_list = (
        make_option('-v', '--verbosity', action='store',
                    dest='verbosity', default='1',
            type='choice', choices=['0', '1', '2', '3'],
            help='Verbosity level; 0=minimal output, 1=normal output,'
                    ' 2=verbose output, 3=very verbose output'),
        make_option('--settings',
            help='The Python path to a settings module, e.g. '
                    '"myproject.settings.main". If this isn\'t provided, '
                    'the DJANGO_SETTINGS_MODULE environment variable will'
                    ' be used.'),
        make_option('--pythonpath',
            help='A directory to add to the Python path, '
                    'e.g. "/home/djangoprojects/myproject".'),
        make_option('--traceback', action='store_true',
            help='Print traceback on exception'),
    )
    help = ''
    args = ''

    # Configuration shortcuts that alter various logic.
    can_import_settings = True
    requires_model_validation = True
    output_transaction = False
    # Whether to wrap the output in a "BEGIN; COMMIT;"

    def __init__(self):
        self.style = color_style()

    @staticmethod
    def get_version():
        """
        Return the Magpy version, which should be correct for all
        built-in Magpy commands. User-supplied commands should
        override this method.

        """
        return magpy.get_version()

    def usage(self, subcommand):
        """
        Return a brief description of how to use this command, by
        default from the attribute ``self.help``.

        """
        usage = '%%prog %s [options] %s' % (subcommand, self.args)
        if self.help:
            return '%s\n\n%s' % (usage, self.help)
        else:
            return usage

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``OptionParser`` which will be used to
        parse the arguments to this command.

        """
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list)

    def print_help(self, prog_name, subcommand):
        """
        Print the help message for this command, derived from
        ``self.usage()``.

        """
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    def run_from_argv(self, argv):
        """
        Set up any environment changes requested (e.g., Python path
        and Django settings), then run this command.

        """
        parser = self.create_parser(argv[0], argv[1])
        options, args = parser.parse_args(argv[2:])
        handle_default_options(options)
        self.execute(*args, **options.__dict__)  # pylint: disable-msg=W0142

    def execute(self, *args, **options):
        """
        Try to execute this command.
        If the command raises a
        ``CommandError``, intercept it and print it sensibly to
        stderr.
        """
        show_traceback = options.get('traceback', False)

        try:
            self.stdout = options.get('stdout', sys.stdout)
            self.stderr = options.get('stderr', sys.stderr)

            output = self.handle(*args, **options)
            if output:
                self.stdout.write(output)

        except CommandError as exception:
            if show_traceback:
                traceback.print_exc()
            else:
                self.stderr.write(
                    smart_str(self.style.ERROR('Error: %s\n' % exception)))
            sys.exit(1)

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.

        """
        raise NotImplementedError()


class ImproperlyConfigured(Exception):
    "Magpy is somehow improperly configured"
    pass


def load_models(appname):
    """Load the models module for the `appname`."""
    return import_module('.models', appname)


class AppCommand(BaseCommand):  # pylint: disable=R0921
    """
    A management command which takes one or more installed application
    names as arguments, and does something with each of them.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_app()``, which will be called once for each application.

    """
    args = '<appname appname ...>'

    def handle(self, *app_labels, **options):
        if not app_labels:
            raise CommandError('Enter at least one appname.')
        try:
            app_list = [load_models(app_label) for app_label in app_labels]
        except (ImproperlyConfigured, ImportError) as exception:
            raise CommandError(
                "%s. Are you sure your applications.installed_apps "
                "setting is correct?" % exception)
        output = []
        for app in app_list:
            app_output = self.handle_app(app, **options)
            if app_output:
                output.append(app_output)
        return '\n'.join(output)

    def handle_app(self, app, **options):
        """
        Perform the command's actions for ``app``, which will be the
        Python module corresponding to an application name given on
        the command line.

        """
        raise NotImplementedError()


class LabelCommand(BaseCommand):  # pylint: disable=R0921
    """
    A management command which takes one or more arbitrary arguments
    (labels) on the command line, and does something with each of
    them.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_label()``, which will be called once for each label.

    If the arguments should be names of installed applications, use
    ``AppCommand`` instead.

    """
    args = '<label label ...>'
    label = 'label'

    def handle(self, *labels, **options):
        if not labels:
            raise CommandError('Enter at least one %s.' % self.label)

        output = []
        for label in labels:
            label_output = self.handle_label(label, **options)
            if label_output:
                output.append(label_output)
        return '\n'.join(output)

    def handle_label(self, label, **options):
        """
        Perform the command's actions for ``label``, which will be the
        string as given on the command line.

        """
        raise NotImplementedError()


class NoArgsCommand(BaseCommand):  # pylint: disable=R0921
    """
    A command which takes no arguments on the command line.

    Rather than implementing ``handle()``, subclasses must implement
    ``handle_noargs()``; ``handle()`` itself is overridden to ensure
    no arguments are passed to the command.

    Attempting to pass arguments will raise ``CommandError``.

    """
    args = ''

    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")
        return self.handle_noargs(**options)

    def handle_noargs(self, **options):
        """
        Perform this command's actions.

        """
        raise NotImplementedError()

##############################################
# Crap to do with colours.                   #
##############################################


def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.
    """
    unsupported_platform = (sys.platform in ('win32', 'Pocket PC'))
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    if unsupported_platform or not is_a_tty:
        return False
    return True


def color_style():
    """Returns a Style object with the Django color scheme."""
    if not supports_color():
        style = no_style()
    else:
        environment_color_style = os.environ.get('DJANGO_COLORS', '')
        color_settings = parse_color_setting(environment_color_style)
        if color_settings:
            class Dummy:
                """A style object."""
                pass
            style = Dummy()
            # The nocolor palette has all available roles.
            # Use that pallete as the basis for populating
            # the palette as defined in the environment.
            for role in PALETTES[NOCOLOR_PALETTE]:
                colour_format = color_settings.get(role, {})
                # pylint: disable-msg=W0142
                setattr(style, role, make_style(**colour_format))
            # For backwards compatibility,
            # set style for ERROR_OUTPUT == ERROR
            style.ERROR_OUTPUT = style.ERROR
        else:
            style = no_style()
    return style


def no_style():
    """Returns a Style object that has no colors."""
    class Dummy:
        """A style object that has no colors."""
        def __getattr__(self, attr):
            return lambda x: x
    return Dummy()

COLOR_NAMES = (
    'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
    )
FOREGROUND = dict([(COLOR_NAMES[index], '3%s' % index) for index in range(8)])
BACKGROUND = dict([(COLOR_NAMES[index], '4%s' % index) for index in range(8)])

RESET = '0'
OPT_DICT = {
    'bold': '1', 'underscore': '4', 'blink': '5',
    'reverse': '7', 'conceal': '8'}


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, value in kwargs.iteritems():
        if k == 'fg':
            code_list.append(FOREGROUND[value])
        elif k == 'bg':
            code_list.append(BACKGROUND[value])
    for opt in opts:
        if opt in OPT_DICT:
            code_list.append(OPT_DICT[opt])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text


def make_style(opts=(), **kwargs):
    """
    Returns a function with default parameters for colorize()

    Example:
        bold_red = make_style(opts=('bold',), fg='red')
        print bold_red('hello')
        KEYWORD = make_style(fg='yellow')
        COMMENT = make_style(fg='blue', opts=('bold',))
    """
    # pylint: disable-msg=W0142
    return lambda text: colorize(text, opts, **kwargs)

NOCOLOR_PALETTE = 'nocolor'
DARK_PALETTE = 'dark'
LIGHT_PALETTE = 'light'

PALETTES = {
    NOCOLOR_PALETTE: {
        'ERROR':        {},
        'NOTICE':       {},
        'SQL_FIELD':    {},
        'SQL_COLTYPE':  {},
        'SQL_KEYWORD':  {},
        'SQL_TABLE':    {},
        'HTTP_INFO':         {},
        'HTTP_SUCCESS':      {},
        'HTTP_REDIRECT':     {},
        'HTTP_NOT_MODIFIED': {},
        'HTTP_BAD_REQUEST':  {},
        'HTTP_NOT_FOUND':    {},
        'HTTP_SERVER_ERROR': {},
    },
    DARK_PALETTE: {
        'ERROR':        {'fg': 'red', 'opts': ('bold',)},
        'NOTICE':       {'fg': 'red'},
        'SQL_FIELD':    {'fg': 'green', 'opts': ('bold',)},
        'SQL_COLTYPE':  {'fg': 'green'},
        'SQL_KEYWORD':  {'fg': 'yellow'},
        'SQL_TABLE':    {'opts': ('bold',)},
        'HTTP_INFO':         {'opts': ('bold',)},
        'HTTP_SUCCESS':      {},
        'HTTP_REDIRECT':     {'fg': 'green'},
        'HTTP_NOT_MODIFIED': {'fg': 'cyan'},
        'HTTP_BAD_REQUEST':  {'fg': 'red', 'opts': ('bold',)},
        'HTTP_NOT_FOUND':    {'fg': 'yellow'},
        'HTTP_SERVER_ERROR': {'fg': 'magenta', 'opts': ('bold',)},
    },
    LIGHT_PALETTE: {
        'ERROR':        {'fg': 'red', 'opts': ('bold',)},
        'NOTICE':       {'fg': 'red'},
        'SQL_FIELD':    {'fg': 'green', 'opts': ('bold',)},
        'SQL_COLTYPE':  {'fg': 'green'},
        'SQL_KEYWORD':  {'fg': 'blue'},
        'SQL_TABLE':    {'opts': ('bold',)},
        'HTTP_INFO':         {'opts': ('bold',)},
        'HTTP_SUCCESS':      {},
        'HTTP_REDIRECT':     {'fg': 'green', 'opts': ('bold',)},
        'HTTP_NOT_MODIFIED': {'fg': 'green'},
        'HTTP_BAD_REQUEST':  {'fg': 'red', 'opts': ('bold',)},
        'HTTP_NOT_FOUND':    {'fg': 'red'},
        'HTTP_SERVER_ERROR': {'fg': 'magenta', 'opts': ('bold',)},
    }
}
DEFAULT_PALETTE = DARK_PALETTE


def parse_color_setting(config_string):
    """Parse a DJANGO_COLORS environment variable to produce the system palette

    The general form of a pallete definition is:

    "palette;role=fg;role=fg/bg;role=fg,option,option;role=fg/bg,option,option"

    where:
        palette is a named palette; one of 'light', 'dark', or 'nocolor'.
        role is a named style used by Django
        fg is a background color. [foreground surely]
        bg is a background color.
        option is a display options.

    Specifying a named palette is the same as manually specifying
    the individual
    definitions for each role. Any individual definitions following the pallete
    definition will augment the base palette definition.

    Valid roles:
        'error', 'notice', 'sql_field', 'sql_coltype', 'sql_keyword',
        'sql_table',
        'http_info', 'http_success', 'http_redirect', 'http_bad_request',
        'http_not_found', 'http_server_error'

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal'

    """
    if not config_string:
        return PALETTES[DEFAULT_PALETTE]

    # Split the color configuration into parts
    parts = config_string.lower().split(';')
    palette = PALETTES[NOCOLOR_PALETTE].copy()
    for part in parts:
        if part in PALETTES:
            # A default palette has been specified
            palette.update(PALETTES[part])
        elif '=' in part:
            # Process a palette defining string
            definition = {}

            # Break the definition into the role,
            # plus the list of specific instructions.
            # The role must be in upper case
            role, instructions = part.split('=')
            role = role.upper()

            styles = instructions.split(',')
            styles.reverse()

            # The first instruction can contain a slash
            # to break apart fg/bg.
            colors = styles.pop().split('/')
            colors.reverse()
            foreg = colors.pop()
            if foreg in COLOR_NAMES:
                definition['fg'] = foreg
            if colors and colors[-1] in COLOR_NAMES:
                definition['bg'] = colors[-1]

            # All remaining instructions are options
            opts = tuple(s for s in styles if s in OPT_DICT.keys())
            if opts:
                definition['opts'] = opts

            # The nocolor palette has all available roles.
            # Use that palette as the basis for determining
            # if the role is valid.
            if role in PALETTES[NOCOLOR_PALETTE] and definition:
                palette[role] = definition

    # If there are no colors specified, return the empty palette.
    if palette == PALETTES[NOCOLOR_PALETTE]:
        return None
    return palette
