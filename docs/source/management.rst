==========================
mag.py management commands
==========================

``mag.py`` is Magpy's command-line utility for administrative tasks.
This document outlines what it can do.


Usage
=====

.. code-block:: bash

    mag.py <command> [options]

``command`` should be one of the commands listed in this document.
``options``, which is optional, should be zero or more of the options available
for the given command.

Getting runtime help
--------------------

Run ``mag.py help`` to display usage information and a list of the
commands provided by each application.

Run ``mag.py help --commands`` to display a list of all available
commands.

Run ``mag.py help <command>`` to display a description of the given
command and a list of its available options.

Determining the version
-----------------------

Run ``mag.py version`` to display the current Mag.py version.

Available commands
==================

startapp <appname> [destination]
--------------------------------

Creates a Magpy app directory structure for the given app name in the current
directory or the given destination.

By default the directory created contains a ``models.py`` file and other app
template files. If only the app name is given, the app directory will be created in the current working
directory.

If the optional destination is provided, Magpy will use that existing
directory rather than creating a new one. You can use '.' to denote the current
working directory.

The new app is not automically brought into use, see add_app below.

For example::

    mag.py startapp myapp /Users/jezdez/Code/myapp

add_app <appname>
-----------------

Adds the app (or apps) to the installed apps setting. This is required for the Magpy Server to recognise your application.

Note your application needs to also be in the Python path, i.e. use the setup.py file of the application to install it into your packages directory.

add_setting [options] [category setting value]
----------------------------------------------

Add a setting to the database. Settings are any little bits of site specific information that you do not want to hard code into your application.  

Settings have a category, a setting name (i.e. key) and value.

list_urls
---------

Show all URLs from the installed applications. Very useful for debugging.

load_models [options] [app_name ...]
------------------------------------

Load the models from app_name(s).

load_pickled_instances [options] [filename ...]
------------------------------------------------------

Add a pickle file of instances to the database.

make_cookie [options] [filelocation]
------------------------------------

Make a cookie secret file.

remove_app [options] [app_name ...]
------------------------------------------

Remove an app_name(s) from installed apps.

remove_setting [options] [category setting]
--------------------------------------------------

Remove a setting from the given setting category.

run [options] [port]
--------------------

Run the REST server.

test <app or test identifier>
-----------------------------

Runs tests for the given application.

collectstatic
-------------

Collects the static files into the static root.

Define the static root with::

    mag.py add_setting static root <filepath>

Each installed app (i.e. one that has been enabled with add_app), has a static directory.

The default is to take these files and group them by application. So an app with example/static/js/example.js will become static/example/js/example.js. To prevent this behaviour, use -p

Syntax coloring
===============

The ``mag.py`` commands will use pretty
color-coded output if your terminal supports ANSI-colored output. It
won't use the color codes if you're piping the command's output to
another program.

The colors used for syntax highlighting can be customized. Django
ships with three color palettes:

* ``dark``, suited to terminals that show white text on a black
  background. This is the default palette.

* ``light``, suited to terminals that show black text on a white
  background.

* ``nocolor``, which disables syntax highlighting.

You select a palette by setting a ``DJANGO_COLORS`` environment
variable to specify the palette you want to use. For example, to
specify the ``light`` palette under a Unix or OS/X BASH shell, you
would run the following at a command prompt::

    export DJANGO_COLORS="light"

You can also customize the colors that are used. Magpy specifies a
number of roles in which color is used:

* ``error`` - A major error.
* ``notice`` - A minor error.
* ``sql_field`` - The name of a model field in SQL.
* ``sql_coltype`` - The type of a model field in SQL.
* ``sql_keyword`` - A SQL keyword.
* ``sql_table`` - The name of a model in SQL.
* ``http_info`` - A 1XX HTTP Informational server response.
* ``http_success`` - A 2XX HTTP Success server response.
* ``http_not_modified`` - A 304 HTTP Not Modified server response.
* ``http_redirect`` - A 3XX HTTP Redirect server response other than 304.
* ``http_not_found`` - A 404 HTTP Not Found server response.
* ``http_bad_request`` - A 4XX HTTP Bad Request server response other than 404.
* ``http_server_error`` - A 5XX HTTP Server Error response.

Each of these roles can be assigned a specific foreground and
background color, from the following list:

* ``black``
* ``red``
* ``green``
* ``yellow``
* ``blue``
* ``magenta``
* ``cyan``
* ``white``

Each of these colors can then be modified by using the following
display options:

* ``bold``
* ``underscore``
* ``blink``
* ``reverse``
* ``conceal``

A color specification follows one of the following patterns:

* ``role=fg``
* ``role=fg/bg``
* ``role=fg,option,option``
* ``role=fg/bg,option,option``

where ``role`` is the name of a valid color role, ``fg`` is the
foreground color, ``bg`` is the background color and each ``option``
is one of the color modifying options. Multiple color specifications
are then separated by semicolon. For example::

    export DJANGO_COLORS="error=yellow/blue,blink;notice=magenta"

would specify that errors be displayed using blinking yellow on blue,
and notices displayed using magenta. All other color roles would be
left uncolored.

Colors can also be specified by extending a base palette. If you put
a palette name in a color specification, all the colors implied by that
palette will be loaded. So::

    export DJANGO_COLORS="light;error=yellow/blue,blink;notice=magenta"

would specify the use of all the colors in the light color palette,
*except* for the colors for errors and notices which would be
overridden as specified.

Bash completion
---------------

If you use the Bash shell, consider installing the Django bash completion
script, which lives in ``extras/django_bash_completion`` in the Django
distribution. It enables tab-completion of ``mag.py`` commands, so you can, for instance...

* Type ``mag.py``.
* Press [TAB] to see all available options.
* Type ``sql``, then [TAB], to see all available options whose names start
  with ``sql``.

Commands provided by applications
=================================

Applications can make commands available, see :doc:`customcommands` for more details.
