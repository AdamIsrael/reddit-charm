#!/usr/bin/python

import os
import os.path
import pwd
import sys
import shlex
import subprocess
import shutil
import glob
import yaml
from ConfigParser import RawConfigParser

sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

from charmhelpers.core import (
    hookenv,
    host
)

from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
)

from charmhelpers.core.hookenv import (
    config,
    open_port,
    relation_set,
    relation_get,
    relation_ids,
    unit_get,
)

# from charmhelpers.core.fstab import (
#     Fstab
# )

try:
    from jinja2 import Template
except ImportError:
    apt_install(['python-jinja2'], fatal=True)
    from jinja2 import Template


hooks = hookenv.Hooks()
log = hookenv.log

SERVICE = 'reddit'
REDDIT_USER = 'reddit'
REDDIT_GROUP = 'reddit'
REDDIT_HOME = '/home/reddit'
REDDIT_INSTALL_PATH = '%s/src/reddit/r2' % REDDIT_HOME

REDDIT_DOMAIN = unit_get('public-address')
REDDIT_MEDIA = '/srv'
CONSUMER_CONFIG_ROOT = '%s/consumer-count.d' % REDDIT_HOME
CASSANDRA_KEYSPACE = 'reddit'
CASSANDRA_COLUMN = 'permacache'

# For simplification of string formatting
CONFIG = {
    'REDDIT_HOME': REDDIT_HOME,
    'REDDIT_USER': REDDIT_USER,
    'REDDIT_GROUP': REDDIT_GROUP,
    'REDDIT_DOMAIN': REDDIT_DOMAIN,
    'CONSUMER_CONFIG_ROOT': CONSUMER_CONFIG_ROOT
}

PACKAGES = [
    'python-software-properties',
    'netcat-openbsd',
    'git-core',
    'python-dev',
    'python-setuptools',
    'python-routes',
    'python-pylons',
    'python-tz',
    'python-crypto',
    'python-babel',
    'cython',
    'python-sqlalchemy',
    'python-beautifulsoup',
    'python-chardet',
    'python-psycopg2',
    'python-pycassa',
    'python-imaging',
    'python-pycaptcha',
    'python-amqplib',
    'python-pylibmc',
    'python-bcrypt',
    'python-snudown',
    'python-l2cs',
    'python-lxml',
    'python-zope.interface',
    'python-kazoo',
    'python-stripe',
    'python-tinycss2',
    'python-flask',
    'geoip-bin',
    'geoip-database',
    'python-geoip',
    'gettext',
    'make',
    'optipng',
    'jpegoptim',
    # 'nodejs',
    'node-less',
    'node-uglify',
    # 'memcached',
    # 'postgresql',
    'postgresql-client',
    # 'rabbitmq-server',
    # 'cassandra',
    # 'haproxy',
    # 'nginx',
    # 'stunnel',
    # 'gunicorn',
    # 'sutro',
    'python-pip',
    'python-jinja2',
]

PIP_MODULES = [
    'pycassa',
    'stripe',
    'tinycss2',
    'l2cs',
]


def nfs_is_mounted(mountpoint):
    mounts = host.mounts()
    for local, remote in mounts:
        if remote == mountpoint:
            return True
    return False


@hooks.hook('nfs-relation-changed')
def nfs_changed():
    # $ relation-get
    # fstype: nfs
    # mountpoint: /srv/data/reddit
    # options: rsize=8192,wsize=8192
    # private-address: 10.0.3.172

    # Install NFS dependencies
    apt_install(packages=['rpcbind', 'nfs-common'], fatal=True)

    fstype = hookenv.relation_get('fstype')
    mountpoint = hookenv.relation_get('mountpoint')
    options = hookenv.relation_get('options')
    privaddr = hookenv.relation_get('private-address')

    if options is None or fstype is None:
        return

    if nfs_is_mounted(mountpoint):
        log('NFS mountpoint %s is already mounted' % mountpoint)
        return

    # Create the local mountpoint
    if not os.path.exists(REDDIT_MEDIA):
        host.mkdir(REDDIT_MEDIA, REDDIT_USER, REDDIT_GROUP, 0222)

    # Setup the NFS mount
    log("Mounting NFS at %s" % mountpoint)
    host.mount(
        '%s:%s' % (privaddr, mountpoint), REDDIT_MEDIA, options=options,
        persist=True, filesystem=fstype
    )

    # Make sure Reddit knows where to look for thumbnails,
    # subreddit stylesheets/images, and icons.
    add_to_ini(values={
        'media_provider': 'filesystem',
        'media_fs_root': REDDIT_MEDIA,
        'media_fs_base_url_http': '',
        'media_fs_base_url_https': '',
        'media_domain': 'localhost',
    })
    make_ini()

    pass


