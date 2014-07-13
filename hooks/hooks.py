#!/usr/bin/python

import os
import sys
import subprocess

sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

from charmhelpers.core import (
    hookenv,
    host,
)

from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install
)

from charmhelpers.core.hookenv import (
    config
)

hooks = hookenv.Hooks()
log = hookenv.log


SERVICE = 'reddit'

PACKAGES = [
    'netcat-openbsd'
    , 'git-core'
    , 'python-dev'
    , 'python-setuptools'
    , 'python-routes'
    , 'python-pylons'
    , 'python-tz'
    , 'python-crypto'
    , 'python-babel'
    , 'cython'
    , 'python-sqlalchemy'
    , 'python-beautifulsoup'
    , 'python-chardet'
    , 'python-psycopg2'
    #, 'python-pycassa'
    , 'python-imaging'
    #, 'python-pycaptcha'
    , 'python-amqplib'
    , 'python-pylibmc'
    , 'python-bcrypt'
    #, 'python-snudown'
    #, 'python-l2cs'
    , 'python-lxml'
    , 'python-zope.interface'
    , 'python-kazoo'
    #, 'python-stripe'
    #, 'python-tinycss2'
    , 'python-flask'
    , 'geoip-bin'
    , 'geoip-database'
    , 'python-geoip'
    , 'gettext'
    , 'make'
    , 'optipng'
    , 'jpegoptim'
    , 'nodejs'
    , 'node-less'
    , 'node-uglify'
    , 'memcached'
    , 'postgresql'
    , 'postgresql-client'
    , 'rabbitmq-server'
    #, 'cassandra'
    , 'haproxy'
    , 'nginx'
    , 'stunnel'
    , 'gunicorn'
    #, 'sutro'
    , 'python-pip'
]
PIP_MODULES = [
    'pycassa'
    , 'stripe'
    , 'tinycss2'
    , 'snudown'
    , 'l2cs'
]
@hooks.hook('install')
def install():
    log('Installing reddit')
    add_source(config('source'), config('key'))
    apt_update(fatal=True)
    apt_install(packages=PACKAGES, fatal=True)
    
    # Install modules via pip that aren't available via apt-get:
    pip_install (PIP_MODULES)
        
    return True


@hooks.hook('config-changed')
def config_changed():
    config = hookenv.config()

    for key in config:
        if config.changed(key):
            log("config['{}'] changed from {} to {}".format(
                key, config.previous(key), config[key]))

    config.save()
    start()


@hooks.hook('upgrade-charm')
def upgrade_charm():
    log('Upgrading reddit')


@hooks.hook('start')
def start():
    #host.service_restart(SERVICE) or host.service_start(SERVICE)
    None


@hooks.hook('stop')
def stop():
    #host.service_stop(SERVICE)
    None

def pip_install(packages=None, upgrade=False):
    # Build in /tmp or Juju's internal git will be confused
    cmd_line = ['pip', 'install', '--src', '/usr/src/']
    if packages is None:
        return(False)
    if upgrade:
        cmd_line.append('--upgrade')
    if not isinstance(packages, list):
        packages = [packages]
 
    for package in packages:
        if package.startswith('svn+') or package.startswith('git+') or package.startswith('hg+') or package.startswith('bzr+'):
            cmd_line.append('-e')
        cmd_line.append(package)

    #cmd_line.append('--use-mirrors')
    return(subprocess.call(cmd_line))

if __name__ == "__main__":
    # execute a hook based on the name the program is called by
    hooks.execute(sys.argv)
