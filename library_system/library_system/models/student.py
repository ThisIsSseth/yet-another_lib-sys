from dataclasses import dataclass, field
from datetime import date
from .member import Member

@dataclass
class Student(Member):
    major: str
    signup_date: date = field(default_factory=date.today)
    active: bool = True
