#!/usr/bin/python

import os
import os.path
import sys
import subprocess
import shutil, glob

sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

from charmhelpers.core import (
    hookenv
    , host
)

from charmhelpers.fetch import (
    add_source
    , apt_update
    , apt_install
)

from charmhelpers.core.hookenv import (
    config
    , open_port
    , relation_set
    , relation_get
    , relation_ids
    , unit_get
)

hooks = hookenv.Hooks()
log = hookenv.log


SERVICE = 'reddit'
REDDIT_USER = 'reddit'
REDDIT_GROUP = 'reddit'
REDDIT_HOME = '/home/reddit'

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
    #, 'nodejs'
    #, 'node-less'
    #, 'node-uglify'
    #, 'memcached'
    #, 'postgresql'
    , 'postgresql-client'
    #, 'rabbitmq-server'
    #, 'cassandra'
    #, 'haproxy'
    #, 'nginx'
    #, 'stunnel'
    #, 'gunicorn'
    #, 'sutro'
    , 'python-pip'
]
PIP_MODULES = [
    'pycassa'
    , 'stripe'
    , 'tinycss2'
    #   Not sure this is available via pip: see https://github.com/reddit/snudown; clone it?
    #, 'snudown'
    , 'l2cs'
]

@hooks.hook('db-relation-joined')
def pgsql_db_joined():
    log("pgsql_db_joined")
    
    # When the relationship is joined, create the reddit database
    print "pgsql!"

@hooks.hook('db-relation-changed')
def pgsql_db_changed():
    log("pgsql_db_changed")
    print "pgsql!!"

@hooks.hook('install')
def install():
    log('Installing reddit')
    add_source(config('source'), config('key'))
    apt_update(fatal=True)
    apt_install(packages=PACKAGES, fatal=True)
    
    # Install modules via pip that aren't available via apt-get:
    pip_install (PIP_MODULES)
    
    add_user_group()
    
    git_pull()
    
    # os.chmod(new_mongo_dir, curr_dir_stat.st_mode)    
    cmd = ['chown', '-R', '%s:%s' % (REDDIT_USER, REDDIT_GROUP), REDDIT_HOME]
    print cmd
    subprocess.call(cmd)
    
    log('Configuring Cassandra')
    
    log('Configuring PostgreSQL')
    
    log('Configuring RabbitMQ')
    
    log('Installing Reddit')
    
    
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


# function clone_reddit_repo {
#     local destination=$REDDIT_HOME/src/${1}
#     local repository_url=https://github.com/${2}.git
#
#     if [ ! -d $destination ]; then
#         sudo -u $REDDIT_USER git clone $repository_url $destination
#     fi
#
#     if [ -d $destination/upstart ]; then
#         cp $destination/upstart/* /etc/init/
#     fi
# }
# clone_reddit_repo reddit reddit/reddit
def clone_reddit_repo (target, repo):
    repository_url = 'https://github.com/%s.git' % repo
    destination = '%s/src/%s' % (REDDIT_HOME, target)
    
    log('Cloning github repo %s to %s' % (repo, destination))

    if os.path.isdir(destination) is False:
        # mkdir
        host.mkdir(destination)
        
        cmd = ['git', 'clone', repository_url, destination]
        print cmd
        subprocess.call(cmd)

        # if [ -d $destination/upstart ]; then
        #     cp $destination/upstart/* /etc/init/
        # fi
        
        if os.path.isdir('%s/upstart' % destination):
            log('Copying upstart script(s)')
            #/home/reddit/src/reddit/upstart
            #/home/reddit/src/reddit/upstart/*
            for file in glob.glob('%s/upstart/*' % destination):
                shutil.copy (file, '/etc/init/')
        # cmd = ['chown', '-R', '%s:%s' % (REDDIT_USER, REDDIT_GROUP), destination]
        # print cmd
        # subprocess.call(cmd)
        
    else:
        # chdir
        # git pull
        # cmd = ['sudo', '-u %s' % REDDIT_USER, 'git', 'clone', GIT_URL, srcdir]
        # log(cmd)
        # subprocess.call(cmd_line)
        None

def clone_reddit_plugin_repo (name):
    clone_reddit_repo (name, 'reddit/reddit-plugin-%s' % name)
    
def git_pull():
    #log('Cloning %s' % GIT_URL)

    # clone_reddit_repo reddit reddit/reddit
    # clone_reddit_repo i18n reddit/reddit-i18n
    # clone_reddit_plugin_repo about
    # clone_reddit_plugin_repo liveupdate
    # clone_reddit_plugin_repo meatspace

    clone_reddit_repo('reddit', 'reddit/reddit')
    clone_reddit_repo('i18n', 'reddit/reddit-i18n')
    clone_reddit_plugin_repo('about')
    clone_reddit_plugin_repo('liveupdate')
    clone_reddit_plugin_repo('meatspace')
        
def add_user_group():
    host.adduser(REDDIT_USER)
    host.add_user_to_group(REDDIT_USER, REDDIT_GROUP)
    
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
