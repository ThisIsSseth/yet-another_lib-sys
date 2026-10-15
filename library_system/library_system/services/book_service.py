from library_system.models.book import Book
from library_system.models.library import Library

class BookService:
    def __init__(self, library: Library):
        self._library = library

    def find_by_title(self, title: str) -> Book | None:
        normalized = title.strip().casefold()
        if not normalized:
            return None
        return next((b for b in self._library.books
                     if b.title.strip().casefold() == normalized), None)

    def search_by_title(self, term: str) -> list[Book]:
        term = term.strip().casefold()
        return [b for b in self._library.books if term and term in b.title.casefold()]

    def search_by_author(self, term: str) -> list[Book]:
        term = term.strip().casefold()
        return [b for b in self._library.books if term and term in b.author.casefold()]

    def find_by_year(self, year: int) -> list[Book]:
        return [b for b in self._library.books if b.publication_year == year]

    def is_available(self, title: str) -> bool:
        book = self.find_by_title(title)
        return book is not None and book.copies > 0

    def add_book(self, book: Book) -> bool:
        if self.find_by_title(book.title) is not None:
            return False
        self._library.books.append(book)
        return True
