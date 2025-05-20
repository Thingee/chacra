import os
from typing import Annotated, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from chacra.auth import authenticate
from chacra.config import CFG
from chacra.models.binaries import Binary
from chacra.models.projects import Project
from chacra.models.repos import Repo
from chacra.routers.util import repository_is_automatic
from chacra import util


router = APIRouter(
    prefix="/binaries",
    tags=["binaries"],
)


async def _get_objects_or_404(entity: object, **kwargs) -> Project:
    instances = None
    if len(kwargs) == 1:
        instances = await entity.get(**kwargs)
    elif len(kwargs) > 1:
        instances = await entity.filter_by(**kwargs)
    if not instances:
        raise HTTPException(status_code=404)
    return instances


@router.get("/")
async def list_projects() -> Dict[str, List[str]]:
    projects = await Project.get_all()
    resp = {}

    for project in projects:
        resp[project.name] = {b.ref for b in project.binaries}
    return resp


@router.post("/{project_name}/")
async def create_project(
        project_name: str,
        auth: Annotated[str, Depends(authenticate)]
    ) -> Dict:
    await Project.get_or_create(name=project_name)
    return {}


@router.get("/{project_name}/")
async def get_project_details(project_name: str) -> Dict[str, List[str]]:
    project = await _get_objects_or_404(Project, name=project_name)

    resp = {}
    refs = {b.ref for b in project.binaries}

    for ref in refs:
        resp[ref] = {b.sha1 for b in project.binaries if b.ref == ref}
    return resp


@router.get("/{project_name}/{ref}/")
async def get_sha1s(project_name: str, ref: str) -> Dict[str, List[str]]:
    project = await _get_objects_or_404(Project, name=project_name)

    resp = {}
    sha1s = {r.sha1 for r in await Repo.filter_by(project=project, ref=ref)}

    if not sha1s:
        raise HTTPException(status_code=404)

    for sha1 in sha1s:
        resp[sha1] = {b.distro for b in await Binary.filter_by(ref=ref,
                                                               sha1=sha1)}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/")
async def get_distros(project_name: str, ref: str,
                      sha1: str) -> Dict[str, List[str]]:
    project = await _get_objects_or_404(Project, name=project_name)
    binaries = await _get_objects_or_404(Binary, project=project, sha1=sha1,
                                         ref=ref)

    resp = {}
    distros = {b.distro for b in binaries}

    for distro in distros:
        resp[distro] = {b.distro_version for b in binaries
                        if b.distro == distro}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/{distro}/")
async def get_distro_versions(project_name: str, ref: str, sha1: str,
                              distro: str) -> Dict[str, List[str]]:
    project = await _get_objects_or_404(Project, name=project_name)
    binaries = await _get_objects_or_404(
        Binary, project=project, sha1=sha1, ref=ref, distro=distro
    )

    resp = {}
    versions = {b.distro_version for b in binaries}
    for version in versions:
        resp[version] = {b.arch for b in binaries
                         if b.distro_version == version}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/")
async def get_archs(project_name: str, ref: str, sha1: str, distro: str,
                    distro_version: str) -> Dict[str, List[str]]:
    project = await _get_objects_or_404(Project, name=project_name)
    binaries = await _get_objects_or_404(
        Binary, project=project, sha1=sha1, ref=ref, distro=distro,
        distro_version=distro_version
    )

    resp = {}
    archs = {b.arch for b in binaries}

    for arch in archs:
        resp[arch] = {b.name for b in binaries if b.arch == arch}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/")
async def get_binaries(project_name: str, ref: str, sha1: str, distro: str,
                       distro_version: str, arch: str) -> Dict[str, Dict]:
    project = await _get_objects_or_404(Project, name=project_name)
    binaries = await _get_objects_or_404(
        Binary,
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
        arch=arch,
    )

    resp = {}
    for binary in binaries:
        resp[binary.name] = binary.as_dict()
    return resp


@router.head("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/")
async def head_binaries(project_name: str, ref: str, sha1: str, distro: str,
                        distro_version: str, arch: str) -> None:
    project = await _get_objects_or_404(Project, name=project_name)
    await _get_objects_or_404(
        Binary,
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
        arch=arch,
    )


async def mark_related_repos(binary: Binary) -> None:
    related_projects = util.get_related_projects(binary.project.name)
    repos = []
    projects = []
    for project_name, refs in related_projects.items():
        p = await Project.get(name=project_name)
        projects.append(p)
        repo_query = []
        if refs == ['all']:
            # we need all the repos available
            repo_query = await Repo.filter_by(project=p)
        else:
            for ref in refs:
                repo_query = await Repo.filter_by(project=p, ref=ref)
        if repo_query:
            for r in repo_query:
                repos.append(r)

    if not repos:
        # there are no repositories associated with this project, so go ahead
        # and create one so that it can be queried by the celery task later
        for project in projects:
            repo = Repo.create(project=project,
                               ref=binary.ref,
                               distro=binary.distro,
                               distro_version=binary.distro_version,
                               sha1=binary.sha1)
            repo.needs_update = repository_is_automatic(project.name)
            repo.type = binary.get_repo_type()

    else:
        for repo in repos:
            repo.needs_update = repository_is_automatic(repo.project.name)
            if repo.type is None:
                repo.type = binary.get_repo_type()


