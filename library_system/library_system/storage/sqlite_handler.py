"""SQLite-backed storage for the Library system.

Replaces JsonHandler as the production storage backend. The on-disk schema
uses PRAGMA user_version = 1 so future schema changes can be migrated.

Migration policy: on the first call to load() where the SQLite file does not
exist, if a legacy library.json is present at the configured fallback path,
the JSON data is imported into a fresh SQLite database. The JSON file is left
in place on disk as a backup.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Optional

from library_system.models.book import Book
from library_system.models.borrow import Borrow
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.models.operator import Operator
from library_system.models.student import Student
from library_system.storage.json_handler import JsonHandler

SCHEMA_VERSION = 1

# Schema definition. PRAGMA user_version is set inside executescript so it
# persists across connections. All tables use IF NOT EXISTS so re-running
# _init_schema on an existing DB is safe.
_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS library_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS managers (
    member_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password INTEGER NOT NULL,
    education TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    pages INTEGER NOT NULL CHECK (pages > 0),
    publication_year INTEGER NOT NULL,
    copies INTEGER NOT NULL DEFAULT 1 CHECK (copies >= 0)
);

CREATE TABLE IF NOT EXISTS students (
    member_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password INTEGER NOT NULL,
    major TEXT NOT NULL,
    signup_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pending_students (
    member_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password INTEGER NOT NULL,
    major TEXT NOT NULL,
    signup_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS operators (
    member_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS borrows (
    borrow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(member_id),
    book_id INTEGER NOT NULL REFERENCES books(book_id),
    loan_period_days INTEGER NOT NULL DEFAULT 5,
    giver_operator_id INTEGER REFERENCES operators(member_id),
    receiver_operator_id INTEGER REFERENCES operators(member_id),
    borrow_date TEXT,
    due_date TEXT,
    real_return_date TEXT
);
"""


