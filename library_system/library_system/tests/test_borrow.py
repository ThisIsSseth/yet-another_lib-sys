import unittest
from library_system.models.book import Book
from library_system.models.student import Student
from library_system.models.operator import Operator
from library_system.models.borrow import Borrow

class BorrowTests(unittest.TestCase):
    def test_approval_and_return_update_inventory(self):
        book = Book(1, "A", "B", 100, 2000, 1)
        student = Student("First", "Last", 12345, 1234, "Engineering")
        operator = Operator("Op", "One", 23456, 1234)
        borrow = Borrow(student, book)
        self.assertTrue(borrow.approve(operator))
        self.assertEqual(book.copies, 0)
        self.assertTrue(borrow.return_book(operator))
        self.assertEqual(book.copies, 1)

    def test_cannot_approve_without_available_copy(self):
        book = Book(1, "A", "B", 100, 2000, 0)
        student = Student("First", "Last", 12345, 1234, "Engineering")
        operator = Operator("Op", "One", 23456, 1234)
        borrow = Borrow(student, book)
        self.assertFalse(borrow.approve(operator))

    def test_cannot_approve_already_approved_request(self):
        book = Book(1, "A", "B", 100, 2000, 1)
        student = Student("First", "Last", 12345, 1234, "Engineering")
        operator = Operator("Op", "One", 23456, 1234)
        borrow = Borrow(student, book)
        self.assertTrue(borrow.approve(operator))
        # Second approval must not consume another copy.
        self.assertFalse(borrow.approve(operator))
        self.assertEqual(book.copies, 0)

    def test_cannot_return_a_pending_request(self):
        book = Book(1, "A", "B", 100, 2000, 1)
        student = Student("First", "Last", 12345, 1234, "Engineering")
        operator = Operator("Op", "One", 23456, 1234)
        borrow = Borrow(student, book)
        # Never approved, so return should fail and must not add a copy.
        self.assertFalse(borrow.return_book(operator))
        self.assertEqual(book.copies, 1)

if __name__ == "__main__":
    unittest.main()