@router.post("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/")
async def upload_binary(project_name: str, ref: str, sha1: str, distro: str,
                        distro_version: str, arch: str,
                        auth: Annotated[str, Depends(authenticate)],
                        file: UploadFile = File(...),
                        force: bool = False) -> Dict:
    project = await _get_objects_or_404(Project, name=project_name)

    binary = await Binary.get(
        name=file.filename,
        project=project,
        ref=ref,
        sha1=sha1,
        distro=distro,
        distro_version=distro_version,
        arch=arch
    )

    if binary and not force:
        raise HTTPException(
            status_code=400,
            detail="Resource already exists and 'force' key was not used"
        )

    # Save the uploaded file
    dir_path = os.path.join(
        CFG.binary_root,
        project.name,
        ref,
        sha1,
        distro,
        distro_version,
        arch
    )
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create or update the binary record
    response_code = 201
    if not binary:
        binary = await Binary.create(
            name=file.filename,
            project=project,
            ref=ref,
            sha1=sha1,
            distro=distro,
            distro_version=distro_version,
            arch=arch,
            path=file_path,
            size=os.path.getsize(file_path)
        )
    else:
        await binary.update(path=file_path, size=os.path.getsize(file_path))
        response_code = 200

    # Mark related repositories for rebuild
    await mark_related_repos(binary)

    return JSONResponse(content={}, status_code=response_code)


@router.get("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/"
            "{binary_name}/")
async def download_binary(
    project_name: str, ref: str, sha1: str, distro: str,
    distro_version: str, arch: str, binary_name: str
) -> FileResponse:
    project = await _get_objects_or_404(Project, name=project_name)
    binary = await _get_objects_or_404(
        Binary,
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
        arch=arch,
        name=binary_name
    )

    if not binary:
        raise HTTPException(status_code=404)

    return FileResponse(binary[0].path)


@router.head("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/"
             "flavors/{flavor}/")
async def head_flavors(project_name: str, ref: str, sha1: str, distro: str,
                       distro_version: str, arch: str, flavor: str) -> None:
    project = await _get_objects_or_404(Project, name=project_name)
    await _get_objects_or_404(
        Binary,
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
        arch=arch,
        flavor=flavor
    )


@router.get("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/"
            "flavors/")
async def get_all_flavors(project_name: str, ref: str, sha1: str, distro: str,
                          distro_version: str, arch: str
                          ) -> Dict[str, List[str]]:
    project = await _get_objects_or_404(Project, name=project_name)
    binaries = await _get_objects_or_404(
        Binary,
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
        arch=arch
    )

    resp = {}
    flavors = {b.flavor for b in binaries}

    for flavor in flavors:
        resp[flavor] = {b.name for b in binaries if b.flavor == flavor}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/"
            "flavors/{flavor}/")
async def get_flavor(project_name: str, ref: str, sha1: str, distro: str,
                     distro_version: str, arch: str, flavor: str) -> Dict:
    project = await _get_objects_or_404(Project, name=project_name)
    binaries = await _get_objects_or_404(
        Binary,
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
        arch=arch,
        flavor=flavor
    )

    resp = {}
    for binary in binaries:
        resp[binary.name] = binary.as_dict()
    return resp


@router.post("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/"
             "flavors/{flavor}/")
async def upload_flavor(project_name: str, ref: str, sha1: str, distro: str,
                        distro_version: str, arch: str, flavor: str,
                        auth: Annotated[str, Depends(authenticate)],
                        file: UploadFile = File(...),
                        force: bool = False) -> Dict:
    project = await _get_objects_or_404(Project, name=project_name)
    binary = await Binary.get(
        name=file.filename,
        project=project,
        ref=ref,
        sha1=sha1,
        distro=distro,
        distro_version=distro_version,
        arch=arch,
        flavor=flavor
    )
    if binary and not force:
        raise HTTPException(
            status_code=400,
            detail="Resource already exists and 'force' key was not used"
        )
    # Save the uploaded file
    dir_path = os.path.join(
        CFG.binary_root,
        project.name,
        ref,
        sha1,
        distro,
        distro_version,
        arch,
        flavor
    )
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    # Create or update the binary record
    response_code = 201
    if not binary:
        binary = await Binary.create(
            name=file.filename,
            project=project,
            ref=ref,
            sha1=sha1,
            distro=distro,
            distro_version=distro_version,
            arch=arch,
            flavor=flavor,
            path=file_path,
            size=os.path.getsize(file_path)
        )
    else:
        await binary.update(path=file_path, size=os.path.getsize(file_path))
        response_code = 200
    # Mark related repositories for rebuild
    await mark_related_repos(binary)
    return JSONResponse(content={}, status_code=response_code)
