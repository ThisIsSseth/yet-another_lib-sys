from library_system.models.library import Library
from library_system.models.student import Student
from library_system.models.operator import Operator
from library_system.models.manager import Manager
from library_system.services.student_service import StudentService

class AuthenticationService:
    def __init__(self, library: Library):
        self._library = library
        self._students = StudentService(library)

    def student_signup(self, student: Student) -> bool:
        return self._students.add_pending_signup(student)

    def student_login(self, student_id: int, password: int) -> Student | None:
        student = self._library.students.get(student_id)
        return student if student and student.password_matches(password) else None

    def operator_login(self, operator_id: int, password: int) -> Operator | None:
        operator = self._library.operators.get(operator_id)
        return operator if operator and operator.password_matches(password) else None

    def manager_login(self, manager_id: int, password: int) -> Manager | None:
        manager = self._library.manager
        return manager if manager.member_id == manager_id and manager.password_matches(password) else None
