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



def create_helper_scripts():

    f = open('/usr/local/bin/reddit-run', 'w')
    f.write(
    """
    #!/bin/bash
    exec paster --plugin=r2 run %s/src/reddit/r2/run.ini "\$@"
    """ % REDDIT_HOME)
    f.close()
    os.chmod('/usr/local/bin/reddit-run', 755)
    
    f = open('/usr/local/bin/reddit-shell', 'w')
    f.write(
    """
    #!/bin/bash
    exec paster --plugin=r2 shell %s/src/reddit/r2/run.ini
    """ % REDDIT_HOME)
    f.close()
    os.chmod('/usr/local/bin/reddit-shell', 755)
    
    return
    
def populate_test_data():
    # cd $REDDIT_HOME/src/reddit/r2
    # reddit-run r2/models/populatedb.py -c 'populate()'
    cmd = ['reddit-run', '%s/src/reddit/r2/models/populatedb.py' % REDDIT_HOME, '-c', '\'populate()\'']
    print cmd
    check = subprocess.check_output(cmd)
    print check
    return
    
def is_pgsql_db_installed():
    
    # Check the system catalog for function(s) created during installation
    sql = "select count(*) from information_schema.tables where table_schema = 'public';"
    #IS_DATABASE_CREATED=$(sudo -u postgres psql -t -c "$SQL")
    cmd = ['psql', '-t', '-c', sql]
    print cmd
    check = subprocess.check_output(cmd)
    
    log('db check = %i' % int(check))
    return int(check)

def install_pgsql_db():
    # Install the base database
    log('installing reddit database')
    # Install reddit's pgsql functions
    # NOTE: These are create or replace, so it should be run every time a git pull happens
    
    cmd = ['psql', '-f', '%s//src/reddit/sql/functions.sql' % REDDIT_HOME]
    print cmd
    check = subprocess.check_output(cmd)
    
    # TODO: Add some kind of output check?
    return True
        
@hooks.hook('db-relation-joined')
def pgsql_db_joined():
    log("pgsql_db_joined")
    hookenv.relation_set(relation_settings={"database": "reddit"})

@hooks.hook('db-relation-broken')
def pgsql_db_changed():
    log("pgsql_db_broken")

@hooks.hook('db-relation-changed')
def pgsql_db_changed():
    log("pgsql_db_changed")
    
    db_user = hookenv.relation_get('user')
    db_pass = hookenv.relation_get('password')
    db_name = hookenv.relation_get('database')
    db_host = hookenv.relation_get('private-address')
    db_port = hookenv.relation_get('port')
    
    if db_name is None:
        log("No database info sent yet.")
        return 0
    log("Database info received -- host: %s; name: %s; user: %s; password: %s" % (db_host, db_name, db_user, db_pass))

    # Following the lead of pgbouncer and using environment variables, but security.
    os.environ['PGHOST'] = db_host
    os.environ['PGPORT'] = db_port
    os.environ['PGDATABASE'] = db_name
    os.environ['PGUSER'] = db_user
    os.environ['PGPASSWORD'] = db_pass
    
    if not is_pgsql_db_installed():
        log('calling install_pgsql_db()')
        if install_pgsql_db():
            log('reddit database installed')
        else:
            log('failed to install pgsql database')
    else:
        log('reddit pgsql database is already installed')
        
    config = hookenv.config()
    if config['development-mode']:
        # Load the pre-populated data
        None
    
    log('Populating test data')
    populate_test_data()
    
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
    
    log('Creating helper scripts')
    create_helper_scripts()
    
    log('Configuring Cassandra')
    
    log('Configuring PostgreSQL')
    
    log('Configuring RabbitMQ')
    
    log('Installing Reddit')
    
    # TODO: This needs to be run under Precise
    # BLOCKED: bug #1316174
    #install_reddit_repo('reddit/r2')
    #install_reddit_repo('i18n')
    #install_reddit_repo('about')
    #install_reddit_repo('liveupdate')
    #install_reddit_repo('meatspace')
    
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


def install_reddit_repo(repo):
    subprocess.call(
    """
    cd %s/src/%s
    sudo -u %s python setup.py build
    python setup.py develop --no-deps
    """ % (REDDIT_HOME, repo, REDDIT_USER), shell=True)
    return

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
