from dataclasses import dataclass
from .member import Member

@dataclass
class Manager(Member):
    education: str
