from datetime import datetime, timezone, UTC
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship

from chacra.routers import util
from chacra.models import EntityBase


if TYPE_CHECKING:
    from chacra.models.projects import Project
    from chacra.models.repos import Repo


class Binary(EntityBase, table=True):
    __tablename__ = "binaries"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=256, index=True)
    path: Optional[str] = Field(default=None, max_length=256)
    ref: Optional[str] = Field(default=None, max_length=256, index=True)
    sha1: str = Field(default="head", max_length=256, index=True)
    distro: str = Field(max_length=256, index=True)
    distro_version: str = Field(max_length=256, index=True)
    arch: str = Field(max_length=256, index=True)
    flavor: str = Field(default="default", max_length=256, index=True)
    built_by: Optional[str] = Field(default=None, max_length=256)
    created: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    modified: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    signed: bool = Field(default=False)
    size: Optional[int] = Field(default=0)
    checksum: Optional[str] = Field(default=None, max_length=256)

    project_id: int = Field(foreign_key="projects.id")
    project: "Project" = Relationship(
        back_populates="binaries", sa_relationship_kwargs={"lazy": "selectin"}
    )

    repo_id: Optional[int] = Field(default=None, foreign_key="repos.id")
    repo: Optional["Repo"] = Relationship(
        back_populates="binaries", sa_relationship_kwargs={"lazy": "selectin"}
    )

    @property
    def last_changed(self):
        if self.modified > self.created:
            last = self.modified
        else:
            last = self.created

        now = datetime.now(UTC)
        difference = now - last.replace(tzinfo=UTC)
        formatted = util.ReadableSeconds(difference.seconds)
        return f"{formatted} ago"

    def get_repo_type(self):
        extension_map = {
            'rpm': 'rpm',
            'deb': 'deb',
            'ddeb': 'deb',
            'dsc': 'deb',
            'changes': 'deb'
        }

        # XXX This is very naive, but 'deb' repos are the only ones that
        # will have .tar or .tar.gz or just .gz extensions for source
        # files, so fallback to that
        return extension_map.get(self.extension, 'deb')
