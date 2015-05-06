import sys
import os
import os.path
sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

import subprocess
import pwd
import shlex
import shutil
import glob
from ConfigParser import RawConfigParser

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
    # relation_set,
    # relation_get,
    # relation_ids,
    unit_get,
)

hooks = hookenv.Hooks()
log = hookenv.log

from settings import (
    PACKAGES,
    PIP_MODULES,
    CONFIG
)

try:
    from jinja2 import Template
except ImportError:
    apt_install(['python-jinja2'], fatal=True)
    from jinja2 import Template


def install_dependencies():
    # Add the reddit PPA
    add_source('ppa:reddit/ppa')

    apt_update(fatal=True)

    template_path = "{0}/templates/etc/apt/preferences.d/reddit.tmpl".format(
        hookenv.charm_dir())

    host.write_file(
        '/etc/apt/preferences.d/reddit',
        Template(open(template_path).read()).render()
    )

    apt_install(packages=PACKAGES, fatal=True)

    # Install modules via pip that aren't available via apt-get:
    pip_install(PIP_MODULES)


def add_to_ini(section='DEFAULT', values={}):
    ini = RawConfigParser()
    ini.optionxform = str  # ensure keys are case-sensitive as expected
    ini.read('%s/juju.update' % CONFIG['REDDIT_INSTALL_PATH'])

    for k in values.keys():
        ini.set(section, k, values[k])

    with open('%s/juju.update' % CONFIG['REDDIT_INSTALL_PATH'], 'w') as cf:
        ini.write(cf)


def make_ini():
    log("Building reddit ini")
    subprocess.call(
        """
cd %s
sudo -u %s make ini
""" % (CONFIG['REDDIT_INSTALL_PATH'], CONFIG['REDDIT_USER']), shell=True)

    if os.path.isfile('%s/run.ini' % CONFIG['REDDIT_INSTALL_PATH']) is False:
        cmd = 'sudo -u %s ln -s %s/juju.ini %s/run.ini' % (
            CONFIG['REDDIT_USER'],
            CONFIG['REDDIT_INSTALL_PATH'],
            CONFIG['REDDIT_INSTALL_PATH']
        )
        log('Symlinking ini - %s' % cmd)
        subprocess.call(shlex.split(cmd))
    # Restart reddit
    host.service_restart('reddit-paster')
    return


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


def install_reddit_repo(repo):
    log('Running setup.py in %s/src/%s' % (CONFIG['REDDIT_HOME'], repo))

    subprocess.call(
        """
cd %s/src/%s
sudo -u %s python setup.py build
python setup.py develop --no-deps""" % (
            CONFIG['REDDIT_HOME'],
            repo,
            CONFIG['REDDIT_USER']
        ),
        shell=True
    )
    return


def clone_reddit_repo(target, repo):
    repository_url = 'https://github.com/%s.git' % repo
    destination = '%s/src/%s' % (CONFIG['REDDIT_HOME'], target)

    log('Cloning github repo %s to %s' % (repo, destination))

    if os.path.isdir(destination) is False:
        host.mkdir(
            destination,
            CONFIG['REDDIT_USER'],
            CONFIG['REDDIT_GROUP'],
            0755
        )

        # TODO: Need to check the status of git clone and make sure
        # TODO: it didn't fail (HTTP timeout/error)
        run_as_user(
            CONFIG['REDDIT_USER'],
            CONFIG['REDDIT_HOME'],
            ['git', 'clone', repository_url, destination]
        )

        if os.path.isdir('%s/upstart' % destination):
            log('Copying upstart script(s)')
            for f in glob.glob('%s/upstart/*' % destination):
                shutil.copy(f, '/etc/init/')

    else:
        log("Updating reddit repo")

        # Get revno
        run_as_user(
            CONFIG['REDDIT_USER'],
            destination,
            ['git', 'pull']
        )


def clone_reddit_plugin_repo(name):
    clone_reddit_repo(name, 'reddit/reddit-plugin-%s' % name)


def git_pull():
    clone_reddit_repo('reddit', 'reddit/reddit')
    clone_reddit_repo('i18n', 'reddit/reddit-i18n')
    clone_reddit_plugin_repo('about')
    clone_reddit_plugin_repo('liveupdate')
    clone_reddit_plugin_repo('meatspace')


