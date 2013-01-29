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
                'magpy.conf.app_template.app_name',
                'magpy.conf.app_template.app_name.management',
                'magpy.conf.app_template.app_name.management.commands'],
      scripts=['mag.py',],
      package_data={'magpy.conf.app_template': ['README.md'],
                    'magpy.conf.app_template.app_name': ['static/index.html'],
                    'magpy': ['static/js/mag.js'],
                    },
     )
