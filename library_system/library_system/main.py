from pathlib import Path
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.models.book import Book
from library_system.models.student import Student
from library_system.models.operator import Operator
from library_system.services.book_service import BookService
from library_system.storage.sqlite_handler import SqliteHandler
from library_system.ui.controller import Controller

# SQLite is the production storage. library.json is kept as a one-time
# migration source: if library.db does not yet exist but library.json does,
# the JSON data is imported into a fresh SQLite database on first run.
DATA_DIR = Path(__file__).parent / "data"
DB_FILE = DATA_DIR / "library.db"
LEGACY_JSON_FILE = DATA_DIR / "library.json"

def create_default_library() -> Library:
    manager = Manager("Default", "Manager", 10001, 1234, "Administration")
    library = Library("Central Library", manager)
    book_service = BookService(library)
    # book_id=0 lets BookService.add_book assign the next id from the Library counter.
    book_service.add_book(Book(0, "The Hobbit", "J. R. R. Tolkien", 310, 1937, 3))
    book_service.add_book(Book(0, "Pride and Prejudice", "Jane Austen", 432, 1813, 2))
    student = Student("Sample", "Student", 20001, 1234, "Computer Engineering")
    library.students[student.member_id] = student
    operator = Operator("Sample", "Operator", 30001, 1234)
    library.operators[operator.member_id] = operator
    return library

def main() -> None:
    storage = SqliteHandler(json_fallback_path=LEGACY_JSON_FILE)
    library = storage.load(DB_FILE, default=create_default_library())
    try:
        Controller(library).run()
    finally:
        storage.save(library, DB_FILE)

if __name__ == "__main__":
    main()
