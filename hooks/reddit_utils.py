import os
import pwd
import grp
import re
import sys
import subprocess
import glob
from lib.utils import render_template
import apt_pkg as apt

from charmhelpers.contrib.openstack.utils import (
    get_hostname,
)



PACKAGES = [
    'git-core'
    , 'python-dev'
    , 'python-setuptools'
    , 'python-routes'
    , 'python-pylons'
    , 'python-boto'
    , 'python-tz'
    , 'python-crypto'
    , 'python-babel'
    , 'cython'
    , 'python-sqlalchemy'
    , 'python-beautifulsoup'
    , 'python-chardet'
    , 'python-psycopg2'
    , 'python-pycassa'
    , 'python-imaging'
    , 'python-pycaptcha'
    , 'python-amqplib'
    , 'python-pylibmc'
    , 'python-bcrypt'
    , 'python-snudown'
    , 'python-l2cs'
    , 'python-lxml'
    , 'python-zope.interface'
    , 'python-kazoo'
    , 'python-stripe'
    , 'python-tinycss2'
    , 'python-flask'
    , 'geoip-bin'
    , 'geoip-database'
    , 'python-geoip'
    , 'nodejs'
    , 'node-less'
    , 'node-uglify'
    , 'gettext'
    , 'make'
    , 'optipng'
    , 'jpegoptim'    
]
