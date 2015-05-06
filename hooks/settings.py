"""
Static settings
"""
from charmhelpers.core.hookenv import unit_get

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
    'python-unidecode',
    'python-mock',
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
    'haproxy',
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
    'CONSUMER_CONFIG_ROOT': CONSUMER_CONFIG_ROOT,
    'REDDIT_INSTALL_PATH': REDDIT_INSTALL_PATH,
    'CASSANDRA_KEYSPACE': CASSANDRA_KEYSPACE,
    'CASSANDRA_COLUMN': CASSANDRA_COLUMN
}