class SqliteHandler:
    """Eager loader/saver: load() reads the entire library into memory,
    save() writes the entire library back. Mirrors the JsonHandler interface
    so it is a drop-in replacement in main.py.
    """

    def __init__(self, json_fallback_path: Optional[Path] = None):
        # When set, library.json at this path is used as a one-time migration
        # source if the SQLite file does not yet exist.
        self._json_fallback = json_fallback_path

    # ------------------------------------------------------------------
    # Public interface (matches JsonHandler)
    # ------------------------------------------------------------------

    def load(self, path: str | Path, default: Optional[Library] = None) -> Library:
        file_path = Path(path)
        if not file_path.exists():
            library = self._source_for_first_run(file_path, default)
            self.save(library, file_path)
            return library
        return self._load_from_db(file_path)

    def save(self, library: Library, path: str | Path) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(file_path))
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            self._init_schema(conn)
            self._migrate_if_needed(conn)
            # Eager full-rewrite strategy. AUTOINCREMENT's sqlite_sequence
            # row survives the DELETE, so the next auto book_id stays correct.
            self._wipe_all(conn)
            self._write_library(conn, library)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # First-run / migration from JSON
    # ------------------------------------------------------------------

    def _source_for_first_run(
        self, file_path: Path, default: Optional[Library]
    ) -> Library:
        if self._json_fallback and Path(self._json_fallback).exists():
            # One-time migration: JSON file is left in place as a backup.
            return JsonHandler().load(self._json_fallback)
        if default is not None:
            return default
        raise FileNotFoundError(file_path)

    # ------------------------------------------------------------------
    # Schema bootstrap and versioning
    # ------------------------------------------------------------------

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(_SCHEMA_SQL)

    def _migrate_if_needed(self, conn: sqlite3.Connection) -> None:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        if current == 0:
            # Brand-new file: executescript above already set user_version = 1.
            return
        if current < SCHEMA_VERSION:
            # Future migrations go here. None needed for v1.
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def _load_from_db(self, path: Path) -> Library:
        conn = sqlite3.connect(str(path))
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            self._migrate_if_needed(conn)

            row = conn.execute(
                "SELECT name FROM library_meta WHERE id = 1"
            ).fetchone()
            if row is None:
                raise ValueError(
                    f"SQLite file at {path} has no library_meta row; "
                    "the database is corrupt or partially initialized."
                )
            library_name = row[0]

            m = conn.execute(
                "SELECT member_id, first_name, last_name, password, education "
                "FROM managers LIMIT 1"
            ).fetchone()
            if m is None:
                raise ValueError(
                    f"SQLite file at {path} has no manager; cannot construct Library."
                )
            manager = Manager(m[1], m[2], m[0], m[3], m[4])
            library = Library(library_name, manager)

            for r in conn.execute(
                "SELECT book_id, title, author, pages, publication_year, copies "
                "FROM books ORDER BY book_id"
            ):
                library.books.append(Book(r[0], r[1], r[2], r[3], r[4], r[5]))

            # next_book_id is derived from the max book_id in the table.
            # SQLite's AUTOINCREMENT will not reuse a deleted id, so deriving
            # from current rows is safe as long as we never delete books
            # without also deleting their borrows. For now, no delete path
            # exists, so this is exact.
            if library.books:
                library.next_book_id = max(b.book_id for b in library.books) + 1
            else:
                library.next_book_id = 1

            for r in conn.execute(
                "SELECT member_id, first_name, last_name, password, major, "
                "signup_date, active FROM students"
            ):
                s = Student(
                    r[1], r[2], r[0], r[3], r[4],
                    date.fromisoformat(r[5]), bool(r[6]),
                )
                library.students[s.member_id] = s

            for r in conn.execute(
                "SELECT member_id, first_name, last_name, password, major, "
                "signup_date, active FROM pending_students"
            ):
                s = Student(
                    r[1], r[2], r[0], r[3], r[4],
                    date.fromisoformat(r[5]), bool(r[6]),
                )
                library.pending_students[s.member_id] = s

            for r in conn.execute(
                "SELECT member_id, first_name, last_name, password FROM operators"
            ):
                o = Operator(r[1], r[2], r[0], r[3])
                library.operators[o.member_id] = o

            for r in conn.execute(
                "SELECT student_id, book_id, loan_period_days, "
                "giver_operator_id, receiver_operator_id, "
                "borrow_date, due_date, real_return_date FROM borrows"
            ):
                student = library.students.get(r[0])
                book = next(
                    (b for b in library.books if b.book_id == r[1]), None
                )
                # Skip dangling borrows — matches the JsonHandler behavior.
                if student is None or book is None:
                    continue
                borrow = Borrow(student, book, r[2])
                borrow.giver_operator = (
                    library.operators.get(r[3]) if r[3] is not None else None
                )
                borrow.receiver_operator = (
                    library.operators.get(r[4]) if r[4] is not None else None
                )
                borrow.borrow_date = (
                    date.fromisoformat(r[5]) if r[5] else None
                )
                borrow.due_date = date.fromisoformat(r[6]) if r[6] else None
                borrow.real_return_date = (
                    date.fromisoformat(r[7]) if r[7] else None
                )
                library.borrows.append(borrow)

            return library
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def _wipe_all(self, conn: sqlite3.Connection) -> None:
        # Order respects FK constraints: borrows first, then parents.
        conn.executescript(
            """
            DELETE FROM borrows;
            DELETE FROM operators;
            DELETE FROM pending_students;
            DELETE FROM students;
            DELETE FROM books;
            DELETE FROM managers;
            DELETE FROM library_meta;
            """
        )

    def _write_library(self, conn: sqlite3.Connection, library: Library) -> None:
        conn.execute(
            "INSERT INTO library_meta (id, name) VALUES (1, ?)",
            (library.name,),
        )

        m = library.manager
        conn.execute(
            "INSERT INTO managers "
            "(member_id, first_name, last_name, password, education) "
            "VALUES (?, ?, ?, ?, ?)",
            (m.member_id, m.first_name, m.last_name, m.password, m.education),
        )

        for b in library.books:
            conn.execute(
                "INSERT INTO books "
                "(book_id, title, author, pages, publication_year, copies) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (b.book_id, b.title, b.author, b.pages,
                 b.publication_year, b.copies),
            )

        for s in library.students.values():
            conn.execute(
                "INSERT INTO students "
                "(member_id, first_name, last_name, password, major, "
                "signup_date, active) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (s.member_id, s.first_name, s.last_name, s.password,
                 s.major, s.signup_date.isoformat(), int(s.active)),
            )

        for s in library.pending_students.values():
            conn.execute(
                "INSERT INTO pending_students "
                "(member_id, first_name, last_name, password, major, "
                "signup_date, active) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (s.member_id, s.first_name, s.last_name, s.password,
                 s.major, s.signup_date.isoformat(), int(s.active)),
            )

        for o in library.operators.values():
            conn.execute(
                "INSERT INTO operators "
                "(member_id, first_name, last_name, password) "
                "VALUES (?, ?, ?, ?)",
                (o.member_id, o.first_name, o.last_name, o.password),
            )

        for b in library.borrows:
            # Skip borrows whose student/book/operator is no longer in the
            # in-memory library so the FK insert does not fail.
            if b.student.member_id not in library.students:
                continue
            if b.book.book_id not in {book.book_id for book in library.books}:
                continue
            giver_id = (
                b.giver_operator.member_id
                if b.giver_operator is not None
                and b.giver_operator.member_id in library.operators
                else None
            )
            receiver_id = (
                b.receiver_operator.member_id
                if b.receiver_operator is not None
                and b.receiver_operator.member_id in library.operators
                else None
            )
            conn.execute(
                "INSERT INTO borrows "
                "(student_id, book_id, loan_period_days, "
                "giver_operator_id, receiver_operator_id, "
                "borrow_date, due_date, real_return_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (b.student.member_id, b.book.book_id, b.loan_period_days,
                 giver_id, receiver_id,
                 b.borrow_date.isoformat() if b.borrow_date else None,
                 b.due_date.isoformat() if b.due_date else None,
                 b.real_return_date.isoformat()
                 if b.real_return_date else None),
            )
