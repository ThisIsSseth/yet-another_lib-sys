from pathlib import Path
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.models.book import Book
from library_system.models.student import Student
from library_system.models.operator import Operator
from library_system.storage.json_handler import JsonHandler
from library_system.ui.controller import Controller

DATA_FILE = Path(__file__).parent / "data" / "library.json"

def create_default_library() -> Library:
    manager = Manager("Default", "Manager", 10001, 1234, "Administration")
    library = Library("Central Library", manager)
    library.books.extend([
        Book("The Hobbit", "J. R. R. Tolkien", 310, 1937, 3),
        Book("Pride and Prejudice", "Jane Austen", 432, 1813, 2),
    ])
    student = Student("Sample", "Student", 20001, 1234, "Computer Engineering")
    library.students[student.member_id] = student
    operator = Operator("Sample", "Operator", 30001, 1234)
    library.operators[operator.member_id] = operator
    return library

def main() -> None:
    storage = JsonHandler()
    library = storage.load(DATA_FILE, default=create_default_library())
    try:
        Controller(library).run()
    finally:
        storage.save(library, DATA_FILE)

if __name__ == "__main__":
    main()
