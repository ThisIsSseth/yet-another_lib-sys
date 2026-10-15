import unittest
from library_system.models.book import Book

class BookTests(unittest.TestCase):
    def test_take_copy_decrements_when_available(self):
        book = Book("A", "B", 100, 2000, 1)
        self.assertTrue(book.take_copy())
        self.assertEqual(book.copies, 0)

    def test_take_copy_fails_when_empty(self):
        book = Book("A", "B", 100, 2000, 0)
        self.assertFalse(book.take_copy())
        self.assertEqual(book.copies, 0)

if __name__ == "__main__":
    unittest.main()
