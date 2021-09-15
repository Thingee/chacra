import os
from celery import shared_task
from chacra import models
from chacra.asynch import base, post_ready, post_building
from chacra import util
from chacra.metrics import Counter, Timer
import logging
import subprocess

logger = logging.getLogger(__name__)


@shared_task(base=base.SQLATask)
def create_rpm_repo(repo_id):
    """
    Go create or update repositories with specific IDs.
    """
    directories = ['SRPMS', 'noarch', 'x86_64', 'aarch64']
    # get the root path for storing repos
    # TODO: Is it possible we can get an ID that doesn't exist anymore?
    repo = models.Repo.get(repo_id)
    post_building(repo)
    timer = Timer(__name__, suffix="create.rpm.%s" % repo.metric_name)
    counter = Counter(__name__, suffix="create.rpm.%s" % repo.metric_name)
    timer.start()
    logger.info("processing repository: %s", repo)
    if util.repository_is_disabled(repo.project.name):
        logger.info("will not process repository: %s", repo)
        repo.needs_update = False
        repo.is_queued = False
        return

    # Determine paths for this repository
    paths = util.repo_paths(repo)
    repo_dirs = [os.path.join(paths['absolute'], d) for d in directories]

    # Before doing work that might take very long to complete, set the repo
    # path in the object and mark needs_update as False
    repo.path = paths['absolute']
    repo.is_updating = True
    repo.is_queued = False
    repo.needs_update = False
    models.commit()

    # this is safe to do, behind the scenes it is just trying to create them if
    # they don't exist and it will include the 'absolute' path
    for d in repo_dirs:
        util.makedirs(d)

    # now that structure is done, we need to symlink the RPMs that belong
    # to this repo so that we can create the metadata.
    conf_extra_repos = util.get_extra_repos(repo.project.name, repo.ref)
    extra_binaries = []
    for project_name, project_refs in conf_extra_repos.items():
        for ref in project_refs:
            extra_binaries += util.get_extra_binaries(
                project_name,
                repo.distro,
                repo.distro_version,
                ref=ref if ref != 'all' else None
            )

    all_binaries = extra_binaries + [b for b in repo.binaries]
    timer.intermediate('collection')
    for binary in all_binaries:
        source = binary.path
        arch_directory = util.infer_arch_directory(binary.name)
        destination_dir = os.path.join(paths['absolute'], arch_directory)
        destination = os.path.join(destination_dir, binary.name)
        try:
            if not os.path.exists(destination):
                os.symlink(source, destination)
        except OSError:
            logger.exception('could not symlink')

    _createrepo(paths['absolute'], repo_dirs, repo.distro)

    logger.info("finished processing repository: %s", repo)
    repo.is_updating = False
    models.commit()
    timer.stop()
    counter += 1
    post_ready(repo)


def _createrepo(base_path, repo_dirs, distro):
    if distro.lower() in ['opensuse', 'sle']:
        # openSUSE/sles zypper expects the repodata on the top level dir
        subprocess.check_call(['createrepo', '--no-database', base_path])
    else:
        for d in repo_dirs:
            # this prevents RPM packages that are larger than 2GB (!!!) from
            # causing the database to fail to store the size and subsequently make
            # the package uninstallable. Ideally, this types of flag options should
            # be configurable
            subprocess.check_call(['createrepo', '--no-database', d])
