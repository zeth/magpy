Serverside Application Server
=============================

The serverside part of Magpy is the application server. The basic command line tool to control the server is called mag.py. To see the basic usage type::

    mag.py help

For help on a specific subcommand, type::

    mag.py help <subcommand>

.. note:: History

    If you have ever used Django before, you will understand if I explain that Magpy started out as a Django application but eventually my site did not use Django anymore. However, the Django background can often be seen - for example, mag.py is a copy of Django's manage.py

The key command is::

    mag.py run

This command starts magpy.server, the core application server. By default, the server runs on port 8000. By using the -p command line option, you can specify a different port.

In development, you will want to use only one instance of the application server at a time for ease of debugging. In production, you typically use one or two per processor core.

You do not accept requests directly at the application server. Instead you will typically have Nginx or another web server proxying requests upstream_ to the application server.

The application server is a subclass of the Tornado server. To understand how to configure Ngnix, refer to the `Tornado documentation`_.

You will want to get the web server setup on your development machine as soon as possible. While Python is pretty flexible about where requests are coming from, `JavaScript is not`_. It is best to avoid any potential headaches by making the differences between the development environment and the deployment environment as small as possible.

Don't forget that in development, you can assign yourself as many local domain names as you need by adding lines to the hosts file (typically /etc/hosts).


.. _upstream: http://wiki.nginx.org/HttpUpstreamModule
.. _`Tornado documentation`: http://www.tornadoweb.org/en/stable/overview.html#running-tornado-in-production
.. _`JavaScript is not`: https://developer.mozilla.org/en-US/docs/JavaScript/Same_origin_policy_for_JavaScript
