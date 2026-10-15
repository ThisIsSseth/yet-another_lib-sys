from library_system.models.book import Book

class View:
    def show_books(self, books: list[Book]) -> None:
        if not books:
            print("No results found.")
            return
        for book in books:
            print(book)

    def message(self, text: str) -> None:
        print(text)
