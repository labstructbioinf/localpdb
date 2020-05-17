import io
import os
from setuptools import setup, find_packages

VERSION = '0.1'
install_reqs = ['setuptools']

setup(name='localpdb',
      version=VERSION,
      description='Python package for handling a local copy of the PDB database and auxiliary files',
      author='Jan Ludwiczak',
      author_email='j.ludwiczak@cent.uw.edu.pl',
      url='https://github.com/labstructbioinf/localpdb',
      packages=find_packages(),
      install_requires=install_reqs,
      scripts=['bin/localpdb_setup.py', 'bin/localpdb_update.py'],
      package_data={'localpdb.utils': ['remote_sources.yml']},
      include_package_data=True,
      )