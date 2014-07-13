# Overview

This is the primary codebase that powers http://reddit.com.

# Usage

This charm is available in the Juju Charm Store, to deploy you'll need at a minimum: a cloud environment, a working Juju installation, and a successful bootstrap. Please refer to the [Juju Getting Started](https://juju.ubuntu.com/docs/getting-started.html) documentation before continuing.

Once bootstrapped, deploy the dependency charms, and then the reddit charm:

    juju deploy postgresql
    juju deploy cassandra
    juju deploy rabbitmq-server
    juju deploy memcached
    juju deploy reddit

Add a relation between the two of them

    juju add-relation reddit postgresql
    juju add-relation reddit cassandra
    juju add-relation reddit rabbitmq-server
    juju add-relation reddit memcached

Expose the reddit installation

    juju expose reddit


Step by step instructions on using the charm:

    juju deploy servicename

and so on. If you're providing a web service or something that the end user needs to go to, tell them here, especially if you're deploying a service that might listen to a non-default port. 

You can then browse to http://ip-address to configure the service. 

## Scale out Usage

If the charm has any recommendations for running at scale, outline them in examples here. For example if you have a memcached relation that improves performance, mention it here. 

## Known Limitations and Issues

This not only helps users but gives people a place to start if they want to help you add features to your charm. 

# Configuration

The configuration options will be listed on the charm store, however If you're making assumptions or opinionated decisions in the charm (like setting a default administrator password), you should detail that here so the user knows how to change it immediately, etc.

# Contact Information

Though this will be listed in the charm store itself don't assume a user will know that, so include that information here:

## Reddit

- [Github]https://github.com/reddit/reddit
- Feel free to add things if it's useful for users
