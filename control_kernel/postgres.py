from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator

from .errors import DatabaseUnavailable


class PostgresConnection:
    """Small DB-API adapter; PostgreSQL is the only supported authority."""

    def __init__(self, dsn: str, connect_factory: Callable[[str], Any] | None = None):
        self.dsn = dsn
        self._connect_factory = connect_factory

    def connect(self) -> Any:
        if self._connect_factory is not None:
            return self._connect_factory(self.dsn)
        try:
            import psycopg
        except ImportError as exc:
            raise DatabaseUnavailable("psycopg is required; SQLite fallback is forbidden") from exc
        return psycopg.connect(self.dsn)

    @contextmanager
    def transaction(self) -> Iterator[tuple[Any, Any]]:
        connection = self.connect()
        try:
            cursor = connection.cursor()
            try:
                yield connection, cursor
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
        finally:
            connection.close()

    @contextmanager
    def session(self) -> Iterator[Any]:
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()
