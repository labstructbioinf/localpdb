import io
import os
from setuptools import setup, find_packages

VERSION = '0.1'
with open('requirements.txt') as f:
      install_reqs = f.read().splitlines()

setup(name='localpdb',
      version=VERSION,
      description='Python package for handling a local copy of the PDB database and auxiliary files',
      author='Jan Ludwiczak',
      author_email='j.ludwiczak@cent.uw.edu.pl',
      url='https://github.com/labstructbioinf/localpdb',
      packages=find_packages(),
      install_requires=install_reqs,
      python_requires=">=3.6.1",
      scripts=['bin/localpdb_setup.py', 'bin/localpdb_update.py'],
      package_data={'localpdb.utils': ['remote_sources.yml'],
                    '': ['requirements.txt']},
      include_package_data=True,
      )