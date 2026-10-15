from datetime import date
from library_system.models.library import Library
from library_system.models.borrow import Borrow
from library_system.models.student import Student
from library_system.models.book import Book
from library_system.models.operator import Operator

class BorrowService:
    def __init__(self, library: Library):
        self._library = library

    def request_book(self, student: Student, book: Book) -> bool:
        if not student.active or book.copies < 1:
            return False
        if any(b.student.member_id == student.member_id and b.book.title.casefold() == book.title.casefold()
               and (b.is_pending or b.is_currently_borrowed) for b in self._library.borrows):
            return False
        self._library.borrows.append(Borrow(student=student, book=book))
        return True

    def find_request(self, student_id: int, title: str) -> Borrow | None:
        key = title.strip().casefold()
        return next((b for b in self._library.borrows
                     if b.student.member_id == student_id
                     and b.book.title.strip().casefold() == key
                     and (b.is_pending or b.is_currently_borrowed)), None)

    def approve(self, student_id: int, title: str, operator: Operator) -> bool:
        borrow = self.find_request(student_id, title)
        return borrow.approve(operator) if borrow else False

    def receive_return(self, student_id: int, title: str, operator: Operator) -> bool:
        borrow = self.find_request(student_id, title)
        return borrow.return_book(operator) if borrow else False

    def history_for_student(self, student_id: int) -> list[Borrow]:
        return [b for b in self._library.borrows if b.student.member_id == student_id]

    def overdue_count_for_student(self, student_id: int) -> int:
        today = date.today()
        return sum(1 for b in self.history_for_student(student_id)
                   if b.due_date is not None and
                   ((b.real_return_date is not None and b.real_return_date > b.due_date)
                    or (b.real_return_date is None and b.due_date < today)))

    def currently_borrowed_count(self) -> int:
        return sum(b.is_currently_borrowed for b in self._library.borrows)
