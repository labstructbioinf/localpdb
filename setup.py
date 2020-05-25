import io
import os
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

VERSION = '0.1.0'
with open('requirements.txt') as f:
      install_reqs = f.read().splitlines()

setup(name='localpdb',
      version=VERSION,
      description='Store, manage and query the local copy of the PDB (Protein Data Bank) resources.',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Jan Ludwiczak',
      author_email='j.ludwiczak@cent.uw.edu.pl',
      url='https://github.com/labstructbioinf/localpdb',
      packages=find_packages(),
      install_requires=install_reqs,
      python_requires=">=3.6.1",
      extras_require={'dev': ['pytest>=4.0', 'pytest-dependency>=0.3', 'pytest_cov>=2.8']},
      scripts=['bin/localpdb_setup.py', 'bin/localpdb_update.py'],
      package_data={'localpdb.utils': ['remote_sources.yml'],
                    '': ['requirements.txt'],
                    'tests': ['test_config.yml']},
      include_package_data=True,
      classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
      ],
      )