def add_user_group():
    host.adduser(CONFIG['REDDIT_USER'])
    host.add_user_to_group(CONFIG['REDDIT_USER'], CONFIG['REDDIT_GROUP'])
    host.chownr(
        CONFIG['REDDIT_HOME'],
        CONFIG['REDDIT_USER'],
        CONFIG['REDDIT_GROUP']
    )


def create_user():
    """
    Create the reddit user/group and the home directory
    """
    log('Creating reddit user/group')
    add_user_group()


def install_reddit_source():
    host.mkdir(
        '%s/src' % CONFIG['REDDIT_HOME'],
        CONFIG['REDDIT_USER'],
        CONFIG['REDDIT_GROUP'],
        0755
    )
    log('Pulling git repo')
    git_pull()

    log('Installing Reddit repo(s)')

    install_reddit_repo('reddit/r2')
    install_reddit_repo('i18n')
    install_reddit_repo('about')
    install_reddit_repo('liveupdate')
    install_reddit_repo('meatspace')

    log("chowning %s" % CONFIG['REDDIT_HOME'])
    host.chownr(
        CONFIG['REDDIT_HOME'],
        CONFIG['REDDIT_USER'],
        CONFIG['REDDIT_GROUP']
    )


def build_reddit():
    # Generate binary translation files
    log("Generating binary translation files")
    subprocess.call("""
    cd %s/src/i18n
    sudo -u %s make
    """ % (CONFIG['REDDIT_HOME'], CONFIG['REDDIT_USER']), shell=True)

    log("Building reddit")
    subprocess.call("""
    cd %s/src/reddit/r2
    sudo -u %s make
    """ % (CONFIG['REDDIT_HOME'], CONFIG['REDDIT_USER']), shell=True)

    log("Creating default ini")

    ini = RawConfigParser()
    ini.optionxform = str  # ensure keys are case-sensitive as expected
    ini.read('%s/juju.update' % CONFIG['REDDIT_INSTALL_PATH'])

    defaults = {
        'debug': 'true',
        'disable_ads': 'true',
        'disable_captcha': 'true',
        'disable_ratelimit': 'true',
        'disable_require_admin_otp': 'true',
        'page_cache_time': '0',
        'domain': '%s' % CONFIG['REDDIT_DOMAIN'],
        'plugins': 'about, liveupdate, meatspace',
        'media_provider': 'filesystem',
        'media_fs_root': '/srv/www/media',
        'media_fs_base_url_http': 'http://%s/media/' % CONFIG['REDDIT_DOMAIN'],
        'media_fs_base_url_https': 'https://%s/media/' % CONFIG['REDDIT_DOMAIN'],
    }
    for k in defaults.keys():
        ini.set('DEFAULT', k, defaults[k])

    try:
        ini.add_section('server:main')
    except:
        pass

    ini.set('server:main', 'port', '8001')
    # open_port(8001)

    with open('%s/juju.update' % CONFIG['REDDIT_INSTALL_PATH'], 'w') as cf:
        ini.write(cf)

    make_ini()

    log('Creating helper scripts')
    create_helper_scripts()


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


def configure_job_environment():

    template_path = "{0}/templates/etc/default/reddit.tmpl".format(
        hookenv.charm_dir())

    host.write_file(
        '/etc/default/reddit',
        Template(open(template_path).read()).render(CONFIG)
    )
    return


def configure_queue_processors():
    if os.path.isdir(CONFIG['CONSUMER_CONFIG_ROOT']) is False:
        host.mkdir(
            CONFIG['CONSUMER_CONFIG_ROOT'],
            CONFIG['REDDIT_USER'],
            CONFIG['REDDIT_GROUP'],
            0755
        )

    def set_consumer_count(queue, count):
        queueFile = '%s/%s' % (CONFIG['CONSUMER_CONFIG_ROOT'], queue)
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

    host.chownr(
        CONFIG['CONSUMER_CONFIG_ROOT'],
        CONFIG['REDDIT_USER'],
        CONFIG['REDDIT_GROUP']
    )

    return
