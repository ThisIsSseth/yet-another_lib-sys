from library_system.models.library import Library
from library_system.models.student import Student

class StudentService:
    def __init__(self, library: Library):
        self._library = library

    def get(self, student_id: int) -> Student | None:
        return self._library.students.get(student_id)

    def add_pending_signup(self, student: Student) -> bool:
        if student.member_id in self._library.students or student.member_id in self._library.pending_students:
            return False
        self._library.pending_students[student.member_id] = student
        return True

    def approve_signup(self, student_id: int) -> bool:
        student = self._library.pending_students.pop(student_id, None)
        if student is None or student_id in self._library.students:
            return False
        self._library.students[student_id] = student
        return True

    def set_active(self, student_id: int, active: bool) -> bool:
        student = self.get(student_id)
        if student is None:
            return False
        student.active = active
        return True
