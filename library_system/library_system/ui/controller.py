from library_system.models.library import Library
from library_system.services.library_manager import LibraryManager
from library_system.services.authentication_service import AuthenticationService
from library_system.utils.session import Session
from library_system.utils.login_status import LoginStatus
from library_system.ui.input_reader import InputReader
from library_system.ui.view import View

class Controller:
    """Coordinates CLI input, services, and session state."""
    def __init__(self, library: Library):
        self.library = library
        self.manager = LibraryManager(library)
        self.auth = AuthenticationService(library)
        self.session = Session()
        self.input = InputReader()
        self.view = View()

    def run(self) -> None:
        while True:
            status = self.session.status
            if status == LoginStatus.LOGGED_OUT:
                print("\n1. Student login  2. Operator login  3. Manager login  4. Guest  0. Exit")
                choice = self.input.read_int("> ", 0, 4)
                if choice == 0:
                    return
                if choice == 1:
                    self._student_login()
                elif choice == 2:
                    self._operator_login()
                elif choice == 3:
                    self._manager_login()
                else:
                    self.session.set_guest()
            elif status == LoginStatus.STUDENT:
                print("\n1. Search books  2. Request book  0. Logout")
                choice = self.input.read_int("> ", 0, 2)
                if choice == 0:
                    self.session.logout()
                elif choice == 1:
                    self._search()
                else:
                    title = self.input.read_text("Book title: ")
                    ok = self.manager.request_book(self.session.student.member_id, title)
                    self.view.message("Request recorded." if ok else "Request failed (check availability, account status, or existing request).")
            elif status == LoginStatus.OPERATOR:
                print("\n1. Search books  2. Add book  3. Approve request  4. Receive return  0. Logout")
                choice = self.input.read_int("> ", 0, 4)
                if choice == 0:
                    self.session.logout()
                elif choice == 1:
                    self._search()
                elif choice == 2:
                    self._add_book()
                elif choice == 3:
                    sid = self.input.read_int("Student ID: ", 10000, 99999)
                    title = self.input.read_text("Book title: ")
                    ok = self.manager.approve_borrow_request(self.session.operator, sid, title)
                    self.view.message("Request approved." if ok else "Could not approve request.")
                else:
                    sid = self.input.read_int("Student ID: ", 10000, 99999)
                    title = self.input.read_text("Book title: ")
                    ok = self.manager.receive_returned_book(self.session.operator, sid, title)
                    self.view.message("Book returned." if ok else "Could not record return.")
            elif status == LoginStatus.MANAGER:
                print("\n1. Approve student signup  2. Add operator  0. Logout")
                choice = self.input.read_int("> ", 0, 2)
                if choice == 0:
                    self.session.logout()
                elif choice == 1:
                    sid = self.input.read_int("Pending student ID: ", 10000, 99999)
                    ok = self.manager.students.approve_signup(sid)
                    self.view.message("Student approved." if ok else "Pending student not found.")
                else:
                    self._add_operator()
            elif status == LoginStatus.GUEST:
                print("\n1. Search books  0. Logout")
                choice = self.input.read_int("> ", 0, 1)
                if choice == 0:
                    self.session.logout()
                else:
                    self._search()

    def _student_login(self):
        sid = self.input.read_int("Student ID: ", 10000, 99999)
        pw = self.input.read_int("Password: ", 1000, 9999)
        student = self.auth.student_login(sid, pw)
        if student:
            self.session.set_student(student)
        else:
            self.view.message("Login failed.")

    def _operator_login(self):
        sid = self.input.read_int("Operator ID: ", 10000, 99999)
        pw = self.input.read_int("Password: ", 1000, 9999)
        operator = self.auth.operator_login(sid, pw)
        if operator:
            self.session.set_operator(operator)
        else:
            self.view.message("Login failed.")

    def _manager_login(self):
        sid = self.input.read_int("Manager ID: ", 10000, 99999)
        pw = self.input.read_int("Password: ", 1000, 9999)
        manager = self.auth.manager_login(sid, pw)
        if manager:
            self.session.set_manager(manager)
        else:
            self.view.message("Login failed.")

    def _search(self):
        print("Search by: 1. Title  2. Author  3. Publication year")
        choice = self.input.read_int("> ", 1, 3)
        if choice == 1:
            results = self.manager.books.search_by_title(self.input.read_text("Title contains: "))
        elif choice == 2:
            results = self.manager.books.search_by_author(self.input.read_text("Author contains: "))
        else:
            year = self.input.read_int("Year: ", 0, 3000)
            results = self.manager.books.find_by_year(year)
        self.view.show_books(results)

    def _add_book(self):
        title = self.input.read_text("Title: ")
        author = self.input.read_text("Author: ")
        pages = self.input.read_int("Pages: ", 1, 5000)
        year = self.input.read_int("Publication year: ", 0, 3000)
        copies = self.input.read_int("Copies: ", 0, 1000)
        from library_system.models.book import Book
        ok = self.manager.books.add_book(Book(title, author, pages, year, copies))
        self.view.message("Book added." if ok else "A book with that title already exists.")

    def _add_operator(self):
        from library_system.models.operator import Operator
        first = self.input.read_text("First name: ")
        last = self.input.read_text("Last name: ")
        operator_id = self.input.read_int("New operator ID: ", 10000, 99999)
        password = self.input.read_int("Temporary password: ", 1000, 9999)
        ok = self.manager.add_operator(Operator(first, last, operator_id, password))
        self.view.message("Operator added." if ok else "That operator ID already exists.")
