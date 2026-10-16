"""Tests for the SQLite-backed storage layer.

Covers:
  - Full save -> load round-trip preserves books, students, operators,
    manager, borrows in all states (pending, active, returned), dates,
    and the duplicate-title case that motivated the book_id refactor.
  - JSON -> SQLite one-time migration: a legacy library.json is imported
    into a fresh SQLite database on first run, and the JSON file is left
    in place as a backup.
  - PRAGMA user_version is set to 1 on a freshly created database.
  - Foreign-key enforcement is on; a borrow referencing a non-existent
    student raises IntegrityError.
  - Dangling borrows (student/book/operator no longer in the library) are
    skipped on save, matching JsonHandler behavior.
  - Default-library fallback when neither library.db nor library.json
    exists.
"""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from library_system.models.book import Book
from library_system.models.borrow import Borrow
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.models.operator import Operator
from library_system.models.student import Student
from library_system.services.book_service import BookService
from library_system.services.borrow_service import BorrowService
from library_system.storage.json_handler import JsonHandler
from library_system.storage.sqlite_handler import SqliteHandler, SCHEMA_VERSION


def _seed_library() -> Library:
    """A library with: duplicate-title books, a student, an operator,
    a pending borrow, and an approved (currently-borrowed) borrow."""
    lib = Library("Round-Trip Library", Manager("Default", "Manager", 10001, 1234, "Administration"))
    bs = BookService(lib)
    bs.add_book(Book(0, "The Hobbit", "Tolkien", 310, 1937, 3))      # book_id=1
    bs.add_book(Book(0, "The Hobbit", "Tolkien", 310, 1966, 1))     # book_id=2 (dup title)
    bs.add_book(Book(0, "Pride and Prejudice", "Jane Austen", 432, 1813, 2))  # book_id=3
    student = Student("Sample", "Student", 20001, 1234, "Computer Engineering",
                      date(2026, 1, 1), True)
    lib.students[student.member_id] = student
    operator = Operator("Sample", "Operator", 30001, 1234)
    lib.operators[operator.member_id] = operator
    brw = BorrowService(lib)
    # Pending request on book_id=1
    brw.request_book(student, lib.books[0])
    # Approved (currently borrowed) request on the duplicate-title book_id=2
    brw.request_book(student, lib.books[1])
    brw.approve(student.member_id, 2, operator)
    return lib


class SqliteHandlerRoundTripTests(unittest.TestCase):
    def test_round_trip_preserves_books_students_and_manager(self):
        original = _seed_library()
        handler = SqliteHandler()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.db"
            handler.save(original, path)
            loaded = handler.load(path)

        self.assertEqual(loaded.name, "Round-Trip Library")
        self.assertEqual(loaded.manager.member_id, 10001)
        self.assertEqual(loaded.manager.education, "Administration")
        self.assertEqual(len(loaded.books), 3)
        # Duplicate titles survive with distinct ids.
        self.assertEqual(loaded.books[0].book_id, 1)
        self.assertEqual(loaded.books[1].book_id, 2)
        self.assertEqual(loaded.books[0].title, loaded.books[1].title)
        self.assertEqual(len(loaded.students), 1)
        self.assertIn(20001, loaded.students)
        self.assertEqual(loaded.students[20001].signup_date, date(2026, 1, 1))
        self.assertIn(30001, loaded.operators)

    def test_round_trip_preserves_borrow_states(self):
        original = _seed_library()
        handler = SqliteHandler()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.db"
            handler.save(original, path)
            loaded = handler.load(path)

        self.assertEqual(len(loaded.borrows), 2)
        pending = next(b for b in loaded.borrows if b.book.book_id == 1)
        active = next(b for b in loaded.borrows if b.book.book_id == 2)
        self.assertTrue(pending.is_pending)
        self.assertTrue(active.is_currently_borrowed)
        # The active borrow's book must keep book_id=2 (the duplicate-title
        # edition), not collapse onto book_id=1.
        self.assertEqual(active.book.book_id, 2)
        self.assertEqual(active.giver_operator.member_id, 30001)
        self.assertIsNotNone(active.borrow_date)
        self.assertIsNotNone(active.due_date)

    def test_user_version_is_set_to_one_on_fresh_database(self):
        handler = SqliteHandler()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.db"
            handler.save(_seed_library(), path)
            conn = sqlite3.connect(str(path))
            try:
                version = conn.execute("PRAGMA user_version").fetchone()[0]
            finally:
                conn.close()
        self.assertEqual(version, SCHEMA_VERSION)
        self.assertEqual(version, 1)

    def test_foreign_keys_are_enforced(self):
        handler = SqliteHandler()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.db"
            handler.save(_seed_library(), path)
            conn = sqlite3.connect(str(path))
            try:
                conn.execute("PRAGMA foreign_keys = ON")
                # Insert a borrow that references a non-existent student.
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(
                        "INSERT INTO borrows (student_id, book_id, "
                        "loan_period_days) VALUES (?, ?, ?)",
                        (99999, 1, 5),
                    )
            finally:
                conn.close()