@hooks.hook('nfs-relation-broken')
def nfs_broken():

    # TODO: unmount NFS
    pass


@hooks.hook('wsgi-relation-joined')
def gunicorn_joined():
    pass


@hooks.hook('wsgi-relation-changed')
def configure_gunicorn():
    log('Setting gunicorn relation')
    hookenv.relation_set(relation_settings={
        'working_dir': '%s/src/reddit/scripts' % (REDDIT_HOME),
        'wsgi_user': REDDIT_USER,
        'wsgi_group': REDDIT_GROUP,
        'listen_ip': '127.0.0.1',
        'port': 5000,
        'wsgi_worker_connections': 1,
        'wsgi_wsgi_file': 'geoip_service',
    })
    pass


@hooks.hook('website-relation-joined')
def haproxy_joined(relation_id=None):
    hookenv.relation_set(
        hostname=unit_get('private-address'),
        port=8001,
    )

    # HACK: this should be a static domain, like reddit.local,
    # HACK: that points to the haproxy IP. Need to document
    # HACK: usage of this outside of a test environment.

    # Update the ini domain= w/private-address
    add_to_ini(values={
        'domain': unit_get('private-address')
    })
    make_ini()

    pass


@hooks.hook('website-relation-changed')
def haproxy_changed(relation_id=None):
    # relation-get
    # private-address: 10.0.3.144

    # TODO: either randomize or get the hostname to set in the server stanza
    hookenv.relation_set(
        hostname=unit_get('private-address'),
        port=8001,
        services=_get_haproxy_config()
    )
    pass


def _get_haproxy_config():
    host = hookenv.unit_get('private-address')

    # acl is-media path_beg /media/,
    # use_backend media_service if is-media,

    yy = """
- {
    service_name: reddit_service,
    service_host: "0.0.0.0",
    service_port: 80,
    service_options: [
      mode http,
      option httpclose,
      option forwardfor,
      timeout connect 4000,
      timeout server 30000,
      timeout queue 60000,
      balance roundrobin,
      timeout client 24h,
    ],
    servers: [
      [my_web_app_1, %s, 8001, maxconn 1],
    ]
  }
- {
    service_name: media_service,
    service_host: "0.0.0.0",
    service_port: 81,
    service_options: [balance leastconn],
    servers: [
      [my_web_app_2, %s, 9000, maxconn 250],
    ]
  }
""" % (host, host)
    return yy


@hooks.hook('cache-relation-joined')
def memcached_joined():
    # relation-get
    # private-address: 10.0.3.144

    pass


@hooks.hook('cache-relation-changed')
def memcached_changed():
    # # relation-get
    # host: 10.0.3.144
    # port: "11211"
    # private-address: 10.0.3.144
    # udp-port: "0"

    host = hookenv.relation_get('host')
    port = hookenv.relation_get('port')
    if host and port:
        memcached = '%s:%d' % (host, int(port))
        add_to_ini(values={
            'memcaches': memcached,
            'memoizecaches': memcached,
            'lockcaches': memcached,
            'rendercaches': memcached,
            'pagecaches': memcached,
            'permacache_memcaches': memcached,
            'srmembercaches': memcached,
            'ratelimitcaches': memcached,
        })
        make_ini()

    pass


@hooks.hook('cache-relation-broken')
def memcached_broken():
    pass


@hooks.hook('db-relation-joined')
def pgsql_db_joined(relation_id=None):
    log("pgsql_db_joined")

    hookenv.relation_set(relation_settings={"database": "reddit"})


@hooks.hook('db-relation-broken')
def pgsql_db_broken():
    log("pgsql_db_broken")
    # May need to remove installed functions, or
    # re-installs will no longer be owner


