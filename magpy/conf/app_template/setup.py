#!/usr/bin/env python
"""Setup file for ${app_name}."""

from distutils.core import setup

setup(name='${app_name}',
      version='1.0',
      description='Description of ${app_name}',
      author='Someone',
      author_email='someone@example.com',
      url='https://github.com/someone/${app_name}/',
      packages=['${app_name}',
                '${app_name}.management',
                '${app_name}.management.commands'],
      package_data={'${app_name}': ['static/*']},
     )
