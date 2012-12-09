#!/usr/bin/env python

from distutils.core import setup

setup(name='Magpy',
      version='1.0',
      description='Asynchronous REST Framework',
      author='Zeth',
      author_email='theology@gmail.co,',
      url='https://github.com/zeth/magpy/',
      packages=['magpy',
                'magpy.server',
                'magpy.management',
                'magpy.management.commands',
                'magpy.conf',
                'magpy.conf.app_template',
                'magpy.conf.app_template.app',
                'magpy.conf.app_template.app.management',
                'magpy.conf.app_template.app.management.commands'],
      scripts=['mag.py',]
     )
