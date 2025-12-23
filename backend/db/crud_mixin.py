"""CRUD mixin for SQLAlchemy models.

This module provides CRUD operations as a mixin that can be added to any
DeclarativeBase subclass.
"""

from typing import Any, ClassVar, Optional, TypeVar

from sqlalchemy import inspect
from sqlalchemy.orm import Session

T = TypeVar("T")


class CRUDMixin:
    """Mixin class that provides CRUD operations for SQLAlchemy models."""

    # Class-level cache for foreign key info
    _fk_cache: ClassVar[dict[str, dict[str, tuple[str, str]]]] = {}

    @classmethod
    def get_foreign_keys(cls) -> dict[str, tuple[str, str]]:
        """Get foreign key information for this model.

        Returns a dict mapping column names to (table_name, column_name) tuples.
        """
        table_name = cls.__tablename__
        if table_name not in cls._fk_cache:
            fk_info = {}
            mapper = inspect(cls)
            for column in mapper.columns:
                for fk in column.foreign_keys:
                    # fk.target_fullname is 'table.column'
                    target_table, target_column = fk.target_fullname.split(".")
                    fk_info[column.name] = (target_table, target_column)
            cls._fk_cache[table_name] = fk_info
        return cls._fk_cache[table_name]

    @classmethod
    def validate_foreign_keys(
        cls, session: Session, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate that foreign key references exist.

        Args:
            session: SQLAlchemy session
            data: Dictionary of column values to validate

        Returns:
            Dictionary with foreign key info (referenced objects exist)

        Raises:
            ValueError: If a foreign key reference doesn't exist
        """
        fk_info = cls.get_foreign_keys()
        fk_status = {}

        # Get the Base class from the same module as cls
        Base = cls.__mro__[-2]  # Assuming DeclarativeBase is second to last in MRO

        for col_name, (target_table, target_column) in fk_info.items():
            if col_name in data and data[col_name] is not None:
                # Find the target model class
                target_cls = None
                for mapper in Base.registry.mappers:
                    if hasattr(mapper.class_, "__tablename__"):
                        if mapper.class_.__tablename__ == target_table:
                            target_cls = mapper.class_
                            break

                if target_cls is not None:
                    # Check if referenced record exists
                    ref_value = data[col_name]
                    exists = (
                        session.query(target_cls)
                        .filter(getattr(target_cls, target_column) == ref_value)
                        .first()
                    )
                    if exists is None:
                        raise ValueError(
                            f"Foreign key constraint failed: {col_name}='{ref_value}' "
                            f"references non-existent {target_table}.{target_column}"
                        )
                    fk_status[col_name] = {"exists": True, "table": target_table}

        return fk_status

    @classmethod
    def create(
        cls: type[T], session: Session, validate_fk: bool = True, **kwargs: Any
    ) -> T:
        """Create a new instance and add it to the session.

        Args:
            session: SQLAlchemy session
            validate_fk: Whether to validate foreign key references
            **kwargs: Column values for the new instance

        Returns:
            The created instance of the model type
        """
        if validate_fk:
            cls.validate_foreign_keys(session, kwargs)

        instance = cls(**kwargs)
        session.add(instance)
        session.flush()
        return instance

    @classmethod
    def get_by_id(cls: type[T], session: Session, id_value: Any) -> Optional[T]:
        """Get a single instance by its primary key.

        Args:
            session: SQLAlchemy session
            id_value: The primary key value (for single PK) or tuple of values (for composite PK)

        Returns:
            The instance if found, None otherwise

        Raises:
            ValueError: If id_value format doesn't match the primary key structure
        """
        mapper = inspect(cls)
        pk_columns = mapper.primary_key

        if len(pk_columns) == 1:
            return session.query(cls).filter(pk_columns[0] == id_value).first()
        elif len(pk_columns) > 1:
            # Composite primary key - id_value should be a tuple
            if not isinstance(id_value, (tuple, list)):
                raise ValueError(
                    f"{cls.__name__} has a composite primary key with {len(pk_columns)} columns. "
                    f"id_value must be a tuple/list of values, got {type(id_value).__name__}"
                )
            if len(id_value) != len(pk_columns):
                raise ValueError(
                    f"{cls.__name__} has {len(pk_columns)} primary key columns, "
                    f"but {len(id_value)} values were provided"
                )
            query = session.query(cls)
            for pk_col, val in zip(pk_columns, id_value):
                query = query.filter(pk_col == val)
            return query.first()
        return None

    @classmethod
    def get_all(cls: type[T], session: Session) -> list[T]:
        """Get all instances of this model.

        Args:
            session: SQLAlchemy session

        Returns:
            List of all instances
        """
        return session.query(cls).all()

    @classmethod
    def find_by(cls: type[T], session: Session, **filters: Any) -> list[T]:
        """Find instances matching the given filters.

        Args:
            session: SQLAlchemy session
            **filters: Column filters (column_name=value)

        Returns:
            List of matching instances
        """
        query = session.query(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query.all()

    @classmethod
    def find_one_by(cls: type[T], session: Session, **filters: Any) -> Optional[T]:
        """Find a single instance matching the given filters.

        Args:
            session: SQLAlchemy session
            **filters: Column filters (column_name=value)

        Returns:
            The first matching instance, or None
        """
        query = session.query(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query.first()

    def update(self: T, session: Session, validate_fk: bool = True, **kwargs: Any) -> T:
        """Update this instance with new values.

        Args:
            session: SQLAlchemy session
            validate_fk: Whether to validate foreign key references
            **kwargs: Column values to update

        Returns:
            The updated instance (self)
        """
        if validate_fk:
            self.__class__.validate_foreign_keys(session, kwargs)

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        session.flush()
        return self

    def delete(self: T, session: Session) -> bool:
        """Delete this instance from the database.

        Args:
            session: SQLAlchemy session

        Returns:
            True if deleted successfully
        """
        session.delete(self)
        session.flush()
        return True

    @classmethod
    def delete_by_id(cls: type[T], session: Session, id_value: Any) -> bool:
        """Delete an instance by its primary key.

        Args:
            session: SQLAlchemy session
            id_value: The primary key value (for single PK) or tuple of values (for composite PK)

        Returns:
            True if found and deleted, False otherwise

        Raises:
            ValueError: If id_value format doesn't match the primary key structure
        """
        instance = cls.get_by_id(session, id_value)
        if instance:
            session.delete(instance)
            session.flush()
            return True
        return False
