#
# Copyright 2012 Canonical Ltd.
#
# This file is sourced from lp:openstack-charm-helpers
#
# Authors:
#  James Page <james.page@ubuntu.com>
#  Paul Collins <paul.collins@canonical.com>
#  Adam Gandelman <adamg@ubuntu.com>
#

import grp
import os
import pwd

from charmhelpers.fetch import (
    apt_install
)
from charmhelpers.core.hookenv import (
    local_unit,
    remote_unit,
    log
)
TEMPLATES_DIR = 'templates'

try:
    import jinja2
except ImportError:
    apt_install('python-jinja2', fatal=True)
    import jinja2


def render_template(template_name, context, template_dir=TEMPLATES_DIR):
    templates = \
        jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)


def is_newer():
    l_unit_no = local_unit().split('/')[1]
    r_unit_no = remote_unit().split('/')[1]
    return (l_unit_no > r_unit_no)


def chown(path, owner='root', group='root', recursive=False):
    """Changes owner of given path, recursively if needed"""
    if os.path.exists(path):
        log('Changing ownership of path %s to %s:%s' %
            (path, owner, group))
        uid = pwd.getpwnam(owner).pw_uid
        gid = grp.getgrnam(group).gr_gid

        if recursive:
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    os.chown(os.path.join(root, d), uid, gid)
                for f in files:
                    os.chown(os.path.join(root, f), uid, gid)
        else:
            os.chown(path, uid, gid)
    else:
        log('%s path does not exist' % path)


def chmod(path, perms, recursive=False):
    """Changes perms of given path, recursively if needed"""
    if os.path.exists(path):
        log('Changing perms of path %s ' % path)

        if recursive:
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    os.chmod(os.path.join(root, d), perms)
                for f in files:
                    os.chmod(os.path.join(root, f), perms)
        else:
            os.chmod(path, perms)
    else:
        log('ERROR', '%s path does not exist' % path)
