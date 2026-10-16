import unittest
from library_system.models.book import Book
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.models.student import Student
from library_system.models.operator import Operator
from library_system.services.book_service import BookService
from library_system.services.borrow_service import BorrowService


def _library_with_book_and_student() -> tuple[Library, Book, Student, Operator]:
    lib = Library("Test", Manager("A", "B", 10001, 1234, "Admin"))
    book = Book(0, "The Hobbit", "Tolkien", 310, 1937, 2)
    BookService(lib).add_book(book)
    student = Student("First", "Last", 20001, 1234, "Engineering")
    lib.students[student.member_id] = student
    operator = Operator("Op", "One", 30001, 1234)
    lib.operators[operator.member_id] = operator
    return lib, book, student, operator


class BorrowServiceTests(unittest.TestCase):
    def test_request_book_creates_pending_borrow(self):
        lib, book, student, _ = _library_with_book_and_student()
        service = BorrowService(lib)
        self.assertTrue(service.request_book(student, book))
        self.assertEqual(len(lib.borrows), 1)
        self.assertTrue(lib.borrows[0].is_pending)

    def test_request_book_rejects_inactive_student(self):
        lib, book, student, _ = _library_with_book_and_student()
        student.active = False
        service = BorrowService(lib)
        self.assertFalse(service.request_book(student, book))
        self.assertEqual(len(lib.borrows), 0)

    def test_request_book_rejects_duplicate_request(self):
        lib, book, student, _ = _library_with_book_and_student()
        service = BorrowService(lib)
        self.assertTrue(service.request_book(student, book))
        # Same student + same book_id while the first is pending must be rejected.
        self.assertFalse(service.request_book(student, book))
        self.assertEqual(len(lib.borrows), 1)

    def test_request_book_allows_same_title_different_id(self):
        lib, book, student, _ = _library_with_book_and_student()
        # Add a second book with the SAME title but a different book_id.
        second_book = Book(0, "The Hobbit", "Different Edition", 310, 1966, 1)
        BookService(lib).add_book(second_book)
        service = BorrowService(lib)
        self.assertTrue(service.request_book(student, book))
        self.assertTrue(service.request_book(student, second_book))
        self.assertEqual(len(lib.borrows), 2)

    def test_approve_then_receive_decrements_then_restocks_copies(self):
        lib, book, student, operator = _library_with_book_and_student()
        service = BorrowService(lib)
        service.request_book(student, book)
        self.assertTrue(service.approve(student.member_id, book.book_id, operator))
        self.assertEqual(book.copies, 1)
        self.assertTrue(service.receive_return(student.member_id, book.book_id, operator))
        self.assertEqual(book.copies, 2)

    def test_approve_unknown_book_id_is_safe(self):
        lib, book, student, operator = _library_with_book_and_student()
        service = BorrowService(lib)
        self.assertFalse(service.approve(student.member_id, 999999, operator))

if __name__ == "__main__":
    unittest.main()
