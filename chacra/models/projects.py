from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship

from chacra.models import EntityBase


if TYPE_CHECKING:
    from chacra.models.binaries import Binary
    from chacra.models.repos import Repo


class Project(EntityBase, table=True):
    __tablename__ = "projects"
    id: Optional[int] = Field(primary_key=True)
    name: str

    binaries: List["Binary"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"lazy": "selectin"}
    )
    repos: List["Repo"] = Relationship(
        back_populates="project", sa_relationship_kwargs={"lazy": "selectin"}
    )
