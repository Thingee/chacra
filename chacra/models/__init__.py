from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Type

from sqlalchemy.engine.result import ChunkedIteratorResult
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine, select, SQLModel


# Database configuration
DATABASE_URL = "postgresql+asyncpg://USER:PASS@HOST:PORT/chacra"


class EntityBase(SQLModel):
    """
    A custom base class that provides utility methods for SQLModel models.
    """

    _session_factory = None

    @classmethod
    def set_session_factory(cls, session_factory) -> None:
        """
        Set the session factory for the model.
        """
        cls._session_factory = session_factory

    @classmethod
    @asynccontextmanager
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        Asynchronous context manager to provide a session.
        """
        if cls._session_factory is None:
            raise ValueError(
                "Session factory is not set. Use `set_session_factory` to "
                "configure it."
            )

        async with cls._session_factory() as session:
            yield session

    @classmethod
    async def get(cls, **kwargs) -> Optional[Type["EntityBase"]]:
        """
        Retrieve a single record matching the given filters.
        """
        async with cls.get_session() as session:
            statement = select(cls).filter_by(**kwargs)
            result = await session.execute(statement)
            return result.unique().scalars().first()

    @classmethod
    async def get_all(cls) -> ChunkedIteratorResult:
        """
        Retrieve all records of the model.
        """
        async with cls.get_session() as session:
            statement = select(cls)
            result = await session.execute(statement)
            return result.unique().scalars().all()

    @classmethod
    async def filter_by(cls, **kwargs) -> ChunkedIteratorResult:
        """
        Retrieve records matching the given filters.
        """
        async with cls.get_session() as session:
            statement = select(cls).filter_by(**kwargs)
            result = await session.execute(statement)
            return result.unique().scalars().all()

    @classmethod
    async def get_or_create(cls, **kwargs) -> Optional[Type["EntityBase"]]:
        async with cls.get_session() as session:
            statement = select(cls).filter_by(**kwargs)
            instance = await session.execute(statement)
            result = instance.scalars().first()

            if result:
                return result

            instance = cls(**kwargs)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)

            return instance


async def create_db_and_tables() -> None:
    """
    Create all tables in the database.
    """
    engine = AsyncEngine(create_engine(DATABASE_URL, echo=True))
    EntityBase.set_session_factory(
        sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