@hooks.hook('db-relation-changed')
def pgsql_db_changed():
    log("pgsql_db_changed")

    if hookenv.relation_get('database') is None:
        log("No database info sent yet.")
        return 0

    db_user = hookenv.relation_get('user')
    db_pass = hookenv.relation_get('password')
    db_name = hookenv.relation_get('database')
    db_host = hookenv.relation_get('host')
    db_port = hookenv.relation_get('port')

    log("Database info received -- host: %s; name: %s; user: %s; password: %s"
        % (db_host, db_name, db_user, db_pass))

    # Following the lead of pgbouncer and
    # using environment variables, but security.
    os.environ['PGHOST'] = db_host
    os.environ['PGPORT'] = db_port
    os.environ['PGDATABASE'] = db_name
    os.environ['PGUSER'] = db_user
    os.environ['PGPASSWORD'] = db_pass

    # Right now, this will point ever database to the same postgresql instance
    # TODO: Allow each database to be configured separately via config.yaml

    # main_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # comment_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # comment2_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # vote_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # email_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # authorize_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # award_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # hc_db = reddit,   127.0.0.1, *,    *,    *,    *,    *
    # traffic_db = reddit,   127.0.0.1, *,    *,    *,    *,    *

    add_to_ini(values={
        'db_port': db_port,
        'db_name': db_name,
        'db_user': db_user,
        'db_pass': db_pass,
        'main_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'comment_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'comment2_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'vote_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'email_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'authorize_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'award_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'hc_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
        'traffic_db': '%s, %s, *, *, *, *, *' % (db_name, db_host),
    })
    make_ini()

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
    pass


@hooks.hook('database-relation-broken')
def cassandra_broken():
    pass


@hooks.hook('database-relation-changed')
def cassandra_changed():
    import pycassa

    # relation-get:
    # port: "9160"
    # private-address: 10.0.3.147
    host = hookenv.relation_get('private-address')
    port = hookenv.relation_get('port')
    if host and port:
        casshost = '%s:%d' % (host, int(port))
        log("Connecting to Cassandra host: %s" % casshost)

        sys = pycassa.system_manager.SystemManager(casshost)

        # Create 'reddit' keyspace
        keyspaces = sys.list_keyspaces()
        if CASSANDRA_KEYSPACE not in keyspaces:
            sys.create_keyspace(
                CASSANDRA_KEYSPACE,
                pycassa.system_manager.SIMPLE_STRATEGY,
                {'replication_factor': '1'}
            )
            log("Created '%s' keyspace" % CASSANDRA_KEYSPACE)
        else:
            log("'%s' keyspace already exists." % CASSANDRA_KEYSPACE)

        column_families = sys.get_keyspace_column_families(
            CASSANDRA_KEYSPACE
        ).keys()

        if CASSANDRA_COLUMN not in column_families:
            sys.create_column_family(
                CASSANDRA_KEYSPACE,
                CASSANDRA_COLUMN,
                column_type='Standard',
                default_validation_class=pycassa.BYTES_TYPE
            )
            log("Created '%s' column" % CASSANDRA_COLUMN)
        else:
            log("'%s' column already exists" % CASSANDRA_COLUMN)

        add_to_ini(values={
            'cassandra_seeds': casshost
        })

        make_ini()

    else:
        log("cassandra not ready")

    return


@hooks.hook('amqp-relation-joined')
def rabbitmq_server_joined(relation_id=None):
    hookenv.relation_set(relation_id=relation_id, username='reddit', vhost='/')
    pass


@hooks.hook('amqp-relation-changed')
def rabbitmq_server_changed(relation_id=None):
    host = hookenv.relation_get('private-address')
    password = hookenv.relation_get('password')
    if host is None or password is None:
        log('rabbitmq not ready')
    else:
        log('rabbitmq is ready!')

        add_to_ini(values={
            'amqp_host': host,
            'amqp_user': 'reddit',
            'amqp_pass': password,
            'amqp_virtual_host': '/',
        })

        make_ini()
    pass


@hooks.hook('amqp-relation-broken')
def rabbitmq_server_broken():
    pass


