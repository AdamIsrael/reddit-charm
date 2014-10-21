# Overview

This reddit charm provides the means to get a working, scalable version of [reddit](https://github.com/reddit/reddit).

# Usage

In order to deploy this charm, you will need a working juju installation. Once bootstrapped, issue these commands:

    juju deploy cs:precise/cassandra
    juju deploy postgresql
    juju deploy rabbitmq-server
    juju deploy memcached
    juju deploy cs:precise/gunicorn
    juju deploy cs:precise/haproxy
    juju deploy cs:precise/nfs
    juju deploy reddit

    # Enable single machine mode for cassandra, if not running a cluster
    juju add-relation reddit:database cassandra:database
    juju add-relation reddit:db postgresql:db
    juju add-relation reddit rabbitmq-server
    juju add-relation reddit memcached
    juju add-relation reddit nfs
    juju add-relation reddit gunicorn

    # Reddit and haproxy, oh my.
    Need to make the charm work simply by IP address of the haproxy node.
    Need to test with multiple haproxy services
    Need to talk about setting the domain, i.e., reddit.local, reddit-is-cool.com, etc.


    juju set haproxy services=" "
    juju add-relation reddit:website haproxy:reverseproxy


    juju expose reddit

After a successful deployment, you can get the reddit unit IP address with:

    juju status reddit

and then browse to http://ip-address/path to configure the service.

The source files are installed to /home/reddit/src/reddit, in the unit machine's file system.

Admin interface
How to add a reddit

# Configuration

The configuration options will be listed on the charm store, however If you're making assumptions or opinionated decisions in the charm (like setting a default administrator password), you should detail that here so the user knows how to change it immediately, etc.

    juju set reddit [option]=[value]
    juju set reddit domain=foobar.com
    juju set reddit user=myname (return password?)
    juju set reddit s3keyid=
    juju set reddit s3secretkey=
    juju set reddit s3buckets=


    juju set haproxy default_timeouts="maxconn 350"

# Caveats
Shared media -- NFS (rsync on join, remove local files on break?) or S3
NFS -- create the mount on the first deployed unit, mount it elsewhere.
First user created is the/an admin user
Sutro - websockets not implemented yet

http://ip-address//subreddits/create

##Cassandra

If you're only going to run one Cassandra node:

    juju set cassandra allow-single-node=true

##NFS - if using the local provider

    apt-get install nfs-common
    modprobe nfsd
    mount -t nfsd nfsd /proc/fs/nfsd

Edit /etc/apparmor.d/lxc/lxc-default to add the following three lines to it:

     mount fstype=nfs,
     mount fstype=nfsd,
     mount fstype=nfs4,
     mount fstype=rpc_pipefs,

after which:

     sudo /etc/init.d/apparmor restart

# TODO

Add interface for monitoring (like nagios)
Time how long it takes to go from a fresh system to a fully running stack.

# Scaling

# Contact Information

Charm maintainer: Adam Israel

## Upstream Project Name

- Upstream website(https://github.com/reddit/reddit)
- Upstream bug tracker
- Upstream mailing list or contact information
