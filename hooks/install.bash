#!/bin/bash

set -e # If any command fails, stop execution of the hook with that error

# Here do anything needed to install the service
# i.e. apt-get install -y foo  or  bzr branch http://myserver/mycode /srv/webroot
# Make sure this hook exits cleanly and is idempotent, common problems here are
# failing to account for a debconf question on a dependency, or trying to pull
# from github without installing git first.

# apt-get install -y reddit

# Is it cool to run an upgrade?
apt-get update && apt-get -y upgrade

apt-get -y install python-software-properties charm-helper-sh

cat <<PACKAGES | xargs apt-get install -y
netcat-openbsd
git-core

python-dev
python-setuptools
python-routes
python-pylons
python-boto
python-tz
python-crypto
python-babel
cython
python-sqlalchemy
python-beautifulsoup
python-chardet
python-psycopg2
python-pycassa
python-imaging
python-pycaptcha
python-amqplib
python-pylibmc
python-bcrypt
python-snudown
python-l2cs
python-lxml
python-zope.interface
python-kazoo
python-stripe
python-tinycss2

python-flask
geoip-bin
geoip-database
python-geoip

nodejs
node-less
node-uglify
gettext
make
optipng
jpegoptim

PACKAGES
#
# E: Unable to locate package python-pycassa
# E: Unable to locate package python-pycaptcha
# E: Unable to locate package python-snudown
# E: Unable to locate package python-l2cs
# E: Unable to locate package python-stripe
# E: Unable to locate package python-tinycss2

# juju-log "Making /mnt/tmp dir ..."
# mkdir -p /mnt/tmp
# chmod 1777 /mnt/tmp
#
# juju-log "Making /mnt/logs ..."
# mkdir -p /mnt/logs/php-fpm
# chmod -R 1777 /mnt/logs

## dont make this an actual ramdisk until later when size can be safely tested
## just using plain disk cache for now
# juju-log "Making Ramdisk mount point and config ..."
# mkdir -p /mnt/ramdisk/proxy-cache
# mkdir -p /mnt/ramdisk/phpfpm-cache
# chmod -R 1777 /mnt/ramdisk

#juju-log "Installing PHP-FPM pool configs ..."
# rm -f /etc/php5/fpm/pool.d/*
# install -o root -g root -m 0644 files/charm/php/php5-fpm_pool.d_www.conf /etc/php5/fpm/pool.d/www.conf
# rsync -az /var/lib/php5 /mnt/ && rm -rf /var/lib/php5 && ln -s /mnt/php5 /var/lib/

#./hooks/install: line 80: juju-log: command not found
juju-log "Installing reddit ..."
git clone https://github.com/reddit/reddit.git /usr/src/reddit


