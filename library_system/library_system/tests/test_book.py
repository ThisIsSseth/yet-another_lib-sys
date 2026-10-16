import unittest
from library_system.models.book import Book

class BookTests(unittest.TestCase):
    def test_take_copy_decrements_when_available(self):
        book = Book(1, "A", "B", 100, 2000, 1)
        self.assertTrue(book.take_copy())
        self.assertEqual(book.copies, 0)

    def test_take_copy_fails_when_empty(self):
        book = Book(1, "A", "B", 100, 2000, 0)
        self.assertFalse(book.take_copy())
        self.assertEqual(book.copies, 0)

    def test_post_init_rejects_empty_title(self):
        with self.assertRaises(ValueError):
            Book(1, "   ", "B", 100, 2000, 1)

    def test_post_init_rejects_nonpositive_pages(self):
        with self.assertRaises(ValueError):
            Book(1, "A", "B", 0, 2000, 1)

    def test_post_init_rejects_negative_copies(self):
        with self.assertRaises(ValueError):
            Book(1, "A", "B", 100, 2000, -1)

if __name__ == "__main__":
    unittest.main()
