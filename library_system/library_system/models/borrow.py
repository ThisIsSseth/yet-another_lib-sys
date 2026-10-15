from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
from .book import Book
from .student import Student
from .operator import Operator

@dataclass
class Borrow:
    student: Student
    book: Book
    loan_period_days: int = 5
    giver_operator: Optional[Operator] = None
    receiver_operator: Optional[Operator] = None
    borrow_date: Optional[date] = None
    due_date: Optional[date] = None
    real_return_date: Optional[date] = None

    @property
    def is_pending(self) -> bool:
        return self.giver_operator is None and self.real_return_date is None

    @property
    def is_currently_borrowed(self) -> bool:
        return self.giver_operator is not None and self.real_return_date is None

    def approve(self, operator: Operator) -> bool:
        if not self.is_pending or not self.book.take_copy():
            return False
        self.giver_operator = operator
        self.borrow_date = date.today()
        self.due_date = self.borrow_date + timedelta(days=self.loan_period_days)
        return True

    def return_book(self, operator: Operator) -> bool:
        if not self.is_currently_borrowed:
            return False
        self.real_return_date = date.today()
        self.receiver_operator = operator
        self.book.add_copy()
        return True
