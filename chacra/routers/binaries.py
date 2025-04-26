from typing import Dict, List

from fastapi import APIRouter, HTTPException

from chacra.models.binaries import Binary
from chacra.models.projects import Project
from chacra.models.repos import Repo


router = APIRouter(
    prefix="/binaries",
    tags=["binaries"],
)


@router.get("/")
async def list_projects() -> Dict[str, List[str]]:
    projects = await Project.get_all()
    resp = {}

    for project in projects:
        resp[project.name] = {b.ref for b in project.binaries}
    return resp


@router.post("/{project_name}/")
async def create_project(project_name: str) -> Dict:
    await Project.get_or_create(name=project_name)
    return {}


@router.get("/{project_name}/")
async def get_project(project_name: str) -> Dict[str, List[str]]:
    project = await Project.get(name=project_name)

    if not project:
        raise HTTPException(status_code=404)

    resp = {}
    refs = {b.ref for b in project.binaries}

    for ref in refs:
        resp[ref] = {b.sha1 for b in project.binaries if b.ref == ref}
    return resp


@router.get("/{project_name}/{ref}/")
async def get_sha1s(project_name: str, ref: str) -> Dict[str, List[str]]:
    project = await Project.get(name=project_name)

    if not project:
        raise HTTPException(status_code=404)

    resp = {}
    sha1s = {r.sha1 for r in await Repo.filter_by(ref=ref)}

    if not sha1s:
        raise HTTPException(status_code=404)

    for sha1 in sha1s:
        resp[sha1] = {b.distro for b in await Binary.filter_by(ref=ref, sha1=sha1)}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/")
async def get_distros(project_name: str, ref: str, sha1: str) -> Dict[str, List[str]]:
    project = await Project.get(name=project_name)
    binaries = await Binary.filter_by(project=project, sha1=sha1, ref=ref)

    resp = {}
    distros = {b.distro for b in binaries}

    for distro in distros:
        resp[distro] = {b.distro_version for b in binaries if b.distro == distro}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/{distro}/")
async def get_distro_versions(
    project_name: str, ref: str, sha1: str, distro: str
) -> Dict[str, List[str]]:
    project = await Project.get(name=project_name)
    binaries = await Binary.filter_by(
        project=project, sha1=sha1, ref=ref, distro=distro
    )

    resp = {}
    versions = {b.distro_version for b in binaries}
    for version in versions:
        resp[version] = {b.arch for b in binaries if b.distro_version == version}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/")
async def get_archs(
    project_name: str, ref: str, sha1: str, distro: str, distro_version: str
) -> Dict[str, List[str]]:
    project = await Project.get(name=project_name)
    binaries = await Binary.filter_by(
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
    )

    resp = {}
    archs = {b.arch for b in binaries}

    for arch in archs:
        resp[arch] = {b.flavor for b in binaries if b.arch == arch}
    return resp


@router.get("/{project_name}/{ref}/{sha1}/{distro}/{distro_version}/{arch}/")
async def get_binaries(
    project_name: str, ref: str, sha1: str, distro: str, distro_version: str, arch: str
) -> Dict[str, Dict]:
    project = await Project.get(name=project_name)
    binaries = await Binary.get(
        project=project,
        sha1=sha1,
        ref=ref,
        distro=distro,
        distro_version=distro_version,
        arch=arch,
    )

    returned_keys = [
        "name",
        "created",
        "modified",
        "signed",
        "size",
        "path",
        "distro",
        "distro_version",
        "arch",
        "ref",
        "sha1",
        "flavor",
        "checksum",
    ]

    resp = {}
    for key in returned_keys:
        resp[key] = getattr(binaries, key)

    return {binaries.name: resp}
