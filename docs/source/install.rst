Installing Magpy
================

Installation
------------

Download the code using::

    git clone https://github.com/zeth/magpy

Enter the Magpy source directory::

    cd magpy

Install Magpy::

    python setup.py install

As always, virtualenv can be a very useful tool.

.. note:: Operating System

    At the moment, we assume you are installing Magpy on a Posix system i.e. GNU/Linux or BSD or Mac OS X, etc.

    There is no particular reason why Magpy should not work on Windows, but no one has tested it yet.

    Indeed, the majority of the known users have Ubuntu Server, so we strongly appreciate any feedback from users of other distributions and operating systems.

Database
--------

.. note:: Database

    It was originally conceived that Magpy would allow the user to choose their own database. However, we liked MongoDB so much that we never bothered supporting another database, so currently you have the choice of that.

Magpy uses the database MongoDB_, you can get the MongoDB from their website or your Linux distribution has probably packaged it already, e.g. on Ubuntu::

    sudo apt-get install mongodb

Web Server
----------

To actually deploy your Magpy powered applications, you need some kind of web server. It is also quite useful when developing your site to have the web server in place, but it is not absolutely required, especially if you are just doing initial experiments or are evaluating if you like Magpy.

We happen to like Nginx_, which on Ubuntu you can install with::

    sudo apt-get install nginx

However, there is no reason why you cannot use lighttpd or Apache or Google App Engine or whatever you want.

Test Framework
--------------

To use Magpy's test framework to test your apps, you need to install PyV8_::

    pip install pyv8

You will only need this on your development machine, it is not required on your deployment server. 

.. note:: Build System

    The install of pyv8 assumes you have a C++ build system setup with make, GCC and all the rest.

    It is also over-sensitive about path locations.

    On Ubuntu, you `can refer to this article`_ which seems to work well.

.. _MongoDB: http://www.mongodb.org/
.. _Motor: http://motor.readthedocs.org
.. _Nginx: http://nginx.org/
.. _PyV8: http://code.google.com/p/pyv8/
.. _`can refer to this article`: http://blog.dinotools.de/2013/02/27/python-build-pyv8-for-python3-on-ubuntu
