from dataclasses import dataclass, field
from .book import Book
from .student import Student
from .operator import Operator
from .manager import Manager
from .borrow import Borrow

@dataclass
class Library:
    name: str
    manager: Manager
    books: list[Book] = field(default_factory=list)
    students: dict[int, Student] = field(default_factory=dict)
    pending_students: dict[int, Student] = field(default_factory=dict)
    operators: dict[int, Operator] = field(default_factory=dict)
    borrows: list[Borrow] = field(default_factory=list)
