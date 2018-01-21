import os
import sys

from setuptools import setup
from distutils.sysconfig import get_python_lib
import importlib.util

''' 
is the Python package in your project. It's the top-level folder containing the 
__init__.py module that should be in the same directory as your setup.py file
/-
  |- README.rst
  |- CHANGES.txt
  |- setup.py
  |- dogs 
     |- __init__.py
     |- catcher.py

To create package and upload:

  python setup.py register
  python setup.py sdist
  twine upload -s dist/path/to/gz

'''


def import_setup_utils():
    # load setup utils
    try:
        setup_utils_spec = \
            importlib.util.spec_from_file_location("setup.utils",
                                                   "setup_utils.py")
        setup_utils = importlib.util.module_from_spec(setup_utils_spec)
        setup_utils_spec.loader.exec_module(setup_utils)
    except Exception as err:
        raise RuntimeError("Failed to find setup_utils.py."
                           " Please copy or link.") from err
    return setup_utils


setup_utils = import_setup_utils()
HERE = os.path.abspath(os.path.dirname(__file__))
PACKAGE = "eventor"
NAME = PACKAGE
METAPATH = os.path.join(HERE, PACKAGE, "__init__.py")
metahost = setup_utils.metahost(PACKAGE)

'''
DESCRIPTION is just a short description of your project. A sentence will suffice.
'''
DESCRIPTION = '''eventor is a python programming facility to program event based sequence of activities'''

'''
AUTHOR and AUTHOR_EMAIL are what they sound like: your name and email address. This 
information is optional, but it's good practice to supply an email address if people 
want to reach you about the project.
'''
AUTHORS = 'Acrisel Team'
AUTHORS_EMAIL = 'support@acrisel.com'

'''
URL is the URL for the project. This URL may be a project website, the Github repository, 
or whatever URL you want. Again, this information is optional.
'''
URL = 'https://github.com/Acrisel/eventor'

# version_file=os.path.join(PACKAGE, 'VERSION.py')
# with open(version_file, 'r') as vf:
#    vline=vf.read()
# VERSION = vline.strip().partition('=')[2].replace("'", "")
# VERSION =__import__(version_file).__version__
VERSION = setup_utils.read_version(metahost=metahost)

# Warn if we are installing over top of an existing installation. This can
# cause issues where files that were deleted from a more recent Accord are
# still present in site-packages. See #18115.
overlay_warning = False
if "install" in sys.argv:
    existing_path = setup_utils.existing_package(PACKAGE)

scripts = setup_utils.scripts(PACKAGE)

# Find all sub packages
packages = setup_utils.packages(PACKAGE)
required = setup_utils.read_required(metahost=metahost)

setup_info = {
    'name': NAME,
    'version': VERSION,
    'url': URL,
    'author': AUTHORS,
    'author_email': AUTHORS_EMAIL,
    'description': DESCRIPTION,
    'long_description': open("README.rst", "r").read(),
    'license': 'MIT',
    'keywords': 'project, virtualenv, parameters',
    'packages': packages,
    'scripts': scripts,
    'install_requires': [
        'SQLAlchemy>=1.1.5',
        'acrilib>=1.0.2',
        'acris>=2.0.2',
        'acrilog>=2.0.11',
        'pyyaml>=3.12',
        'namedlist>=1.7',
        ],
    'extras_require': {'extra': ['setproctitle>=1.1']},
    'classifiers': ['Development Status :: 5 - Production/Stable',
                    'Environment :: Other Environment',
                    # 'Framework :: Project Settings and Operation',
                    'Intended Audience :: Developers',
                    'License :: OSI Approved :: MIT License',
                    'Operating System :: OS Independent',
                    'Programming Language :: Python',
                    'Programming Language :: Python :: 3',
                    'Programming Language :: Python :: 3.2',
                    'Programming Language :: Python :: 3.3',
                    'Programming Language :: Python :: 3.4',
                    'Programming Language :: Python :: 3.5',
                    'Programming Language :: Python :: 3.6',
                    'Topic :: Software Development :: Libraries :: Application Frameworks',
                    ]}
setup(**setup_info)


if overlay_warning:
    sys.stderr.write("""

========
WARNING!
========

You have just installed ProjEnv over top of an existing
installation, without removing it first. Because of this,
your install may now include extraneous files from a
previous version that have since been removed from
Accord. This is known to cause a variety of problems. You
should manually remove the

%(existing_path)s

directory and re-install ProjEnv.

""" % {"existing_path": existing_path})
