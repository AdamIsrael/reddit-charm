#!/usr/bin/python

import os
import os.path
import pwd
import sys
import shlex, subprocess
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
REDDIT_DOMAIN = unit_get('public-address')
CONSUMER_CONFIG_ROOT = '%s/consumer-count.d' % REDDIT_HOME

# For simplification of string formatting
CONFIG = { 
    'REDDIT_HOME': REDDIT_HOME
    , 'REDDIT_USER': REDDIT_USER
    , 'REDDIT_GROUP': REDDIT_GROUP
    , 'REDDIT_DOMAIN': REDDIT_DOMAIN
    , 'CONSUMER_CONFIG_ROOT': CONSUMER_CONFIG_ROOT
}

PACKAGES = [
    'python-software-properties'
    ,'netcat-openbsd'
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
    , 'gettext'
    , 'make'
    , 'optipng'
    , 'jpegoptim'
    #, 'nodejs'
    , 'node-less'
    , 'node-uglify'
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
    #, 'kazoo'
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
    os.chmod('/usr/local/bin/reddit-run', 0755)
    
    f = open('/usr/local/bin/reddit-shell', 'w')
    f.write(
    """
    #!/bin/bash
    exec paster --plugin=r2 shell %s/src/reddit/r2/run.ini
    """ % REDDIT_HOME)
    f.close()
    os.chmod('/usr/local/bin/reddit-shell', 0755)
    
    return
    
def populate_test_data():
    # cd $REDDIT_HOME/src/reddit/r2
    # reddit-run r2/models/populatedb.py -c 'populate()'
    cmd = ['reddit-run', '%s/src/reddit/r2/models/populatedb.py' % REDDIT_HOME, '-c', '\'populate()\'']
    check = subprocess.check_output(cmd)
    # TODO: sanity check the return output
    return
    
def is_pgsql_db_installed():
    # Check the system catalog for table(s) created during installation
    sql = "select count(*) from information_schema.tables where table_schema = 'public';"
    cmd = ['psql', '-t', '-c', sql]
    check = subprocess.check_output(cmd)
    return int(check)

def install_pgsql_functions():
    # Install the base database
    log('installing reddit functions')
    # Install reddit's pgsql functions
    # NOTE: These are create or replace, so it should be run every time a git pull happens
    cmd = ['psql', '-f', '%s//src/reddit/sql/functions.sql' % REDDIT_HOME]
    check = subprocess.check_output(cmd)
    
    # TODO: sanity check the return output
    return True
        
@hooks.hook('db-relation-joined')
def pgsql_db_joined():
    log("pgsql_db_joined")
    hookenv.relation_set(relation_settings={"database": "reddit"})

@hooks.hook('db-relation-broken')
def pgsql_db_broken():
    log("pgsql_db_broken")

@hooks.hook('db-relation-changed')
def pgsql_db_changed():
    log("pgsql_db_changed")
    
    if hookenv.relation_get('database') is None:
        log("No database info sent yet.")
        return 0

    db_user = hookenv.relation_get('user')
    db_pass = hookenv.relation_get('password')
    db_name = hookenv.relation_get('database')
    db_host = hookenv.relation_get('private-address')
    db_port = hookenv.relation_get('port')

    log("Database info received -- host: %s; name: %s; user: %s; password: %s" % (db_host, db_name, db_user, db_pass))

    # Following the lead of pgbouncer and using environment variables, but security.
    os.environ['PGHOST'] = db_host
    os.environ['PGPORT'] = db_port
    os.environ['PGDATABASE'] = db_name
    os.environ['PGUSER'] = db_user
    os.environ['PGPASSWORD'] = db_pass
    
    if not is_pgsql_db_installed():
        if install_pgsql_functions():
            log('reddit database functions installed')
        
    # config = hookenv.config()
    # if config['development-mode']:
    #     # Load the pre-populated data
    #     log('Populating test data')
    #     populate_test_data()
    #     None

@hooks.hook('database-relation-joined')
def cassandra_joined():
    #hookenv.relation_set(relation_settings={"database": "reddit"})
    return

@hooks.hook('database-relation-changed')
def cassandra_changed():
    import pycassa
    #from pycassa.system_manager import *
    #from pycassa.types import *

    # relation-get:
    # port: "9160"
    # private-address: 10.0.3.147
    casshost = '%s:%d' % (hookenv.get_relation('private-address'), hookenv.get_relation('port'))

    # Create 'reddit' keyspace
    sys = pycassa.system_manager.SystemManager(casshost)
    

    # if ! echo | cassandra-cli -h localhost -k reddit &> /dev/null; then
    # echo "create keyspace reddit;" | cassandra-cli -h localhost -B
    # fi
    try:
        sys.create_keyspace('reddit', pycassa.system_manager.SIMPLE_STRATEGY, {'replication_factor': '1'})
        log("Created 'reddit' keyspace")
    except pycassa.cassandra.ttypes.InvalidRequestException:
        log("'reddit' keyspace already exists.")
        pass
    # throws pycassa.cassandra.ttypes.InvalidRequestException on duplicate
    
    # cat <<CASS | cassandra-cli -B -h localhost -k reddit || true
    # create column family permacache with column_type = 'Standard' and
    # comparator = 'BytesType';
    # CASS
    try:
        sys.create_column_family('reddit', 'permacache', column_type='Standard', default_validation_class=pycassa.types.BYTES_TYPE)
        log("Created 'reddit' column")
    except pycassa.cassandra.ttypes.InvalidRequestException:
        log("'reddit' column already exists")
        pass
    
    return
    
@hooks.hook('install')
def install():
    log('Installing reddit')
    

    add_source(config('source'), config('key'))
    apt_update(fatal=True)
    
    # Add the reddit PPA
    # TODO: is there a better way to do this via charmhelpers?
    
    # apt-get update
    # # add the reddit ppa for some custom packages
    # apt-get install $APTITUDE_OPTIONS python-software-properties
    # apt-add-repository -y ppa:reddit/ppa
    add_source('ppa:reddit/ppa')
    
    f = open('/etc/apt/preferences.d/reddit', 'w')
    f.write(
    """Package: *
Pin: release o=LP-PPA-reddit
Pin-Priority: 600""")

    f.close()

    apt_update(fatal=True)
    
    apt_install(packages=PACKAGES, fatal=True)
    
    # Install modules via pip that aren't available via apt-get:
    pip_install (PIP_MODULES)
    
    add_user_group()
    
    git_pull()
    
    log('Configuring Cassandra')
    
    log('Configuring PostgreSQL')
    
    log('Configuring RabbitMQ')
    
    log('Installing Reddit')
    
    # TODO: This needs to be run under Precise
    install_reddit_repo('reddit/r2')
    install_reddit_repo('i18n')
    install_reddit_repo('about')
    install_reddit_repo('liveupdate')
    install_reddit_repo('meatspace')
    
    # Generate binary translation files
    log("Generating binary translation files")
    subprocess.call("""
    cd %s/src/i18n
    sudo -u %s make
    """ % (REDDIT_HOME, REDDIT_USER), shell=True)

    install_path = '%s/src/reddit/r2' % REDDIT_HOME
    
    log("Building reddit")
    subprocess.call("""
    cd %s/src/reddit/r2
    sudo -u %s make
    """ % (REDDIT_HOME, REDDIT_USER), shell=True)

    # TODO: Move this to config-change?
    # TODO: Think about scalablity of the reddit app
    # TODO: Should I add reddit's ini options to the charm config?
    # TODO: Figure out the process for dealing with changes to the ini set via config -- i.e., does 'make ini' need to be re-run?
    # Default the domain to the local server, until the config option has been changed.
    log("Creating default ini")
    f = open('%s/development.update' % install_path, 'w')
    f.write(
    """
# after editing this file, run "make ini" to
# generate a new development.ini
[DEFAULT]
debug = true
disable_ads = true
disable_captcha = true
disable_ratelimit = true
disable_require_admin_otp = true
page_cache_time = 0
domain = %s
plugins = about, liveupdate, meatspace
media_provider = filesystem
media_fs_root = /srv/www/media
media_fs_base_url_http = http://%s/media/
media_fs_base_url_https = https://%s/media/
[server:main]
port = 8001
    """ % (REDDIT_DOMAIN, REDDIT_DOMAIN, REDDIT_DOMAIN))
    f.close()
    #uid = pwd.getpwnam(REDDIT_USER).pw_uid
    #gid = pwd.getpwnam(REDDIT_USER).pw_gid
    #os.chown('%s/development.update' % install_path, uid, gid)
    
    log("Building reddit ini")
    subprocess.call("""
    cd %s
    sudo -u %s make ini
    """ % (install_path, REDDIT_USER), shell=True)
    
    # if [ ! -L run.ini ]; then
    # sudo -u $REDDIT_USER ln -s development.ini run.ini
    # fi
    if os.path.isfile('%s/run.ini' % install_path) is False:
        cmd = 'sudo -u %s ln -s %s/development.ini %s/run.ini' % (REDDIT_USER, install_path, install_path)
        log('Symlinking ini - %s' % cmd)
        subprocess.call(shlex.split(cmd))
    
    log('Creating helper scripts')
    create_helper_scripts()

    
    log("chowning %s" % REDDIT_HOME)
    cmd = 'chown -R %s:%s %s' % (REDDIT_USER, REDDIT_GROUP, REDDIT_HOME)
    log(cmd)
    subprocess.call(shlex.split(cmd))
    
    log('Configuring job environment')
    configure_job_environment()
    # Start reddit
    # initctl emit reddit-start
    
    return True

def configure_nginx():
    return
    
def configure_haproxy():
    return
    
def configure_stunnel():
    return
    
def configure_sutro():
    return
    
def configure_geoip():
    return
    
def configure_job_environment():
    
    
    if os.path.isfile('/etc/default/reddit') is False:
        f = open('/etc/default/reddit', 'w')
        f.write("""
export REDDIT_ROOT=%(REDDIT_HOME)s/src/reddit/r2
export REDDIT_INI=%(REDDIT_HOME)s/src/reddit/r2/run.ini
export REDDIT_USER=%(REDDIT_USER)s
export REDDIT_GROUP=%(REDDIT_GROUP)s
export REDDIT_CONSUMER_CONFIG=%(CONSUMER_CONFIG_ROOT)s
alias wrap-job=%(REDDIT_HOME)s/src/reddit/scripts/wrap-job
alias manage-consumers=%(REDDIT_HOME)s/src/reddit/scripts/manage-consumers        
        """ % CONFIG)
        f.close()
        
    return
    
def configure_queue_processors():
    if os.path.isdir(CONSUMER_CONFIG_ROOT) is False:
        host.mkdir(CONSUMER_CONFIG_ROOT)

    def set_consumer_count(queue, count):
        queueFile = '%s/%s' % (CONSUMER_CONFIG_ROOT, queue)
        if os.path.isfile(queueFile) is False:
            f = open(queueFile, 'w')
            f.write(count)
            f.close()
            
    set_consumer_count('log_q', 0)
    set_consumer_count('cloudsearch_q', 0)
    set_consumer_count('scraper_q', 1)
    set_consumer_count('scraper_q', 1)
    set_consumer_count('commentstree_q', 1)
    set_consumer_count('newcomments_q', 1)
    set_consumer_count('vote_link_q', 1)
    set_consumer_count('vote_comment_q', 1)
    
    cmd = 'chown -R %s:%s %s/' % (REDDIT_USER, REDDIT_GROUP, CONSUMER_CONFIG_ROOT)
    log(cmd)
    subprocess.call(shlex.split(cmd))
    
    return
    
def install_crontab():
    return
    
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
    """cd %s/src/%s
sudo -u %s python setup.py build
python setup.py develop --no-deps""" % (REDDIT_HOME, repo, REDDIT_USER), shell=True)
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