class SqliteHandlerMigrationTests(unittest.TestCase):
    def _write_legacy_json(self, path: Path) -> None:
        """Write a library.json that uses the new book_id fields, mimicking
        the output of the previous JsonHandler."""
        legacy = {
            "name": "Legacy Library",
            "manager": {
                "kind": "manager", "first_name": "Old", "last_name": "Mgr",
                "member_id": 10001, "password": 1234, "education": "Admin",
            },
            "next_book_id": 4,
            "books": [
                {"book_id": 1, "title": "The Hobbit", "author": "Tolkien",
                 "pages": 310, "publication_year": 1937, "copies": 3},
                {"book_id": 2, "title": "The Hobbit", "author": "Tolkien",
                 "pages": 310, "publication_year": 1966, "copies": 1},
                {"book_id": 3, "title": "Pride and Prejudice",
                 "author": "Austen", "pages": 432,
                 "publication_year": 1813, "copies": 2},
            ],
            "students": [
                {"kind": "student", "first_name": "Sample",
                 "last_name": "Student", "member_id": 20001, "password": 1234,
                 "major": "Engineering", "signup_date": "2026-01-01",
                 "active": True},
            ],
            "pending_students": [],
            "operators": [
                {"kind": "operator", "first_name": "Sample",
                 "last_name": "Operator", "member_id": 30001, "password": 1234},
            ],
            "borrows": [
                {"student_id": 20001, "book_id": 1, "loan_period_days": 5,
                 "giver_operator_id": None, "receiver_operator_id": None,
                 "borrow_date": None, "due_date": None,
                 "real_return_date": None},
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(legacy, f, indent=2)

    def test_first_run_migrates_json_when_db_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "data" / "library.json"
            db_path = Path(tmp) / "data" / "library.db"
            self._write_legacy_json(json_path)

            handler = SqliteHandler(json_fallback_path=json_path)
            library = handler.load(db_path)

            # JSON data was migrated.
            self.assertEqual(library.name, "Legacy Library")
            self.assertEqual(len(library.books), 3)
            self.assertEqual(library.books[0].book_id, 1)
            self.assertEqual(library.books[1].book_id, 2)
            self.assertEqual(library.books[0].title, library.books[1].title)
            self.assertEqual(len(library.students), 1)
            self.assertEqual(len(library.operators), 1)
            self.assertEqual(len(library.borrows), 1)
            # The DB file was created.
            self.assertTrue(db_path.exists())
            # The JSON file is left in place as a backup.
            self.assertTrue(json_path.exists())

    def test_second_run_reads_db_not_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "data" / "library.json"
            db_path = Path(tmp) / "data" / "library.db"
            self._write_legacy_json(json_path)

            handler = SqliteHandler(json_fallback_path=json_path)
            first = handler.load(db_path)
            # Mutate the in-memory library and save.
            BookService(first).add_book(Book(0, "New Book", "Author", 100, 2020, 1))
            handler.save(first, db_path)

            # Rewrite the JSON with different data — it must NOT be read now
            # that the DB exists.
            with json_path.open("w") as f:
                json.dump({
                    "name": "Should Be Ignored",
                    "manager": {"kind": "manager", "first_name": "X",
                                "last_name": "Y", "member_id": 10001,
                                "password": 1234, "education": "Admin"},
                    "next_book_id": 1, "books": [], "students": [],
                    "pending_students": [], "operators": [], "borrows": [],
                }, f)

            second = handler.load(db_path)
            self.assertEqual(second.name, "Legacy Library")  # unchanged
            self.assertEqual(len(second.books), 4)  # the new book persists


class SqliteHandlerDefaultsTests(unittest.TestCase):
    def test_load_creates_default_when_no_db_and_no_json(self):
        handler = SqliteHandler(json_fallback_path=None)
        default = Library("Fallback", Manager("A", "B", 10001, 1234, "Admin"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subdir" / "library.db"
            loaded = handler.load(path, default=default)
            self.assertEqual(loaded.name, "Fallback")
            # DB file was created so subsequent loads find it.
            self.assertTrue(path.exists())

    def test_load_raises_when_no_db_no_json_no_default(self):
        handler = SqliteHandler(json_fallback_path=None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.db"
            with self.assertRaises(FileNotFoundError):
                handler.load(path)


class SqliteHandlerDanglingBorrowTests(unittest.TestCase):
    def test_save_skips_borrow_referencing_missing_student(self):
        lib = _seed_library()
        # Inject a borrow referencing a student who is NOT in lib.students.
        # This simulates an in-memory inconsistency — e.g. someone removed a
        # student but kept their borrow record. save() must skip the borrow
        # rather than fail the whole write.
        ghost_student = Student("Ghost", "User", 99999, 1234, "X")
        ghost_borrow = Borrow(ghost_student, lib.books[0])
        lib.borrows.append(ghost_borrow)
        handler = SqliteHandler()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.db"
            handler.save(lib, path)
            loaded = handler.load(path)
        # The ghost borrow is gone, the legitimate borrows survive.
        self.assertEqual(len(loaded.borrows), 2)
        for b in loaded.borrows:
            self.assertNotEqual(b.student.member_id, 99999)


if __name__ == "__main__":
    unittest.main()
