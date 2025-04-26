from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship

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