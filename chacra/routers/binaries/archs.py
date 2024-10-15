import logging
import os

from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from chacra.models import Binary, Project
from chacra import models, util
from chacra.routers import error
from chacra.routers.util import repository_is_automatic
from chacra.routers.binaries import BinaryController
from chacra.routers.binaries import flavors as _flavors
from chacra.auth import basic_auth


logger = logging.getLogger(__name__)


class Arch(BaseModel):
        arch: str
        project_id: int
        distro: str
        distro_version: str
        ref: str
        sha1: str


app = FastAPI()

router = APIRouter(
        prefix='/binaries/archs',
        responses={405: {'description': 'Method not allowed'}}
)

@router.post('/')
def index():
    return HTMLResponse(status_code=405)

@router.head('/')
def index_head(arch: Arch):
    binaries = arch.project.binaries.filter_by(
        distro=arch.distro,
        distro_version=arch.distro_version,
        ref=arch.ref,
        sha1=arch.sha1,
        arch=arch.arch).all()

    if not binaries:
        return HTMLResponse(status_code=404)
    return dict()

@router.get('/')
def index_get(arch: Arch):
    binaries = arch.project.binaries.filter_by(
        distro=arch.distro,
        distro_version=arch.distro_version,
        ref=arch.ref,
        sha1=arch.sha1,
        arch=arch.arch).all()

    if not binaries:
        return HTMLResponse(status_code=404)

    resp = {}
    for b in arch.project.binaries.filter_by(
            distro=arch.distro,
            distro_version=arch.distro_version,
            ref=arch.ref,
            sha1=arch.sha1,
            arch=arch.arch).all():
        resp[b.name] = b
    return resp

def get_binary(arch, name):
    return Binary.filter_by(
        name=name, project=arch.project, arch=self.arch,
        distro=arch.distro, distro_version=self.distro_version,
        ref=arch.ref, sha1=self.sha1
    ).first()

@router.post('/')
def index_post(arch: Arch):
    contents = request.POST.get('file', False)
    if contents is False:
        error('/errors/invalid/', 'no file object found in "file" param in POST request')
    file_obj = contents.file
    filename = contents.filename
    arch.binary = self.get_binary(filename)
    arch.binary_name = filename
    if arch.binary is not None:
        if os.path.exists(arch.binary.path):
            if request.POST.get('force', False) is False:
                error('/errors/invalid', 'resource already exists and "force" key was not used')

    full_path = arch.save_file(file_obj)

    if arch.binary is None:
        path = full_path
        distro = request.context['distro']
        distro_version = request.context['distro_version']
        arch = request.context['arch']
        ref = request.context['ref']
        sha1 = request.context['sha1']

        arch.binary = Binary(
            arch.binary_name, self.project, arch=arch,
            distro=distro, distro_version=distro_version,
            ref=ref, sha1=sha1, path=path, size=os.path.getsize(path)
        )
    else:
        arch.binary.path = full_path

    # check if this binary is interesting for other configured projects,
    # and if so, then mark those other repos so that they can be re-built
    arch.mark_related_repos()
    return dict()

def mark_related_repos(arch):
    related_projects = util.get_related_projects(arch.project.name)
    repos = []
    projects = []
    for project_name, refs in related_projects.items():
        p = models.projects.get_or_create(name=project_name)
        projects.append(p)
        repo_query = []
        if refs == ['all']:
            # we need all the repos available
            repo_query = models.Repo.filter_by(project=p).all()
        else:
            for ref in refs:
                repo_query = models.Repo.filter_by(project=p, ref=ref).all()
        if repo_query:
            for r in repo_query:
                repos.append(r)

    if not repos:
        # there are no repositories associated with this project, so go ahead
        # and create one so that it can be queried by the celery task later
        for project in projects:
            repo = models.Repo(
                project,
                arch.ref,
                arch.distro,
                arch.distro_version,
                sha1=arch.sha1,
            )
            repo.needs_update = repository_is_automatic(project.name)
            repo.type = arch.binary._get_repo_type()

    else:
        for repo in repos:
            repo.needs_update = repository_is_automatic(repo.project.name)
            if repo.type is None:
                repo.type = arch.binary._get_repo_type()

def create_directory(arch):
    end_part = request.url.split('binaries/')[-1].rstrip('/')
    # take out the binary name
    end_part = end_part.split(arch.binary_name)[0]
    path = os.path.join(pecan.conf.binary_root, end_part.lstrip('/'))
    if not os.path.isdir(path):
        os.makedirs(path)
    return path

def save_file(arch, file_obj):
    dir_path = arch.create_directory()
    if arch.binary_name in os.listdir(dir_path):
        # resource exists so we will update it
        response.status = 200
    else:
        # we will create a resource
        response.status = 201

    destination = os.path.join(dir_path, arch.binary_name)

    with open(destination, 'wb') as f:
        file_iterable = FileIter(file_obj)
        for chunk in file_iterable:
            f.write(chunk)

    # return the full path to the saved object:
    return destination
