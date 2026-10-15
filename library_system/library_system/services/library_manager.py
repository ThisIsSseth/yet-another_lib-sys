from library_system.models.library import Library
from library_system.models.book import Book
from library_system.models.student import Student
from library_system.models.operator import Operator
from library_system.services.book_service import BookService
from library_system.services.student_service import StudentService
from library_system.services.borrow_service import BorrowService

class LibraryManager:
    """Facade preserving the role of the Java LibraryManager."""
    def __init__(self, library: Library):
        self.library = library
        self.books = BookService(library)
        self.students = StudentService(library)
        self.borrows = BorrowService(library)

    def request_book(self, student_id: int, title: str) -> bool:
        student = self.students.get(student_id)
        book = self.books.find_by_title(title)
        return bool(student and book and self.borrows.request_book(student, book))

    def approve_borrow_request(self, operator: Operator, student_id: int, title: str) -> bool:
        return self.borrows.approve(student_id, title, operator)

    def receive_returned_book(self, operator: Operator, student_id: int, title: str) -> bool:
        return self.borrows.receive_return(student_id, title, operator)

    def add_operator(self, operator: Operator) -> bool:
        if operator.member_id in self.library.operators:
            return False
        self.library.operators[operator.member_id] = operator
        return True

    def student_stats(self, student_id: int) -> str:
        student = self.students.get(student_id)
        if student is None:
            return "Student not found."
        history = self.borrows.history_for_student(student_id)
        active = sum(b.is_currently_borrowed for b in history)
        overdue = self.borrows.overdue_count_for_student(student_id)
        return (f"Stats for {student.full_name} (ID={student_id}):\n"
                f"- Total borrows: {len(history)}\n"
                f"- Currently not returned: {active}\n"
                f"- Overdue returns: {overdue}")
