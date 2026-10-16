import unittest
from library_system.models.book import Book
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.services.book_service import BookService


def _library() -> Library:
    return Library("Test", Manager("A", "B", 10001, 1234, "Admin"))


class BookServiceTests(unittest.TestCase):
    def test_add_book_assigns_sequential_ids_from_counter(self):
        lib = _library()
        service = BookService(lib)
        b1 = Book(0, "Title One", "Author", 100, 2000, 1)
        b2 = Book(0, "Title Two", "Author", 100, 2000, 1)
        self.assertTrue(service.add_book(b1))
        self.assertTrue(service.add_book(b2))
        self.assertEqual(b1.book_id, 1)
        self.assertEqual(b2.book_id, 2)
        self.assertEqual(lib.next_book_id, 3)

    def test_add_book_allows_duplicate_titles(self):
        lib = _library()
        service = BookService(lib)
        first = Book(0, "Same Title", "Author A", 100, 2000, 1)
        second = Book(0, "Same Title", "Author B", 200, 2010, 2)
        self.assertTrue(service.add_book(first))
        self.assertTrue(service.add_book(second))
        self.assertEqual(len(lib.books), 2)
        self.assertNotEqual(first.book_id, second.book_id)

    def test_add_book_rejects_explicit_duplicate_id(self):
        lib = _library()
        service = BookService(lib)
        self.assertTrue(service.add_book(Book(7, "A", "B", 100, 2000, 1)))
        self.assertFalse(service.add_book(Book(7, "C", "D", 100, 2000, 1)))

    def test_explicit_high_id_advances_counter_so_no_future_collision(self):
        lib = _library()
        service = BookService(lib)
        # Caller supplies an explicit id ahead of the current counter.
        self.assertTrue(service.add_book(Book(10, "A", "B", 100, 2000, 1)))
        self.assertEqual(lib.next_book_id, 11)
        # Subsequent auto-assigned book must not collide with id=10.
        auto = Book(0, "B", "C", 100, 2000, 1)
        self.assertTrue(service.add_book(auto))
        self.assertEqual(auto.book_id, 11)
        self.assertEqual(lib.next_book_id, 12)

    def test_find_by_id_returns_match(self):
        lib = _library()
        service = BookService(lib)
        service.add_book(Book(0, "A", "B", 100, 2000, 1))
        service.add_book(Book(0, "C", "D", 100, 2000, 1))
        self.assertIsNotNone(service.find_by_id(1))
        self.assertIsNone(service.find_by_id(99))

    def test_search_by_title_is_case_insensitive_and_substring(self):
        lib = _library()
        service = BookService(lib)
        service.add_book(Book(0, "The Hobbit", "Tolkien", 310, 1937, 1))
        results = service.search_by_title("HObb")
        self.assertEqual(len(results), 1)

if __name__ == "__main__":
    unittest.main()
