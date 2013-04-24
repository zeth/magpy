Settings
========

Settings are any little bits of site specific information that you do not want to hard code into your applications' source code.


Settings in the database
------------------------

It is encouraged to put as many site specific settings as possible in the database. Either in the _settings collection or your own defined collections.

There is a handy mag.py command for quickly adding a setting to the database, use as follows::

    mag.py add_setting category setting value

_settings is a collection where each instance is a category of settings and each instance field is the settings name and value.



Config File
-----------

A lot of site specific settings are just data like any other, and are best put in the database.

However, in order to connect to the database, we need certain settings to be defined already - i.e. what the database is called. These are in the config file.

Also some data may be so sensitive that we may not be comfortable exposing to the website at all, such as the cookie secret.

The config file is (of course) in the JSON format, you can put keys and values in as you might expect.

The settings file also allows Javascript style comments, these are stripped out before the file is loaded.

You can tell the server where to find the settings file with the --conf argument to mag.py run::

    mag.py run --conf /srv/mysite/mysitesettings.json

If you don't give a settings file, then Magpy uses the file magpy/server/defaultconfig.json, which by default looks like this:

.. code-block:: javascript

    {
        "port": 8000,
        "cookie_secret": "11oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
        "databases": {
            "default": {
                "ENGINE": "mongodb",
                "NAME": "vmr"}
        }
    }


Cookie Secret
-------------

When users of your website log in, they each receive a cookie, this is signed using a secret key (i.e. a cookie secret). Therefore, you should create your own cookie secret and specify it in the config file.

If you create a config file using the create_config_file command, it will automatically create a cookie secret for you. E.g. say config.json is the new file path::

    mag.py create_config_file config.json

If you accidentally share the cookie secret, e.g. accidentally push it to github or something, then don't worry. All you need to do is run the command again on the file, which will update the cookie secret.

Database Settings
-----------------

The database settings allow you to define the database(s) used by your site.


.. note:: Motivation

    One of my personal gripes while using a major Python web framework, is that it required a 'settings.py' file that started out quite long, and then when you included some third party applications, got even longer. A lot of these settings could have just been replaced by sensible defaults. Furthermore, the whole thing was a maintenance nightmare - every time a new version of the framework or an application came out, it would all break because the settings.py file was out of date. When you have a few dozen sites running on the framework, going through every settings.py file with diff was like pulling teeth.

    This problem never happens with some other applications, for example, Wordpress, since most of the settings are in the database. When the schema changes, the authors of Wordpress or plugins would provide a helper script or command which would migrate the schema for you.

    I avoided any config file for as long as possible, but it became inevitable. However, it is still optional to some degree - you can at least develop a site without worrying too much about it. 
