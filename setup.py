#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='PacVis',
      version='0.2.7',
      description='Visualize pacman local database using Vis.js,' +
                  ' inspired by pacgraph',
      author='Jiachen Yang',
      author_email='farseerfc@archlinuxcn.org',
      url='https://pacvis.farseerfc.me/',
      packages=find_packages(),
      package_data={'pacvis': ['templates/index.template.html',
                               'static/*'
                               ]},
      entry_points={
          'console_scripts': ['pacvis = pacvis.pacvis:main']
      },
      install_requires=["tornado", "pyalpm",],
      )