@hooks.hook('install')
def install():
    log('Installing dependencies')

    add_source(config('source'), config('key'))
    apt_update(fatal=True)

    # Add the reddit PPA
    add_source('ppa:reddit/ppa')

    # TODO: is there a better way to do this via charmhelpers?
    template_path = "{0}/templates/etc-apt-preferences.d-reddit.tmpl".format(
        hookenv.charm_dir())

    host.write_file(
        '/etc/apt/preferences.d/reddit',
        Template(open(template_path).read()).render()
    )
    # run(['service', 'rsyslog', 'restart'])

    apt_update(fatal=True)

    apt_install(packages=PACKAGES, fatal=True)

    # Install modules via pip that aren't available via apt-get:
    pip_install(PIP_MODULES)

    log('Creating reddit user/group')
    add_user_group()
    host.mkdir('%s/src' % REDDIT_HOME, REDDIT_USER, REDDIT_GROUP, 0755)

    log('Pulling git repo')
    git_pull()

    log('Installing Reddit repo(s)')

    # TODO: This needs to be run under Precise
    install_reddit_repo('reddit/r2')
    install_reddit_repo('i18n')
    install_reddit_repo('about')
    install_reddit_repo('liveupdate')
    install_reddit_repo('meatspace')

    log("chowning %s" % REDDIT_HOME)
    host.chownr(REDDIT_HOME, REDDIT_USER, REDDIT_GROUP)

    # Generate binary translation files
    log("Generating binary translation files")
    subprocess.call("""
    cd %s/src/i18n
    sudo -u %s make
    """ % (REDDIT_HOME, REDDIT_USER), shell=True)

    log("Building reddit")
    subprocess.call("""
    cd %s/src/reddit/r2
    sudo -u %s make
    """ % (REDDIT_HOME, REDDIT_USER), shell=True)

    log("Creating default ini")

    ini = RawConfigParser()
    ini.optionxform = str  # ensure keys are case-sensitive as expected
    ini.read('%s/juju.update' % REDDIT_INSTALL_PATH)

    defaults = {
        'debug': 'true',
        'disable_ads': 'true',
        'disable_captcha': 'true',
        'disable_ratelimit': 'true',
        'disable_require_admin_otp': 'true',
        'page_cache_time': '0',
        # 'domain': '%s' % REDDIT_DOMAIN,
        'plugins': 'about, liveupdate, meatspace',
        'media_provider': 'filesystem',
        'media_fs_root': '/srv/www/media',
        'media_fs_base_url_http': 'http://%s/media/' % REDDIT_DOMAIN,
        'media_fs_base_url_https': 'https://%s/media/' % REDDIT_DOMAIN,
    }
    for k in defaults.keys():
        ini.set('DEFAULT', k, defaults[k])

    try:
        ini.add_section('server:main')
    except:
        pass

    ini.set('server:main', 'port', '8001')

    with open('%s/juju.update' % REDDIT_INSTALL_PATH, 'w') as cf:
        ini.write(cf)

    make_ini()

    log('Creating helper scripts')
    create_helper_scripts()

    # log("chowning %s" % REDDIT_HOME)
    # cmd = 'chown -R %s:%s %s' % (REDDIT_USER, REDDIT_GROUP, REDDIT_HOME)
    # log(cmd)
    # subprocess.call(shlex.split(cmd))

    log('Configuring job environment')
    configure_job_environment()

    log('Configuring queue processors')
    configure_queue_processors()

    # TODO: Start reddit
    # Start reddit
    # initctl emit reddit-start

    return True


def make_ini():
    log("Building reddit ini")
    subprocess.call(
        """
cd %s
sudo -u %s make ini
""" % (REDDIT_INSTALL_PATH, REDDIT_USER), shell=True)

    if os.path.isfile('%s/run.ini' % REDDIT_INSTALL_PATH) is False:
        cmd = 'sudo -u %s ln -s %s/juju.ini %s/run.ini' % (
            REDDIT_USER,
            REDDIT_INSTALL_PATH,
            REDDIT_INSTALL_PATH
        )
        log('Symlinking ini - %s' % cmd)
        subprocess.call(shlex.split(cmd))
    # Restart reddit
    host.service_restart('reddit-paster')
    return


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

    template_path = "{0}/templates/etc-default-reddit.tmpl".format(
        hookenv.charm_dir())

    host.write_file(
        '/etc/default/reddit',
        Template(open(template_path).read()).render(CONFIG)
    )
    return


