import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship

from chacra.models import EntityBase


if TYPE_CHECKING:
    from chacra.models.binaries import Binary
    from chacra.models.projects import Project


class Repo(EntityBase, table=True):
    __tablename__ = "repos"

    id: Optional[int] = Field(default=None, primary_key=True)
    path: Optional[str] = Field(default=None, max_length=256)
    ref: Optional[str] = Field(default=None, max_length=256, index=True)
    sha1: str = Field(default="head", max_length=256, index=True)
    distro: str = Field(max_length=256, index=True)
    distro_version: str = Field(max_length=256, index=True)
    flavor: str = Field(default="default", max_length=256, index=True)
    modified: datetime.datetime = Field(
        default_factory=datetime.datetime.now(datetime.UTC)
    )
    signed: bool = Field(default=False)
    needs_update: bool = Field(default=True)
    is_updating: bool = Field(default=False)
    is_queued: bool = Field(default=False)
    type: Optional[str] = Field(default=None)
    size: int = Field(default=0)

    project_id: int = Field(foreign_key="projects.id")
    project: Optional["Project"] = Relationship(
        back_populates="repos", sa_relationship_kwargs={"lazy": "selectin"}
    )

    binaries: List["Binary"] = Relationship(
        back_populates="repo", sa_relationship_kwargs={"lazy": "selectin"}
    )
