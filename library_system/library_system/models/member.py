from dataclasses import dataclass

@dataclass
class Member:
    first_name: str
    last_name: str
    member_id: int
    password: int

    ID_LENGTH = 5
    PASSWORD_LENGTH = 4

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def password_matches(self, password: int) -> bool:
        return self.password == password
