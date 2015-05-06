#!/usr/bin/python
import sys
import os
sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

import subprocess
from relations import(
    CassandraRelation,
    GunicornRelation,
    PostgresqlRelation,
    MemcachedRelation,
    RabbitMQRelation
)

from charmhelpers.core.services import helpers
from charmhelpers.core import (
    hookenv,
    # host
)

from charmhelpers.fetch import (
    add_source,
    apt_update,
    apt_install,
)

from settings import (
    PACKAGES,
    PIP_MODULES,
    CONFIG
)

from helpers import (
    install_dependencies,
    create_user,
    install_reddit_source,
    build_reddit,
    add_to_ini,
    make_ini,
    configure_job_environment,
    configure_queue_processors
)


def install(service_name):
    hookenv.log('Install called for %s' % service_name)

    install_dependencies()

    create_user()

    install_reddit_source()

    build_reddit()

    hookenv.log('Configuring job environment')
    configure_job_environment()


def init_database(service_name):
    config = hookenv.config()
    # if config.previous('db_initialized'):
    #     return

    hookenv.log('Initializing database')
    postgresql = PostgresqlRelation()['db'][0]

    import json
    hookenv.log(json.dumps(postgresql))

    add_to_ini(values={
        'db_port': postgresql['port'],
        'db_name': postgresql['database'],
        'db_user': postgresql['user'],
        'db_pass': postgresql['password'],
        'main_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'comment_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'comment2_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'vote_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'email_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'authorize_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'award_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'hc_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
        'traffic_db': '%s, %s, *, *, *, *, *' % (postgresql['database'], postgresql['host']),
    })

    # Following the lead of pgbouncer and
    # using environment variables, but security.
    os.environ['PGHOST'] = postgresql['host']
    os.environ['PGPORT'] = postgresql['port']
    os.environ['PGDATABASE'] = postgresql['database']
    os.environ['PGUSER'] = postgresql['user']
    os.environ['PGPASSWORD'] = postgresql['password']

    cmd = [
        'psql',
        '-f',
        '%s//src/reddit/sql/functions.sql' % CONFIG['REDDIT_HOME']
    ]
    subprocess.check_output(cmd)

    config['db_initialized'] = True
    config.save()


def init_cassandra(service_name):
    hookenv.log('Initializing cassandra')
    cassandra = CassandraRelation()['database'][0]

    import pycassa

    casshost = '%s:%s' % (cassandra['private-address'], cassandra['port'])
    hookenv.log("Connecting to Cassandra host: %s" % casshost)

    sm = pycassa.system_manager.SystemManager(casshost)

    # Create 'reddit' keyspace
    keyspaces = sm.list_keyspaces()
    if CONFIG['CASSANDRA_KEYSPACE'] not in keyspaces:
        sm.create_keyspace(
            CONFIG['CASSANDRA_KEYSPACE'],
            pycassa.system_manager.SIMPLE_STRATEGY,
            {'replication_factor': '1'}
        )
        hookenv.log("Created '%s' keyspace" % CONFIG['CASSANDRA_KEYSPACE'])
    else:
        hookenv.log("'%s' keyspace already exists." % CONFIG['CASSANDRA_KEYSPACE'])

    column_families = sm.get_keyspace_column_families(
        CONFIG['CASSANDRA_KEYSPACE']
    ).keys()

    if CONFIG['CASSANDRA_COLUMN'] not in column_families:
        sm.create_column_family(
            CONFIG['CASSANDRA_KEYSPACE'],
            CONFIG['CASSANDRA_COLUMN'],
            column_type='Standard',
            default_validation_class=pycassa.BYTES_TYPE
        )
        hookenv.log("Created '%s' column" % CONFIG['CASSANDRA_COLUMN'])
    else:
        hookenv.log("'%s' column already exists" % CONFIG['CASSANDRA_COLUMN'])

    add_to_ini(values={
        'cassandra_seeds': casshost
    })

    hookenv.log('Configuring queue processors')
    configure_queue_processors()


def init_rabbitmq(service_name):
    hookenv.log('Initializing rabbitmq')
    rabbitmq = RabbitMQRelation()['amqp'][0]
    add_to_ini(values={
        'amqp_host': rabbitmq['private-address'],
        'amqp_user': 'reddit',
        'amqp_pass': rabbitmq['password'],
        'amqp_virtual_host': '/',
    })


def init_gunicorn(service_name):
    hookenv.log('Initializing gunicorn')
    # gunicorn = GunicornRelation()['wsgi'][0]


def init_memcached(service_name):
    hookenv.log('Initializing memcached')
    memcached = MemcachedRelation()['cache'][0]

    mserver = '%s:%s' % (memcached['host'], memcached['port'])
    add_to_ini(values={
        'memcaches': mserver,
        'memoizecaches': mserver,
        'lockcaches': mserver,
        'rendercaches': mserver,
        'pagecaches': mserver,
        'permacache_memcaches': mserver,
        'srmembercaches': mserver,
        'ratelimitcaches': mserver,
    })


def configure(service_name):
    make_ini()
