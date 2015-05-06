#!/usr/bin/python
import sys
import os
sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

from charmhelpers.core.services import helpers

from charmhelpers.core import hookenv

REDDIT_USER = 'reddit'
REDDIT_GROUP = 'reddit'
REDDIT_HOME = '/home/reddit'


class NFSRelation(helpers.RelationContext):
    """
    Relation context for the `cassandra` interface.

    :param str name: Override the relation :attr:`name`, since it can vary from charm to charm
    :param list additional_required_keys: Extend the list of :attr:`required_keys`
    """
    name = 'nfs'
    interface = 'mount'

    def __init__(self, *args, **kwargs):
        self.required_keys = ['private-address', 'port']
        super(NFSRelation, self).__init__(*args, **kwargs)


class GunicornRelation(helpers.RelationContext):
    """
    Relation context for the `wsgi` interface.

    :param str name: Override the relation :attr:`name`, since it can vary from charm to charm
    :param list additional_required_keys: Extend the list of :attr:`required_keys`
    """
    name = 'wsgi'
    interface = 'wsgi'
    data = {}

    def __init__(self, *args, **kwargs):
        self.required_keys = ['private-address']

        for key, value in kwargs.iteritems():
            self.data[key] = value

        super(GunicornRelation, self).__init__(*args, **kwargs)

    def provide_data(self):
        hookenv.log('returning data for gunicorn')
        return {
            'working_dir': '%s/src/reddit/scripts' % (REDDIT_HOME),
            'wsgi_user': REDDIT_USER,
            'wsgi_group': REDDIT_GROUP,
            'listen_ip': '127.0.0.1',
            'port': 5000,
            'wsgi_worker_connections': 1,
            'wsgi_wsgi_file': 'geoip_service',
        }


class MemcachedRelation(helpers.RelationContext):
    """
    Relation context for the `cassandra` interface.

    :param str name: Override the relation :attr:`name`, since it can vary from charm to charm
    :param list additional_required_keys: Extend the list of :attr:`required_keys`
    """
    name = 'cache'
    interface = 'cache'

    def __init__(self, *args, **kwargs):
        self.required_keys = ['host', 'port']
        super(MemcachedRelation, self).__init__(*args, **kwargs)


class RabbitMQRelation(helpers.RelationContext):
    """
    Relation context for the `cassandra` interface.

    :param str name: Override the relation :attr:`name`, since it can vary from charm to charm
    :param list additional_required_keys: Extend the list of :attr:`required_keys`
    """
    name = 'amqp'
    interface = 'rabbitmq'

    vhost = None
    username = None
    required_keys = []

    def __init__(self, username=None, vhost=None):
        """
        This works around a bug with the RelationContext class that expects
        the required keys to be set before it will call provide_data.
        """
        if username and vhost:
            self.username = username
            self.vhost = vhost
        else:
            self.required_keys = ['private-address', 'hostname', 'password']

        super(RabbitMQRelation, self).__init__(self.name)

    # def is_ready(self):
    #     ready = super(RabbitMQRelation, self).is_ready()
    #     if self.username and self.vhost:
    #         ready = True
    #     return ready
    #
    # def _is_ready(self, unit_data):
    #     ready = super(RabbitMQRelation, self)._is_ready(unit_data)
    #     if self.username and self.vhost:
    #         ready = True
    #     return ready

    def provide_data(self):
        """
        Return data to be relation_set for this interface.
        """
        return {
            'username': self.username,
            'vhost': self.vhost
        }


class PostgresqlRelation(helpers.RelationContext):
    """
    Relation context for the `cassandra` interface.

    :param str name: Override the relation :attr:`name`, since it can vary from charm to charm
    :param list additional_required_keys: Extend the list of :attr:`required_keys`
    """
    name = 'db'
    interface = 'pgsql'

    def __init__(self, *args, **kwargs):
        self.required_keys = [
            'database',
            'host',
            'schema_user',
            'schema_password',
            'state',
            'user',
            'password',
            'port'
        ]
        super(PostgresqlRelation, self).__init__(*args, **kwargs)


class CassandraRelation(helpers.RelationContext):
    """
    Relation context for the `cassandra` interface.

    :param str name: Override the relation :attr:`name`, since it can vary from charm to charm
    :param list additional_required_keys: Extend the list of :attr:`required_keys`
    """
    name = 'database'
    interface = 'cassandra'

    def __init__(self, *args, **kwargs):
        self.required_keys = ['private-address', 'port']
        super(CassandraRelation, self).__init__(*args, **kwargs)


class HttpRelation(helpers.HttpRelation):
    """
    Override HttpRelation to fix the required keys, and return the port
    provided by the relation, rather than the hard-coded port 80
    """
    required_keys = ['hostname', 'port']

    def provide_data(self):
        return {
            'host': hookenv.unit_get('hostname'),
            'port': hookenv.unit_get('port'),
        }
