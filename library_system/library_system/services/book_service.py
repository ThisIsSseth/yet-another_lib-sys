from library_system.models.book import Book
from library_system.models.library import Library

class BookService:
    def __init__(self, library: Library):
        self._library = library

    def find_by_id(self, book_id: int) -> Book | None:
        return next((b for b in self._library.books if b.book_id == book_id), None)

    def find_by_title(self, title: str) -> Book | None:
        """Display helper — returns the first book whose title matches.

        Title is no longer a unique identifier; prefer find_by_id for state-changing operations.
        """
        normalized = title.strip().casefold()
        if not normalized:
            return None
        return next((b for b in self._library.books
                     if b.title.strip().casefold() == normalized), None)

    def list_all(self) -> list[Book]:
        return list(self._library.books)

    def search_by_title(self, term: str) -> list[Book]:
        term = term.strip().casefold()
        return [b for b in self._library.books if term and term in b.title.casefold()]

    def search_by_author(self, term: str) -> list[Book]:
        term = term.strip().casefold()
        return [b for b in self._library.books if term and term in b.author.casefold()]

    def find_by_year(self, year: int) -> list[Book]:
        return [b for b in self._library.books if b.publication_year == year]

    def is_available(self, book_id: int) -> bool:
        book = self.find_by_id(book_id)
        return book is not None and book.copies > 0

    def add_book(self, book: Book) -> bool:
        """Append a book. Assigns the next book_id when the caller passes 0,
        and allows duplicate titles (books are now identified by book_id).

        When the caller supplies an explicit book_id, the counter is advanced past it
        so a subsequent auto-assigned book cannot collide.
        """
        if book.book_id == 0:
            book.book_id = self._library.next_book_id
            self._library.next_book_id += 1
        elif self.find_by_id(book.book_id) is not None:
            return False
        elif book.book_id >= self._library.next_book_id:
            self._library.next_book_id = book.book_id + 1
        self._library.books.append(book)
        return True
