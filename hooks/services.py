#!/usr/bin/python
import sys
import os
sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

from charmhelpers.core.services.base import ServiceManager

import reddit
from relations import(
    CassandraRelation,
    GunicornRelation,
    PostgresqlRelation,
    MemcachedRelation,
    RabbitMQRelation
)


def manage():
    manager = ServiceManager([
        {
            'service': 'reddit',
            'ports': [80, 8001],  # ports to after start
            'provided_data': [
                GunicornRelation(),
                RabbitMQRelation(username='reddit', vhost='/')
            ],
            'required_data': [
                # helpers.RequiredConfig('domain'),
                # HttpRelation(),
                CassandraRelation(),
                MemcachedRelation(),
                PostgresqlRelation(),
                GunicornRelation(),
                RabbitMQRelation(),
            ],
            'data_ready': [
                # helpers.render_template(
                #     source='siegerc',
                #     target='%s/.siegerc' % hookenv.charm_dir()),
                reddit.install,
                reddit.init_database,
                reddit.init_cassandra,
                reddit.init_memcached,
                reddit.init_rabbitmq,
                reddit.init_gunicorn,
                reddit.configure
            ],
            'data_lost': [
            ],
        },
    ])
    manager.manage()