def configure_queue_processors():
    if os.path.isdir(CONSUMER_CONFIG_ROOT) is False:
        host.mkdir(CONSUMER_CONFIG_ROOT, REDDIT_USER, REDDIT_GROUP, 0755)

    def set_consumer_count(queue, count):
        queueFile = '%s/%s' % (CONSUMER_CONFIG_ROOT, queue)
        if os.path.isfile(queueFile) is False:
            f = open(queueFile, 'w')
            f.write('%s' % count)
            f.close()

    set_consumer_count('log_q', 0)
    set_consumer_count('cloudsearch_q', 0)
    set_consumer_count('scraper_q', 1)
    set_consumer_count('scraper_q', 1)
    set_consumer_count('commentstree_q', 1)
    set_consumer_count('newcomments_q', 1)
    set_consumer_count('vote_link_q', 1)
    set_consumer_count('vote_comment_q', 1)

    host.chownr(CONSUMER_CONFIG_ROOT, REDDIT_USER, REDDIT_GROUP)

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

    if config.changed('development-mode'):
        if config['development-mode']:
            # Development mode: Engage!
            log('Turning on development mode')
            cmd = """
reddit-run %s/r2/models/populatedb.py -c 'populate()'
""" % REDDIT_INSTALL_PATH

            log(cmd)
            subprocess.call(cmd)
            # cd $REDDIT_HOME/src/reddit/r2
            # reddit-run r2/models/populatedb.py -c 'populate()'

        else:
            log('Turning off development mode')
    else:
        log('Development mode not changed')
    config.save()
    start()


@hooks.hook('upgrade-charm')
def upgrade_charm():
    log('Upgrading reddit')


@hooks.hook('start')
def start():
    # host.service_restart(SERVICE) or host.service_start(SERVICE)
    None


@hooks.hook('stop')
def stop():
    # host.service_stop(SERVICE)
    None


def add_to_ini(section='DEFAULT', values={}):
    ini = RawConfigParser()
    ini.optionxform = str  # ensure keys are case-sensitive as expected
    ini.read('%s/juju.update' % REDDIT_INSTALL_PATH)

    for k in values.keys():
        ini.set(section, k, values[k])

    with open('%s/juju.update' % REDDIT_INSTALL_PATH, 'w') as cf:
        ini.write(cf)


def install_reddit_repo(repo):
    log('Running setup.py in %s/src/%s' % (REDDIT_HOME, repo))

    # TODO: Get this to work with run_as_user
    # cwd = '%s/src/%s' % (REDDIT_HOME, repo)
    # return run_as_user(
    #     REDDIT_USER,
    #     cwd,
    #     'cd %s; python setup.py develop --no-deps' % cwd,
    #     shell=True
    # )

    subprocess.call(
        """
cd %s/src/%s
sudo -u %s python setup.py build
python setup.py develop --no-deps""" % (
            REDDIT_HOME,
            repo,
            REDDIT_USER
        ),
        shell=True
    )
    return


# clone_reddit_repo reddit reddit/reddit
def clone_reddit_repo(target, repo):
    repository_url = 'https://github.com/%s.git' % repo
    destination = '%s/src/%s' % (REDDIT_HOME, target)

    log('Cloning github repo %s to %s' % (repo, destination))

    if os.path.isdir(destination) is False:
        # mkdir
        host.mkdir(destination, REDDIT_USER, REDDIT_GROUP, 0755)

        # TODO: Need to check the status of git clone and make sure
        # TODO: it didn't fail (HTTP timeout/error)
        run_as_user(
            REDDIT_USER,
            REDDIT_HOME,
            ['git', 'clone', repository_url, destination]
        )

        # cmd = ['git', 'clone', repository_url, destination]
        # print cmd
        # subprocess.call(cmd)

        if os.path.isdir('%s/upstart' % destination):
            log('Copying upstart script(s)')
            for file in glob.glob('%s/upstart/*' % destination):
                shutil.copy(file, '/etc/init/')
        # cmd = ['chown', '-R', '%s:%s' %
        # (REDDIT_USER, REDDIT_GROUP), destination]
        # print cmd
        # subprocess.call(cmd)

    else:
        log("Updating reddit repo")

        # Get revno
        run_as_user(
            REDDIT_USER,
            destination,
            ['git', 'pull']
        )

        # chdir
        # git pull
        # cmd = ['sudo', '-u %s' % REDDIT_USER,
        # 'git', 'clone', GIT_URL, srcdir]
        # log(cmd)
        # subprocess.call(cmd_line)
        None


