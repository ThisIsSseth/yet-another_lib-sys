import json
import os
import tempfile
import unittest
from datetime import date
from library_system.models.book import Book
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.models.operator import Operator
from library_system.models.student import Student
from library_system.services.book_service import BookService
from library_system.services.borrow_service import BorrowService
from library_system.storage.json_handler import JsonHandler


def _seed_library() -> Library:
    lib = Library("Round-Trip Library", Manager("Default", "Manager", 10001, 1234, "Administration"))
    book_service = BookService(lib)
    book_service.add_book(Book(0, "The Hobbit", "Tolkien", 310, 1937, 3))
    book_service.add_book(Book(0, "The Hobbit", "Tolkien", 310, 1966, 1))  # duplicate title, different id
    student = Student("Sample", "Student", 20001, 1234, "Computer Engineering", date(2026, 1, 1), True)
    lib.students[student.member_id] = student
    operator = Operator("Sample", "Operator", 30001, 1234)
    lib.operators[operator.member_id] = operator
    borrow_service = BorrowService(lib)
    # Pending request
    borrow_service.request_book(student, lib.books[0])
    # Approved (currently borrowed) request on the duplicate-title book
    borrow_service.request_book(student, lib.books[1])
    borrow_service.approve(student.member_id, lib.books[1].book_id, operator)
    return lib


class JsonHandlerRoundTripTests(unittest.TestCase):
    def test_save_then_load_preserves_books_students_and_next_book_id(self):
        original = _seed_library()
        handler = JsonHandler()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "library.json")
            handler.save(original, path)
            loaded = handler.load(path)

        self.assertEqual(loaded.name, original.name)
        self.assertEqual(loaded.next_book_id, original.next_book_id)
        self.assertEqual(len(loaded.books), 2)
        self.assertEqual(loaded.books[0].book_id, 1)
        self.assertEqual(loaded.books[1].book_id, 2)
        # Duplicate titles must survive the round-trip as distinct books.
        self.assertEqual(loaded.books[0].title, loaded.books[1].title)
        self.assertEqual(len(loaded.students), 1)
        self.assertIn(20001, loaded.students)

    def test_round_trip_preserves_borrow_states(self):
        original = _seed_library()
        handler = JsonHandler()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "library.json")
            handler.save(original, path)
            loaded = handler.load(path)

        self.assertEqual(len(loaded.borrows), 2)
        pending = next(b for b in loaded.borrows if b.book.book_id == 1)
        active = next(b for b in loaded.borrows if b.book.book_id == 2)
        self.assertTrue(pending.is_pending)
        self.assertTrue(active.is_currently_borrowed)
        # Borrow.book must be re-resolved by book_id, not title.
        self.assertEqual(active.book.book_id, 2)
        self.assertEqual(active.book.author, "Tolkien")

    def test_next_book_id_is_inferred_from_books_when_absent_in_json(self):
        handler = JsonHandler()
        legacy = {
            "name": "Legacy",
            "manager": {"kind": "manager", "first_name": "A", "last_name": "B",
                         "member_id": 10001, "password": 1234, "education": "Admin"},
            "books": [
                {"book_id": 5, "title": "X", "author": "Y", "pages": 10, "publication_year": 2000, "copies": 1},
                {"book_id": 12, "title": "Z", "author": "W", "pages": 20, "publication_year": 2010, "copies": 1},
            ],
            "students": [],
            "pending_students": [],
            "operators": [],
            "borrows": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "library.json")
            with open(path, "w") as f:
                json.dump(legacy, f)
            loaded = handler.load(path)
        self.assertEqual(loaded.next_book_id, 13)
        self.assertEqual(len(loaded.books), 2)

    def test_load_creates_default_when_file_missing(self):
        handler = JsonHandler()
        default = Library("Default", Manager("A", "B", 10001, 1234, "Admin"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "subdir", "library.json")
            loaded = handler.load(path, default=default)
            self.assertEqual(loaded.name, "Default")
            # The default must have been written to disk so subsequent loads find it.
            self.assertTrue(os.path.exists(path))

if __name__ == "__main__":
    unittest.main()
