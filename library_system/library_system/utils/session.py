from dataclasses import dataclass
from library_system.models.student import Student
from library_system.models.operator import Operator
from library_system.models.manager import Manager
from library_system.utils.login_status import LoginStatus

@dataclass
class Session:
    status: LoginStatus = LoginStatus.LOGGED_OUT
    student: Student | None = None
    operator: Operator | None = None
    manager: Manager | None = None

    def logout(self) -> None:
        self.status = LoginStatus.LOGGED_OUT
        self.student = self.operator = self.manager = None

    def set_student(self, student: Student) -> None:
        self.logout()
        self.student, self.status = student, LoginStatus.STUDENT

    def set_operator(self, operator: Operator) -> None:
        self.logout()
        self.operator, self.status = operator, LoginStatus.OPERATOR

    def set_manager(self, manager: Manager) -> None:
        self.logout()
        self.manager, self.status = manager, LoginStatus.MANAGER

    def set_guest(self) -> None:
        self.logout()
        self.status = LoginStatus.GUEST