def clone_reddit_plugin_repo(name):
    clone_reddit_repo(name, 'reddit/reddit-plugin-%s' % name)


def git_pull():
    # log('Cloning %s' % GIT_URL)

    clone_reddit_repo('reddit', 'reddit/reddit')
    clone_reddit_repo('i18n', 'reddit/reddit-i18n')
    clone_reddit_plugin_repo('about')
    clone_reddit_plugin_repo('liveupdate')
    clone_reddit_plugin_repo('meatspace')


def add_user_group():
    host.adduser(REDDIT_USER)
    host.add_user_to_group(REDDIT_USER, REDDIT_GROUP)
    host.chownr(REDDIT_HOME, REDDIT_USER, REDDIT_GROUP)


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
        if (package.startswith('svn+') or package.startswith('git+')
           or package.startswith('hg+') or package.startswith('bzr+')):
            cmd_line.append('-e')

        cmd_line.append(package)

    # cmd_line.append('--use-mirrors')
    return(subprocess.call(cmd_line))


def create_helper_scripts():

    template_path = "{0}/templates/reddit-run.tmpl".format(
        hookenv.charm_dir())

    host.write_file(
        '/usr/local/bin/reddit-run',
        Template(open(template_path).read()).render(CONFIG)
    )

    template_path = "{0}/templates/reddit-shell.tmpl".format(
        hookenv.charm_dir())

    host.write_file(
        '/usr/local/bin/reddit-shell',
        Template(open(template_path).read()).render(CONFIG)
    )

    os.chmod('/usr/local/bin/reddit-run', 0755)
    os.chmod('/usr/local/bin/reddit-shell', 0755)

    return


def populate_test_data():
    # cd $REDDIT_HOME/src/reddit/r2
    # reddit-run r2/models/populatedb.py -c 'populate()'
    cmd = [
        'reddit-run',
        '%s/src/reddit/r2/models/populatedb.py' % REDDIT_HOME,
        '-c',
        '\'populate()\''
    ]
    check = subprocess.check_output(cmd)
    # TODO: sanity check the return output
    return


def is_pgsql_db_installed():
    # Check the system catalog for table(s) created during installation
    sql = """
    SELECT count(*)
    FROM information_schema.tables WHERE
    table_schema = 'public';
    """
    cmd = ['psql', '-t', '-c', sql]
    check = subprocess.check_output(cmd)
    return int(check)


def install_pgsql_functions():
    # Install the base database
    log('installing reddit functions')

    # TODO: Fix this. Currently throws a file not found
    # return run_as_user(
    #     REDDIT_USER,
    #     REDDIT_HOME,
    #     'psql -f %s/src/reddit/sql/functions.sql' % REDDIT_HOME
    # )

    # Install reddit's pgsql functions
    # NOTE: These are create or replace, so it
    # should be run every time a git pull happens
    cmd = ['psql', '-f', '%s//src/reddit/sql/functions.sql' % REDDIT_HOME]
    subprocess.check_output(cmd)

    # TODO: sanity check the return output
    # return True


# It'd be nice to have this exposed in charmhelpers. There's one, but
# it's part of unison. It should probably go in cli
def run_as_user(user, cwd, cmd, shell=False):
    # check = subprocess.check_output(cmd)
    pw_record = pwd.getpwnam(user)
    uid = pw_record.pw_uid
    gid = pw_record.pw_gid

    env = os.environ.copy()
    env['HOME'] = pw_record.pw_dir
    env['USER'] = env['LOGNAME'] = user
    # env['PWD'] = cwd

    # cmd = 'cd %s; %s' % (cwd, cmd)
    log("Running '%s' with PWD: %s" % (cmd, cwd))

    # os.environ['PWD'] = cwd
    process = subprocess.Popen(
        cmd,
        preexec_fn=demote(uid, gid),
        cwd=cwd,
        env=env,
        shell=shell,
        # stdout=subprocess.PIPE,
    )
    (output, err) = process.communicate()
    log("command output: %s" % output)
    result = process.wait()
    if(result == 0):
        return True
    else:
        return False


def demote(uid, gid):
    def result():
        os.setgid(gid)
        os.setuid(uid)
    return result


@host.restart_on_change({
    '/etc/': ['adsf']
})
def ini_changed():
    pass


if __name__ == "__main__":
    # execute a hook based on the name the program is called by
    hooks.execute(sys.argv)
