# Overview

This reddit charm provides the means to get a working version of [reddit](https://github.com/reddit/reddit).

Also remember to check the [icon guidelines](https://juju.ubuntu.com/docs/authors-charm-icon.html) so that your charm looks good in the Juju GUI.

# Usage

In order to deploy this charm, you will need a working juju installation. Once bootstrapped, issue these commands:

    juju deploy cassandra
    juju deploy postgresql
    juju deploy rabbitmq-server
    juju deploy memcached
    juju deploy reddit
    juju add-relation reddit:database cassandra:database
    juju add-relation reddit:db postgresql:db
    juju add-relation reddit rabbitmq-server
    juju add-relation reddit memcached    
    juju deploy gunicorn
    juju add-relation reddit gunicorn    
    juju expose reddit

After a successful deployment, you can get the reddit unit IP address with:

    juju status reddit

and then browse to http://ip-address to configure the service. The source files are installed to /home/reddit/src/reddit, in the unit machine's file system.

# Configuration

The configuration options will be listed on the charm store, however If you're making assumptions or opinionated decisions in the charm (like setting a default administrator password), you should detail that here so the user knows how to change it immediately, etc.

# Contact Information

Charm maintainer: Adam Israel

## Upstream Project Name

- Upstream website(https://github.com/reddit/reddit)
- Upstream bug tracker
- Upstream mailing list or contact information
