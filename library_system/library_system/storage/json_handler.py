import json
from dataclasses import fields
from datetime import date
from pathlib import Path
from typing import Any
from library_system.models.book import Book
from library_system.models.borrow import Borrow
from library_system.models.library import Library
from library_system.models.manager import Manager
from library_system.models.operator import Operator
from library_system.models.student import Student

class JsonHandler:
    """Explicit conversion between domain objects and JSON-compatible data."""
    def save(self, library: Library, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("w", encoding="utf-8") as file:
            json.dump(self._library_to_dict(library), file, indent=2)

    def load(self, path: str | Path, default: Library | None = None) -> Library:
        file_path = Path(path)
        if not file_path.exists():
            if default is None:
                raise FileNotFoundError(file_path)
            self.save(default, file_path)
            return default
        with file_path.open(encoding="utf-8") as file:
            raw = json.load(file)
        return self._library_from_dict(raw)

    def _library_to_dict(self, lib: Library) -> dict[str, Any]:
        return {
            "name": lib.name,
            "manager": self._member_to_dict(lib.manager, "manager"),
            "books": [self._book_to_dict(b) for b in lib.books],
            "students": [self._member_to_dict(s, "student") for s in lib.students.values()],
            "pending_students": [self._member_to_dict(s, "student") for s in lib.pending_students.values()],
            "operators": [self._member_to_dict(o, "operator") for o in lib.operators.values()],
            "borrows": [{
                "student_id": b.student.member_id, "book_title": b.book.title,
                "loan_period_days": b.loan_period_days,
                "giver_operator_id": b.giver_operator.member_id if b.giver_operator else None,
                "receiver_operator_id": b.receiver_operator.member_id if b.receiver_operator else None,
                "borrow_date": b.borrow_date.isoformat() if b.borrow_date else None,
                "due_date": b.due_date.isoformat() if b.due_date else None,
                "real_return_date": b.real_return_date.isoformat() if b.real_return_date else None,
            } for b in lib.borrows]
        }

    def _member_to_dict(self, member, kind: str) -> dict[str, Any]:
        result = {"kind": kind, "first_name": member.first_name, "last_name": member.last_name,
                  "member_id": member.member_id, "password": member.password}
        if isinstance(member, Student):
            result.update(major=member.major, signup_date=member.signup_date.isoformat(), active=member.active)
        if isinstance(member, Manager):
            result["education"] = member.education
        return result

    def _book_to_dict(self, book: Book) -> dict[str, Any]:
        return {"title": book.title, "author": book.author, "pages": book.pages,
                "publication_year": book.publication_year, "copies": book.copies}

    def _library_from_dict(self, raw: dict[str, Any]) -> Library:
        manager_data = raw["manager"]
        manager = Manager(manager_data["first_name"], manager_data["last_name"],
                          manager_data["member_id"], manager_data["password"], manager_data["education"])
        lib = Library(raw["name"], manager)
        lib.books = [Book(**item) for item in raw.get("books", [])]
        for key, target in (("students", lib.students), ("pending_students", lib.pending_students)):
            for item in raw.get(key, []):
                student = Student(item["first_name"], item["last_name"], item["member_id"], item["password"],
                                  item["major"], date.fromisoformat(item["signup_date"]), item.get("active", True))
                target[student.member_id] = student
        for item in raw.get("operators", []):
            operator = Operator(item["first_name"], item["last_name"], item["member_id"], item["password"])
            lib.operators[operator.member_id] = operator
        for item in raw.get("borrows", []):
            student = lib.students.get(item["student_id"])
            book = next((b for b in lib.books if b.title == item["book_title"]), None)
            if student is None or book is None:
                continue
            borrow = Borrow(student, book, item.get("loan_period_days", 5))
            giver_id = item.get("giver_operator_id")
            receiver_id = item.get("receiver_operator_id")
            borrow.giver_operator = lib.operators.get(giver_id)
            borrow.receiver_operator = lib.operators.get(receiver_id)
            borrow.borrow_date = date.fromisoformat(item["borrow_date"]) if item.get("borrow_date") else None
            borrow.due_date = date.fromisoformat(item["due_date"]) if item.get("due_date") else None
            borrow.real_return_date = date.fromisoformat(item["real_return_date"]) if item.get("real_return_date") else None
            lib.borrows.append(borrow)
        return lib
